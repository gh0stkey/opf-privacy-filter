# OPF Privacy Filter

A PII (Personally Identifiable Information) detection and redaction HTTP service built on [OpenAI Privacy Filter](https://github.com/openai/privacy-filter).

## Docker Usage

### Pull Image

```bash
docker pull ghcr.io/gh0stkey/opf-privacy-filter:latest
```

### Run

```bash
docker run -d -p 8000:8000 --name opf ghcr.io/gh0stkey/opf-privacy-filter:latest
```

With GPU acceleration:

```bash
docker run -d -p 8000:8000 --gpus all -e OPF_DEVICE=cuda --name opf ghcr.io/gh0stkey/opf-privacy-filter:latest
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPF_DEVICE` | `cpu` | Inference device: `cpu` or `cuda` |
| `OPF_OUTPUT_MODE` | `typed` | Output mode |
| `OPF_CHECKPOINT` | - | Custom model checkpoint path |

### API Endpoints

The service listens on `http://localhost:8000` by default. Model loading takes ~1-2 minutes on first start.

**Health Check**

```bash
curl http://localhost:8000/health
```

**Redact Single Text**

```bash
curl -X POST http://localhost:8000/redact \
  -H "Content-Type: application/json" \
  -d '{"text": "My name is John and my email is john@example.com"}'
```

**Redact Text Only (returns redacted string)**

```bash
curl -X POST http://localhost:8000/redact/text \
  -H "Content-Type: application/json" \
  -d '{"text": "My name is John and my email is john@example.com"}'
```

**Batch Redaction**

```bash
curl -X POST http://localhost:8000/redact/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Call me at 555-1234", "My SSN is 123-45-6789"]}'
```

### Build Locally

```bash
docker build -t opf-privacy-filter .
docker run -d -p 8000:8000 opf-privacy-filter
```
