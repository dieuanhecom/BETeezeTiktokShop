from concurrent.futures import ThreadPoolExecutor

import requests


def kill():
    response = requests.get('http://192.168.1.42:2000/login')
    print(response)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(kill) for i in range(10000000)]

        for future in futures:
            print(future.result())
