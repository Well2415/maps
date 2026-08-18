FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# A imagem base instala o Chromium na pasta pessoal do usuario root
# (/root/.cache/ms-playwright). O Render roda o container como um usuario sem
# privilegios ("sandbox"), que nao enxerga essa pasta - por isso o app dava erro
# "Executable doesn't exist" em runtime. Fixando o caminho num diretorio proprio
# e liberando leitura/execucao pra qualquer usuario, o navegador fica acessivel
# independente de quem estiver rodando o container.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium \
    && chmod -R o+rX /ms-playwright

COPY . .

# threads=1 e proposital: cada requisicao abre um Chromium inteiro. Com mais de
# uma thread, duas buscas simultaneas abririam dois navegadores ao mesmo tempo e
# estourariam a RAM do plano gratis (512MB). Com 1, a segunda requisicao so
# espera a primeira terminar em vez de derrubar o servidor.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 1 --timeout 280 app:app"]
