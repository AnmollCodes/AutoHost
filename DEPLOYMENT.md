# AutoHost AI Agent - Production Deployment Guide

**Version**: 1.0.0 (Production Release)

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running Locally](#running-locally)
5. [Docker Deployment](#docker-deployment)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Logging](#monitoring--logging)
8. [Troubleshooting](#troubleshooting)
9. [Production Checklist](#production-checklist)

---

## System Requirements

### Minimum Requirements
- **OS**: Linux, macOS, or Windows 10+
- **Python**: 3.11 or higher
- **RAM**: 8GB (16GB recommended)
- **VRAM**: 4GB (for local LLM models)
- **Disk**: 20GB (varies by LLM model size)

### Software Dependencies
- Docker (for sandbox isolation) [optional but recommended]
- Ollama (for local LLM inference)
- Git (for version control)

### Network Requirements
- **Ollama API**: Port 11434 (local)
- **AutoHost API**: Port 8000 (configurable)
- **WebSocket**: Port 8000 (same as API)

---

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/autohost.git
cd autohost
```

### Step 2: Create Virtual Environment

```bash
# Linux/macOS
python3.11 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# User installation
pip install -e .

# Development installation (includes testing tools)
pip install -e ".[dev]"
```

### Step 4: Install Ollama (if not already installed)

```bash
# Visit https://ollama.ai
# Download and install for your OS

# Verify installation
ollama --version
```

### Step 5: Download LLM Model

```bash
# Pull a model (examples)
ollama pull kimi-k2.5:cloud          # ~4GB - Recommended
ollama pull llama2           # ~3.8GB - Alternative
ollama pull neural-chat      # ~4.7GB - Alternative

# Verify model availability
ollama list
```

---

## Configuration

### Environment Setup

Create a `.env` file in the project root:

```env
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
WORKER_THREADS=4

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=kimi-k2.5:cloud
OLLAMA_TIMEOUT=300

# Security Configuration
SECRET_KEY=your-random-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Sandbox Configuration
SANDBOX_MODE=docker          # docker or permissive
ALLOW_INTERNET_ACCESS=false
MAX_EXECUTION_TIME=300

# Database Configuration
DATABASE_URL=sqlite:///./autohost.db
DATABASE_ECHO=false

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/autohost.log
LOG_FORMAT=json

# Features
ENABLE_CODE_EXECUTION=true
ENABLE_FILE_ACCESS=true
ENABLE_INTERNET_SEARCH=true
REQUIRE_PATH_CONFIRMATION=true
```

### Generate Secret Key

```python
import secrets
print(secrets.token_urlsafe(32))
```

### Production Environment (AWS Example)

```env
# AWS Integration
AWS_REGION=us-east-1
S3_BUCKET=autohost-tasks
DYNAMODB_TABLE=autohost-tasks

# RDS Database
DATABASE_URL=postgresql://user:pass@rds.amazonaws.com/autohost

# CloudWatch Logging
CLOUDWATCH_GROUP=/autohost/production
```

---

## Running Locally

### Start Ollama Service

```bash
ollama serve
# Ollama is now listening on http://localhost:11434
```

### Start AutoHost Server (in new terminal)

```bash
# From project root with venv activated
python -m agent.orchestrator.server

# Or use the CLI
autohost serve --port 8000 --host 0.0.0.0
```

### Access Web Interface

Open browser to `http://localhost:8000`

### Example API Calls

```bash
# Health check
curl http://localhost:8000/health

# Create task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"request": "List files in current directory"}'

# Monitor task
curl http://localhost:8000/api/tasks/{task_id}

# WebSocket connection
wscat -c ws://localhost:8000/ws
```

---

## Docker Deployment

### Build Docker Image

```bash
# Standard build
docker build -t autohost:latest .

# Build with specific Python version
docker build --build-arg PYTHON_VERSION=3.11 -t autohost:1.0.0 .

# Multi-stage build for production
docker build -f Dockerfile.prod -t autohost:prod .
```

### Run Docker Container

```bash
# Basic run
docker run -p 8000:8000 \
  --env-file .env \
  autohost:latest

# With volume mounts
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  autohost:latest

# With GPU support (NVIDIA)
docker run -p 8000:8000 \
  --gpus all \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  autohost:latest
```

### Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    command: serve
    environment:
      - OLLAMA_KEEP_ALIVE=24h

  autohost:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8000
      - LOG_LEVEL=INFO
    depends_on:
      - ollama
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  ollama_data:
```

Start services:

```bash
docker-compose up -d
docker-compose logs -f autohost
```

---

## Security Hardening

### 1. Production Secret Management

```python
# Use AWS Secrets Manager or HashiCorp Vault
from aws_secretsmanager_caching import SecretCache

cache = SecretCache()
secret = cache.get_secret_string('autohost/production')
```

### 2. Enable All Security Features

```env
# .env
REQUIRE_PATH_CONFIRMATION=true
ENABLE_CSRF_PROTECTION=true
ENABLE_RATE_LIMITING=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=3600
SANDBOX_MODE=docker
MAX_EXECUTION_TIME=300
RESTRICTED_PYTHON=true
```

### 3. SSL/TLS Certificate Setup

```bash
# Using Let's Encrypt with Certbot
certbot certonly --standalone -d yourdomain.com

# In docker-compose.yml
environment:
  - SSL_CERT_PATH=/etc/ssl/certs/yourdomain.com
  - SSL_KEY_PATH=/etc/ssl/private/yourdomain.com
volumes:
  - /etc/letsencrypt:/etc/ssl:ro
```

### 4. Database Encryption

```python
# SQLAlchemy with AES encryption
from sqlalchemy_utils import EncryptedType, AesEngine

cipher_suite = AesEngine()
encrypted_field = EncryptedType(String, 'password_key', impl=String, cipher_engine=cipher_suite)
```

### 5. Firewall Rules (Linux)

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 8000/tcp    # AutoHost API
sudo ufw allow 22/tcp      # SSH (if needed)
sudo ufw enable
```

### 6. Network Isolation (Docker)

```bash
# Create isolated network
docker network create autohost-net

# Run containers on isolated network
docker run --network autohost-net -p 8000:8000 autohost:latest
docker run --network autohost-net -p 11434:11434 ollama/ollama:latest
```

---

## Monitoring & Logging

### Application Metrics

```python
# Access metrics endpoint
curl http://localhost:8000/metrics

# Returns Prometheus-compatible metrics
autohost_tasks_total{status="completed"} 245
autohost_errors_total{type="rate_limit"} 12
autohost_request_duration_seconds{endpoint="/api/tasks"} 0.234
```

### Log Aggregation Setup

```bash
# Configure structured logging to CloudWatch
# See logs/cloudwatch_config.yaml

# Or to ELK Stack:
# pip install python-logstash-async
# Configure in agent/logging.py
```

### Health Monitoring

```bash
# Check service health
curl http://localhost:8000/health

# Check LLM connectivity
curl http://localhost:8000/health/llm

# Check database status
curl http://localhost:8000/health/db
```

### Performance Profiling

```bash
# Enable profiling endpoint (development only)
export ENABLE_PROFILING=true
python -m cProfile -o profile.prof -m agent.orchestrator.server

# View results
python -m pstats profile.prof
```

---

## Troubleshooting

### Issue: LLM Connection Failed

```bash
# Check Ollama is running
curl http://localhost:11434

# Check network connectivity
docker network inspect <network-name>

# Ollama logs
docker logs $(docker ps | grep ollama | awk '{print $1}')
```

### Issue: Port Already in Use

```bash
# Linux/macOS
lsof -i :8000
kill -9 <PID>

# Windows
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process
```

### Issue: Permission Denied (Sandbox)

```bash
# Check Docker daemon is running
docker ps

# Verify user permissions
sudo usermod -aG docker $USER

# Restart Docker
sudo systemctl restart docker
```

### Issue: Database Locked

```bash
# Remove stale SQLite lock file
rm autohost.db-wal
rm autohost.db-shm

# Use WAL mode for better concurrency
sqlite3 autohost.db
PRAGMA journal_mode=WAL;
```

### Issue: Out of Memory

```bash
# Increase container resources
docker run --memory=16g autohost:latest

# Or in docker-compose.yml
services:
  autohost:
    deploy:
      resources:
        limits:
          memory: 16G
```

---

## Production Checklist

- [ ] Environment variables configured for production
- [ ] Secret key generated and stored securely
- [ ] SSL/TLS certificates installed
- [ ] Database backups configured
- [ ] Firewall rules implemented
- [ ] Rate limiting enabled and tested
- [ ] User authentication configured
- [ ] CSRF protection enabled
- [ ] Logging aggregated to centralized system
- [ ] Health checks configured
- [ ] Monitoring alerts set up
- [ ] Disaster recovery plan documented
- [ ] Load balancer configured (if multi-instance)
- [ ] Database connection pooling configured
- [ ] Cache warming configured
- [ ] Error tracking (Sentry/DataDog) integrated
- [ ] Performance testing completed
- [ ] Security scan passed (OWASP)
- [ ] All tests passing (pytest --cov=agent)
- [ ] Documentation updated

---

## Support & Troubleshooting

For issues and questions:
1. Check the [FAQ](./FAQ.md)
2. Review [Security Policy](./SECURITY.md)
3. Open an issue on GitHub
4. Consult [Architecture Documentation](./architecture.md)

---

**Last Updated**: 2024  
**Maintained by**: AutoHost Team
