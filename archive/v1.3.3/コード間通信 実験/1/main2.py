from multiprocessing.managers import BaseManager
import time

class ManagerWithList(BaseManager): pass

def main():
    manager = ManagerWithList(address=('127.0.0.1', 50000), authkey=b'secret')
    manager.register('get_shared_list')
    manager.connect()
    shared_list = manager.get_shared_list()
    print(shared_list)

    print('Client connected. Accessing shared list...')

    # Access and modify the shared list
    shared_list.append('some_data')

    print(f'Shared list contents: {shared_list}')

if __name__ == '__main__':
    main()
