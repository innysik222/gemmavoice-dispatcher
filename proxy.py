import asyncio
import aiohttp
from aiohttp import web

async def handle_http(request):
    print(f"DEBUG: Proxying HTTP {request.method} {request.path_qs}")
    try:
        async with aiohttp.ClientSession() as session:
            url = 'http://127.0.0.1:3000' + request.path_qs
            headers = {k: v for k, v in request.headers.items() if k.lower() != 'host'}
            headers['Host'] = 'localhost:3000'
            
            async with session.request(
                request.method, 
                url, 
                headers=headers, 
                data=await request.read(),
                allow_redirects=False
            ) as resp:
                body = await resp.read()
                excluded_headers = {'content-encoding', 'transfer-encoding', 'content-length', 'connection', 'keep-alive'}
                response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers}
                return web.Response(body=body, status=resp.status, headers=response_headers)
    except Exception as e:
        print(f"ERROR in handle_http: {e}")
        return web.Response(text=str(e), status=500)

async def handle_ws(request):
    print(f"DEBUG: Proxying WS {request.path_qs}")
    ws_server = web.WebSocketResponse()
    await ws_server.prepare(request)
    
    try:
        async with aiohttp.ClientSession() as session:
            url = 'ws://127.0.0.1:8000' + request.path_qs
            async with session.ws_connect(url) as ws_client:
                async def forward(ws_from, ws_to):
                    async for msg in ws_from:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await ws_to.send_str(msg.data)
                        elif msg.type == aiohttp.WSMsgType.BINARY:
                            await ws_to.send_bytes(msg.data)
                        elif msg.type == aiohttp.WSMsgType.CLOSE:
                            await ws_to.close()
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                
                await asyncio.gather(
                    forward(ws_server, ws_client),
                    forward(ws_client, ws_server)
                )
    except Exception as e:
        print(f"ERROR in handle_ws: {e}")
    return ws_server

app = web.Application()
app.router.add_route('*', '/ws/{tail:.*}', handle_ws)
app.router.add_route('*', '/{tail:.*}', handle_http)

if __name__ == '__main__':
    print("Starting Unified Proxy on 0.0.0.0:8080...")
    web.run_app(app, host='0.0.0.0', port=8080)
