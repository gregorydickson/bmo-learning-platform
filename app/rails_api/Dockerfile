FROM ruby:3.2.2-slim as base

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies (including curl for health checks)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    nodejs \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install gems
COPY Gemfile Gemfile.lock ./
RUN bundle install

# Copy application code
COPY . .

# Precompile assets (if needed)
# RUN bundle exec rails assets:precompile

# Switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Entrypoint prepares the database.
ENTRYPOINT ["bin/docker-entrypoint"]

# Run application
CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
