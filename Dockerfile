# Use the official Python image as the base image
FROM python:3.12-slim

# Expose the port that the app runs on
EXPOSE 38080

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt



# Run main.py when the container launches
CMD ["python", "streamer_shield_chatbot.py"]