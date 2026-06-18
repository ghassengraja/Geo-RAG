import httpx
import json

async def run_chat():
    async with httpx.AsyncClient(timeout=120) as client:
        print("Sending request to ingest tunisia.geojson...")
        data = {
            "session_id": "test-session-123",
            "user_input": "Please ingest the file /datapc/tunisia.geojson into the HBase catalog 'tunisia_catalog' with the feature name 'tunisia_feature'."
        }
        async with client.stream("POST", "http://127.0.0.1:8000/api/agent/chat", data=data) as response:
            async for line in response.aiter_lines():
                if line:
                    print(line)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_chat())
