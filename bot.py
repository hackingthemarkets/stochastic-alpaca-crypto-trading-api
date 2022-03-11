import config
import vectorbt as vbt
import pandas as pd
import pandas_ta as ta
from datetime import datetime
from alpaca_trade_api.rest import REST, TimeFrame

alpaca = REST(config.API_KEY, config.SECRET_KEY, 'https://paper-api.alpaca.markets')

in_position_quantity = 0
pending_orders = {}
dollar_amount = 10000
logfile = 'trade.log'

def check_order_status():
    global in_position_quantity

    removed_order_ids = []

    print("{} - checking order status".format(datetime.now().isoformat()))

    if len(pending_orders.keys()) > 0:
        print("found pending orders")
        for order_id in pending_orders:
            order = alpaca.get_order(order_id)

            if order.filled_at is not None:
                filled_message = "order to {} {} {} was filled {} at price {}\n".format(order.side, order.qty, order.symbol, order.filled_at, order.filled_avg_price)
                print(filled_message)
                with open(logfile, 'a') as f:
                    f.write(str(order))
                    f.write(filled_message)
            
                if order.side == 'buy':
                    in_position_quantity = float(order.qty)
                else:
                    in_position_quantity = 0

                removed_order_ids.append(order_id)
            else:
                print("order has not been filled yet")

    for order_id in removed_order_ids:
        del pending_orders[order_id]


def send_order(symbol, quantity, side):
    print("{} - sending {} order".format(datetime.now().isoformat(), side))
    order = alpaca.submit_order(symbol, quantity, side, 'market')
    print(order)
    pending_orders[order.id] = order


def get_bars():
    print("{} - getting bars".format(datetime.now().isoformat()))
    data = vbt.CCXTData.download(['SOLUSDT'], start='30 minutes ago', timeframe='1m')
    df = data.get()
    df.ta.stoch(append=True)
    print(df)

    last_k = df['STOCHk_14_3_3'].iloc[-1]
    last_d = df['STOCHd_14_3_3'].iloc[-1]
    last_close = df['Close'].iloc[-1]

    print(last_k)
    print(last_d)
    print(last_close)

    if last_d < 20 and last_k > last_d:
        if in_position_quantity == 0:
            # buy
            send_order('SOLUSD', dollar_amount / last_close, 'buy')
        else:
            print("== already in position, nothing to do ==")

    if last_d > 80 and last_k < last_d:
        if in_position_quantity > 0:
            # sell
            send_order('SOLUSD', in_position_quantity, 'sell')
        else:
            print("== you have nothing to sell ==")


manager = vbt.ScheduleManager()
manager.every().do(check_order_status)
manager.every().minute.at(':00').do(get_bars)
manager.start()

