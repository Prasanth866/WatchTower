FROM python:3.11-slim

WORKDIR /backend

RUN pip install --no-cache-dir uv

RUN apt-get update && apt-get install -y --no-install-recommends curl \
	&& rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .

RUN uv pip install --system .

COPY . .

RUN chmod +x /backend/scripts/entrypoint.sh

CMD ["/backend/scripts/entrypoint.sh"]
