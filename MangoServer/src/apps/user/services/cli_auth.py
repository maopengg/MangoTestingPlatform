import base64
import hashlib
import re
import secrets
from urllib.parse import urlsplit

from django.core.cache import cache


class CliAuthService:
    """Exchange a page session for a short-lived, one-time CLI authorization code."""

    CACHE_PREFIX = 'cli:auth:code:v1:'
    CODE_TTL_SECONDS = 60
    STATE_PATTERN = re.compile(r'^[A-Za-z0-9_-]{32,128}$')
    PKCE_PATTERN = re.compile(r'^[A-Za-z0-9_-]{43,128}$')

    @classmethod
    def validate_redirect_uri(cls, value: str | None) -> bool:
        if not value:
            return False
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            return False
        return (
                parsed.scheme == 'http'
                and parsed.hostname == '127.0.0.1'
                and parsed.username is None
                and parsed.password is None
                and port is not None
                and 1024 <= port <= 65535
                and parsed.path == '/callback'
                and not parsed.query
                and not parsed.fragment
        )

    @classmethod
    def create_code(cls, *, token: str, user, redirect_uri: str, state: str, code_challenge: str):
        if not cls.validate_redirect_uri(redirect_uri):
            return None
        if not cls.STATE_PATTERN.fullmatch(state or ''):
            return None
        if not cls.PKCE_PATTERN.fullmatch(code_challenge or ''):
            return None
        code = secrets.token_urlsafe(32)
        cache.set(cls._cache_key(code), {
            'token': token,
            'code_challenge': code_challenge,
            'redirect_uri': redirect_uri,
            'user_id': user.id,
            'username': user.username,
        }, cls.CODE_TTL_SECONDS)
        return {'code': code, 'expires_in': cls.CODE_TTL_SECONDS}

    @classmethod
    def exchange_code(cls, *, code: str, code_verifier: str, redirect_uri: str):
        if not code or not cls.PKCE_PATTERN.fullmatch(code_verifier or ''):
            return None
        key = cls._cache_key(code)
        authorization = cache.get(key)
        if not authorization:
            return None
        # Every exchange attempt consumes the code, including a failed verifier attempt.
        cache.delete(key)
        if authorization.get('redirect_uri') != redirect_uri:
            return None
        challenge = cls._pkce_challenge(code_verifier)
        if not secrets.compare_digest(challenge, authorization.get('code_challenge', '')):
            return None
        return {
            'token': authorization['token'],
            'user_id': authorization['user_id'],
            'username': authorization['username'],
        }

    @classmethod
    def _cache_key(cls, code: str) -> str:
        digest = hashlib.sha256(code.encode('utf-8')).hexdigest()
        return f'{cls.CACHE_PREFIX}{digest}'

    @staticmethod
    def _pkce_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
