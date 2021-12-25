import ujson
from binance_client import binance_futures_client
import asyncio
import websockets
import aiohttp
from datetime import datetime, timedelta
async def fetch():
    while True:
        # get listen key
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            listen_key = await binance_futures_client.listen_key(session)
            start = datetime.now()
        # subscribe for user_data_websocket
        async for msg in binance_futures_client.user_data_stream(session, listen_key):
            
            print(response := ujson.loads(msg))
            # keep-alive listen key
            if datetime.now() > start + timedelta(minutes=40):
                async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
                    await binance_futures_client.keep_alive_listen_key(session)
            
            # listen-key expiration handling
            if response.get('e') and response['e'] == 'listenKeyExpired':
                continue




asyncio.get_event_loop().run_until_complete(fetch())
