# Use the latest Ubuntu base image
FROM ubuntu:22.04

# Create a non-root user
RUN useradd -m -s /bin/bash cursor

# Install Python 3, pip, and venv for Python development
RUN apt-get update -y && \
    apt-get install -y \
    build-essential \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv && \
    rm -rf /var/lib/apt/lists/*

# Switch to the non-root user
USER cursor

# Set the working directory to the user's home directory
WORKDIR /home/cursor

# Install Python dependencies
RUN pip3 install --user pytest

CMD ["bash"]