FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies including LibreOffice and fonts
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    libreoffice \
    libreoffice-writer \
    libreoffice-common \
    fonts-liberation \
    fonts-dejavu \
    fontconfig \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories with correct permissions
RUN mkdir -p /root/.config/libreoffice \
    && mkdir -p /tmp/libreoffice \
    && chmod 1777 /tmp/libreoffice \
    && mkdir -p /app/data/chroma \
    && mkdir -p /app/logs

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
COPY backend-requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r backend-requirements.txt \
    && pip install --no-cache-dir \
    PyPDF2>=3.0.0 \
    python-docx>=0.8.11

# Copy the rest of the application
COPY src /app/src

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV HOME=/root
ENV PATH="/usr/lib/libreoffice/program:${PATH}"
ENV TMPDIR=/tmp/libreoffice

# Expose port for FastAPI
EXPOSE 8001

# Start the FastAPI server
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"] 