import asyncio
import logging
from typing import Optional

class BridgeServer:
    def __init__(self, host: str = 'localhost', port: int = 8766):
        self.host = host
        self.port = port
        self.server: Optional[asyncio.Server] = None
        self.clients = set()
        self.heartbeat_interval = 30  # 心跳间隔秒数
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger('BridgeServer')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    async def start(self):
        try:
            self.server = await asyncio.start_server(
                self.handle_client, self.host, self.port)
            self.logger.info(f"Server started on {self.host}:{self.port}")
            async with self.server:
                await self.server.serve_forever()
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise

    async def handle_client(self, reader, writer):
        client_addr = writer.get_extra_info('peername')
        self.logger.info(f"New connection from {client_addr}")
        self.clients.add(writer)

        try:
            while True:
                data = await asyncio.wait_for(
                    reader.read(100), timeout=self.heartbeat_interval)
                if not data:
                    break
                # 处理客户端数据
                await self.process_data(data, writer)
        except asyncio.TimeoutError:
            self.logger.warning(f"Client {client_addr} timeout")
        except Exception as e:
            self.logger.error(f"Client {client_addr} error: {e}")
        finally:
            self.logger.info(f"Client {client_addr} disconnected")
            self.clients.discard(writer)
            writer.close()
            await writer.wait_closed()

    async def process_data(self, data, writer):
        # 实现具体的数据处理逻辑
        pass

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("Server stopped")

async def main():
    server = BridgeServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())