# Use an official PyTorch base image
FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-devel

# Set label for the docker image description
LABEL description="Docker image for xtts-api-server"

# Install required packages
RUN apt-get update && apt-get install --no-install-recommends -y python3-dev portaudio19-dev libportaudio2 libasound2-dev libportaudiocpp0 git python3-pip make g++ ffmpeg && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install virtualenv
RUN python3 -m pip install --upgrade pip setuptools wheel ninja virtualenv

# Set the working directory to /app
WORKDIR /app

# Copy the speakers folder to /app/speakers directory
COPY latent_speaker_folder /app/latent_speaker_folder

# Copy the models folder to /app/xtts_models directory
COPY xtts_models /app/xtts_models

# Copy the application source code and setup.py to /app directory
COPY xtts_api_server ./xtts_api_server
COPY setup.py .

# Install the application
RUN pip install .

# Expose the container port
EXPOSE 8020

# Command to run the server
CMD ["bash", "-c", "python3 -m xtts_api_server --listen -p 8020 -t 'http://localhost:8020' -lsf 'latent_speaker_folder' -o 'output' -mf 'xtts_models' -d 'cuda' --deepspeed"]
