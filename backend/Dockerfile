# =============================================================================
# IU Digital · Analítica Académica — Backend (FastAPI + Motor MongoDB)
# Imagen productiva para Google Cloud Run
# =============================================================================
FROM python:3.11-slim AS runtime

# System deps (build + runtime). Poppler solo si se usan PDFs; se puede quitar.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias primero (mejor caché de capas)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Cloud Run inyecta PORT (default 8080). Fastapi escucha 0.0.0.0:$PORT.
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Puerto expuesto (solo documental; Cloud Run usa $PORT)
EXPOSE 8080

# Health check (para orquestadores que lo soporten; Cloud Run usa /api/health)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/api/health" || exit 1

# Comando de inicio: uvicorn en modo producción (sin --reload)
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers 2 --proxy-headers --forwarded-allow-ips='*'"]
