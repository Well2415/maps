"""Scraper do Google Maps via Playwright (sem API key, sem custo).

Aviso: isso navega diretamente na pagina publica do Google Maps, o que nao
e o metodo oficialmente suportado pelo Google (viola os Termos de Servico
dele) e pode quebrar quando o Google mudar o HTML da pagina, ou ser
bloqueado em uso muito intenso. Use com moderacao.
"""
import re
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

# Muitos pequenos negocios cadastram um link de rede social no campo "site" do
# Google Maps, em vez de um site proprio de verdade. Para quem vende sites,
# isso ainda conta como lead (a empresa nao tem presenca web propria).
_DOMINIOS_REDE_SOCIAL = (
    "facebook.com",
    "instagram.com",
    "m.me",
    "linktr.ee",
    "wa.me",
    "web.whatsapp.com",
)

SEARCH_URL_TEMPLATE = "https://www.google.com/maps/search/{query}?hl=pt-BR"
CONSENT_BUTTON_TEXTS = ["Aceitar tudo", "Rejeitar tudo", "Accept all", "I agree"]

# Icon fonts do Google usam a Private Use Area do Unicode (U+E000-U+F8FF) para
# desenhar iconezinhos dentro de elementos de texto; e preciso remover isso do
# texto extraido, senao o nome/endereco vem com lixo binario junto. Os ranges
# sao montados a partir dos codepoints (em vez de caracteres literais no
# codigo-fonte) para evitar problemas de encoding do proprio arquivo.
_ICONE_RANGES = [
    (0xE000, 0xF8FF),  # Private Use Area (icon fonts)
    (0x200B, 0x200F),  # espacos/marcas de largura zero
    (0x202A, 0x202E),  # marcas de direcao de texto (bidi)
    (0xFE0F, 0xFE0F),  # variation selector (emoji)
]
_ICONE_OU_CONTROLE_RE = re.compile(
    "[" + "".join("\\u{:04x}-\\u{:04x}".format(ini, fim) for ini, fim in _ICONE_RANGES) + "]"
)


class ScraperError(Exception):
    pass


def _limpar_texto(texto):
    if not texto:
        return texto
    texto = _ICONE_OU_CONTROLE_RE.sub("", texto)
    return texto.strip()


def _accept_consent_if_present(page):
    for texto in CONSENT_BUTTON_TEXTS:
        try:
            botao = page.get_by_role("button", name=texto)
            if botao.count() > 0:
                botao.first.click(timeout=2000)
                page.wait_for_timeout(500)
                return
        except Exception:
            continue


def _coletar_links(page, max_results):
    try:
        page.wait_for_selector('a[href*="/maps/place/"]', timeout=15000)
    except Exception:
        return []

    hrefs = []
    seen = set()
    rodadas_sem_novidade = 0
    anterior = 0

    while len(hrefs) < max_results and rodadas_sem_novidade < 4:
        anchors = page.locator('a[href*="/maps/place/"]')
        count = anchors.count()
        for i in range(count):
            href = anchors.nth(i).get_attribute("href")
            if href and href not in seen:
                seen.add(href)
                hrefs.append(href)

        if len(hrefs) == anterior:
            rodadas_sem_novidade += 1
        else:
            rodadas_sem_novidade = 0
        anterior = len(hrefs)

        try:
            page.mouse.wheel(0, 2200)
        except Exception:
            break
        page.wait_for_timeout(1400)

    return hrefs[:max_results]


def _extrair_detalhes(page, url):
    try:
        page.goto(url, timeout=30000)
        page.wait_for_selector("h1", timeout=10000)
        page.wait_for_timeout(800)
    except Exception:
        return None

    nome = "Empresa sem nome"
    try:
        h1 = page.locator("h1").first
        if h1.count() > 0:
            texto = _limpar_texto(h1.inner_text(timeout=2000))
            if texto:
                nome = texto
    except Exception:
        pass

    website = None
    try:
        website_btn = page.locator('a[data-item-id="authority"]').first
        if website_btn.count() > 0:
            website = website_btn.get_attribute("href")
    except Exception:
        pass

    telefone = None
    try:
        phone_btn = page.locator('button[data-item-id^="phone:tel:"]').first
        if phone_btn.count() > 0:
            data_item_id = phone_btn.get_attribute("data-item-id") or ""
            match = re.search(r"phone:tel:(.+)", data_item_id)
            if match:
                telefone = match.group(1)
    except Exception:
        pass

    endereco = None
    try:
        addr_btn = page.locator('button[data-item-id="address"]').first
        if addr_btn.count() > 0:
            endereco = _limpar_texto(addr_btn.inner_text(timeout=2000))
    except Exception:
        pass

    rating = None
    qtd_avaliacoes = None
    try:
        rating_el = page.locator('div.F7nice span[aria-hidden="true"]').first
        if rating_el.count() > 0:
            rating = _limpar_texto(rating_el.inner_text(timeout=1500)).replace(",", ".")
        count_el = page.locator('div.F7nice span[aria-label*="avalia"]').first
        if count_el.count() > 0:
            aria = count_el.get_attribute("aria-label") or ""
            match = re.search(r"([\d.,]+)", aria)
            if match:
                qtd_avaliacoes = match.group(1)
    except Exception:
        pass

    return {
        "nome": nome,
        "endereco": endereco or "",
        "telefone": telefone,
        "website": website,
        "rating": rating,
        "qtd_avaliacoes": qtd_avaliacoes,
        "url": url,
    }


def search_places(query, max_results=20, headless=True):
    """Busca no Google Maps e retorna lista de dicts com dados de cada empresa."""
    resultados = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                locale="pt-BR",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            url_busca = SEARCH_URL_TEMPLATE.format(query=query.replace(" ", "+"))
            page.goto(url_busca, timeout=60000)
            _accept_consent_if_present(page)

            links = _coletar_links(page, max_results)
            if not links:
                browser.close()
                return resultados

            for link in links:
                detalhe = _extrair_detalhes(page, link)
                if detalhe:
                    resultados.append(detalhe)

            browser.close()
    except Exception as e:
        raise ScraperError(
            "Nao foi possivel concluir a busca no Google Maps. "
            "Verifique sua conexao e se o navegador do Playwright foi instalado "
            f"('playwright install chromium'). Detalhe: {e}"
        )

    return resultados


def classificar_presenca_web(website):
    """Retorna 'sem_site', 'so_rede_social' ou 'tem_site'."""
    if not website:
        return "sem_site"
    dominio = urlparse(website).netloc.lower()
    for social in _DOMINIOS_REDE_SOCIAL:
        if social in dominio:
            return "so_rede_social"
    return "tem_site"


def filter_leads(places):
    """Mantem empresas sem site proprio (sem_site ou so_rede_social) e marca o status."""
    leads = []
    for p in places:
        status = classificar_presenca_web(p.get("website"))
        if status == "tem_site":
            continue
        lead = dict(p)
        lead["status_web"] = status
        leads.append(lead)
    return leads
