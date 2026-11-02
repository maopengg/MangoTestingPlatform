# -*- coding: utf-8 -*-
import os
import re
import zipfile
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0242


class SkillResourceService:
    SKILL_ROOT = os.path.join(settings.STATIC_RESOURCE_DIR, 'skill_templates')
    SAFE_KEY_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

    @classmethod
    def list_skills(cls) -> list[dict]:
        if not os.path.isdir(cls.SKILL_ROOT):
            return []
        items = []
        for key in sorted(os.listdir(cls.SKILL_ROOT)):
            skill_dir = cls.safe_skill_dir(key)
            skill_file = os.path.join(skill_dir, 'SKILL.md') if skill_dir else ''
            if not skill_dir or not os.path.isfile(skill_file):
                continue
            content = cls.read_skill_content(key)
            meta = cls.parse_frontmatter(content)
            items.append({
                'key': key,
                'name': meta.get('name') or key,
                'description': meta.get('description') or '',
                'sections': cls.extract_sections(content),
            })
        return items

    @classmethod
    def detail(cls, key: str) -> dict | None:
        skill_dir = cls.safe_skill_dir(key)
        if not skill_dir:
            return None
        skill_file = os.path.join(skill_dir, 'SKILL.md')
        if not os.path.isfile(skill_file):
            return None
        content = cls.read_skill_content(key)
        meta = cls.parse_frontmatter(content)
        return {
            'key': key,
            'name': meta.get('name') or key,
            'description': meta.get('description') or '',
            'sections': cls.extract_sections(content),
            'content': content,
            'files': cls.list_skill_files(skill_dir),
        }

    @classmethod
    def safe_skill_dir(cls, key: str) -> str | None:
        if not key or not cls.SAFE_KEY_RE.match(key):
            return None
        skill_root = os.path.abspath(cls.SKILL_ROOT)
        skill_dir = os.path.abspath(os.path.join(skill_root, key))
        if not skill_dir.startswith(skill_root + os.sep):
            return None
        if not os.path.isdir(skill_dir):
            return None
        return skill_dir

    @classmethod
    def read_skill_content(cls, key: str) -> str:
        skill_dir = cls.safe_skill_dir(key)
        if not skill_dir:
            return ''
        with open(os.path.join(skill_dir, 'SKILL.md'), 'r', encoding='utf-8') as file:
            return file.read()

    @staticmethod
    def parse_frontmatter(content: str) -> dict:
        if not content.startswith('---'):
            return {}
        end_index = content.find('\n---', 3)
        if end_index < 0:
            return {}
        meta = {}
        for line in content[3:end_index].strip().splitlines():
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            meta[key.strip()] = value.strip()
        return meta

    @staticmethod
    def extract_sections(content: str) -> list[dict]:
        if content.startswith('---'):
            end_index = content.find('\n---', 3)
            if end_index >= 0:
                content = content[end_index + 4:]
        sections = []
        current = None
        for line in content.splitlines():
            if line.startswith('## '):
                if current:
                    sections.append(current)
                current = {'title': line[3:].strip(), 'content': []}
            elif current:
                current['content'].append(line)
        if current:
            sections.append(current)
        return [
            {
                'title': item['title'],
                'summary': '\n'.join(item['content']).strip()[:500],
            }
            for item in sections[:8]
        ]

    @classmethod
    def list_skill_files(cls, skill_dir: str) -> list[str]:
        files = []
        for root, _, names in os.walk(skill_dir):
            for name in names:
                file_path = os.path.join(root, name)
                files.append(os.path.relpath(file_path, skill_dir))
        return sorted(files)

    @classmethod
    def build_zip_response(cls, key: str):
        skill_dir = cls.safe_skill_dir(key)
        if not skill_dir:
            return None
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for root, _, files in os.walk(skill_dir):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    relative_path = os.path.relpath(file_path, skill_dir)
                    archive.write(file_path, os.path.join(key, relative_path))
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{key}.zip"'
        return response


class SkillResourceViews(ViewSet):

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_list(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0001, SkillResourceService.list_skills())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_detail(self, request: Request):
        data = SkillResourceService.detail(request.query_params.get('key') or '')
        if not data:
            return ResponseData.fail(RESPONSE_MSG_0242)
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_download(self, request: Request):
        response = SkillResourceService.build_zip_response(request.query_params.get('key') or '')
        if not response:
            return ResponseData.fail(RESPONSE_MSG_0242)
        return response
