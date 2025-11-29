# Multi-stage Production Dockerfile for AI Orchestrator
# Security: Non-root user, multi-stage build, minimal attack surface

# Stage 1: Builder
FROM python:3.11-slim as builder

# Security labels
LABEL maintainer="DevOps Team"
LABEL version="1.0.0"
LABEL description="AI Agents Orchestrator - Production Build"

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
COPY pyproject.toml .
COPY setup.py .

# Install dependencies with security updates
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Security labels
LABEL maintainer="DevOps Team"
LABEL version="1.0.0"
LABEL description="AI Agents Orchestrator - Production Runtime"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=5001 \
    LOG_LEVEL=INFO \
    ENVIRONMENT=production

# Security: Create non-root user with specific UID/GID
RUN groupadd -r -g 1000 orchestrator && \
    useradd -r -u 1000 -g orchestrator -m -s /bin/bash orchestrator

# Set working directory
WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy Python dependencies from builder
COPY --from=builder --chown=orchestrator:orchestrator /root/.local /home/orchestrator/.local

# Copy application code with proper ownership
COPY --chown=orchestrator:orchestrator orchestrator/ ./orchestrator/
COPY --chown=orchestrator:orchestrator adapters/ ./adapters/
COPY --chown=orchestrator:orchestrator ui/ ./ui/
COPY --chown=orchestrator:orchestrator config/ ./config/
COPY --chown=orchestrator:orchestrator ai-orchestrator ./ai-orchestrator
COPY --chown=orchestrator:orchestrator setup.py .
COPY --chown=orchestrator:orchestrator pyproject.toml .
COPY --chown=orchestrator:orchestrator README.md .
COPY --chown=orchestrator:orchestrator LICENSE .

# Make scripts executable
RUN chmod +x ai-orchestrator && \
    chmod +x ui/*.py 2>/dev/null || true

# Create necessary directories with proper permissions
RUN mkdir -p \
    /app/output \
    /app/workspace \
    /app/reports \
    /app/sessions \
    /app/logs \
    /app/tmp \
    && chown -R orchestrator:orchestrator /app

# Security: Set read-only permissions for config
RUN chmod -R 755 /app/orchestrator /app/adapters /app/ui && \
    chmod -R 444 /app/config/*.yaml 2>/dev/null || true

# Switch to non-root user
USER orchestrator

# Add local bin to PATH
ENV PATH="/home/orchestrator/.local/bin:${PATH}"

# Expose application port
EXPOSE 5001

# Health check - curl to health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Volume for persistent data
VOLUME ["/app/workspace", "/app/sessions", "/app/logs", "/app/output"]

# Default command - run web UI
ENTRYPOINT ["python"]
CMD ["ui/app.py"]
