import json
from pathlib import Path

# ================================================
# Загрузка и управление локализацией
# ================================================

def load_locale(language: str) -> dict:
    # Загружает тексты для указанного языка из JSON файла
    locale_file = Path(__file__).parent.parent / "locales" / f"{language}.json"
    
    try:
        with open(locale_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Если файл языка не найден, загружаем русский как fallback
        fallback_file = Path(__file__).parent.parent / "locales" / "ru.json"
        with open(fallback_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        # В случае любых других ошибок возвращаем минимальный набор
        return {"error": "Ошибка загрузки локализации"}

# ================================================
# Словарь с загруженными текстами
# ================================================
texts = {
    "ru": load_locale("ru"),
    "en": load_locale("en"),
    "uk": load_locale("uk")
}

def get_text(key: str, language_code: str = "en", **kwargs) -> str:
    # Возвращает локализованный текст на нужном языке
    lang_texts = texts.get(language_code, texts["en"])
    text_template = lang_texts.get(key, key)
    
    try:
        return text_template.format(**kwargs)
    except KeyError as e:
        # Если не хватает параметров для форматирования, возвращаем как есть
        return text_template
    except Exception:
        # В случае любых других ошибок возвращаем ключ
        return key
