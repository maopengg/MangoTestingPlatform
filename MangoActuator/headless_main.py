# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 无桌面界面的执行器入口
# @Time   : 2025-04-16 15:07
# @Author : 毛鹏
import asyncio
import argparse
import os
import shutil
import subprocess
import sys
import time


def bootstrap_xvfb_if_needed():
    if not sys.platform.startswith('linux'):
        return
    if os.getenv('DISPLAY'):
        os.environ.setdefault('ACTUATOR_LIVE_STREAM_SUPPORTED', '1')
        return
    if os.getenv('ACTUATOR_XVFB_BOOTSTRAPPED') == '1':
        return
    if os.getenv('ACTUATOR_DISABLE_XVFB_BOOTSTRAP') == '1':
        os.environ.setdefault('ACTUATOR_LIVE_STREAM_SUPPORTED', '0')
        return

    xvfb_run = shutil.which('xvfb-run')
    xvfb = shutil.which('Xvfb')
    if not xvfb_run and not xvfb:
        os.environ.setdefault('ACTUATOR_LIVE_STREAM_SUPPORTED', '0')
        return

    fallback_seconds = int(os.getenv('ACTUATOR_XVFB_FALLBACK_SECONDS', '10'))
    xvfb_screen = os.getenv('ACTUATOR_XVFB_SCREEN', '1440x900x24')
    env = os.environ.copy()
    env['ACTUATOR_XVFB_BOOTSTRAPPED'] = '1'
    env['ACTUATOR_LIVE_STREAM_SUPPORTED'] = '1'
    if xvfb_run:
        command = [
            xvfb_run,
            '-a',
            '-s',
            f'-screen 0 {xvfb_screen}',
            sys.executable,
            os.path.abspath(__file__),
            *sys.argv[1:],
        ]
        print('检测到 xvfb-run，使用 Xvfb 启动执行器。')
    else:
        display_value = os.getenv('ACTUATOR_DISPLAY', ':99')
        xvfb_log = open('/tmp/mango-actuator-xvfb.log', 'a', encoding='utf-8')
        xvfb_process = subprocess.Popen(
            [xvfb, display_value, '-screen', '0', xvfb_screen],
            stdout=xvfb_log,
            stderr=xvfb_log,
            env=env,
        )
        time.sleep(1)
        if xvfb_process.poll() is not None:
            print('Xvfb 进程启动失败，降级为普通 Python 启动。')
            os.environ['ACTUATOR_XVFB_BOOTSTRAPPED'] = '1'
            os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'] = '0'
            xvfb_log.close()
            return
        env['DISPLAY'] = display_value
        command = [
            sys.executable,
            os.path.abspath(__file__),
            *sys.argv[1:],
        ]
        print(f'检测到 Xvfb，使用 DISPLAY={display_value} 启动执行器。')
    process = subprocess.Popen(command, env=env)
    time.sleep(fallback_seconds)
    if process.poll() is None:
        exit_code = process.wait()
        if not xvfb_run:
            xvfb_process.terminate()
            xvfb_process.wait(timeout=5)
            xvfb_log.close()
        raise SystemExit(exit_code)
    exit_code = process.returncode
    if not xvfb_run:
        xvfb_process.terminate()
        xvfb_process.wait(timeout=5)
        xvfb_log.close()
    if exit_code == 0:
        raise SystemExit(0)
    print(f'Xvfb 启动执行器失败，退出码：{exit_code}，降级为普通 Python 启动。')
    os.environ['ACTUATOR_XVFB_BOOTSTRAPPED'] = '1'
    os.environ['ACTUATOR_LIVE_STREAM_SUPPORTED'] = '0'


bootstrap_xvfb_if_needed()

from mangotools.mangos import Mango

from src import process
from src.enums.tools_enum import CacheKeyEnum
from src.services.runtime import RuntimeInstanceAlreadyRunning, RuntimeInstanceLock
from src.services.perf.k6_runtime import ensure_k6_available
from src.services.capabilities import CapabilityRegistry
from src.settings import settings
from src.tools import project_dir
from src.tools.send_global_msg import global_consumer_news
from src.tools.set_config import SetConfig
from src.tools.url import is_valid_url, platform_ws_url


