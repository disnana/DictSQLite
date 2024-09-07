from multiprocessing import Manager
from multiprocessing.managers import BaseManager
import time

class ManagerWithList(BaseManager): pass

class SharedListManager:
    def __init__(self):
        self.shared_list = []

    def get_shared_list(self):
        return self.shared_list

def start_server():
    manager = ManagerWithList(address=('127.0.0.1', 50000), authkey=b'secret')
    manager.register('get_shared_list', callable=shared_list_manager.get_shared_list)
    server = manager.get_server()
    server.serve_forever()

if __name__ == '__main__':
    shared_list_manager = SharedListManager()
    start_server()
