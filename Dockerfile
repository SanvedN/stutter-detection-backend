FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg + locales + build essentials for some Python libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    locales \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Configure locales (important for UTF-8)
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Download NLTK data
RUN python -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger maxent_ne_chunker words tagsets english

# Download spaCy English model
RUN python -m spacy download en_core_web_sm

# Copy your app code
COPY . .

# Expose the port (optional, good practice)
EXPOSE 10000

# Run the app with Gunicorn binding to the PORT env variable
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
