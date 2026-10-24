# -*- coding: utf-8 -*-


from src.apps.ai.exceptions import ai_service_error


class AgentDocumentService:
    @staticmethod
    def read_document(source_url: str = "", source_content: str = "") -> dict:
        content = source_content or ""
        url = source_url or ""
        if url and "feishu.cn" in url and not content:
            raise ai_service_error("飞书文档自动读取暂未接入，请粘贴文档正文或先保存为上下文资料")
        return {
            "url": url,
            "content": content,
            "revision": "",
        }
