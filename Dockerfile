# Multi-stage build for Gongle Secure Theater
# Stage 1: Build Rust binary
FROM rust:1.81-slim AS rust-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Rust project files
COPY wofl_obs-defuscrypt/Cargo.toml wofl_obs-defuscrypt/Cargo.lock ./
COPY wofl_obs-defuscrypt/src ./src

# Build release binary with optimizations
RUN cargo build --release

# Stage 2: Python Flask app
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN useradd -m -s /bin/bash gongle

# Create necessary directories
RUN mkdir -p /app/gongle-web /app/bin /var/log/supervisor /var/log/nginx

# Copy Rust binary from builder
COPY --from=rust-builder /app/target/release/wofl_obs-defuscrypt /app/bin/

# Copy Python application
WORKDIR /app/gongle-web
COPY gongle-web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gongle-web/ .
COPY integration/ /app/integration/

# Copy configuration files
COPY config/nginx.conf /etc/nginx/nginx.conf
COPY config/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create directories for data
RUN mkdir -p /app/data /app/logs /app/tmp

# Set permissions
RUN chown -R gongle:gongle /app /var/log/nginx /var/log/supervisor

# Expose ports
EXPOSE 80 443 5000

# Environment variables
ENV FLASK_APP=app.py
ENV PYTHONPATH=/app/gongle-web:/app/integration
ENV RUST_BINARY_PATH=/app/bin/wofl_obs-defuscrypt

# Create entrypoint script
RUN echo '#!/bin/bash\n\
echo "🎭 Starting Gongle Data Protection Theater..."\n\
echo "📊 Initializing database..."\n\
cd /app/gongle-web\n\
python -c "from app import app, db; app.app_context().push(); db.create_all()"\n\
echo "🚀 Launching services..."\n\
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Fix permissions BEFORE switching user
RUN chown -R gongle:gongle /app /var/log/nginx /var/log/supervisor /var/run /tmp

# Keep running as root for supervisord
# USER gongle

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]