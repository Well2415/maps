# Gerador de Leads via Google Maps (100% gratuito)

Web app local que busca empresas no Google Maps por segmento (advocacia, contabilidade,
dentista, etc.) e cidade, filtra as que **nao tem site cadastrado** e gera um link do
WhatsApp (`wa.me`) pronto, com mensagem pre-preenchida, para cada uma.

## Como funciona

1. Voce digita o tipo de empresa, a cidade e (opcional) o link do seu site/portfolio no
   formulario.
2. Um navegador automatizado (Playwright + Chromium) abre o Google Maps, faz a busca e
   le os resultados da pagina — nome, endereco, telefone, site e avaliacao.
3. Empresas que ja tem site proprio sao descartadas. Ficam so as que "precisam de site":
   sem nenhum site, ou so com link de Facebook/Instagram cadastrado (muito comum em
   pequenos negocios, e ainda conta como lead pra quem vende sites).
4. Para cada uma, e gerado um link `https://wa.me/<telefone>?text=<mensagem>` com a
   mensagem ja escrita — incluindo o link do seu site/portfolio, se voce preencheu.
5. Da para baixar tudo em CSV, ou usar o **modo de disparo assistido** (veja abaixo) pra
   percorrer os leads um por um mais rapido.

**Nao usa nenhuma API paga do Google** — nao precisa de conta no Google Cloud, chave de
API nem cartao de credito.

### Sobre automacao de envio no WhatsApp

Este projeto **nao envia mensagens sozinho**. Ele so gera o link e a mensagem prontos —
quem aperta "Enviar" dentro do WhatsApp e sempre voce. Isso e proposital: automatizar o
disparo de primeiro contato para numeros que nunca falaram com voce (via bot/WhatsApp Web
nao oficial, ou mesmo via API oficial da Meta sem opt-in) viola os Termos de Servico do
WhatsApp e as politicas da Meta, e o risco real e seu numero ser banido, alem de ser
considerado spam.

O que existe pra deixar o processo rapido sem cruzar essa linha e o **modo de disparo
assistido**: depois de uma busca, clique em "Iniciar disparo assistido" — ele abre uma
tela que mostra um lead por vez, com botao "Abrir WhatsApp e enviar". Voce clica, manda a
mensagem (ja personalizada e com seu link) dentro do proprio WhatsApp, volta pra aba e
clica "Marquei como enviado, proximo" pra ir pro seguinte. Continua sendo voce que envia
cada mensagem, mas sem precisar caçar telefone por telefone na tabela.

> **Importante:** este metodo le a pagina publica do Google Maps diretamente (scraping),
> o que **nao e o metodo oficialmente suportado pelo Google** e tecnicamente viola os
> Termos de Servico dele. Ele pode parar de funcionar se o Google mudar o layout da
> pagina, e uso muito intenso/repetido pode levar a bloqueios temporarios de IP. Para um
> uso mais pesado e estavel a longo prazo, o caminho oficial e a Google Places API (paga,
> com cota gratis mensal) — se algum dia isso virar um problema, e so pedir para trocar
> a fonte de dados.

## 1. Instalar dependencias

```powershell
# criar e ativar um ambiente virtual (recomendado)
python -m venv venv
venv\Scripts\activate

# instalar dependencias Python
pip install -r requirements.txt

# baixar o navegador usado pelo Playwright (so precisa fazer uma vez)
playwright install chromium
```

## 2. (Opcional) Configurar variaveis de ambiente

```powershell
copy .env.example .env
```

Valores no `.env`:
- `SECRET_KEY` — qualquer string aleatoria (nao obrigatorio pra rodar localmente).
- `PORTFOLIO_LINK` — link do seu site/portfolio, usado como valor padrao no campo
  "Link do seu site/portfolio" do formulario (voce ainda pode trocar por busca, se quiser).

## 3. Rodar

```powershell
python app.py
```

Acesse http://127.0.0.1:5000 no navegador.

## Estrutura do projeto

```
app.py                -> rotas Flask (formulario, busca, export CSV)
maps_scraper.py        -> scraping do Google Maps via Playwright
whatsapp.py             -> geracao dos links wa.me com mensagem pre-preenchida
templates/index.html   -> pagina (formulario + tabela de resultados)
static/style.css       -> estilo da pagina
```

## Limitacoes e observacoes importantes

- A busca roda **de forma sincrona** enquanto voce espera na pagina — quanto maior o
  numero de resultados escolhido, mais tempo demora (cada empresa exige abrir a pagina
  de detalhes dela). Comece com valores baixos (10-20) para testar.
- O layout do Google Maps muda com frequencia; se a busca comecar a retornar tudo vazio,
  os seletores em `maps_scraper.py` provavelmente precisam de ajuste.
- Em uso muito repetido/rapido, o Google pode exibir captcha ou bloquear temporariamente
  o IP. Se isso acontecer, espere um tempo antes de tentar de novo e evite rodar buscas
  em sequencia muito rapida.
- O link do WhatsApp so e gerado se a empresa tiver telefone visivel na ficha do Google
  Maps.
- **Uso responsavel**: este projeto so gera o link de contato — o envio da mensagem e
  sempre uma acao manual sua, clicando no botao. Evite qualquer automacao de disparo em
  massa pelo WhatsApp: isso viola os Termos de Servico do WhatsApp e pode ser considerado
  spam. Ao entrar em contato, personalize a mensagem e respeite a LGPD (ex: pare de
  contatar quem pedir para nao ser mais contatado).
