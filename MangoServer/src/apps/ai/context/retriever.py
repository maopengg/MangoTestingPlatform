# -*- coding: utf-8 -*-
import re


class StructuredContextRetriever:
    @staticmethod
    def terms(query: str) -> set[str]:
        text = (query or "").lower()
        terms = {
            token
            for token in re.split(r"[^a-zA-Z0-9_\u4e00-\u9fff]+", text)
            if len(token) >= 2
        }
        terms.update(text[index:index + 4] for index in range(0, max(len(text) - 3, 0), 4))
        return {item for item in terms if item}

    @classmethod
    def select(cls, chunks: list[dict], query: str, limit: int) -> list[dict]:
        terms = cls.terms(query)
        scored = []
        for chunk in chunks:
            title = " / ".join(chunk.get("title_path") or []).lower()
            content = str(chunk.get("content") or "")
            normalized = content.lower()
            score = sum(5 for term in terms if term in title)
            score += sum(2 for term in terms if term in normalized)
            if chunk.get("index") == 1:
                score += 1
            scored.append((score, int(chunk.get("index") or 0), chunk))

        selected = []
        size = 0
        for _, _, chunk in sorted(scored, key=lambda item: (-item[0], item[1])):
            content = str(chunk.get("content") or "")
            if selected and size + len(content) > limit:
                continue
            selected.append(chunk)
            size += len(content)
            if size >= limit:
                break
        return sorted(selected, key=lambda item: int(item.get("index") or 0))
