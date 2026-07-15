FROM python:3.12-slim

# uv : gestionnaire de paquets Python (~10x plus rapide que pip)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# Couche de cache : les dépendances changent rarement, le code souvent.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

COPY app ./app

ENV PATH="/srv/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
