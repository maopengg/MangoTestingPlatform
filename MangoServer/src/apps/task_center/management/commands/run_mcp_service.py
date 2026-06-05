from django.core.management.base import BaseCommand

from src.services.runtime.mcp.runner import run_mcp_service


class Command(BaseCommand):
    help = 'Run Mango MCP service'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='0.0.0.0')
        parser.add_argument('--port', type=int, default=8010)

    def handle(self, *args, **options):
        try:
            run_mcp_service(options['host'], options['port'])
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('mcp-service 已停止'))
