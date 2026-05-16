import asyncio
import aiohttp

async def test():
    async with aiohttp.ClientSession() as session:
        print("Connecting to wss://tdbns-5-182-57-106.run.pinggy-free.link/ws/dispatcher")
        try:
            async with session.ws_connect('wss://tdbns-5-182-57-106.run.pinggy-free.link/ws/dispatcher') as ws:
                await ws.send_str('{"text":"hello external"}')
                print("Sent hello")
                async for msg in ws:
                    print("Received:", msg.data)
                    break
        except Exception as e:
            print("Failed to connect:", type(e).__name__, e)

asyncio.run(test())
