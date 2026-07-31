FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# ffmpeg provides ffprobe, needed by VideoAnalyzer/AudioAnalyzer - without
# it those analyzers still run but report ffprobe_available: False rather
# than failing the upload.
RUN apt-get update && apt-get install -y \
    libmagic1 \
    postgresql-client \
    build-essential \
    libssl-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
