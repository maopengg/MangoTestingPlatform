import asyncio
import logging
from typing import Optional

class BridgeClient:
    def __init__(self, host: str = 'localhost', port: int = 8766):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.heartbeat_interval = 30  # 心跳间隔秒数
        self.max_retries = 3  # 最大重试次数
        self.retry_delay = 5  # 重试延迟秒数
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger('BridgeClient')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    async def connect(self):
        for attempt in range(self.max_retries):
            try:
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=15
                )
                self.logger.info(f"成功连接到桥接服务器 {self.host}:{self.port}")
                return True
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"连接失败: {str(e)}")
                    raise
                self.logger.warning(f"连接尝试 {attempt + 1}/{self.max_retries} 失败: {str(e)}")
                await asyncio.sleep(self.retry_delay)
        return False

    async def send_data(self, data: bytes):
        if not self.writer:
            raise ConnectionError("未连接到服务器")
        
        try:
            self.writer.write(data)
            await self.writer.drain()
            self.logger.debug(f"已发送 {len(data)} 字节数据")
        except Exception as e:
            self.logger.error(f"发送数据失败: {str(e)}")
            await self.close()
            raise

    async def receive_data(self):
        if not self.reader:
            raise ConnectionError("未连接到服务器")
        
        try:
            data = await asyncio.wait_for(
                self.reader.read(4096),
                timeout=self.heartbeat_interval
            )
            if not data:
                raise ConnectionError("连接已关闭")
            self.logger.debug(f"已接收 {len(data)} 字节数据")
            return data
        except Exception as e:
            self.logger.error(f"接收数据失败: {str(e)}")
            await self.close()
            raise

    async def heartbeat(self):
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.writer:
                    self.writer.write(b'\x00')  # 心跳包
                    await self.writer.drain()
            except Exception as e:
                self.logger.error(f"心跳失败: {str(e)}")
                await self.close()
                break

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.reader = None
            self.writer = None
            self.logger.info("连接已关闭")

async def main():
    client = BridgeClient()
    try:
        await client.connect()
        asyncio.create_task(client.heartbeat())
        # 示例数据发送
        await client.send_data(b'Hello, Bridge Server!')
        response = await client.receive_data()
        print(f"收到响应: {response.decode()}")
    except Exception as e:
        print(f"客户端错误: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())