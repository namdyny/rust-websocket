from decimal import Decimal
from multiprocessing import Process
from threading import Thread
from time import sleep, time
from traceback import format_exc
from manager.subscriber.subscriber import *
from configs.globals import *
import requests
import hmac
import hashlib
import math

api_key = "5IbS2QSoOp5LqkbXgQraig0jSACjJjyZWlPthP0b2S82NmULmBNoflV1UomF5gOw"

def get_signature(query_string):
    secret = "0B5fmQ5T8VHwJ2n5I3p1qdpkrXVQVjo18hZWl3HCHd73LqSoaVJOK3ikWOHhXHzt"
    timestamp = int(time() * 1000)
    query_string = f"{query_string}&timestamp={timestamp}"
    signature = hmac.new(
        secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{query_string}&signature={signature}"

class Manager:
    def __init__(self) -> None:
        self.arb_threshold = 0.003
        self.usd_size = 15

    def request_msg_constructor(self, quote: str, id: int):
        params = []
        for base in SUBSCRIBING_PAIRS:
            params.append(f"{base.lower()}{quote.lower()}@bookTicker")
        return {
            "method": "SUBSCRIBE",
            "params": params,
            "id": id
        }

    def get_quantize(self, base_info: dict):
        price_q = base_info["filters"][0]["tickSize"].strip("0")
        size_q = base_info["filters"][2]["stepSize"].strip("0")
        return Decimal(price_q), Decimal(size_q)

    def start(self):
        self.usdt_subscriber = Subscriber(self.request_msg_constructor("USDT", 1))
        self.busd_subscriber = Subscriber(self.request_msg_constructor("BUSD", 2))
        p_usdt = Process(target=self.usdt_subscriber.start)
        p_usdt.daemon = True
        p_usdt.start()
        p_busd = Process(target=self.busd_subscriber.start)
        p_busd.daemon = True
        p_busd.start()
        
        exchange_info = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
        trader_p = []
        for base in SUBSCRIBING_PAIRS:
            base_info = [i for i in exchange_info["symbols"] if i["symbol"] == f"{base}USDT"][0]
            price_q, size_q = self.get_quantize(base_info)
            trader_p.append(Process(
                target=self.arbitrage_trader,
                args=(base, price_q, size_q, "USDT", "BUSD")
            ))
            base_info = [i for i in exchange_info["symbols"] if i["symbol"] == f"{base}BUSD"][0]
            price_q, size_q = self.get_quantize(base_info)
            trader_p.append(Process(
                target=self.arbitrage_trader, args=(base, price_q, size_q, "BUSD", "USDT")
            ))
        for p in trader_p:
            p.daemon = True
            p.start()
        for p in trader_p: p.join()
    
    # buy with usdt sell to busd
    # usdt ask < busd bid
    def arbitrage_trader(self, pair: str, price_q: Decimal, size_q: Decimal, buy_from: str, sell_to: str):
        split_size_q_decimal = str(size_q).split('.')
        if len(split_size_q_decimal) > 1:
            floor_ask_size = 10 ** len(split_size_q_decimal[1])
        else:
            floor_ask_size = 1
    
        def place_order(order_string):
            try:
                res = requests.post(
                    f"https://api.binance.com/api/v3/order?{order_string}",
                    headers={"X-MBX-APIKEY": api_key}
                ).json()
                if "code" in res:
                    pass
                else:
                    if Decimal(res["executedQty"]) != Decimal(0):
                        print(f"** {res['side']} {res['symbol']} P={res['price']} V={res['executedQty']} **")
            except:
                print(f"Order requests failed {order_string}")

        if buy_from == "USDT":    
            bid_subscriber = self.usdt_subscriber
            ask_subscriber = self.busd_subscriber
        else:
            bid_subscriber = self.busd_subscriber
            ask_subscriber = self.usdt_subscriber
        while True:
            place_order_p = []
            try:
                arb_percentage = (
                    float(ask_subscriber.price_dict[f"{pair}{sell_to}"]["b"]) - 
                    float(bid_subscriber.price_dict[f"{pair}{buy_from}"]["a"])
                ) / float(bid_subscriber.price_dict[f"{pair}{buy_from}"]["a"])
                if arb_percentage > self.arb_threshold:
                    bid_price = Decimal(float(bid_subscriber.price_dict[f"{pair}{buy_from}"]["a"])).quantize(price_q)
                    bid_size = (Decimal(self.usd_size) / Decimal(bid_price)).quantize(size_q)
                    ask_size = Decimal(math.floor(float(bid_size * Decimal(0.999)) * floor_ask_size) / floor_ask_size).quantize(size_q)
                    
                    if Decimal(bid_subscriber.price_dict[f"{pair}{buy_from}"]["A"]) > bid_size * Decimal(2) and \
                        Decimal(ask_subscriber.price_dict[f"{pair}{sell_to}"]["B"]) > ask_size * Decimal(2):

                        bid_query_string = f"symbol={pair}{buy_from}&side=BUY&type=LIMIT&timeInForce=FOK&quantity={str(bid_size)}&price={str(bid_price)}"
                        bid_order_string = get_signature(bid_query_string)
                        ask_query_string = f"symbol={pair}{sell_to}&side=SELL&type=MARKET&quantity={str(ask_size)}"
                        ask_order_string = get_signature(ask_query_string)
                        
                        place_order_p.append(Thread(target=place_order, args=(bid_order_string,)))
                        for _ in range(8):
                            place_order_p.append(Thread(target=place_order, args=(ask_order_string,)))
                        for p in place_order_p:
                            p.daemon = True
                            p.start()
                            sleep(0.0000001)
                        for p in place_order_p: p.join()
                        
                        print(f"{pair}{buy_from} {pair}{sell_to} %={Decimal(arb_percentage).quantize(Decimal('0.000001'))} cycle bid_price={bid_price} bid_size={bid_size} ask@market ask_size={ask_size}")

                        sleep(10)
                else:
                    if arb_percentage > 0:
                        print(f"%={Decimal(arb_percentage).quantize(Decimal('0.000001'))}")

            except KeyError:
                print(f"{pair}{buy_from} {pair}{sell_to} Price book not ready")
                # print(format_exc())
                sleep(5)

            except: print(format_exc())

    # buy with busd sell to usdt
    # TODO
    def busd_usdt_trader(self, pair, price_q, size_q):
        while True:
            pass
            # try:
            #     print(f"{pair} busd_usdt", self.busd_subscriber.price_dict[f"{pair}BUSD"]["b"], self.usdt_subscriber.price_dict[f"{pair}USDT"]["a"])
            # except: pass
