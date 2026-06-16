# -*- coding: utf-8 -*-


class FunctionalCaseContentSplitter:
    @classmethod
    def split_content(cls, content: str, chunk_size: int) -> list[str]:
        text = content or ""
        if len(text) <= chunk_size:
            return [text]
        table_chunks = cls.split_markdown_table_rows(text, chunk_size)
        if table_chunks:
            return table_chunks
        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            split_at = max(text.rfind("\n## ", start, end), text.rfind("\n|", start, end), text.rfind("\n", start, end))
            if split_at > start + chunk_size // 2:
                end = split_at
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start = max(end - 600, 0)
        return chunks

    @staticmethod
    def split_markdown_table_rows(text: str, chunk_size: int) -> list[str]:
        lines = text.splitlines()
        table_lines = [line for line in lines if line.strip().startswith("|") and line.strip().endswith("|")]
        if len(table_lines) < 20:
            return []
        prefix = []
        for line in lines:
            if line.strip().startswith("|") and line.strip().endswith("|"):
                break
            prefix.append(line)
        header = table_lines[:2]
        rows = table_lines[2:]
        chunks = []
        current = prefix + header
        for row in rows:
            candidate = "\n".join([*current, row])
            if len(candidate) > chunk_size and len(current) > len(prefix) + len(header):
                chunks.append("\n".join(current))
                current = prefix + header + [row]
            else:
                current.append(row)
        if len(current) > len(prefix) + len(header):
            chunks.append("\n".join(current))
        return chunks
