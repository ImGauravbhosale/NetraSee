FROM python:3.12-slim

WORKDIR /srv

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv sync --no-dev

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
