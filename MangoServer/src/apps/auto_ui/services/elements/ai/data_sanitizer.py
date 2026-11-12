# -*- coding: utf-8 -*-
import re
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.utils import timezone


class ElementAiDataSanitizer:
    """Server-side safety boundary for browser-derived element context."""

    SENSITIVE_KEY = re.compile(
        r'(password|passwd|pwd|token|secret|authorization|cookie|session|api[-_]?key|access[-_]?key)',
        re.I,
    )
    SENSITIVE_ASSIGNMENT = re.compile(
        r'(?i)((?:password|passwd|pwd|token|secret|authorization|cookie|session|api[-_]?key|access[-_]?key)'
        r'\s*[=:]\s*)([^\s"\'<>;&]+)',
    )
    BEARER = re.compile(r'(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}')
    JWT = re.compile(r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b')
    EMAIL = re.compile(r'(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])')
    PHONE = re.compile(r'(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)')
    LONG_NUMBER = re.compile(r'(?<!\d)\d{12,19}(?!\d)')
    VALUE_ATTRIBUTE = re.compile(r'(?i)(\svalue\s*=\s*)(["\']).*?\2', re.S)
    TEXTAREA = re.compile(r'(?is)(<textarea\b[^>]*>).*?(</textarea>)')

    @classmethod
    def datetime_text(cls, value) -> str:
        """Normalize executor and database datetimes for UI responses."""
        if value in (None, ''):
            return ''
        parsed = value
        if isinstance(value, str):
            source = value.strip()
            try:
                parsed = datetime.fromisoformat(source[:-1] + '+00:00' if source.endswith('Z') else source)
            except ValueError:
                return cls.text(source, 64)
        if not isinstance(parsed, datetime):
            return cls.text(parsed, 64)
        if timezone.is_aware(parsed):
            parsed = timezone.localtime(parsed)
        return parsed.strftime('%Y-%m-%d %H:%M:%S')

    @classmethod
    def text(cls, value, limit: int | None = None) -> str:
        text = str(value or '')
        text = cls.BEARER.sub(r'\1 [REDACTED]', text)
        text = cls.JWT.sub('[REDACTED_JWT]', text)
        text = cls.SENSITIVE_ASSIGNMENT.sub(r'\1[REDACTED]', text)
        text = cls.EMAIL.sub('[REDACTED_EMAIL]', text)
        text = cls.PHONE.sub('[REDACTED_PHONE]', text)
        text = cls.LONG_NUMBER.sub('[REDACTED_NUMBER]', text)
        return text if limit is None else text[:limit]

    @classmethod
    def html(cls, value, limit: int) -> str:
        text = cls.text(value)
        text = cls.VALUE_ATTRIBUTE.sub(r'\1\2[REDACTED]\2', text)
        text = cls.TEXTAREA.sub(r'\1[REDACTED]\2', text)
        return text[:limit]

    @classmethod
    def url(cls, value, limit: int = 20000) -> str:
        value = str(value or '')
        try:
            parts = urlsplit(value)
            query = []
            for key, item in parse_qsl(parts.query, keep_blank_values=True):
                query.append((key, '[REDACTED]' if cls.SENSITIVE_KEY.search(key) else cls.text(item, 200)))
            return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))[:limit]
        except Exception:
            return cls.text(value, limit)

    @classmethod
    def json_value(cls, value, depth: int = 0):
        if depth > 8:
            return '[TRUNCATED]'
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                key_text = str(key)[:120]
                result[key_text] = '[REDACTED]' if cls.SENSITIVE_KEY.search(key_text) else cls.json_value(item,
                                                                                                          depth + 1)
            return result
        if isinstance(value, (list, tuple)):
            return [cls.json_value(item, depth + 1) for item in value[:200]]
        if isinstance(value, str):
            return cls.text(value, 2000)
        return value

    @classmethod
    def attributes(cls, value) -> dict:
        result = {}
        for key, item in (value or {}).items():
            key_text = str(key)[:120]
            if cls.SENSITIVE_KEY.search(key_text):
                continue
            result[key_text] = cls.text(item, 500)
        return result

    @classmethod
    def snapshot(cls, data: dict) -> dict:
        value = dict(data or {})
        value['url'] = cls.url(value.get('url'))
        value['frame_url'] = cls.url(value.get('frame_url'))
        value['title'] = cls.text(value.get('title'), 512)
        value['element_text'] = cls.text(value.get('element_text'), 2000)
        value['element_name'] = cls.text(value.get('element_name'), 512)
        value['element_placeholder'] = cls.text(value.get('element_placeholder'), 512)
        value['element_value'] = ''
        value['element_attributes'] = cls.attributes(value.get('element_attributes'))
        value['outer_html'] = cls.html(value.get('outer_html'), 8000)
        value['parent_html'] = cls.html(value.get('parent_html'), 16000)
        value['nearby_html'] = cls.html(value.get('nearby_html'), 20000)
        value['page_dom_digest'] = cls.json_value(value.get('page_dom_digest') or {})
        value['accessibility_digest'] = cls.json_value(value.get('accessibility_digest') or {})
        return value

    @classmethod
    def locator_candidates(cls, candidates) -> list[dict]:
        """Sanitize candidate diagnostics while preserving executable locator fields."""
        if isinstance(candidates, dict):
            candidates = candidates.get('attempts') or candidates.get('candidates') or []
        result = []
        for candidate in candidates or []:
            if not isinstance(candidate, dict):
                continue
            row = {}
            for key, item in candidate.items():
                key_text = str(key)[:120]
                if key_text == 'loc':
                    row[key_text] = str(item or '')[:20000]
                elif key_text in {'element_text', 'candidate_text', 'reason', 'reject_reason', 'matched_label'}:
                    row[key_text] = cls.text(item, 2000)
                elif cls.SENSITIVE_KEY.search(key_text):
                    row[key_text] = '[REDACTED]'
                else:
                    row[key_text] = cls.json_value(item)
            result.append(row)
        return result[:50]

    @classmethod
    def candidate_document(cls, value) -> dict:
        if isinstance(value, dict):
            return {
                'schema_version': 2,
                'location_status': cls.text(value.get('location_status') or 'failed', 40),
                'final_source': cls.text(value.get('final_source'), 80) or None,
                'reason': cls.text(value.get('reason'), 2000) or None,
                'attempts': cls.locator_candidates(value.get('attempts') or []),
                'derived_locators': cls.locator_candidates(value.get('derived_locators') or []),
                'selected_locators': cls.locator_candidates(value.get('selected_locators') or []),
            }
        return {
            'schema_version': 2,
            'location_status': 'verified' if any(
                item.get('verified') for item in cls.locator_candidates(value)
            ) else 'failed',
            'final_source': None,
            'reason': None,
            'attempts': cls.locator_candidates(value),
            'derived_locators': [],
            'selected_locators': [],
        }

    @classmethod
    def runtime_elements(cls, elements) -> list[dict]:
        result = []
        for element in elements or []:
            if not isinstance(element, dict):
                continue
            row = {}
            for key, item in element.items():
                key_text = str(key)[:120]
                if key_text == 'loc':
                    row[key_text] = str(item or '')[:20000]
                elif key_text in {'element_text', 'text_snippets', 'error_message'}:
                    row[key_text] = cls.json_value(item)
                elif key_text in {'page_url', 'frame_url'}:
                    row[key_text] = cls.url(item)
                elif cls.SENSITIVE_KEY.search(key_text):
                    row[key_text] = '[REDACTED]'
                else:
                    row[key_text] = cls.json_value(item)
            result.append(row)
        return result[:200]

    @classmethod
    def locator_engine(cls, value) -> dict:
        if not isinstance(value, dict):
            return {}
        result = {}
        for key, item in value.items():
            key_text = str(key)[:120]
            if key_text in {'loc', 'selected_loc', 'used_loc'}:
                result[key_text] = str(item or '')[:20000]
            elif key_text == 'candidates':
                document = cls.candidate_document(item)
                result[key_text] = document['attempts']
                result['candidate_document'] = document
            elif cls.SENSITIVE_KEY.search(key_text):
                result[key_text] = '[REDACTED]'
            else:
                result[key_text] = cls.json_value(item)
        return result

    @classmethod
    def runtime_snapshot(cls, value) -> dict:
        if not isinstance(value, dict):
            return {}
        result = cls.json_value(value)
        result['page_url'] = cls.url(value.get('page_url'))
        result['page_title'] = cls.text(value.get('page_title'), 512)
        result['error_message'] = cls.text(value.get('error_message'), 20000)
        result['checked_time'] = cls.datetime_text(value.get('checked_time'))
        result['viewport'] = cls.json_value(value.get('viewport') or {})
        result['locator_engine'] = cls.locator_engine(value.get('locator_engine') or {})
        result['elements'] = cls.runtime_elements(value.get('elements') or [])
        return result

    @classmethod
    def heal_record(cls, value) -> dict:
        if not isinstance(value, dict):
            return {}
        result = {}
        for key, item in value.items():
            key_text = str(key)[:120]
            if key_text in {'failed_loc', 'selected_loc'}:
                result[key_text] = str(item or '')[:20000]
            elif key_text == 'candidates':
                result[key_text] = cls.locator_candidates(item)
            elif key_text == 'page_url':
                result[key_text] = cls.url(item)
            elif key_text in {'failed_reason', 'error_message'}:
                result[key_text] = cls.text(item, 20000)
            elif cls.SENSITIVE_KEY.search(key_text):
                result[key_text] = '[REDACTED]'
            else:
                result[key_text] = cls.json_value(item)
        return result
