import asyncio
import aiohttp

async def test():
    async with aiohttp.ClientSession() as session:
        print("Connecting to ws://localhost:8080/ws/dispatcher")
        async with session.ws_connect('ws://localhost:8080/ws/dispatcher') as ws:
            await ws.send_str('{"text":"hello"}')
            print("Sent hello")
            async for msg in ws:
                print("Received:", msg.data)
                break

asyncio.run(test())
