"""Compare image/source state without storing deployment credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import re

from bootstrap import private_write


PATHS = {
    'backend': ['MangoServer/', 'skill/', '.dockerignore'],
    'frontend': ['mango-console/', 'skill/', '.dockerignore'],
}


class GitCommandError(ValueError):
    pass


def git(root, *args):
    result = subprocess.run(['git', *args], cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        detail = result.stderr.decode('utf-8', errors='replace')
        detail = re.sub(r'https?://\S+', '[URL hidden]', detail)
        detail = re.sub(r'(?i)(password|token|authorization|secret|cookie)(\s*[:=]\s*|\s+)[^\s,;]+', r'\1=[redacted]', detail)
        detail = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', detail).strip()[:1200]
        raise GitCommandError(f'Git {args[0]} 失败（退出码 {result.returncode}）：{detail or "未提供错误详情"}')
    return result.stdout


def fingerprint(root, component):
    names = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *PATHS[component])
    digest = hashlib.sha256()
    for name in sorted(set(filter(None, names.split(b'\0')))):
        path = root / name.decode()
        digest.update(name + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.is_file() else b'missing')
    return digest.hexdigest()


def inspect_image(name):
    result = subprocess.run(['docker', 'image', 'inspect', name], capture_output=True, text=True)
    if result.returncode:
        return None
    try:
        image = json.loads(result.stdout)[0]
        return {'id': image['Id'], 'revision': (image['Config'].get('Labels') or {}).get('org.opencontainers.image.revision')}
    except (ValueError, KeyError, IndexError):
        raise ValueError('无法读取镜像构建状态。') from None


def needs_build(root, component, name):
    image = inspect_image(name)
    if image is None:
        return True
    current = fingerprint(root, component)
    path = root / 'deploy/generated/last-success.json'
    if path.exists():
        try:
            old = json.loads(path.read_text()).get(component, {})
        except ValueError:
            old = {}
        if old.get('fingerprint') == current and old.get('image_id') == image['id']:
            return False
    # Previously published images can be reused if their relevant source is unchanged.
    revision = image.get('revision')
    if revision and len(revision) == 40 and all(x in '0123456789abcdef' for x in revision):
        exists = subprocess.run(['git', 'cat-file', '-e', revision + '^{commit}'], cwd=str(root),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if exists:
            changed = git(root, 'diff', '--name-only', revision, '--', *PATHS[component])
            untracked = git(root, 'ls-files', '--others', '--exclude-standard', '--', *PATHS[component])
            if not changed.strip() and not untracked.strip():
                return False
    return True


def record(root, backend, frontend):
    state = {'revision': git(root, 'rev-parse', 'HEAD').decode().strip()}
    for component, name in [('backend', backend), ('frontend', frontend)]:
        image = inspect_image(name)
        if image is None:
            raise ValueError('部署后镜像不存在，未记录成功状态。')
        state[component] = {'image_id': image['id'], 'fingerprint': fingerprint(root, component)}
    private_write(root / 'deploy/generated/last-success.json', json.dumps(state, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['needs-build', 'record'])
    parser.add_argument('root', type=Path)
    parser.add_argument('first')
    parser.add_argument('second')
    args = parser.parse_args()
    try:
        if args.action == 'record':
            record(args.root, args.first, args.second)
        else:
            print(int(needs_build(args.root, args.first, args.second)))
    except GitCommandError as error:
        parser.exit(1, str(error) + '\n源码检查未通过，未继续部署。\n')
    except (ValueError, OSError, subprocess.SubprocessError):
        parser.exit(1, '无法验证源码与镜像状态，已停止部署；请检查 Git、Docker 和目录权限。\n')


if __name__ == '__main__':
    main()