class HeadlessLoop:

    def __init__(self):
        self.loop = Mango.t()


CONFIG_KEY_MAPPING = {
    '服务地址': CacheKeyEnum.HOST.value,
    '平台地址': CacheKeyEnum.HOST.value,
    'host': CacheKeyEnum.HOST.value,
    'WS链接': CacheKeyEnum.WS.value,
    'ws': CacheKeyEnum.WS.value,
    'websocket': CacheKeyEnum.WS.value,
    '用户名': CacheKeyEnum.USERNAME.value,
    '账号': CacheKeyEnum.USERNAME.value,
    'username': CacheKeyEnum.USERNAME.value,
    '密码': CacheKeyEnum.PASSWORD.value,
    'password': CacheKeyEnum.PASSWORD.value,
    '代理地址': CacheKeyEnum.PROXY_URL.value,
    'proxy_url': CacheKeyEnum.PROXY_URL.value,
    '浏览器类型': CacheKeyEnum.WEB_TYPE.value,
    'web_type': CacheKeyEnum.WEB_TYPE.value,
    '浏览器路径': CacheKeyEnum.WEB_PATH.value,
    'web_path': CacheKeyEnum.WEB_PATH.value,
    '浏览器并行数': CacheKeyEnum.WEB_PARALLEL.value,
    'web_parallel': CacheKeyEnum.WEB_PARALLEL.value,
    'UI队列容量': CacheKeyEnum.UI_QUEUE_SIZE.value,
    'ui_queue_size': CacheKeyEnum.UI_QUEUE_SIZE.value,
    '浏览器H5模式': CacheKeyEnum.WEB_H5.value,
    'web_h5': CacheKeyEnum.WEB_H5.value,
    '最大化': CacheKeyEnum.WEB_MAX.value,
    'web_max': CacheKeyEnum.WEB_MAX.value,
    '视频录制': CacheKeyEnum.WEB_RECORDING.value,
    'web_recording': CacheKeyEnum.WEB_RECORDING.value,
    '无头模式': CacheKeyEnum.WEB_HEADERS.value,
    'web_headers': CacheKeyEnum.WEB_HEADERS.value,
    '操作截图上传': CacheKeyEnum.WEB_STEP_SCREENSHOT.value,
    'web_step_screenshot': CacheKeyEnum.WEB_STEP_SCREENSHOT.value,
    '静态资源缓存': CacheKeyEnum.WEB_STATIC_CACHE_ENABLED.value,
    'web_static_cache_enabled': CacheKeyEnum.WEB_STATIC_CACHE_ENABLED.value,
    'pytest并行数': CacheKeyEnum.PYTEST_PARALLEL.value,
    'pytest_parallel': CacheKeyEnum.PYTEST_PARALLEL.value,
    'pytest队列容量': CacheKeyEnum.PYTEST_QUEUE_SIZE.value,
    'pytest_queue_size': CacheKeyEnum.PYTEST_QUEUE_SIZE.value,
}

BROWSER_TYPE_MAPPING = {
    '谷歌浏览器': 0,
    'chrome': 0,
    'chromium': 0,
    'edge': 1,
    '火狐': 2,
    'firefox': 2,
    'webkit': 3,
}

DEFAULT_EXECUTOR_PASSWORD = '123456'


def parse_config_value(value: str):
    if value == '':
        return ''
    if value[0:1] in ('"', "'") and value[-1:] == value[0:1]:
        return value[1:-1]
    lower_value = value.lower()
    if lower_value in {'true', 'yes', 'on', '是', '开启', '启用'}:
        return True
    if lower_value in {'false', 'no', 'off', '否', '关闭', '禁用'}:
        return False
    try:
        return int(value)
    except ValueError:
        return value


def normalize_config_key(key: str) -> str:
    normalized_key = CONFIG_KEY_MAPPING.get(key)
    if normalized_key:
        return normalized_key
    raise Exception(f"配置项 '{key}' 暂不支持，请检查启动参数")


