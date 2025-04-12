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

# Create a directory for user profile (required by LibreOffice)
RUN mkdir -p /root/.config/libreoffice

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
    PyPDF2>=3.0.0 \
    python-docx>=0.8.11

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /app/data/chroma \
    && mkdir -p /app/logs \
    && mkdir -p /tmp/libreoffice \
    && chmod 1777 /tmp/libreoffice

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV HOME=/root
ENV PATH="/usr/lib/libreoffice/program:${PATH}"

# Expose ports for FastAPI and Streamlit
EXPOSE 8001 8501

# Copy the startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Set the entrypoint
CMD ["/app/start.sh"] 