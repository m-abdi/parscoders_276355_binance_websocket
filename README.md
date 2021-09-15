# asynchronous_binance_client

This is an asynchronous library that is written for using binance services.

You need aiohttp and asyncio for delealing with methods and properties.


1- First instantiate from BinanceFuturesClient:

binance_client = BinanceFuturesClient(api_key, secret_key, testnet=False)


2 - Then from aiohttp.ClientSession:

async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:  


3- Finally await methods:

await binance_client.candlestick_data(session, 'BTCUSDT', interval='4h', limit=300)
