import csv
import io
import json
import os

from dotenv import load_dotenv
from flask import Flask, Response, render_template, request

from maps_scraper import ScraperError, filter_leads, search_places
from whatsapp import DEFAULT_MESSAGE_TEMPLATE, build_whatsapp_link

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

MAX_RESULTS_PADRAO = 15
MAX_RESULTS_MINIMO = 5
# Limitado a 25 pra caber no plano gratis do Render (512MB de RAM): cada
# resultado abre uma pagina de detalhes inteira no Chromium, entao um numero
# alto demais derruba o servidor (memoria) ou estoura o timeout da requisicao.
MAX_RESULTS_LIMITE = 25
PORTFOLIO_LINK_PADRAO = os.environ.get("PORTFOLIO_LINK", "")

STATUS_LABELS = {
    "sem_site": "Sem site",
    "so_rede_social": "So rede social",
}


def _leads_json_seguro(leads):
    # escapa "</" para o JSON poder ser embutido dentro de uma tag <script> sem
    # risco de um nome de empresa vindo do Maps conter "</script>" e quebrar a pagina.
    return json.dumps(leads, ensure_ascii=False).replace("</", "<\\/")


def montar_leads(tipo_empresa, cidade, mensagem_template, max_results, link_portfolio):
    query = f"{tipo_empresa} em {cidade}" if cidade else tipo_empresa
    places = search_places(query, max_results=max_results)
    sem_site = filter_leads(places)

    leads = []
    for p in sem_site:
        nome = p.get("nome", "Empresa sem nome")
        endereco = p.get("endereco", "")
        telefone = p.get("telefone")
        link = (
            build_whatsapp_link(telefone, nome, mensagem_template, link_portfolio)
            if telefone
            else None
        )
        leads.append(
            {
                "nome": nome,
                "endereco": endereco,
                "telefone": telefone or "Nao informado",
                "avaliacao": p.get("rating"),
                "qtd_avaliacoes": p.get("qtd_avaliacoes"),
                "status_web": STATUS_LABELS.get(p.get("status_web"), ""),
                "whatsapp_link": link,
            }
        )
    return leads


@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        leads=None,
        tipo_empresa="",
        cidade="",
        mensagem=DEFAULT_MESSAGE_TEMPLATE,
        link_portfolio=PORTFOLIO_LINK_PADRAO,
        max_results=MAX_RESULTS_PADRAO,
        max_results_minimo=MAX_RESULTS_MINIMO,
        max_results_limite=MAX_RESULTS_LIMITE,
        erro=None,
        total=None,
        leads_json="[]",
    )


@app.route("/buscar", methods=["POST"])
def buscar():
    tipo_empresa = request.form.get("tipo_empresa", "").strip()
    cidade = request.form.get("cidade", "").strip()
    mensagem = request.form.get("mensagem", "").strip() or DEFAULT_MESSAGE_TEMPLATE
    link_portfolio = request.form.get("link_portfolio", "").strip() or PORTFOLIO_LINK_PADRAO

    try:
        max_results = int(request.form.get("max_results", MAX_RESULTS_PADRAO))
    except ValueError:
        max_results = MAX_RESULTS_PADRAO
    max_results = max(MAX_RESULTS_MINIMO, min(max_results, MAX_RESULTS_LIMITE))

    erro = None
    leads = []

    if not tipo_empresa:
        erro = "Informe o tipo de empresa (ex: advocacia, contabilidade, dentista)."
    else:
        try:
            leads = montar_leads(tipo_empresa, cidade, mensagem, max_results, link_portfolio)
        except ScraperError as e:
            erro = str(e)
        except Exception as e:  # falha inesperada de navegador/rede
            erro = f"Falha inesperada ao buscar no Google Maps: {e}"

    return render_template(
        "index.html",
        leads=leads,
        tipo_empresa=tipo_empresa,
        cidade=cidade,
        mensagem=mensagem,
        link_portfolio=link_portfolio,
        max_results=max_results,
        max_results_minimo=MAX_RESULTS_MINIMO,
        max_results_limite=MAX_RESULTS_LIMITE,
        erro=erro,
        total=len(leads),
        leads_json=_leads_json_seguro(leads),
    )


@app.route("/exportar-csv", methods=["POST"])
def exportar_csv():
    tipo_empresa = request.form.get("tipo_empresa", "leads")
    cidade = request.form.get("cidade", "")
    leads_json = request.form.get("leads_json", "[]")

    try:
        leads = json.loads(leads_json)
    except json.JSONDecodeError:
        leads = []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Nome", "Endereco", "Telefone", "Status Web", "Avaliacao", "Qtd Avaliacoes", "Link WhatsApp"])
    for lead in leads:
        writer.writerow(
            [
                lead.get("nome", ""),
                lead.get("endereco", ""),
                lead.get("telefone", ""),
                lead.get("status_web", ""),
                lead.get("avaliacao") or "",
                lead.get("qtd_avaliacoes") or "",
                lead.get("whatsapp_link") or "",
            ]
        )

    filename = f"leads_{tipo_empresa}_{cidade}.csv".replace(" ", "_")
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
