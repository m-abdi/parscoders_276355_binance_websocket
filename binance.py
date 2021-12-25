import hashlib
import hmac
import websockets
import ujson
from datetime import datetime


class BinanceFuturesClient:
    def __init__(self, api_key, secret_key, testnet: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        if testnet:
            self.base_url = 'https://testnet.binancefuture.com'
            self.base_socket = 'wss://stream.binancefuture.com'
        else:
            self.base_url = 'https://fapi.binance.com'
            self.base_socket = 'wss://fstream.binance.com'

    async def exchange_information(self, session):
        """Current exchange trading rules and symbol information"""
        async with session.get(self.base_url + '/fapi/v1/exchangeInfo') as resp:
            info = await resp.json()
        return info

    async def user_commission_rate(self, session, symbol: str, recv_window=5000):
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'recvWindow': recv_window,
                  'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.get(self.base_url + '/fapi/v1/commissionRate', headers=headers, params=params) as resp:
            info = await resp.json()
        return info

    async def symbol_price_ticker(self, session, symbol: str):
        """Latest price for a symbol or symbols.

        Weight:
        1 for a single symbol;
        2 when the symbol parameter is omitted
        If the symbol is not sent, prices for all symbols will be returned in an array.
        :param session: aiohttp module session
        :param symbol: STRING  optional
        :return: {"symbol": ,"price": ,"time": }
        """
        params = {'symbol': symbol}
        async with session.get(self.base_url + '/fapi/v1/ticker/price', params=params) as resp:
            ticker = await resp.json()
        return ticker

    async def top_trader_long_short_ratio_positions(self, session, symbol: str, period: str, limit=500, start_time = None,
                                                    end_time = None):
        """

        symbol 	STRING 	YES 	
        period 	ENUM 	YES 	"5m","15m","30m","1h","2h","4h","6h","12h","1d"
        limit 	LONG 	NO 	default 30, max 500
        startTime 	LONG 	NO 	
        endTime 	LONG 	NO

        
        If startTime and endTime are not sent, the most recent data is returned.
        Only the data of the latest 30 days is available.
        """
        params = {'symbol': symbol, 'period': period, 'limit': limit, 'startTime': start_time,
                  'endTime': end_time, 'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params, just_clean=True)
        async with session.get(self.base_url + '/futures/data/topLongShortPositionRatio', params=params) as resp:
            data = await resp.json()
        return data
    
    async def change_initial_leverage(self, session, symbol: str, leverage: int, recv_window=5000):
        """Change user's initial leverage of specific symbol market.

        :param recv_window:
        :param session:
        :param symbol:
        :param leverage: target initial leverage: int from 1 to 125
        :return: {"leverage": 21, "maxNotionalValue": "1000000", "symbol": "BTCUSDT"}
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'leverage': leverage, 'recvWindow': recv_window,
                  'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.post(self.base_url + '/fapi/v1/leverage', headers=headers, data=params) as resp:
            data = await resp.json()
        return data
    

    async def change_margin_type(self, session, symbol: str, margin_type, recv_window=5000):
        """

        :param session:
        :param symbol:
        :param margin_type:
        :param recv_window:
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'marginType': margin_type, 'recvWindow': recv_window,
                  'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.post(self.base_url + '/fapi/v1/marginType', headers=headers, data=params) as resp:
            data = await resp.json()
        return data

    async def account_trade_list(self, session, symbol: str, start_time=None, end_time=None, from_id=None, limit: int=None,
                                 recv_window=5000):
        """Get trades for a specific account and symbol.

        :param session:
        :param symbol:
        :param start_time:
        :param end_time:
        :param from_id: Trade id to fetch from. Default gets most recent trades.
        :param limit: Default 500; max 1000.
        :param recv_window:
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'startTime': start_time, 'endTime': end_time, 'fromId': from_id, 'limit': limit,
                  'recvWindow': recv_window, 'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.get(self.base_url + '/fapi/v1/userTrades', headers=headers, params=params) as resp:
            li = resp.json()
        return li

    def signature(self, params, just_clean=False):
        """Makes a signature and adds it to the parameters dictionary.

        :param just_clean: bool
        :param params: dict
        :return: params
        """
        keys = [o for o in iter(params)]
        for e in keys:
            if not params[e]:
                del params[e]
        if just_clean:
            return params
        data = list(params.items())
        query_string = '&'.join(["{}={}".format(d[0], d[1]) for d in data])
        m = hmac.new(self.secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256)
        params.update({'signature': m.hexdigest()})
        return params

    async def candlestick_data(self, session, pair: str, interval=None, start_time=None, end_time=None, limit=None,
                               contract_type='PERPETUAL'):
        """Kline/candlestick bars for a specific contract type.

        Klines are uniquely identified by their open time.
        Weight: based on parameter LIMIT
        :param pair: STRING  required
        :param contract_type: ENUM  required
        :param interval: ENUM  required
        :param start_time: LONG optional
        :param end_time: LONG optional
        :param limit: INT  optional Default 500; max 1500
        :return: [[Open time, Open, High, Low, Close (or latest price), Volume, Close time,
         Quote asset volume, Number of trades, Taker buy volume, Taker buy quote asset volume, Ignore]]
        If startTime and endTime are not sent, the most recent klines are returned.
        Contract type:
        PERPETUAL
        CURRENT_MONTH
        NEXT_MONTH
        """

        params = {'pair': pair, 'contractType': contract_type, 'interval': interval,
                  'startTime': start_time, 'endTime': end_time, 'limit': limit}
        params = self.signature(params, just_clean=True)
        async with session.get(self.base_url + '/fapi/v1/continuousKlines', params=params) as resp:
            data = await resp.json()
        return data

    async def new_order(self, session, symbol: str, side, position_side, type, time_in_force=None, quantity=None,
                        reduce_only=None,
                        price=None, new_client_order_id=None, stop_price=None, close_position=None,
                        activation_price=None,
                        callback_rate=None, working_type=None, price_protect=None, new_order_resp_type=None,
                        recv_window=5000):
        """Send in a new order.

        :param symbol:
        :param side: BUY or SELL
        :param position_side: Default BOTH for One-way Mode ; LONG or SHORT for Hedge Mode. It must be sent in Hedge Mode.
        :param type:
        :param time_in_force:
        :param quantity: DECIMAL Cannot be sent with closePosition=true(Close-All)
        :param reduce_only: "true" or "false". default "false". Cannot be sent in Hedge Mode; cannot be sent with closePosition=true
        :param price:
        :param new_client_order_id: A unique id among open orders. Automatically generated if not sent.
         Can only be string following the rule: ^[\.A-Z\:/a-z0-9_-]{1,36}$
        :param stop_price: Used with STOP/STOP_MARKET or TAKE_PROFIT/TAKE_PROFIT_MARKET orders.
        :param close_position: true, false；Close-All，used with STOP_MARKET or TAKE_PROFIT_MARKET.
        :param activation_price: Used with TRAILING_STOP_MARKET orders, default as the latest price(supporting different workingType)
        :param callback_rate: Used with TRAILING_STOP_MARKET orders, min 0.1, max 5 where 1 for 1%
        :param working_type: stopPrice triggered by: "MARK_PRICE", "CONTRACT_PRICE". Default "CONTRACT_PRICE"
        :param price_protect: "TRUE" or "FALSE", default "FALSE". Used with STOP/STOP_MARKET or TAKE_PROFIT/TAKE_PROFIT_MARKET orders.
        :param new_order_resp_type: "ACK", "RESULT", default "ACK"
        :param recv_window: 5000 milliseconds
        :return:

        Additional mandatory parameters based on type:
        Type 	                            Additional mandatory parameters

        LIMIT 	                            timeInForce, quantity, price
        MARKET 	                            quantity
        STOP/TAKE_PROFIT 	                quantity, price, stopPrice
        STOP_MARKET/TAKE_PROFIT_MARKET 	    stopPrice
        TRAILING_STOP_MARKET 	            callbackRate
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'side': side, 'positionSide': position_side, 'type': type,
                  'timeInForce': time_in_force, 'quantity': quantity, 'reduceOnly': reduce_only, 'price': price,
                  'newClientOrderId': new_client_order_id, 'stopPrice': stop_price, 'closePosition': close_position,
                  'activationPrice': activation_price, 'callbackRate': callback_rate, 'workingType': working_type,
                  'priceProtect': price_protect, 'newOrderRespType': new_order_resp_type, 'recvWindow': recv_window,
                  'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.post(self.base_url + '/fapi/v1/order', headers=headers, data=params) as order:
            trade = await order.json()
        return trade

    async def query_order(self, session, symbol, order_id=None, orig_client_order_id=None, recv_window=5000):
        """Check an order's status.

        These orders will not be found:

            order status is CANCELED or EXPIRED, AND
            order has NO filled trade, AND
            created time + 7 days < current time

        :param session:
        :param symbol:
        :param order_id:
        :param orig_client_order_id: STRING  NO
        :param recv_window:
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'orderId': order_id, 'origClientOrderId': orig_client_order_id,
                  'recvWindow': recv_window, 'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.get(self.base_url + '/fapi/v1/order', headers=headers, params=params) as resp:
            return await resp.json()

    async def cancel_order(self, session, symbol, order_id=None, orig_client_order_id=None, recv_window=5000):
        """Cancel an active order.

        :param recv_window:
        :param symbol:
        :param order_id: LONG
        :param orig_client_order_id: STRING
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'orderId': order_id, 'origClientOrderId': orig_client_order_id,
                  'recvWindow': recv_window, 'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.delete(self.base_url + '/fapi/v1/order', headers=headers, params=params) as resp:
            return await resp.json()

    async def cancel_all_open_orders(self, session, symbol: str, recv_window=5000):
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'recvWindow': recv_window,
                  'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.delete(self.base_url + '/fapi/v1/allOpenOrders', headers=headers, params=params) as resp:
            return await resp.json()

    async def cancel_multiple_orders(self, session, symbol, order_id_list=None, orig_client_order_id_list=None, recv_window=5000):
        """

        :param symbol:  STRING 	YES
        :param order_id_list:  	LIST<LONG> 	NO 	max length 10  e.g. [1234567,2345678]
        :param orig_client_order_id_list: LIST<STRING> 	NO 	max length 10
        e.g. ["my_id_1","my_id_2"], encode the double quotes. No space after comma.
        Either orderIdList or origClientOrderIdList must be sent.
        :param recv_window:
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'orderIdList': order_id_list, 'origClientOrderIdList': orig_client_order_id_list,
                  'recvWindow': recv_window, 'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.delete(self.base_url + '/fapi/v1/batchOrders', headers=headers, params=params) as resp:
            return await resp.json()

    async def account_balance(self, session, recv_window=5000):
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'recvWindow': recv_window, 'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.get(self.base_url + '/fapi/v2/balance', headers=headers, params=params) as resp:
            return await resp.json()

    async def position_information(self, session, symbol: str, recv_window=5000):
        """Get current position information.

        :param symbol:
        :param recv_window:
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol,'recvWindow': recv_window,
                  'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.get(self.base_url + '/fapi/v2/positionRisk', headers=headers, params=params) as resp:
            return await resp.json()

    async def listen_key(self, session):
        """Start a new user data stream.

        The stream will close after 60 minutes unless a keepalive is sent. If the account has an active listenKey,
         that listenKey will be returned and its validity will be extended for 60 minutes.

        :param session:
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        async with session.post(self.base_url + '/fapi/v1/listenKey', headers=headers) as listen_key:
            listen_key = await listen_key.json()
            return listen_key['listenKey']

    async def keep_alive_listen_key(self, session):
        """Keepalive a user data stream to prevent a time out.

        User data streams will close after 60 minutes. It's recommended to send a ping about every 60 minutes.
        :param session:
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        async with session.put(self.base_url + '/fapi/v1/listenKey', headers=headers) as listen_key:
            listen_key = await listen_key.json()
        return listen_key

    async def close_listen_key(self, session):
        """Close out a user data stream.

        :param session:
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        async with session.delete(self.base_url + '/fapi/v1/listenKey', headers=headers) as listen_key:
            listen_key = await listen_key.json()
        return listen_key

    async def user_data_stream(self, session, listen_key):
        uri = self.base_socket + f'/ws/{listen_key}'
        async with websockets.connect(uri) as ws:
            yield await ws.recv()

    async def aggregate_trade_streams(self, symbol):
        """The Aggregate Trade Streams push trade information that is aggregated for a single taker order every 100 milliseconds.

        :param symbol: str insensitive
        :return: price
        """
        url = self.base_socket + f'/ws/{symbol.lower()}@aggTrade'
        async with websockets.connect(url) as webs:
            async for msg in webs:
                yield ujson.loads(msg)
    
    async def combined_stream(self, stream1, stream2):
        url = self.base_socket + f"/stream?streams={stream1}/{stream2}"

    async def mark_price_stream(self, session, symbol):
        """The Aggregate Trade Streams push trade information that is aggregated for a single taker order every 100 milliseconds.

        :param symbol: str insensitive
        :return: price
        """
        uri = self.base_socket + f'/ws/{symbol.lower()}@markPrice'
        async with websockets.connect(uri) as webs:
            while True:
                yield webs.recv()

    async def cc_candlestick_streams(self, session, symbol: str, interval, contract_type='perpetual'):
        """Continuous Contract Kline/Candlestick Streams.

        :param interval: m -> minutes; h -> hours; d -> days; w -> weeks; M -> months
        :param contract_type:  perpetual, current_quarter, next_quarter
        :param session:
        :param symbol:
        :return:
        """
        url = self.base_socket + f'/ws/{symbol.lower()}_{contract_type}@continuousKline_{interval}'
        async with session.ws_connect(url) as ws:
            async for msg in ws:
                yield msg




class BinanceSpotClient:
    def __init__(self, api_key, secret_key, testnet: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        if testnet:
            self.base_url = ' 	https://testnet.binance.vision/api'
            self.base_socket = 'wss://testnet.binance.vision'
        else:
            self.base_url = 'https://api.binance.com'
            self.base_socket = 'wss://stream.binance.com:9443'

    async def exchange_information(self, session):
        """Current exchange trading rules and symbol information.

        :return:
        """
        async with session.get(self.base_url + '/api/v3/exchangeInfo') as resp:
            info = await resp.json()
        return info

    async def symbol_price_ticker(self, session, symbol=None):
        """Latest price for a symbol or symbols.

        :param session: No
        :param symbol:
        :return:
        """
        params = {'symbol': symbol}
        async with session.get(self.base_url + '/api/v3/ticker/price', params=params) as resp:
            info = await resp.json()
        return info

    def signature(self, params, just_clean=False):
        """Makes a signature and adds it to the parameters dictionary.

        :param just_clean: bool
        :param params: dict
        :return: params
        """
        keys = [o for o in iter(params)]
        for e in keys:
            if not params[e]:
                del params[e]
        if just_clean:
            return params
        data = list(params.items())
        query_string = '&'.join(["{}={}".format(d[0], d[1]) for d in data])
        m = hmac.new(self.secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256)
        params.update({'signature': m.hexdigest()})
        return params

    async def new_order(self, session, symbol: str, side, type, time_in_force=None, quantity=None,
                        quote_order_qty=None, price=None, new_client_order_id=None, stop_price=None, iceberg_qty=None,
                        new_order_resp_type=None, recv_window=5000):
        """Send in a new order.

        :param session:
        :param symbol:
        :param side:
        :param type:
        :param time_in_force:
        :param quantity: DECIMAL
        :param quote_order_qty: DECIMAL
        :param price: DECIMAL
        :param new_client_order_id: STRING 	NO 	A unique id among open orders. Automatically generated if not sent.
        :param stop_price: DECIMAL 	NO 	Used with STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, and TAKE_PROFIT_LIMIT orders.
        :param iceberg_qty: DECIMAL NO 	Used with LIMIT, STOP_LOSS_LIMIT, and TAKE_PROFIT_LIMIT to create an iceberg order.
        :param new_order_resp_type: Set the response JSON. ACK, RESULT, or FULL; MARKET and LIMIT order types default to FULL, all other orders default to ACK.
        :param recv_window: The value cannot be greater than 60000
        :return:
        """
        headers = {'X-MBX-APIKEY': self.api_key}
        params = {'symbol': symbol, 'side': side, 'type': type,
                  'timeInForce': time_in_force, 'quantity': quantity, 'quoteOrderQty': quote_order_qty, 'price': price,
                  'newClientOrderId': new_client_order_id, 'stopPrice': stop_price, 'icebergQty': iceberg_qty,
                  'newOrderRespType': new_order_resp_type, 'recvWindow': recv_window,
                  'timestamp': f'{round(datetime.now().timestamp() * 1000)}'}
        params = self.signature(params)
        async with session.post(self.base_url + '/api/v3/order', headers=headers, data=params) as order:
            trade = await order.json()
        return trade
