import asyncio
from app.db.connection import DatabasePool

async def main():
    await DatabasePool.init_pool()
    await DatabasePool.close_pool()
    print("Database table recreated successfully.")

asyncio.run(main())
