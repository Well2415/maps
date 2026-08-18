"""Geracao de links do WhatsApp (wa.me) com mensagem pre-preenchida."""
import re
import urllib.parse

DEFAULT_MESSAGE_TEMPLATE = (
    "Ola! Vi que a {nome} ainda nao possui um site e gostaria de apresentar "
    "um servico de criacao de sites e landing pages para ajudar a atrair mais clientes. "
    "Da uma olhada em alguns exemplos do meu trabalho: {link}\n"
    "Podemos conversar?"
)


def format_phone_digits(phone):
    """Remove tudo que nao for digito. wa.me espera codigo do pais + DDD + numero, sem simbolos."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    return digits or None


def _montar_mensagem(template, business_name, link):
    if not link:
        # remove a linha/frase que menciona o link quando nao ha um configurado,
        # em vez de deixar "{link}" sobrando ou uma frase quebrada no meio da mensagem.
        template = "\n".join(
            linha for linha in template.split("\n") if "{link}" not in linha
        )
    try:
        return template.format(nome=business_name, link=link or "")
    except (KeyError, IndexError):
        return template


def build_whatsapp_link(phone, business_name, message_template=None, link=None):
    digits = format_phone_digits(phone)
    if not digits:
        return None
    template = message_template or DEFAULT_MESSAGE_TEMPLATE
    message = _montar_mensagem(template, business_name, link)
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{digits}?text={encoded_message}"
