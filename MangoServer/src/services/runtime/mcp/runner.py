import uvicorn

from src.services.mcp_server.app import mcp_asgi_app


def run_mcp_service(host: str, port: int):
    uvicorn.run(mcp_asgi_app(), host=host, port=port)

