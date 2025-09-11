FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_ENV=true

WORKDIR /app

# Install system dependencies including tools for Hyperledger Fabric + Docker
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    curl \
    wget \
    ca-certificates \
    netcat-openbsd \
    jq \
    git \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get update && apt-get install -y docker-ce-cli

# Install Docker Compose
RUN curl -L "https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
RUN chmod +x /usr/local/bin/docker-compose

# Download and install Hyperledger Fabric binaries manually with config
RUN mkdir -p /opt/hyperledger-fabric-bin && \
    cd /tmp && \
    curl -sSL https://github.com/hyperledger/fabric/releases/download/v2.5.4/hyperledger-fabric-linux-amd64-2.5.4.tar.gz | \
    tar -xzf - && \
    mv bin/* /opt/hyperledger-fabric-bin/ && \
    chmod +x /opt/hyperledger-fabric-bin/* && \
    mkdir -p /opt/fabric-config && \
    mv config/* /opt/fabric-config/ && \
    rm -rf bin config

# Add Fabric binaries to PATH
ENV PATH="/opt/hyperledger-fabric-bin:$PATH"

# Set Hyperledger environment variables for your handler
ENV FABRIC_CFG_PATH=/opt/fabric-config \
    HLF_NETWORK_PATH=/hyperledger \
    CHANNEL_NAME=mychannel \
    CHAINCODE_NAME=voting

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create logs directory for your handler
RUN mkdir -p /app/logs

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "backend.wsgi:application"]