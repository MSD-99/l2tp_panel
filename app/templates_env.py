from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.i18n import translate
from app.settings import load_settings

templates = Jinja2Templates(directory="app/templates")


@pass_context
def t(context, key: str, **kwargs) -> str:
    request = context["request"]
    lang = getattr(request.state, "lang", "fa")
    default = kwargs.pop("default", None)
    from app.i18n import TRANSLATIONS
    if default is not None and key not in TRANSLATIONS:
        text = default
    else:
        text = translate(key, lang)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


@pass_context
def current_lang(context) -> str:
    request = context["request"]
    return getattr(request.state, "lang", "fa")


@pass_context
def show_ssl_warning(context) -> bool:
    """Small, non-blocking nudge: plain HTTP + no configured domain/SSL."""
    request = context["request"]
    settings = load_settings()
    if settings.get("ssl_enabled"):
        return False
    return request.url.scheme != "https"


templates.env.globals["t"] = t
templates.env.globals["current_lang"] = current_lang
templates.env.globals["show_ssl_warning"] = show_ssl_warning
