FROM python:3.14-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY src ./src

RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "ragdoll.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
