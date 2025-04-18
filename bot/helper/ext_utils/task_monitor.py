#!/usr/bin/env python3
import asyncio
import time
import gc
from asyncio import create_task
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Deque

try:
    import psutil
except ImportError:
    import pip

    pip.main(["install", "psutil"])
    import psutil

from bot import (
    LOGGER,
    task_dict,
    task_dict_lock,
    queue_dict_lock,
    queued_dl,
    queued_up,
    non_queued_dl,
    non_queued_up,
)
from bot.helper.ext_utils.status_utils import (
    MirrorStatus,
    speed_string_to_bytes,
)
from bot.helper.telegram_helper.message_utils import send_message, auto_delete_message

# Constants for monitoring
CHECK_INTERVAL = 60  # Check every 60 seconds
SPEED_THRESHOLD = 50 * 1024  # 50 KB/s in bytes
CONSECUTIVE_CHECKS = 3  # Number of consecutive checks for confirmation
ELAPSED_TIME_THRESHOLD = 3600  # 1 hour in seconds
LONG_ETA_THRESHOLD = 86400  # 24 hours in seconds
WAIT_TIME_BEFORE_CANCEL = 600  # 10 minutes in seconds
LONG_COMPLETION_THRESHOLD = 14400  # 4 hours in seconds
CPU_HIGH_THRESHOLD = 90  # 90% CPU usage
CPU_LOW_THRESHOLD = 40  # 40% CPU usage
MEMORY_HIGH_THRESHOLD = 75  # 75% memory usage
MEMORY_LOW_THRESHOLD = 60  # 60% memory usage

# Store monitoring data
task_speeds: Dict[str, Deque[int]] = defaultdict(
    lambda: deque(maxlen=CONSECUTIVE_CHECKS)
)
task_warnings: Dict[str, Dict] = {}
cpu_usage_history: Deque[float] = deque(maxlen=CONSECUTIVE_CHECKS)
memory_usage_history: Deque[float] = deque(maxlen=CONSECUTIVE_CHECKS)
queued_by_monitor: Set[int] = set()  # Store tasks queued by the monitor
cpu_intensive_tasks: List[Tuple[int, str]] = []  # [(mid, task_type), ...]
memory_intensive_tasks: List[Tuple[int, str]] = []  # [(mid, task_type), ...]


async def get_task_speed(task) -> int:
    """Get the current download speed of a task in bytes per second."""
    try:
        if not hasattr(task, "speed") or not callable(task.speed):
            return 0

        speed = task.speed()
        if isinstance(speed, str):
            # Convert string speed (like "1.5 MB/s") to bytes
            return speed_string_to_bytes(speed)
        return speed
    except Exception as e:
        LOGGER.debug(f"Error getting task speed: {e}")
        return 0


async def get_task_eta(task) -> int:
    """Get the estimated time remaining for a task in seconds."""
    try:
        if not hasattr(task, "eta") or not callable(task.eta):
            return float("inf")

        eta = task.eta()
        if isinstance(eta, str):
            if eta == "-" or "∞" in eta:
                return float("inf")  # Infinite ETA
            # Try to convert readable time to seconds
            try:
                # Parse time string like "2h 3m 4s" to seconds
                parts = eta.split()
                seconds = 0
                for part in parts:
                    if "h" in part:
                        seconds += int(part.replace("h", "")) * 3600
                    elif "m" in part:
                        seconds += int(part.replace("m", "")) * 60
                    elif "s" in part:
                        seconds += int(part.replace("s", ""))
                return seconds
            except Exception:
                # If parsing fails, return infinite ETA
                return float("inf")
        return eta
    except Exception as e:
        LOGGER.debug(f"Error getting task ETA: {e}")
        return float("inf")  # Return infinite ETA on error


