from json import dumps, loads
from multiprocessing import Manager
from websocket import create_connection
from configs.globals import *


class Subscriber:
    def __init__(self, request_msg) -> None:
        self.request_msg = request_msg
        manager = Manager()
        self.price_dict = manager.dict()

    def start(self):
        self.ws = create_connection(BINANCE_WS_URL)
        self.ws.send(dumps(self.request_msg))
        # skip first 5 msg to prevent irrelavent msg
        for _ in range(5): self.ws.recv()
        while True:
            msg = loads(self.ws.recv())
            self.price_dict[msg['s']] = msg
