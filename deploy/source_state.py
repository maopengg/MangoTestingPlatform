"""Compare image/source state without storing deployment credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from bootstrap import private_write


PATHS = {
    'backend': ['MangoServer/', 'skill/', '.dockerignore'],
    'frontend': ['mango-console/', 'skill/', '.dockerignore'],
}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL)


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
        try:
            git(root, 'cat-file', '-e', revision + '^{commit}')
            changed = git(root, 'diff', '--name-only', revision, '--', *PATHS[component])
            untracked = git(root, 'ls-files', '--others', '--exclude-standard', '--', *PATHS[component])
            if not changed.strip() and not untracked.strip():
                return False
        except subprocess.CalledProcessError:
            pass
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
    except (ValueError, OSError, subprocess.SubprocessError):
        parser.exit(1, '无法验证源码与镜像状态，已停止部署；请检查 Git、Docker 和目录权限。\n')


if __name__ == '__main__':
    main()
