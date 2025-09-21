# CloudRun最適化 Dockerfile for Kaboom Stock Trading API
FROM python:3.12-slim AS builder

# 作業ディレクトリ設定
WORKDIR /app

# システムパッケージ更新・必要なパッケージインストール
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# uvをインストール（高速なPython package manager）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Python依存関係ファイルをコピー
COPY pyproject.toml ./
COPY uv.lock ./

# 依存関係をインストール
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.12-slim AS production

# 作業ディレクトリ設定
WORKDIR /app

# 非rootユーザー作成（セキュリティ向上）
RUN useradd -m -u 1000 kaboom && \
    mkdir -p /app && \
    chown -R kaboom:kaboom /app

# 必要なランタイムライブラリのみインストール
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Builderステージから仮想環境をコピー
COPY --from=builder /app/.venv /app/.venv

# アプリケーションコードをコピー
COPY --chown=kaboom:kaboom app/ /app/app/

# バッチ処理モジュールをコピー
COPY --chown=kaboom:kaboom batch/ /app/batch/

# 非rootユーザーに切り替え
USER kaboom

# Pythonパス設定
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

# CloudRun最適化設定
ENV PORT=8080
ENV HOST=0.0.0.0

# Gunicorn設定（CloudRun推奨）
ENV WORKERS=1
ENV WORKER_CLASS=uvicorn.workers.UvicornWorker
ENV WORKER_CONNECTIONS=1000
ENV MAX_REQUESTS=1000
ENV MAX_REQUESTS_JITTER=100
ENV TIMEOUT=60
ENV KEEPALIVE=5

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ポート公開
EXPOSE ${PORT}

# 起動コマンド
CMD gunicorn app.main:app \
    --bind ${HOST}:${PORT} \
    --workers ${WORKERS} \
    --worker-class ${WORKER_CLASS} \
    --worker-connections ${WORKER_CONNECTIONS} \
    --max-requests ${MAX_REQUESTS} \
    --max-requests-jitter ${MAX_REQUESTS_JITTER} \
    --timeout ${TIMEOUT} \
    --keep-alive ${KEEPALIVE} \
    --access-logfile - \
    --error-logfile - \
    --log-level info