async def estimate_completion_time(task) -> int:
    """Estimate completion time based on file size and current speed."""
    try:
        # Get processed bytes and total size
        if hasattr(task, "processed_bytes") and callable(task.processed_bytes):
            processed_str = task.processed_bytes()
            if isinstance(processed_str, str):
                processed = speed_string_to_bytes(processed_str)
            else:
                processed = processed_str
        else:
            processed = 0

        if hasattr(task, "size") and callable(task.size):
            size_str = task.size()
            if isinstance(size_str, str):
                size = speed_string_to_bytes(size_str)
            else:
                size = size_str
        else:
            size = 0

        # Get current speed
        speed = await get_task_speed(task)

        if speed <= 0 or size <= 0 or processed >= size:
            return float("inf")

        # Calculate remaining time
        remaining_bytes = size - processed
        eta_seconds = remaining_bytes / speed if speed > 0 else float("inf")

        return eta_seconds
    except Exception as e:
        LOGGER.debug(f"Error estimating completion time: {e}")
        return float("inf")


async def get_task_elapsed_time(task) -> int:
    """Get the elapsed time for a task in seconds."""
    try:
        if not hasattr(task, "listener"):
            return 0
        if not hasattr(task.listener, "message"):
            return 0
        if not hasattr(task.listener.message, "date"):
            return 0

        return int(time.time() - task.listener.message.date.timestamp())
    except Exception as e:
        LOGGER.debug(f"Error getting task elapsed time: {e}")
        return 0


async def is_task_slow(task, gid: str) -> bool:
    """Check if a task's download speed is consistently below threshold."""
    speed = await get_task_speed(task)
    task_speeds[gid].append(speed)

    # Check if we have enough data points and all are below threshold
    if len(task_speeds[gid]) >= CONSECUTIVE_CHECKS and all(
        s <= SPEED_THRESHOLD for s in task_speeds[gid]
    ):
        return True
    return False


async def should_cancel_task(task, gid: str) -> Tuple[bool, str]:
    """Determine if a task should be cancelled based on monitoring criteria."""
    try:
        if not hasattr(task, "status") or not callable(task.status):
            return False, ""

        status = (
            await task.status()
            if asyncio.iscoroutinefunction(task.status)
            else task.status()
        )

        # Only monitor download tasks
        if status not in [MirrorStatus.STATUS_DOWNLOAD, MirrorStatus.STATUS_QUEUEDL]:
            return False, ""
    except Exception as e:
        LOGGER.debug(f"Error checking task status: {e}")
        return False, ""

    elapsed_time = await get_task_elapsed_time(task)
    eta = await get_task_eta(task)
    is_slow = await is_task_slow(task, gid)

    # Get user tag for notifications
    user_tag = (
        f"@{task.listener.user.username}"
        if hasattr(task.listener.user, "username") and task.listener.user.username
        else f"<a href='tg://user?id={task.listener.user_id}'>{task.listener.user_id}</a>"
    )

    # Case 1: Task estimation > 24h or no estimation && elapsed > 1h
    if (
        eta == float("inf") or eta > LONG_ETA_THRESHOLD
    ) and elapsed_time > ELAPSED_TIME_THRESHOLD:
        if gid not in task_warnings:
            task_warnings[gid] = {
                "warning_sent": False,
                "warning_time": 0,
                "reason": f"Long estimated completion time or no progress. {user_tag} please cancel this task if it's stuck.",
                "case": 1,
            }

        if not task_warnings[gid]["warning_sent"]:
            task_warnings[gid]["warning_sent"] = True
            task_warnings[gid]["warning_time"] = time.time()
            return False, task_warnings[gid]["reason"]

        # Check if 10 minutes have passed since warning
        if time.time() - task_warnings[gid]["warning_time"] > WAIT_TIME_BEFORE_CANCEL:
            return (
                True,
                f"Task was warned 10 minutes ago but not cancelled manually. {task_warnings[gid]['reason']}",
            )

    # Case 2: Slow download + long ETA + elapsed > 1h
    if (
        is_slow
        and (eta == float("inf") or eta > LONG_ETA_THRESHOLD)
        and elapsed_time > ELAPSED_TIME_THRESHOLD
    ):
        return (
            True,
            f"Slow download speed (≤50KB/s) with long estimated completion time. {user_tag}",
        )

    # Case 3: Slow download + estimated completion > 4h
    if is_slow:
        estimated_time = await estimate_completion_time(task)
        if estimated_time > LONG_COMPLETION_THRESHOLD:  # 4 hours
            return (
                True,
                f"Slow download speed (≤50KB/s) with estimated completion time over 4 hours. {user_tag}",
            )

    return False, ""


