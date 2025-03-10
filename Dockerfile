FROM ubuntu:24.10

WORKDIR /usr/src/app
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/src/app/.venv/bin:$PATH"
ENV PYTHONPATH="/usr/src/app:$PYTHONPATH"

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
    pip3 install --no-cache-dir \
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

# Ensure bot directory is renamed to tghbot if not already
RUN if [ -d "bot" ] && [ ! -d "tghbot" ]; then mv bot tghbot; fi
RUN if [ -d "tghbot/helper/aeon_utils" ]; then mv tghbot/helper/aeon_utils tghbot/helper/tgh_utils; fi

# Update Python imports
RUN find . -type f -name "*.py" -exec sed -i 's/from bot\./from tghbot./g; s/import bot\./import tghbot./g; s/from aeon_utils/from tgh_utils/g' {} +

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
VOLUME /usr/src/app/config.py

# Ensure virtual environment is always activated
SHELL ["/bin/bash", "-c"]
CMD source $VIRTUAL_ENV/bin/activate && bash start.sh