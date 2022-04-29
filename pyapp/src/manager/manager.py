from decimal import Decimal
from multiprocessing import Process
from time import sleep, time
from manager.subscriber.subscriber import *
from configs.globals import *
import requests
import hmac
import hashlib
import math

api_key = ""

def get_signature(query_string):
    secret = ""
    timestamp = int(time() * 1000)
    query_string = f"{query_string}&timestamp={timestamp}"
    signature = hmac.new(
        secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{query_string}&signature={signature}"

class Manager:
    def __init__(self) -> None:
        self.arb_threshold = 0.000000000001
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
            trader_p.append(Process(target=self.usdt_busd_trader, args=(base, price_q, size_q)))
            base_info = [i for i in exchange_info["symbols"] if i["symbol"] == f"{base}BUSD"][0]
            price_q, size_q = self.get_quantize(base_info)
            trader_p.append(Process(target=self.busd_usdt_trader, args=(base, price_q, size_q)))
        for p in trader_p:
            p.daemon = True
            p.start()
        for p in trader_p: p.join()
    
    # buy with usdt sell to busd
    # usdt ask < busd bid
    def usdt_busd_trader(self, pair: str, price_q: Decimal, size_q: Decimal):
        split_size_q_decimal = str(size_q).split('.')
        if len(split_size_q_decimal) > 1:
            floor_ask_size = 10 ** len(split_size_q_decimal[1])
        else:
            floor_ask_size = 1
    
        while True:
            try:
                arb_percentage = (
                    float(self.busd_subscriber.price_dict[f"{pair}BUSD"]["b"]) - 
                    float(self.usdt_subscriber.price_dict[f"{pair}USDT"]["a"])
                ) / float(self.usdt_subscriber.price_dict[f"{pair}USDT"]["a"])
                if arb_percentage > self.arb_threshold:
                    bid_price = Decimal(1.1 * float(self.usdt_subscriber.price_dict[f"{pair}USDT"]["a"])).quantize(price_q)
                    bid_size = (Decimal(self.usd_size) / Decimal(bid_price)).quantize(size_q)
                    ask_size = Decimal(math.floor(float(bid_size * Decimal(0.999)) * floor_ask_size) / floor_ask_size).quantize(size_q)
                    bid_query_string = f"symbol={pair}USDT&side=BUY&type=LIMIT&timeInForce=FOK&quantity={str(bid_size)}&price={str(bid_price)}"
                    bid_order_string = get_signature(bid_query_string)
                    ask_query_string = f"symbol={pair}BUSD&side=SELL&type=MARKET&quantity={str(ask_size)}"
                    ask_order_string = get_signature(ask_query_string)
                    
                    print(requests.post(f"https://api.binance.com/api/v3/order?{bid_order_string}", headers={"X-MBX-APIKEY": api_key}).json())
                    print(requests.post(f"https://api.binance.com/api/v3/order?{ask_order_string}", headers={"X-MBX-APIKEY": api_key}).json())
                    
                    print(bid_order_string, ask_order_string)
                    sleep(10)
            except: pass

    # buy with busd sell to usdt
    # TODO
    def busd_usdt_trader(self, pair, price_q, size_q):
        while True:
            pass
            # try:
            #     print(f"{pair} busd_usdt", self.busd_subscriber.price_dict[f"{pair}BUSD"]["b"], self.usdt_subscriber.price_dict[f"{pair}USDT"]["a"])
            # except: pass
