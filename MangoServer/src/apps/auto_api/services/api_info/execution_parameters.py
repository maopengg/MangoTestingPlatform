import re

from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService


class ApiInfoExecutionParametersService:
    @staticmethod
    def collect(payload):
        names = {}

        def visit(value):
            if isinstance(value, str):
                for name in re.findall(r'\$\{\{([^{}]+)\}\}', value):
                    if name.strip():
                        names.setdefault(name, None)
            elif isinstance(value, dict):
                for key, item in value.items():
                    visit(key)
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        def visit_config(config):
            if not isinstance(config, dict):
                return
            for field, value in config.items():
                if field == 'headers':
                    continue
                if field in ('config', 'sse_config', 'mcp_config', 'mcp_binding', 'grpc_config', 'grpc_binding'):
                    visit_config(value)
                else:
                    visit(value)

        for field in ('url', 'params', 'body_config'):
            visit(payload.get(field))
        for field in ('sse_config', 'mcp_config', 'mcp_binding', 'grpc_binding', 'protocol_config'):
            visit_config(payload.get(field))
        return list(names)

    @classmethod
    def names(cls, api_info_id, *, revision_id=None, release_id=None):
        payload, _ = ApiInfoRuntimeService.resolve_payload(
            api_info_id, revision_id=revision_id, release_id=release_id,
        )
        return cls.collect(payload)
