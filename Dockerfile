FROM python:3.11-slim

WORKDIR /app

# Dependances systeme pour psycopg (libpq)
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# Dependances Python (cache Docker si requirements.txt ne change pas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Repertoire data pour la cle secrete Flask
RUN mkdir -p /app/data

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app.main:app"]
