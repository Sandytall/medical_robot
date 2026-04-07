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

# Install Python packages
RUN pip3 install --no-cache-dir \
    opencv-python \
    numpy \
    scipy \
    pillow \
    pygame \
    pyaudio \
    pyttsx3 \
    requests \
    pyzmq \
    psutil \
    py_trees \
    face_recognition \
    openai \
    openai-whisper \
    fastapi \
    uvicorn \
    sqlalchemy \
    RPi.GPIO

# Create workspace
WORKDIR /ros2_workspace

# Copy source files
COPY src/ /ros2_workspace/src/

# Initialize rosdep
RUN rosdep init && rosdep update

# Install dependencies
RUN rosdep install --from-paths src --ignore-src -r -y

# Build workspace (this will be done in docker-compose to allow for development)
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build"

# Source ROS2 setup
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "source /ros2_workspace/install/setup.bash" >> ~/.bashrc

# Create shared data directory
RUN mkdir -p /shared_data/database /shared_data/faces /shared_data/logs

EXPOSE 8000

CMD ["bash"]