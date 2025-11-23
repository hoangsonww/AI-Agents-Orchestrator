# Multi-stage Dockerfile for AI Orchestrator
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
COPY pyproject.toml .
COPY setup.py .

# Install dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r orchestrator && useradd -r -g orchestrator orchestrator

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/orchestrator/.local

# Copy application code
COPY --chown=orchestrator:orchestrator orchestrator/ ./orchestrator/
COPY --chown=orchestrator:orchestrator adapters/ ./adapters/
COPY --chown=orchestrator:orchestrator config/ ./config/
COPY --chown=orchestrator:orchestrator ai-orchestrator ./ai-orchestrator
COPY --chown=orchestrator:orchestrator setup.py .
COPY --chown=orchestrator:orchestrator pyproject.toml .
COPY --chown=orchestrator:orchestrator README.md .

# Make CLI executable
RUN chmod +x ai-orchestrator

# Create necessary directories
RUN mkdir -p /app/output /app/workspace /app/reports /app/sessions /app/logs && \
    chown -R orchestrator:orchestrator /app

# Switch to non-root user
USER orchestrator

# Add local bin to PATH
ENV PATH="/home/orchestrator/.local/bin:${PATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
ENTRYPOINT ["./ai-orchestrator"]
CMD ["--help"]
