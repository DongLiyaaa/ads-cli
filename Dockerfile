FROM node:22-bookworm-slim AS frontend
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-server.lock ./
RUN pip install --no-cache-dir -r requirements-server.lock
COPY agent-harness/ ./agent-harness/
RUN pip install --no-cache-dir --no-deps ./agent-harness && useradd --uid 10001 --create-home ads
COPY --from=frontend /build/web/dist ./web/dist
USER ads
EXPOSE 6666
CMD ["ads-control", "serve", "--host", "0.0.0.0", "--port", "6666"]
