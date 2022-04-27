from json import dumps, loads
from manager.manager import *
import websocket


if __name__ == "__main__":
    manager = Manager()
    manager.start()