async def should_queue_task(task_type: str) -> Tuple[bool, str]:
    """Determine if a task should be queued based on system resource usage."""
    # Check CPU usage
    if task_type == "cpu" and all(
        usage >= CPU_HIGH_THRESHOLD for usage in cpu_usage_history
    ):
        return True, f"High CPU usage ({cpu_usage_history[-1]}%) detected"

    # Check memory usage
    if task_type == "memory" and all(
        usage >= MEMORY_HIGH_THRESHOLD for usage in memory_usage_history
    ):
        return True, f"High memory usage ({memory_usage_history[-1]}%) detected"

    return False, ""


async def can_resume_queued_tasks() -> Tuple[bool, str]:
    """Check if queued tasks can be resumed based on system resources."""
    # Check CPU usage for resuming CPU-intensive tasks
    if all(usage <= CPU_LOW_THRESHOLD for usage in cpu_usage_history):
        return True, "cpu"

    # Check memory usage for resuming memory-intensive tasks
    if all(usage <= MEMORY_LOW_THRESHOLD for usage in memory_usage_history):
        return True, "memory"

    return False, ""


async def identify_resource_intensive_tasks():
    """Identify CPU and memory intensive tasks."""
    global cpu_intensive_tasks, memory_intensive_tasks

    # Reset lists
    cpu_intensive_tasks = []
    memory_intensive_tasks = []

    async with task_dict_lock:
        for mid, task in task_dict.items():
            # Skip already queued tasks
            if mid in queued_by_monitor:
                continue

            try:
                # Skip tasks that are already being cancelled
                if (
                    hasattr(task, "listener")
                    and hasattr(task.listener, "is_cancelled")
                    and task.listener.is_cancelled
                ):
                    continue

                # Check if task has status method
                if not hasattr(task, "status") or not callable(task.status):
                    continue

                # Identify CPU-intensive tasks (FFmpeg, archive/extract operations)
                status = (
                    await task.status()
                    if asyncio.iscoroutinefunction(task.status)
                    else task.status()
                )

                if status in [MirrorStatus.STATUS_FFMPEG, MirrorStatus.STATUS_CONVERT]:
                    cpu_intensive_tasks.append((mid, "cpu"))
                elif status in [
                    MirrorStatus.STATUS_ARCHIVE,
                    MirrorStatus.STATUS_EXTRACT,
                ]:
                    cpu_intensive_tasks.append((mid, "cpu"))

                # Identify memory-intensive tasks (large downloads, uploads)
                if status in [MirrorStatus.STATUS_DOWNLOAD, MirrorStatus.STATUS_UPLOAD]:
                    # Check if task has size method
                    if not hasattr(task, "size") or not callable(task.size):
                        continue

                    try:
                        # Check if task is handling large files (>1GB)
                        size_str = task.size()
                        size = (
                            speed_string_to_bytes(size_str)
                            if isinstance(size_str, str)
                            else size_str
                        )
                        if size > 1024 * 1024 * 1024:  # 1GB
                            memory_intensive_tasks.append((mid, "memory"))
                    except Exception as e:
                        LOGGER.debug(f"Error checking task size: {e}")
            except Exception as e:
                LOGGER.debug(f"Error identifying resource intensive task {mid}: {e}")


