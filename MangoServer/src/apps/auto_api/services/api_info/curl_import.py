"""Parse imported cURL text without executing commands or fetching remote URLs."""

import argparse
import shlex
from urllib.parse import urlparse

from curlparser import parse
from curlparser.parser import parser as legacy_parser

from src.apps.auto_api.exceptions import API_CURL_IMPORT_INVALID, AutoApiError


class _ImportArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise AutoApiError(API_CURL_IMPORT_INVALID)

    def exit(self, status=0, message=None):
        raise AutoApiError(API_CURL_IMPORT_INVALID)

    def print_help(self, file=None):
        return None


def parse_import_curl(command):
    if not isinstance(command, str) or not command.strip():
        raise AutoApiError(API_CURL_IMPORT_INVALID)
    try:
        tokens = shlex.split(command.strip().replace('\\\r\n', ' ').replace('\\\n', ' '))
    except ValueError:
        raise AutoApiError(API_CURL_IMPORT_INVALID) from None
    if not tokens or tokens[0] != 'curl':
        raise AutoApiError(API_CURL_IMPORT_INVALID)

    normalized = ['curl']
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in ('--compressed', '--location', '-L', '--silent', '-s', '--show-error', '-S'):
            index += 1
            continue
        if token in ('--url', '-I', '--head') or token.startswith('--url='):
            if token in ('-I', '--head'):
                normalized.extend(['-X', 'HEAD'])
            elif token.startswith('--url='):
                normalized.append(token.split('=', 1)[1])
            else:
                index += 1
                if index >= len(tokens):
                    raise AutoApiError(API_CURL_IMPORT_INVALID)
                normalized.append(tokens[index])
        else:
            normalized.append(token)
            # Keep option values intact, even when they look like cURL options.
            option = token.split('=', 1)[0]
            action = legacy_parser._option_string_actions.get(option)
            if action is not None and action.nargs != 0 and '=' not in token:
                index += 1
                if index >= len(tokens):
                    raise AutoApiError(API_CURL_IMPORT_INVALID)
                normalized[-1] = f'{token}={tokens[index]}'
        index += 1

    validator = _ImportArgumentParser(parents=[legacy_parser], add_help=False, allow_abbrev=False)
    validator.parse_args(normalized)
    try:
        parsed = parse(shlex.join(normalized))
        url = urlparse(parsed.url)
        if url.scheme not in ('http', 'https') or not url.hostname:
            raise AutoApiError(API_CURL_IMPORT_INVALID)
    except ValueError:
        raise AutoApiError(API_CURL_IMPORT_INVALID) from None
    return parsed
