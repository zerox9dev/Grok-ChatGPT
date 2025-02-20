from bot.locales.lang import texts  # Импортируем тексты


def get_text(key: str, language_code: str = "en", **kwargs) -> str:
    """Возвращает текст на нужном языке."""
    lang_texts = texts.get(language_code, texts["en"])
    return lang_texts.get(key, key).format(**kwargs)