async def queue_task(mid: int, reason: str):
    """Queue a task due to resource constraints."""
    try:
        async with task_dict_lock:
            if mid not in task_dict:
                return

            task = task_dict[mid]

            # Check if task has listener attribute
            if not hasattr(task, "listener"):
                LOGGER.warning(
                    f"Task {mid} doesn't have listener attribute, can't queue"
                )
                return

            listener = task.listener

            # Check if task is already cancelled
            if hasattr(listener, "is_cancelled") and listener.is_cancelled:
                return

            # Mark as queued by monitor
            queued_by_monitor.add(mid)

            # Add to appropriate queue
            async with queue_dict_lock:
                if mid in non_queued_dl:
                    non_queued_dl.remove(mid)
                    queued_dl[mid] = asyncio.Event()
                    LOGGER.info(f"Queued download task {listener.name} due to {reason}")
                elif mid in non_queued_up:
                    non_queued_up.remove(mid)
                    queued_up[mid] = asyncio.Event()
                    LOGGER.info(f"Queued upload task {listener.name} due to {reason}")
                else:
                    # Task is not in any queue, can't queue it
                    queued_by_monitor.discard(mid)
                    return

            # Notify user
            if hasattr(listener, "message"):
                # Get user tag for notifications
                user_tag = (
                    f"@{listener.user.username}"
                    if hasattr(listener.user, "username") and listener.user.username
                    else f"<a href='tg://user?id={listener.user_id}'>{listener.user_id}</a>"
                )

                queue_msg = await send_message(
                    listener.message,
                    f"⚠️ <b>Task Queued</b> ⚠️\n\n"
                    f"<b>Name:</b> <code>{listener.name}</code>\n"
                    f"<b>Reason:</b> {reason}\n\n"
                    f"Task will resume automatically when system resources are available.\n\n"
                    f"{user_tag} your task has been queued!",
                )

                # Auto-delete queue message after 5 minutes
                if not isinstance(queue_msg, str):
                    create_task(auto_delete_message(queue_msg, time=300))
    except Exception as e:
        LOGGER.error(f"Error queuing task {mid}: {e}")


async def resume_queued_tasks(resource_type: str):
    """Resume tasks that were queued due to resource constraints."""
    try:
        tasks_to_resume = []

        # Identify tasks to resume based on resource type
        if resource_type == "cpu":
            for mid, task_type in cpu_intensive_tasks:
                if mid in queued_by_monitor and task_type == "cpu":
                    tasks_to_resume.append(mid)
        elif resource_type == "memory":
            for mid, task_type in memory_intensive_tasks:
                if mid in queued_by_monitor and task_type == "memory":
                    tasks_to_resume.append(mid)

        if not tasks_to_resume:
            return

        # Resume identified tasks
        async with queue_dict_lock:
            for mid in tasks_to_resume:
                try:
                    if mid in queued_dl:
                        queued_dl[mid].set()
                        LOGGER.info(f"Resuming queued download task {mid}")
                    elif mid in queued_up:
                        queued_up[mid].set()
                        LOGGER.info(f"Resuming queued upload task {mid}")
                    else:
                        LOGGER.warning(
                            f"Task {mid} not found in any queue, can't resume"
                        )
                        continue

                    # Remove from queued_by_monitor
                    queued_by_monitor.discard(mid)
                except Exception as e:
                    LOGGER.error(f"Error resuming task {mid}: {e}")
    except Exception as e:
        LOGGER.error(f"Error in resume_queued_tasks: {e}")


async def cancel_task(task, gid: str, reason: str):
    """Cancel a task with the given reason."""
    try:
        LOGGER.info(f"Cancelling task {task.listener.name}: {reason}")

        # Get user tag for notifications
        user_tag = (
            f"@{task.listener.user.username}"
            if hasattr(task.listener.user, "username") and task.listener.user.username
            else f"<a href='tg://user?id={task.listener.user_id}'>{task.listener.user_id}</a>"
        )

        # Notify user before cancellation
        cancel_msg = await send_message(
            task.listener.message,
            f"⚠️ <b>Task Cancelled</b> ⚠️\n\n"
            f"<b>Name:</b> <code>{task.listener.name}</code>\n"
            f"<b>Reason:</b> {reason}\n\n"
            f"<b>This task was automatically cancelled by the system.</b>\n\n"
            f"{user_tag} your task has been cancelled!",
        )

        # Auto-delete cancellation message after 5 minutes
        if not isinstance(cancel_msg, str):
            create_task(auto_delete_message(cancel_msg, time=300))

        # Cancel the task
        if hasattr(task, "cancel_task") and callable(task.cancel_task):
            await task.cancel_task()
        else:
            # Fallback: Mark as cancelled and let the task handle it
            task.listener.is_cancelled = True
            LOGGER.warning(
                f"Task {task.listener.name} doesn't have cancel_task method, marked as cancelled"
            )

        # Clean up task_warnings to prevent memory leaks
        if gid in task_warnings:
            del task_warnings[gid]

    except Exception as e:
        LOGGER.error(f"Error cancelling task: {e}")


