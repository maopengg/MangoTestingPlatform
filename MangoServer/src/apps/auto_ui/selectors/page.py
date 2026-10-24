"""页面查询使用的标准化规则。"""


def normalize_page_url(url: str | None) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    if value == "/":
        return "/"
    return value.rstrip("/")
