FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
# ffmpeg for audio processing
# git for dependencies
# poppler-utils for pdf2image
# tesseract-ocr for OCR
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Run application
# Point to src.main:app since main.py is in src/
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
