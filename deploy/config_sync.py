"""Protect locally edited deployment configuration during fast-forward updates."""
import argparse
import json
from pathlib import Path
import subprocess

from bootstrap import configuration_text, parse_env, private_write


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=str(root), stderr=subprocess.DEVNULL)


def backup_path(root):
    directory = Path(git(root, 'rev-parse', '--git-dir').decode().strip())
    if not directory.is_absolute():
        directory = root / directory
    return directory / 'mango-deploy-example-backup.json'


def prepare(root):
    backup = backup_path(root)
    if backup.exists():
        raise ValueError('存在未恢复的部署配置备份，请先运行 python3 deploy/config_sync.py restore --failed；原配置未删除')
    path = root / '.env.example'
    original = path.read_text()
    parse_env(original, '.env.example')
    if subprocess.run(['git', 'diff', '--cached', '--quiet', '--', '.env.example'], cwd=str(root)).returncode:
        raise ValueError('.env.example 已暂存，请先处理暂存状态；未改动配置')
    tracked = git(root, 'show', 'HEAD:.env.example').decode()
    if original == tracked:
        return
    private_write(backup, json.dumps({'original': original, 'tracked': tracked}, ensure_ascii=False))
    private_write(path, tracked)


def restore(root, failed=False):
    backup = backup_path(root)
    if not backup.exists():
        return
    saved = json.loads(backup.read_text())
    path = root / '.env.example'
    if failed:
        private_write(path, saved['original'])
    else:
        original = parse_env(saved['original'])
        baseline = parse_env(saved['tracked'])
        overrides = {key: value for key, value in original.items() if value != baseline.get(key)}
        private_write(path, configuration_text(path.read_text(), overrides))
    backup.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'restore'])
    parser.add_argument('--failed', action='store_true')
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parent.parent
        prepare(root) if args.action == 'prepare' else restore(root, args.failed)
    except ValueError as error:
        parser.exit(1, str(error) + '\n')
    except (OSError, subprocess.SubprocessError):
        parser.exit(1, '无法保护或恢复 .env.example，请检查文件权限和 .git/mango-deploy-example-backup.json；未输出配置值\n')


if __name__ == '__main__':
    main()
