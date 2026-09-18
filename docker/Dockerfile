FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code
COPY .python-version pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY app/ app/

CMD ["/code/.venv/bin/fastapi", "run", "/code/app/main.py", "--port", "8000"]
