# Alternative Docker Build Strategies

If the chunked approach still times out, try these alternatives:

## Option 1: Use requirements.txt with retries
```bash
# Create requirements.txt and use pip retry mechanism
pip3 install --no-cache-dir --timeout 600 --retries 3 -r requirements.txt
```

## Option 2: Pre-built base image
```dockerfile
# Use a pre-built image with common ML libraries
FROM nvcr.io/nvidia/pytorch:23.08-py3
# Or use python:3.10-slim and install only what you need
```

## Option 3: Multi-stage build
```dockerfile
# Build heavy dependencies in separate stage
FROM python:3.10-slim as builder
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

FROM ros:humble-ros-base
COPY --from=builder /usr/local/lib/python3.*/site-packages/ /usr/local/lib/python3.*/site-packages/
```

## Option 4: Use pip cache mount (Docker BuildKit)
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install --timeout 600 torch
```

## Option 5: Manual retry script
```bash
#!/bin/bash
# retry-build.sh
for i in {1..3}; do
    docker compose -f docker-compose.yml -f docker-compose.pi.yml build && break
    echo "Build attempt $i failed, retrying..."
    sleep 10
done
```