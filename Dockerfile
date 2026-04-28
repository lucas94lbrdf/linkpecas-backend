# Dockerfile - Backend LinkPeça Marketplace
FROM python:3.11-slim-bullseye

# Impede que o Python gere arquivos .pyc e permite logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

# Instala dependências do sistema necessárias para algumas libs Python (como psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY . .

# Expõe a porta padrão (embora o Cloud Run use a variável $PORT)
EXPOSE 8000

# Comando para rodar a aplicação usando a porta dinâmica
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT