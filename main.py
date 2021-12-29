import ujson
from binance_client import binance_futures_client
import asyncio
import aiohttp
from datetime import datetime, timedelta

async def fetch(handle_open_position, handle_order_status, desired_order_id, symbol):
    leave_stream = False
    while True:
        try:
            # get listen key
            async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
                listen_key = await binance_futures_client.listen_key(session)
                start = datetime.now()
                # initial check
                positions = await asyncio.create_task(binance_futures_client.position_information(session))
                order_status = await asyncio.create_task(binance_futures_client.query_order(session, symbol, order_id=desired_order_id))
                # handle position
                try:
                    for position in positions:
                        if position.get('positionAmt') and float(position['positionAmt']) != 0:
                            await asyncio.to_thread(handle_open_position, symbol=symbol, side=position['positionSide'], amount=position['positionAmt'])
                except Exception as exc:
                    pass
                # handle order status
                try:
                    if order_status.get('status'):
                        await asyncio.to_thread(handle_order_status, order_status=order_status['status'])
                except:
                    pass

            # subscribe for user_data_websocket
            async for msg in binance_futures_client.user_data_stream(listen_key):
                try:
                    response = msg
                except:
                    response = {}
                # keep-alive listen key
                if datetime.now() > start + timedelta(minutes=10):
                    async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
                        await binance_futures_client.keep_alive_listen_key(session)
                        start = datetime.now()

                # listen-key expiration handling
                if response.get('e') and response['e'] == 'listenKeyExpired':
                    break

                # handle position
                elif response.get('e') and response['e'] == "ACCOUNT_UPDATE" and response['a'].get('P'):
                    for position in response['a']['P']:
                        leave_stream = await asyncio.to_thread(handle_open_position, symbol=position['s'], side=position['ps'], amount=position['pa'])
                        if leave_stream:
                            break

                # handle order status
                elif response.get('e') and response['e'] == "ORDER_TRADE_UPDATE" and response.get('o'):
                    order_id = response['o']["i"]
                    order_status = response['o']["X"]
                    leave_stream = await asyncio.to_thread(handle_order_status, order_status=order_status, order_id=order_id)
                
                if leave_stream:
                    break
            if leave_stream:
                break

        except Exception as exc:
            print(exc.args)
            continue


# ***change these callbacks*** :
def handle_open_position(symbol, side, amount): 
    print(symbol, side, amount)
    # if you want to leave entry_point:
    return True
    # if you don't want to leave, return False
def handle_order_status(order_status, order_id): 
    print(order_status, order_id)
    # if you want to leave entry_point:
    return True
    # if you don't want to leave, return False
#

# import this function into your project
def entry_point(handle_open_position=handle_open_position,
                handle_order_status=handle_order_status,
                order_id=8886774,
                symbol='BTCUSDT'):

    asyncio.run(
        fetch(
            handle_open_position, handle_order_status, order_id, symbol
        )
    )


if __name__ == "__main__":
    entry_point()
