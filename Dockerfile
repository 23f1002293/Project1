# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variable for unbuffered output
ENV PYTHONUNBUFFERED True

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app

# Cloud Run automatically sets the PORT environment variable.
# Uvicorn should listen on 0.0.0.0 and the port specified by the PORT environment variable (default is 8080).
ENV PORT 8080
EXPOSE 8080

# Command to run your application using Uvicorn. 
# Replace 'main:app' with your actual file name and FastAPI instance name if different.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
