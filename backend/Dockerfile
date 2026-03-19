FROM python:3.11-slim

WORKDIR /backend

RUN pip install uv

RUN apt-get update && apt-get install -y curl

COPY pyproject.toml .

RUN uv pip install --system .

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
