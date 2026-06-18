import httpx
import asyncio
from app.livy_client import livy_client
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    await livy_client.init_session()
    print("Testing PySpark:")
    res = await livy_client.execute_code('print(1+1)')
    print(res)
    print("Testing Scala:")
    res2 = await livy_client.execute_scala_code('println(1+1)')
    print(res2)
    await livy_client.close()

if __name__ == "__main__":
    asyncio.run(main())
