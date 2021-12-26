from binance import BinanceFuturesClient


api_key = '<YOUR_API_KEY>'
secret_key = '<YOUR_SECRET_KEY>'


binance_futures_client = BinanceFuturesClient(api_key,secret_key, testnet=False)