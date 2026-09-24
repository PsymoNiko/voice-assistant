from packages.language import detect_language, normalize_persian
from packages.response_processor import process_markdown


def test_language_and_normalization():
    assert "رِدیس" in normalize_persian("Redis")
    assert detect_language("hello world").startswith("en")


def test_markdown_policy():
    blocks, speech = process_markdown("Hello\n\n```python\nprint(1)\n```")
    assert blocks[0]["type"] == "text"
    assert any(block["type"] == "code" for block in blocks)
    assert "code example" in speech
