from multiprocessing import Process
from manager.subscriber.subscriber import *
from configs.globals import *



class Manager:
    def __init__(self) -> None:
        pass

    def request_msg_constructor(self, quote: str, id: int):
        params = []
        for base in SUBSCRIBING_PAIRS:
            params.append(f"{base.lower()}{quote.lower()}@bookTicker")
        return {
            "method": "SUBSCRIBE",
            "params": params,
            "id": id
        }

    def start(self):
        self.usdt_subscriber = Subscriber(self.request_msg_constructor("USDT", 1))
        self.busd_subscriber = Subscriber(self.request_msg_constructor("BUSD", 2))
        p_usdt = Process(target=self.usdt_subscriber.start)
        p_usdt.daemon = True
        p_usdt.start()
        p_busd = Process(target=self.busd_subscriber.start)
        p_busd.daemon = True
        p_busd.start()
        
        trader_p = []
        for base in SUBSCRIBING_PAIRS:
            trader_p.append(Process(target=self.usdt_busd_trader, args=(base,)))
            trader_p.append(Process(target=self.busd_usdt_trader, args=(base,)))
        for p in trader_p:
            p.daemon = True
            p.start()
        for p in trader_p: p.join()
        # while True:
        #     print(self.usdt_subscriber.price_dict, self.busd_subscriber.price_dict)
    

    def usdt_busd_trader(self, pair):
        while True:
            try:
                print(f"{pair} usdt_busd", self.usdt_subscriber.price_dict[f"{pair}USDT"]["b"], self.busd_subscriber.price_dict[f"{pair}BUSD"]["a"])
            except: pass
    
    def busd_usdt_trader(self, pair):
        while True:
            try:
                print(f"{pair} busd_usdt", self.busd_subscriber.price_dict[f"{pair}BUSD"]["b"], self.usdt_subscriber.price_dict[f"{pair}USDT"]["a"])
            except: pass
