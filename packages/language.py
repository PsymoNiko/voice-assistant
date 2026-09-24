from langdetect import detect


def detect_language(text: str) -> str:
    if not text.strip():
        return "en-US"
    try:
        language = detect(text)
    except Exception:
        language = "en"
    return {"fa": "fa-IR", "ru": "ru-RU", "tr": "tr-TR", "en": "en-US"}.get(language, f"{language}-XX")


def normalize_persian(text: str) -> str:
    replacements = {
        "Nginx": "اِن‌جینِکس", "Docker": "داکر", "Kubernetes": "کوبِرنِتِیز",
        "PostgreSQL": "پُستگرِس", "Redis": "رِدیس", "API": "اِی‌پی‌آی", "SSH": "اِس‌اِس‌اِچ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text
