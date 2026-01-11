# Use the same Python version as Hugging Face auto-created
FROM python:3.13.5-slim

# Install system dependencies required by Python packages
RUN apt-get update && apt-get install -y \
    # Core system packages
    build-essential \
    curl \
    git \
    python3-dev \
    gcc \
    g++ \
    make \
    cmake \
    \
    # Video processing dependencies
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    \
    # XML processing dependencies (for lxml)
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    \
    # Clean up apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p temp outputs cache

# Expose port for Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]