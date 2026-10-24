# -*- coding: utf-8 -*-
import re


class StructuredContextSplitter:
    MAX_CHUNK_SIZE = 6000

    @classmethod
    def split(cls, text: str) -> list[dict]:
        lines = (text or "").splitlines()
        chunks = []
        current = []
        title_path = []
        in_code = False

        def flush():
            content = "\n".join(current).strip()
            if content:
                chunks.extend(cls._split_large(content, title_path))
            current.clear()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
            heading = re.match(r"^(#{1,6})\s+(.+)$", stripped) if not in_code else None
            if heading:
                flush()
                level = len(heading.group(1))
                title_path[level - 1:] = [heading.group(2).strip()]
            elif not in_code and not stripped and len("\n".join(current)) >= 1200:
                flush()
                continue
            current.append(line)
        flush()
        return [
            {**item, "index": index}
            for index, item in enumerate(chunks, start=1)
        ]

    @classmethod
    def _split_large(cls, content: str, title_path: list[str]) -> list[dict]:
        if len(content) <= cls.MAX_CHUNK_SIZE:
            return [{"title_path": list(title_path), "content": content}]
        parts = []
        start = 0
        while start < len(content):
            end = min(start + cls.MAX_CHUNK_SIZE, len(content))
            split_at = max(content.rfind("\n\n", start, end), content.rfind("\n", start, end))
            if split_at > start + cls.MAX_CHUNK_SIZE // 2:
                end = split_at
            parts.append({"title_path": list(title_path), "content": content[start:end].strip()})
            start = end
        return [item for item in parts if item["content"]]