def normalize_config_value(key: str, value):
    if key == CacheKeyEnum.WEB_TYPE.value and isinstance(value, str):
        mapped_value = BROWSER_TYPE_MAPPING.get(value.strip().lower()) or BROWSER_TYPE_MAPPING.get(value.strip())
        if mapped_value is not None:
            return mapped_value
    return value


def normalize_ws_url(value):
    if not value:
        return None
    parsed_url = str(value).strip()
    if parsed_url.startswith('ws://') or parsed_url.startswith('wss://'):
        return parsed_url.rstrip('/') + '/'
    return platform_ws_url(parsed_url)


def apply_runtime_config(config: dict):
    for raw_key, raw_value in config.items():
        key = normalize_config_key(str(raw_key).strip())
        value = normalize_config_value(key, raw_value)
        if value in ('', None):
            continue
        method_name = f"set_{key}"
        set_method = getattr(SetConfig, method_name, None)
        if not set_method:
            raise Exception(f"Warning: Method '{method_name}' not found in SetConfig")
        if key == CacheKeyEnum.HOST.value:
            if is_valid_url(value):
                http_url = is_valid_url(value)
                SetConfig.set_host(http_url)  # type: ignore
                if CacheKeyEnum.WS.value not in config:
                    SetConfig.set_ws(platform_ws_url(http_url))  # type: ignore
            else:
                raise Exception('请设置正确的服务地址')
        elif key == CacheKeyEnum.WS.value:
            ws_url = normalize_ws_url(value)
            if not ws_url:
                raise Exception('请设置正确的WS链接')
            SetConfig.set_ws(ws_url)  # type: ignore
        else:
            set_method(value)


def parse_bool(value):
    if isinstance(value, bool) or value is None:
        return value
    parsed_value = parse_config_value(str(value))
    if isinstance(parsed_value, bool):
        return parsed_value
    raise argparse.ArgumentTypeError(f'{value} 不是有效布尔值，可选 true/false、yes/no、on/off')


def parse_args():
    parser = argparse.ArgumentParser(
        description='芒果执行器无桌面界面启动入口。'
    )
    parser.add_argument('--version', action='store_true', help='打印执行器启动脚本版本后退出')
    parser.add_argument(
        '--env',
        default=os.getenv('EXECUTOR_TYPE'),
        help='已废弃：旧执行器类型，仅用于兼容迁移',
    )
    parser.add_argument(
        '--profile',
        default=(
            os.getenv('MANGO_ACTUATOR_PROFILE')
            or (None if os.getenv('EXECUTOR_TYPE') else 'standard')
        ),
        choices=[
            'minimal', 'pytest', 'standard', 'android', 'full', 'custom',
            'pytest_web', 'web_ui', 'android_ui', 'ios_ui',
        ],
        help='执行器安装预设，不参与任务调度',
    )
    parser.add_argument(
        '--capabilities',
        default=os.getenv('MANGO_CAPABILITIES_ENABLED'),
        help='显式启用能力，逗号分隔：pytest,web_ui,android_ui,ios_ui,perf',
    )
    parser.add_argument('--host', default='http://127.0.0.1:8000', help='平台后端服务地址，例如 https://mango-platform.example.com')
    parser.add_argument('--ws', default=os.getenv('ACTUATOR_WS'),
                        help='高级选项：覆盖平台实时服务WS地址；默认根据 --host 自动推导')
    parser.add_argument('--username', default='open', help='执行器登录账号')
    parser.add_argument('--password', default=DEFAULT_EXECUTOR_PASSWORD, help=f'执行器登录密码，未传时默认使用 {DEFAULT_EXECUTOR_PASSWORD}')
    parser.add_argument('--proxy-url', help='HTTP 代理地址')
    parser.add_argument('--web-type', default='谷歌浏览器', help='浏览器类型：谷歌浏览器/chrome/chromium/edge/firefox/webkit')
    parser.add_argument('--web-path', help='浏览器可执行文件路径')
    parser.add_argument('--web-parallel', type=int, default=5, help='UI 浏览器并行数')
    parser.add_argument('--ui-queue-size', type=int, help='UI 本地待执行队列容量')
    parser.add_argument('--web-h5', type=parse_bool, help='是否开启浏览器 H5 模式')
    parser.add_argument('--web-max', type=parse_bool, help='是否启动浏览器最大化')
    parser.add_argument('--web-recording', type=parse_bool, help='是否开启 UI 执行视频录制')
    parser.add_argument(
        '--web-headers',
        type=parse_bool,
        help='是否开启无头模式；未传时保留本地配置，Linux 首次运行默认开启',
    )
    parser.add_argument('--web-step-screenshot', type=parse_bool, help='是否上传每个 WEB 元素操作截图')
    parser.add_argument('--web-static-cache', dest='web_static_cache_enabled', type=parse_bool,
                        help='是否开启浏览器静态资源缓存，默认关闭')
    parser.add_argument('--pytest-parallel', type=int, help='pytest 用例并行数')
    parser.add_argument('--pytest-queue-size', type=int, help='pytest 本地待执行队列容量')
    return parser.parse_args()


