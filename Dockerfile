FROM ubuntu:24.10

WORKDIR /usr/src/app
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/usr/local/bin:/usr/src/app/.venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    python3-pip \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip3 install --break-system-packages --no-cache-dir uv

# Create virtual environment
RUN uv venv

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN . .venv/bin/activate && uv pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .
RUN chmod +x start.sh

# Create necessary directories
RUN mkdir -p downloads

# Set permissions
RUN chmod 777 /usr/src/app
RUN chmod 777 downloads

# Run Aeon script first to install dependencies
RUN bash Aeon

# Create symlinks for binaries to ensure they're in PATH
RUN ln -sf /usr/local/bin/xnox /usr/bin/xnox \
    && ln -sf /usr/bin/xtra /usr/bin/ffmpeg \
    && ln -sf /usr/bin/xone /usr/bin/rclone \
    && ln -sf /usr/bin/xria /usr/bin/aria2c

VOLUME /usr/src/app/downloads
VOLUME /usr/src/app/config.py

CMD ["bash", "start.sh"]