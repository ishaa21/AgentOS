FROM python:3.11-slim

WORKDIR /app

# Install OS-level deps for psycopg2 (if using psycopg2 instead of psycopg2-binary in prod)
# RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080

CMD ["uvicorn", "multi_agent_backend:app", "--host", "0.0.0.0", "--port", "8080"]