def build_config_from_args(args) -> dict:
    arg_config = {
        'host': args.host,
        'ws': args.ws,
        'username': args.username,
        'password': args.password,
        'proxy_url': args.proxy_url,
        'web_type': args.web_type,
        'web_path': args.web_path,
        'web_parallel': args.web_parallel,
        'ui_queue_size': args.ui_queue_size,
        'web_h5': args.web_h5,
        'web_max': args.web_max,
        'web_recording': args.web_recording,
        'web_headers': args.web_headers,
        'web_step_screenshot': args.web_step_screenshot,
        'web_static_cache_enabled': args.web_static_cache_enabled,
        'pytest_parallel': args.pytest_parallel,
        'pytest_queue_size': args.pytest_queue_size,
    }
    return {key: value for key, value in arg_config.items() if value is not None}


def validate_required_config():
    if not SetConfig.get_password():  # type: ignore
        SetConfig.set_password(DEFAULT_EXECUTOR_PASSWORD)  # type: ignore
    missing = []
    if not SetConfig.get_host():  # type: ignore
        missing.append('--host')
    if not SetConfig.get_username():  # type: ignore
        missing.append('--username')
    if missing:
        raise Exception(f'执行器启动参数缺失：{", ".join(missing)}')


async def main():
    args = parse_args()
    if args.version:
        print(f"mango-actuator {settings.SETTINGS.get('version', 'dev')}")
        return
    RuntimeInstanceLock.acquire_process_lock(os.path.join(project_dir.cache(), 'actuator.lock'))
    if args.env:
        os.environ['EXECUTOR_TYPE'] = args.env
    if args.profile:
        os.environ['MANGO_ACTUATOR_PROFILE'] = args.profile
    if args.capabilities:
        os.environ['MANGO_CAPABILITIES_ENABLED'] = args.capabilities
    if 'perf' in CapabilityRegistry.enabled_codes():
        try:
            k6_binary = ensure_k6_available()
            if k6_binary:
                print(f'k6 性能引擎已就绪：{k6_binary}')
            else:
                print('k6 性能引擎不可用，本执行器不会承接性能测试。')
        except Exception as error:
            print(f'k6 性能引擎自动安装失败，本执行器将继续启动但不会承接性能测试：{error}')
    SetConfig.restore_runtime_settings()
    SetConfig.ensure_web_headers_default(sys.platform.startswith('linux'))
    await asyncio.sleep(5)
    config = build_config_from_args(args)
    apply_runtime_config(config)
    validate_required_config()
    await process(HeadlessLoop(), True)
    await global_consumer_news()
    while True:
        await asyncio.sleep(0.1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeInstanceAlreadyRunning as error:
        print(error, file=sys.stderr)
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        print('执行器已停止。')
# docker build -t mango_actuator .
# docker run -it mango_actuator
