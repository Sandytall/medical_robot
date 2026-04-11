FROM ros:humble-ros-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3-pip \
    python3-dev \
    python3-colcon-common-extensions \
    python3-rosdep \
    libboost-all-dev \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-camera-info-manager \
    ros-humble-sensor-msgs \
    ros-humble-geometry-msgs \
    ros-humble-std-msgs \
    ros-humble-vision-msgs \
    ros-humble-diagnostic-msgs \
    ros-humble-nav-msgs \
    ros-humble-joy \
    python3-opencv \
    python3-numpy \
    python3-scipy \
    libasound2-dev \
    libportaudio2 \
    portaudio19-dev \
    pulseaudio-utils \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages optimized for Pi 5 ARM64
# Basic packages first (ARM64-compatible versions)
RUN pip3 install --no-cache-dir --timeout 600 \
    numpy==1.24.4 \
    scipy==1.11.3 \
    pillow==10.1.0 \
    requests==2.31.0 \
    pyzmq==25.1.1 \
    psutil==5.9.6 \
    pyyaml==6.0.1

# Multimedia packages (ARM64 tested)
RUN pip3 install --no-cache-dir --timeout 600 \
    opencv-python==4.8.1.78 \
    pygame==2.5.2 \
    pyttsx3==2.90

# Audio packages (compile from source for ARM64)
RUN pip3 install --no-cache-dir --timeout 600 \
    pyaudio==0.2.13 --no-binary=pyaudio

# Pi 5 GPIO packages (latest for Pi 5 support)
RUN pip3 install --no-cache-dir --timeout 600 \
    RPi.GPIO==0.7.1 \
    lgpio==0.2.2.0

# Behavior trees (lightweight, ARM64 compatible)
RUN pip3 install --no-cache-dir --timeout 600 \
    py_trees==2.2.3

# Face recognition - build from source for Pi 5
# Install dlib without CUDA/AVX (ARM64 optimized)
RUN pip3 install --no-cache-dir --timeout 1800 \
    dlib==19.24.2 \
    --global-option="--no" --global-option="--set" \
    --global-option="DLIB_NO_GUI_SUPPORT=1"

RUN pip3 install --no-cache-dir --timeout 600 \
    face_recognition==1.3.0

# OpenAI packages (use CPU-only torch for ARM64)
RUN pip3 install --no-cache-dir --timeout 1200 \
    torch==2.1.0+cpu \
    torchaudio==2.1.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip3 install --no-cache-dir --timeout 1200 \
    openai==1.3.8 \
    openai-whisper==20231117

# Web framework packages (ARM64 compatible)
RUN pip3 install --no-cache-dir --timeout 600 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    sqlalchemy==2.0.23

# Pi Camera support
RUN pip3 install --no-cache-dir --timeout 600 \
    picamera2==0.3.12

# Create workspace
WORKDIR /ros2_workspace

# Copy source files
COPY src/ /ros2_workspace/src/

# Initialize rosdep (skip if already exists)
RUN if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then rosdep init; fi && rosdep update

# Install dependencies
RUN rosdep install --from-paths src --ignore-src -r -y

# Build workspace
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build --packages-select mars_core mars_hardware mars_voice mars_behaviors --symlink-install"

# Source ROS2 setup
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "if [ -f /ros2_workspace/install/setup.bash ]; then source /ros2_workspace/install/setup.bash; fi" >> ~/.bashrc

# Create shared data directory
RUN mkdir -p /shared_data/database /shared_data/faces /shared_data/logs

EXPOSE 8000

CMD ["bash"]