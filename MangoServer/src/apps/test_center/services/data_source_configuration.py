from pathlib import Path

from src.apps.data_factory.models import Database
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.test_center.exceptions import DATA_SOURCE_CONNECTION_DUPLICATED, TestCenterError


class DataSourceConfigurationService:
    """连接身份与密码、展示名称及逻辑绑定的库名无关。"""

    @staticmethod
    def _identity(values):
        kind = values['db_type']
        if kind == DataSourceTypeEnum.SQLITE.value:
            return kind, str(Path(values['file_path']).expanduser().resolve())
        identity = (kind, values['host'].strip().lower(), values['port'], values['user'])
        if kind == DataSourceTypeEnum.ELASTICSEARCH.value:
            extra = values['extra_config'] or {}
            prefix = extra.get('path_prefix', '').strip().strip('/')
            return (*identity, extra.get('scheme', 'http'), '/' + prefix if prefix else '')
        return identity

    @classmethod
    def validate_unique(cls, attrs, *, instance=None):
        fields = ('db_type', 'host', 'port', 'user', 'file_path', 'extra_config')
        defaults = {'host': '', 'port': 0, 'user': '', 'file_path': '', 'extra_config': {}}
        values = {
            key: attrs.get(key, getattr(instance, key) if instance is not None else defaults.get(key))
            for key in fields
        }
        if values['db_type'] == DataSourceTypeEnum.SQLITE.value:
            attrs['file_path'] = str(Path(values['file_path']).expanduser().resolve())
            values['file_path'] = attrs['file_path']
        else:
            attrs['host'] = values['host'].strip().lower()
            values['host'] = attrs['host']
        candidates = Database.objects.filter(db_type=values['db_type'])
        if values['db_type'] != DataSourceTypeEnum.SQLITE.value:
            candidates = candidates.filter(port=values['port'])
        if instance is not None:
            candidates = candidates.exclude(pk=instance.pk)
        identity = cls._identity(values)
        for candidate in candidates.only('id', 'display_name', *fields).order_by('id'):
            if cls._identity({key: getattr(candidate, key) for key in fields}) == identity:
                raise TestCenterError(
                    DATA_SOURCE_CONNECTION_DUPLICATED,
                    value=(candidate.display_name, candidate.pk),
                )
