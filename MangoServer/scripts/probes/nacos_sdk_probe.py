import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Optional, Sequence


DEFAULT_GROUP = "DEFAULT_GROUP"
MIN_SDK_PYTHON_VERSION = (3, 10)


@dataclass(frozen=True)
class NacosProbeSettings:
    server_address: str = "localhost:8848"
    endpoint: Optional[str] = None
    namespace_id: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None) -> "NacosProbeSettings":
        source = os.environ if environ is None else environ
        return cls(
            server_address=source.get("NACOS_SERVER_ADDR", cls.server_address),
            endpoint=_optional(source.get("NACOS_ENDPOINT")),
            namespace_id=source.get("NACOS_NAMESPACE_ID", cls.namespace_id),
            username=_optional(source.get("NACOS_USERNAME")),
            password=_optional(source.get("NACOS_PASSWORD")),
            access_key=_optional(source.get("NACOS_ACCESS_KEY")),
            secret_key=_optional(source.get("NACOS_SECRET_KEY")),
            log_level=source.get("NACOS_LOG_LEVEL", cls.log_level),
        )


def _optional(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    return value


def build_client_config(settings: NacosProbeSettings, builder):
    if settings.endpoint is not None:
        builder = builder.endpoint(settings.endpoint)
    else:
        builder = builder.server_address(settings.server_address)
    builder = builder.namespace_id(settings.namespace_id)

    if settings.username is not None:
        builder = builder.username(settings.username)
    if settings.password is not None:
        builder = builder.password(settings.password)
    if settings.access_key is not None:
        builder = builder.access_key(settings.access_key)
    if settings.secret_key is not None:
        builder = builder.secret_key(settings.secret_key)

    return builder.log_level(settings.log_level).build()


def _ensure_supported_python(version_info: Optional[Sequence[int]] = None) -> None:
    current = tuple((version_info or sys.version_info)[:2])
    if current < MIN_SDK_PYTHON_VERSION:
        raise RuntimeError(
            "当前 nacos-sdk-python 会导入 Python 3.10+ 语法，"
            "请使用 Python 3.10 或更高版本运行此工具。"
        )


async def get_config(data_id: str, group: str, settings: NacosProbeSettings) -> str:
    _ensure_supported_python()
    try:
        from v2.nacos import ClientConfigBuilder, ConfigParam, NacosConfigService
    except ImportError as exc:
        raise RuntimeError("请先安装依赖: pip install nacos-sdk-python") from exc

    client_config = build_client_config(settings, ClientConfigBuilder())
    client = await NacosConfigService.create_config_service(client_config)
    try:
        return await client.get_config(ConfigParam(data_id=data_id, group=group))
    finally:
        await client.shutdown()


async def publish_config(
    data_id: str,
    group: str,
    content: str,
    config_type: str,
    settings: NacosProbeSettings,
) -> bool:
    _ensure_supported_python()
    try:
        from v2.nacos import ClientConfigBuilder, ConfigParam, NacosConfigService
    except ImportError as exc:
        raise RuntimeError("请先安装依赖: pip install nacos-sdk-python") from exc

    client_config = build_client_config(settings, ClientConfigBuilder())
    client = await NacosConfigService.create_config_service(client_config)
    try:
        return await client.publish_config(
            ConfigParam(
                data_id=data_id,
                group=group,
                content=content,
                type=config_type,
            )
        )
    finally:
        await client.shutdown()


def read_publish_content(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nacos Python SDK probe for MangoServer.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    get_parser = subparsers.add_parser("get", help="Read a Nacos config.")
    _add_common_args(get_parser)

    publish_parser = subparsers.add_parser("publish", help="Publish a full config file to Nacos.")
    _add_common_args(publish_parser)
    publish_parser.add_argument("--file", required=True, help="Local UTF-8 config file to publish.")
    publish_parser.add_argument(
        "--type",
        default="",
        dest="config_type",
        help="Nacos config type, for example yaml/properties/json.",
    )

    return parser.parse_args(_normalize_legacy_args(argv))


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-id", required=True, help="Nacos config data id.")
    parser.add_argument("--group", default=DEFAULT_GROUP, help="Nacos config group.")
    parser.add_argument("--server-addr", help="Override NACOS_SERVER_ADDR.")
    parser.add_argument("--endpoint", help="Override NACOS_ENDPOINT.")
    parser.add_argument("--namespace-id", help="Override NACOS_NAMESPACE_ID.")


def _format_target(settings: NacosProbeSettings) -> str:
    if settings.endpoint is not None:
        return f"endpoint={settings.endpoint}"
    return f"server_address={settings.server_address}"


def _normalize_legacy_args(argv: Optional[Sequence[str]]) -> Sequence[str]:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"get", "publish", "-h", "--help"}:
        return args
    return ["get"] + args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parse_args(argv)
    settings = NacosProbeSettings.from_env()
    if args.server_addr:
        settings = replace(settings, server_address=args.server_addr)
    if args.endpoint:
        settings = replace(settings, endpoint=args.endpoint)
    if args.namespace_id is not None:
        settings = replace(settings, namespace_id=args.namespace_id)

    try:
        if args.command == "get":
            content = asyncio.run(get_config(args.data_id, args.group, settings))
            print(content)
            return 0

        if args.command == "publish":
            content = read_publish_content(args.file)
            success = asyncio.run(
                publish_config(args.data_id, args.group, content, args.config_type, settings)
            )
            print("publish success" if success else "publish failed")
            return 0 if success else 1
    except Exception as exc:
        raise RuntimeError(
            f"Nacos {args.command} failed via {_format_target(settings)}, "
            f"namespace={settings.namespace_id}, data_id={args.data_id}, group={args.group}"
        ) from exc

    raise RuntimeError(f"不支持的命令: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
