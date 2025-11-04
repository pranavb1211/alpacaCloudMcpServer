# Dockerfile
#
# Docker configuration for Alpaca MCP Server
# Location: /Dockerfile
# Purpose: Creates containerized deployment of the Alpaca MCP Server for Docker registry

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for potential native extensions
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy project files
COPY pyproject.toml requirements.txt README.md ./
COPY src/ ./src/
COPY .github/core .github/core

# Install Python dependencies
# Use pip instead of uvx for container environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash alpaca && \
    chown -R alpaca:alpaca /app
USER alpaca

# Set environment variables
ENV PYTHONPATH=/app
ENV ALPACA_PAPER_TRADE=True
ENV PYTHONUNBUFFERED=1

# Health check to verify the server can import properly
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "from alpaca_mcp_server import server; print('Health check passed')" || exit 1

# Expose port for HTTP transport (optional)
EXPOSE 8000

# Default command runs the server with stdio transport
# Can be overridden for HTTP transport: docker run -p 8000:8000 image --transport http
ENTRYPOINT ["alpaca-mcp-server"]
CMD ["serve"]
