# Sunn in one container: the API and the built web app on port 7860, Hugging Face Spaces'
# default. Every setting comes from the environment (docs/DEPLOY.md); nothing secret is baked in.

# 1. Build the web app.
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# 2. The backend, with the web app's build next to it.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /usr/local/bin/uv

# Spaces run the container as user 1000, so the app's folder belongs to that user; data/ and
# logs/ are written there at runtime.
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    PATH=/home/user/app/.venv/bin:$PATH

COPY --chown=user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY --chown=user src/ src/
COPY --chown=user content/ content/
COPY --chown=user data/default_phrases_en.txt data/default_phrases_hi.txt data/
COPY --from=web --chown=user /web/dist web/dist

EXPOSE 7860
CMD ["python", "src/server.py", "--host", "0.0.0.0", "--port", "7860"]
