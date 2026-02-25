# Use official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

ARG PIP_REQUIREMENTS=requirements.txt

# Install Python dependencies
COPY requirements.txt /app/
COPY requirements.prod.txt /app/
RUN pip install --upgrade pip
RUN pip install -r "/app/${PIP_REQUIREMENTS}"

# Copy project
COPY backend/ /app/

# Create media and static directories
RUN mkdir -p /app/media/uploads /app/staticfiles
RUN chmod +x /app/entrypoint.prod.sh

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
