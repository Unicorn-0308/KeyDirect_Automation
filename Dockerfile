# Multi-stage build for minimal image size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage - runtime image
FROM python:3.11-slim

# Install dependencies for Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg2 \
    unzip \
    ca-certificates \
    apt-transport-https \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    google-chrome-stable \
    && google-chrome --version \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/*

# Install ChromeDriver matching Chrome version
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1) \
    && echo "Chrome version: ${CHROME_VERSION}" \
    && CHROMEDRIVER_VERSION=$(curl -s "https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CHROME_VERSION}") \
    && echo "ChromeDriver version: ${CHROMEDRIVER_VERSION}" \
    && wget -q "https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip" \
    && unzip -q chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64 \
    && chromedriver --version

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Run the application with uvicorn
CMD ["gunicorn", "main:app", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "3600", "--bind", "0.0.0.0:8000"]
