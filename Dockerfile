FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# threads=1 e proposital: cada requisicao abre um Chromium inteiro. Com mais de
# uma thread, duas buscas simultaneas abririam dois navegadores ao mesmo tempo e
# estourariam a RAM do plano gratis (512MB). Com 1, a segunda requisicao so
# espera a primeira terminar em vez de derrubar o servidor.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 1 --timeout 280 app:app"]
