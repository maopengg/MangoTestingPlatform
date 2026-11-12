"""Single-use MCP confirmations in shared, non-evictable runtime storage."""

import hashlib
import json
import logging
import secrets

from pydantic import ValidationError

from src.apps.system.enums.mcp_confirmation import McpConfirmationStatusEnum
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.exceptions import SYSTEM_RUNTIME_KV_CORRUPT, SYSTEM_RUNTIME_KV_INVALID, SystemError
from src.apps.system.schemas.mcp_confirmation import McpConfirmationBindingSchema
from src.apps.system.services.runtime_kv import RuntimeKV


logger = logging.getLogger(__name__)


class McpConfirmationService:
    @staticmethod
    def _key(user_id: int, action: str, target_id: int | str, token: str) -> str:
        binding = json.dumps([user_id, action, str(target_id), token], ensure_ascii=True, separators=(',', ':'))
        return hashlib.sha256(binding.encode('utf-8')).hexdigest()

    @classmethod
    def issue(cls, user_id: int, action: str, target_id: int | str, confirm_text: str, ttl_seconds: int = 600) -> str:
        logger.info('event=mcp_confirmation_issue user_id=%s', user_id)
        try:
            try:
                payload = McpConfirmationBindingSchema.model_validate({
                    'user_id': user_id, 'action': action, 'target_id': str(target_id), 'confirm_text': confirm_text,
                }, strict=True)
            except ValidationError as error:
                raise SystemError(SYSTEM_RUNTIME_KV_INVALID) from error
            if type(ttl_seconds) is not int or not 0 < ttl_seconds <= 2147483647:
                raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
            token = secrets.token_urlsafe(24)
            store = RuntimeKV.namespace(RuntimeKVNamespaceEnum.MCP_CONFIRMATION)
            store.set(cls._key(user_id, action, target_id, token), payload.model_dump(), ttl=ttl_seconds)
        except Exception as error:
            logger.error('event=mcp_confirmation_issue_failed user_id=%s error_type=%s', user_id, type(error).__name__)
            raise
        logger.info('event=mcp_confirmation_issued user_id=%s ttl_seconds=%s', user_id, ttl_seconds)
        return token

    @classmethod
    def consume(cls, user_id: int, action: str, target_id: int | str,
                token: str, confirm_text: str) -> McpConfirmationStatusEnum:
        logger.info('event=mcp_confirmation_consume user_id=%s', user_id)
        try:
            store = RuntimeKV.namespace(RuntimeKVNamespaceEnum.MCP_CONFIRMATION)
            key = cls._key(user_id, action, target_id, token)
            entry = store.get_entry(key)
            if not entry.found:
                logger.info('event=mcp_confirmation_missing user_id=%s', user_id)
                return McpConfirmationStatusEnum.EXPIRED
            try:
                payload = McpConfirmationBindingSchema.model_validate(entry.value, strict=True)
            except ValidationError as error:
                raise SystemError(SYSTEM_RUNTIME_KV_CORRUPT) from error
            if (payload.user_id, payload.action, payload.target_id) != (user_id, action, str(target_id)):
                logger.warning('event=mcp_confirmation_binding_mismatch user_id=%s', user_id)
                return McpConfirmationStatusEnum.EXPIRED
            if payload.confirm_text != confirm_text:
                logger.info('event=mcp_confirmation_text_mismatch user_id=%s', user_id)
                return McpConfirmationStatusEnum.TEXT_MISMATCH
            # Recheck both version and expiry under the store's row lock before accepting.
            if not store.delete_if_version(key, entry.version):
                logger.info('event=mcp_confirmation_consume_conflict user_id=%s', user_id)
                return McpConfirmationStatusEnum.EXPIRED
        except Exception as error:
            logger.error('event=mcp_confirmation_consume_failed user_id=%s error_type=%s', user_id, type(error).__name__)
            raise
        logger.info('event=mcp_confirmation_consumed user_id=%s', user_id)
        return McpConfirmationStatusEnum.ACCEPTED
