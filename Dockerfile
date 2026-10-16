FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN --mount=type=secret,id=cloud_ca \
    if [ -f /run/secrets/cloud_ca ]; then export npm_config_cafile=/run/secrets/cloud_ca; fi; npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
COPY backend ./backend
RUN --mount=type=secret,id=cloud_ca \
    if [ -f /run/secrets/cloud_ca ]; then export PIP_CERT=/run/secrets/cloud_ca; fi; \
    pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir --no-deps -e .
COPY datasets ./datasets
COPY --from=frontend /build/dist ./frontend/dist
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn responsewatch.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
