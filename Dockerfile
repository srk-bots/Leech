FROM ubuntu:24.10

WORKDIR /usr/src/app
ENV DEBIAN_FRONTEND=noninteractive
# Initialize PYTHONPATH first, then append to it
ENV PYTHONPATH="/usr/src/app"
ENV PATH="/usr/src/app/.venv/bin:$PATH"
# Disable git reset to preserve files
ENV ENABLE_GIT_RESET="false"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    python3-pip \
    libffi-dev \
    git \
    sabnzbdplus \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip3 install --break-system-packages --no-cache-dir uv

# Create virtual environment
RUN uv venv
ENV VIRTUAL_ENV=/usr/src/app/.venv

# Install base Python packages
RUN . $VIRTUAL_ENV/bin/activate && \
    pip3 install --break-system-packages --no-cache-dir \
    setuptools \
    pymongo \
    motor \
    uvloop \
    cython \
    wheel

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN . $VIRTUAL_ENV/bin/activate && \
    uv pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install the local package in development mode
RUN . $VIRTUAL_ENV/bin/activate && pip install --break-system-packages -e .

# Ensure bot directory is renamed to tghbot if not already
RUN if [ -d "bot" ] && [ ! -d "tghbot" ]; then \
    echo "Renaming bot to tghbot directory" && \
    mv bot tghbot && \
    # Create a symlink for backward compatibility
    ln -sf /usr/src/app/tghbot /usr/src/app/bot; \
fi

# Ensure helper utils are correctly named
RUN if [ -d "tghbot/helper/aeon_utils" ]; then \
    echo "Renaming aeon_utils to tgh_utils" && \
    mv tghbot/helper/aeon_utils tghbot/helper/tgh_utils; \
fi

# Update Python imports (with more thorough search patterns)
RUN find . -type f -name "*.py" -exec sed -i 's/from bot\./from tghbot./g; s/import bot\./import tghbot./g; s/ bot\./ tghbot./g; s/from aeon_utils/from tgh_utils/g' {} +

# Verify the correct module structure
RUN if [ -d "tghbot" ]; then \
    echo "tghbot directory exists" && \
    ls -la tghbot && \
    echo "Checking for __main__.py" && \
    if [ -f "tghbot/__main__.py" ]; then \
        echo "tghbot/__main__.py exists"; \
    else \
        echo "tghbot/__main__.py does not exist!"; \
    fi; \
else \
    echo "tghbot directory does not exist!"; \
fi

RUN chmod +x start.sh

# Create necessary directories
RUN mkdir -p downloads

# Set permissions
RUN chmod -R 777 /usr/src/app
RUN chmod 777 downloads

# Run Aeon script for additional dependencies
RUN bash Aeon

# Create symlinks for binaries
RUN ln -sf /usr/local/bin/xnox /usr/bin/xnox \
    && ln -sf /usr/bin/xtra /usr/bin/ffmpeg \
    && ln -sf /usr/bin/xone /usr/bin/rclone \
    && ln -sf /usr/bin/xria /usr/bin/aria2c \
    && ln -sf $(which sabnzbdplus) /usr/bin/xnzb

VOLUME /usr/src/app/downloads

# Ensure virtual environment is always activated
SHELL ["/bin/bash", "-c"]
CMD source $VIRTUAL_ENV/bin/activate && bash start.sh