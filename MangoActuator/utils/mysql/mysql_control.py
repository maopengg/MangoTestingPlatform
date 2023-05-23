# # @Project: auto_test
# # @Description:
# # @Time   : 2022-11-17 20:27
# # @Author : 毛鹏
# import asyncio
# from typing import Optional
#
# import aiomysql
#
# # from config.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
# from utils.decorator.singleton import singleton
#
#
# @singleton
# class MysqlDB:
#
#     def __init__(self):
#         self.pool: Optional[aiomysql.pool.Pool] = None
#
#     async def connect(self):
#         self.pool = await aiomysql.create_pool(
#             host=MYSQL_HOST,
#             port=MYSQL_PORT,
#             user=MYSQL_USER,
#             password=MYSQL_PASSWORD,
#             db=MYSQL_DB,
#             autocommit=True
#         )
#
#     async def disconnect(self):
#         self.pool.close()
#         await self.pool.wait_closed()
#
#     async def execute(self, query, *args):
#         async with self.pool.acquire() as conn:
#             async with conn.cursor() as cur:
#                 return await cur.execute(query, args)
#
#     async def select(self, query, *args) -> dict:
#         async with self.pool.acquire() as conn:
#             async with conn.cursor(aiomysql.DictCursor) as cur:
#                 await cur.execute(query, args)
#                 return await cur.fetchall()
#
#     async def insert(self, table, data):
#         keys = ','.join(data.keys())
#         values = ','.join(['%s'] * len(data))
#         query = f'INSERT INTO {table} ({keys}) VALUES ({values})'
#         await self.execute(query, *data.values())
#
#     async def update(self, table, data, condition):
#         key_values = ','.join([f'{key}=%s' for key in data.keys()])
#         query = f'UPDATE {table} SET {key_values} WHERE {condition}'
#         await self.execute(query, *data.values())
#
#     async def delete(self, table, condition):
#         query = f'DELETE FROM {table} WHERE {condition}'
#         await self.execute(query)
#
#
# async def main():
#     my = MysqlDB()
#     await my.connect()
#     data = await my.select("SELECT * FROM ui_case")
#     for i in data:
#         print(i)
#     await asyncio.sleep(1)
#
#
# if __name__ == '__main__':
#     asyncio.run(main())
