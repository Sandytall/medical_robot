FROM ros:humble-ros-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
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

# Install Python packages in chunks to avoid timeouts and improve caching
# Basic packages first
RUN pip3 install --no-cache-dir --timeout 600 \
    numpy \
    scipy \
    pillow \
    requests \
    pyzmq \
    psutil \
    pyyaml

# Multimedia and audio packages
RUN pip3 install --no-cache-dir --timeout 600 \
    opencv-python \
    pygame \
    pyaudio \
    pyttsx3

# AI/ML packages (these are large and may timeout)
RUN pip3 install --no-cache-dir --timeout 600 \
    py_trees \
    face_recognition

# OpenAI packages (largest - torch dependency)
RUN pip3 install --no-cache-dir --timeout 600 \
    openai \
    openai-whisper

# Web framework packages
RUN pip3 install --no-cache-dir --timeout 600 \
    fastapi \
    uvicorn \
    sqlalchemy \
    RPi.GPIO

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