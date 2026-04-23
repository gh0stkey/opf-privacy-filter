FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential \
    && rm -rf /var/lib/apt/lists/*

# Clone the official OpenAI privacy-filter repo
RUN git clone --depth 1 https://github.com/openai/privacy-filter.git .

# Install dependencies (CPU-only torch to keep the image small)
RUN pip install --no-cache-dir --prefix=/install \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir --prefix=/install -e . && \
    pip install --no-cache-dir --prefix=/install fastapi uvicorn[standard]

# --- Final stage ---
FROM python:3.12-slim

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local
# Copy the project source
COPY --from=builder /build /app

# Copy our server file
COPY server.py .

# Download the model at build time so it's baked into the image
RUN python -c "from opf._api import resolve_checkpoint_path; resolve_checkpoint_path(None)"

# Create non-root user
RUN useradd -m -s /bin/bash opf && \
    cp -r /root/.opf /home/opf/.opf && \
    chown -R opf:opf /home/opf/.opf
USER opf

ENV OPF_DEVICE=cpu
ENV OPF_OUTPUT_MODE=typed
ENV HOME=/home/opf

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
