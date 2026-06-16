import asyncio
from app.api.routes import app_graph
from langchain_core.messages import HumanMessage

async def main():
    print("Graph compiled successfully with RedisSaver!")
    
asyncio.run(main())