async def monitor_tasks():
    try:
        # Update system resource usage history
        try:
            cpu_usage_history.append(psutil.cpu_percent())
            memory_usage_history.append(psutil.virtual_memory().percent)
        except Exception as e:
            LOGGER.error(f"Error getting system resource usage: {e}")
            # Use default values if we can't get actual usage
            cpu_usage_history.append(0)
            memory_usage_history.append(0)

        # Clean up task_warnings for tasks that no longer exist
        async with task_dict_lock:
            active_gids = set(task_dict.keys())
            for gid in list(task_warnings.keys()):
                if gid not in active_gids:
                    del task_warnings[gid]

        # Identify resource-intensive tasks
        await identify_resource_intensive_tasks()

        # Check if we can resume any queued tasks
        can_resume, resource_type = await can_resume_queued_tasks()
        if can_resume and queued_by_monitor:
            await resume_queued_tasks(resource_type)

        # Monitor active tasks
        async with task_dict_lock:
            # Make a copy of the task_dict to avoid modification during iteration
            tasks_to_check = list(task_dict.items())

        # Process tasks outside the lock to minimize lock contention
        for gid, task in tasks_to_check:
            try:
                # Skip tasks without listener attribute
                if not hasattr(task, "listener"):
                    continue

                # Skip tasks that are already queued
                if task.listener.mid in queued_by_monitor:
                    continue

                # Skip tasks that are already being cancelled
                if (
                    hasattr(task.listener, "is_cancelled")
                    and task.listener.is_cancelled
                ):
                    continue

                # Check if task should be cancelled
                should_cancel, cancel_reason = await should_cancel_task(task, gid)
                if should_cancel:
                    # Verify task is still in task_dict before cancelling
                    async with task_dict_lock:
                        if gid not in task_dict:
                            continue
                    await cancel_task(task, gid, cancel_reason)
                    continue

                # Send warning if needed but not already sent
                if (
                    gid in task_warnings
                    and task_warnings[gid]["warning_sent"]
                    and not should_cancel
                ):
                    if not task_warnings[gid].get("notification_sent", False):
                        # Verify task has message attribute
                        if not hasattr(task.listener, "message"):
                            continue

                        # Get user tag for notifications
                        user_tag = (
                            f"@{task.listener.user.username}"
                            if hasattr(task.listener.user, "username")
                            and task.listener.user.username
                            else f"<a href='tg://user?id={task.listener.user_id}'>{task.listener.user_id}</a>"
                        )

                        # Send warning notification to user
                        warning_msg = await send_message(
                            task.listener.message,
                            f"⚠️ <b>Task Warning</b> ⚠️\n\n"
                            f"<b>Name:</b> <code>{task.listener.name}</code>\n"
                            f"<b>Issue:</b> {task_warnings[gid]['reason']}\n\n"
                            f"<b>This task will be automatically cancelled in {WAIT_TIME_BEFORE_CANCEL // 60} minutes "
                            f"if not manually cancelled.</b>\n"
                            f"<b>Use /cancel command to cancel it manually.</b>\n\n"
                            f"{user_tag} please take action!",
                        )
                        # Auto-delete warning message after 5 minutes
                        if not isinstance(warning_msg, str):
                            create_task(auto_delete_message(warning_msg, time=300))
                        task_warnings[gid]["notification_sent"] = True

                # Check if task should be queued due to system resource constraints
                for task_info in cpu_intensive_tasks + memory_intensive_tasks:
                    mid, task_type = task_info
                    if mid == task.listener.mid:
                        should_queue, queue_reason = await should_queue_task(task_type)
                        if should_queue:
                            # Verify task is still in task_dict before queuing
                            async with task_dict_lock:
                                if gid not in task_dict:
                                    continue
                            await queue_task(mid, queue_reason)
                            break
            except Exception as e:
                LOGGER.error(f"Error processing task {gid}: {e}")

        # Add periodic memory cleanup
        if time.time() % 300 < 1:  # Every ~5 minutes
            gc.collect()  # Force garbage collection
    except Exception as e:
        LOGGER.error(f"Error in task monitoring: {e}")


async def start_monitoring():
    """Start the task monitoring loop."""
    LOGGER.info("Starting task monitoring system")
    while True:
        await monitor_tasks()
        await asyncio.sleep(CHECK_INTERVAL)
