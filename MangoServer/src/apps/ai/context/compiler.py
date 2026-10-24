# -*- coding: utf-8 -*-
from src.apps.ai.context.retriever import StructuredContextRetriever
from src.apps.ai.context.splitter import StructuredContextSplitter


class StructuredContextCompiler:
    @classmethod
    def select(cls, text: str, query: str, limit: int) -> str:
        content = text or ""
        if len(content) <= limit:
            return content
        chunks = StructuredContextSplitter.split(content)
        selected = StructuredContextRetriever.select(chunks, query, limit)
        rendered = []
        for item in selected:
            title = " / ".join(item.get("title_path") or [])
            body = str(item.get("content") or "")
            rendered.append(f"[章节：{title}]\n{body}" if title else body)
        return "\n\n".join(rendered)[:limit]
