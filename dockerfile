FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.4.9 /uv /bin/uv

ADD . /app

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

CMD ["uv", "run", "python", "rfp_ui.py"]