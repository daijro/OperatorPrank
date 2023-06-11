if __name__ != '__mp_main__':
    import grequests  # ignore in multiprocessing
import requests

import json
import logging
import os
import pickle
import random
import re
import sys
import time
from base64 import b64decode
from multiprocessing import Process
from multiprocessing import Queue as MPQueue
from queue import Queue

import inquirer
from bs4 import BeautifulSoup as bs
from fake_headers import Headers
from mailtm import Email


__author__ = 'daijro'
__version__ = '1.1'


logging.basicConfig(level=logging.INFO)


class FetchProxy:
    test_url = b64decode('aHR0cHM6Ly9wcmFua2hvdGxpbmUuY29t').decode()

    def __init__(self):
        self.proxy_list = None

    def get(self):
        if not self.proxy_list:
            self.set_proxy_list()
        return self.test_proxies()

    def test_proxies(self):
        while True:
            proxy = random.choice(self.proxy_list)
            self.proxy_list.remove(proxy)  # remove bad proxy from list
            try:
                resp = requests.get(
                    self.test_url,
                    proxies={'socks5': proxy, 'socks5h': proxy},
                    timeout=2,
                    headers=Headers(headers=True).generate(),
                )
                assert resp.status_code != 403  # request forbidden
            except Exception:
                print('Bad proxy:', proxy.ljust(24, ' '), end='\r')
                continue
            return proxy

    def set_proxy_list(self):
        resp = requests.get('https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt')
        self.proxy_list = resp.text.splitlines()
        print(f'Found {len(self.proxy_list)} proxies')


class Pranker:
    base_url = b64decode('aHR0cHM6Ly9wcmFua2hvdGxpbmUuY29t').decode()
    base_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9',
        'Sec-Ch-Ua': '"Not?A_Brand";v="8", "Chromium";v="108"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/108.0.5359.125 Safari/537.36',
    }
    account_api_headers = {
        'Accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': b64decode('aHR0cHM6Ly9wcmFua2hvdGxpbmUuY29t').decode(),
        'Referer': b64decode('aHR0cHM6Ly9wcmFua2hvdGxpbmUuY29tL3Byb2ZpbGU=').decode(),
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'X-Requested-With': 'XMLHttpRequest',
    }

    def __init__(self):
        self.email_queue = None
        self.email = None
        self.tokens = None
        self.proc = None
        self.proxy_fetcher = FetchProxy()

    def buildSession(self, new_email=True):
        self.sess = requests.Session()
        self.email_queue = MPQueue()
        if self.getSavedSession():
            return  # session loaded
        new_email and self.spawnEmailHandler()
        proxy = self.proxy_fetcher.get()
        print('Found working proxy:', proxy)
        self.sess.proxies = {'https': proxy}
        self.generateAccount()

    def spawnEmailHandler(self):
        # kill existing email handler
        self.proc and self.proc.terminate()
        # start email handler thread
        self.proc = Process(target=self.emailHandler, daemon=True)
        self.proc.start()

    def emailHandler(self):
        listen_queue = Queue()

        def listener(message):
            txt = message['text'] or message['html']
            otp = re.search(r'Your login confirmation code is: (\d+)', txt)[1]
            print('Verification code:', otp)
            listen_queue.put(otp)

        # create new email
        print("Registering email")
        test = Email()
        test.register()
        print(f"Email Address: {str(test.address)}")
        self.email_queue.put(test.address)

        # start listening
        test.start(listener)
        self.email_queue.put(listen_queue.get())
        test.stop()  # stop

    def generateAccount(self):
        '''
        send first request to home page to generate cookies
        '''
        self.sess.headers.update(self.base_headers)
        try:
            resp = self.sess.get(f'{self.base_url}/')
            assert resp.status_code == 200
        except Exception:
            return self.failed_status(resp, new_email=False)
        # set cookies
        self.sess.cookies.set("welcome_state", "4")
        self.sess.cookies.set("G_ENABLED_IDPS", "google")
        '''
        send account requests
        '''
        if not self.email:
            self.email = self.email_queue.get()  # wait for email
        account_api_url = f"{self.base_url}/api/?a=login"

        self.sess.headers.update(self.account_api_headers)
        create_account = {
            "email": self.email,  # wait for email
            "pass": '',
            "type": "email",
            "access_token": '',
        }
        try:
            resp = self.sess.post(account_api_url, data=create_account)  # create account
            assert resp.status_code == 200
        except Exception:
            return self.failed_status(resp)
        print('Waiting for email verification code')
        create_account['pass'] = self.email_queue.get()  # wait for verification code
        resp = self.sess.post(account_api_url, data=create_account)  # verify email
        acc_resp = resp.json()
        if 'details' in acc_resp and 'Error' in acc_resp['details']:
            self.failed_status(resp)
        self.saveSession()
        self.setTokens()

    def failed_status(self, resp, new_email=True):
        print('Status:', resp.status_code)
        print('Captcha flagged. Retrying...')
        self.deleteSavedSession()  # delete saved session if exists (proxy was bad)
        return self.buildSession(new_email=new_email)  # retry

    def getSavedSession(self):
        if not os.path.exists("pickle.bin"):
            return
        with open("pickle.bin", "rb") as f:
            self.sess.cookies.update(pickle.load(f))
        with open("proxies.json", "r") as f:
            self.sess.proxies = json.load(f)
        print('Loaded saved session')
        self.setTokens()
        return True

    def deleteSavedSession(self):
        if not os.path.exists("pickle.bin"):
            return
        os.remove("pickle.bin")
        os.remove("proxies.json")

    def saveSession(self):
        with open('pickle.bin', 'wb') as f:
            pickle.dump(self.sess.cookies, f)
        with open('proxies.json', 'w') as f:
            json.dump(self.sess.proxies, f)

    def setTokens(self):
        '''
        get number of tokens
        '''
        headers = {
            **self.base_headers,
            'Referer': f'{self.base_url}/profile',
            'Sec-Fetch-Site': 'same-origin',
        }
        resp = self.sess.get(f'{self.base_url}/profile', headers=headers)
        if resp.status_code != 200:
            return self.failed_status(resp)
        self.tokens = int(bs(resp.text, 'lxml').find('div', class_='left').text.strip())

    @staticmethod
    def normalize_phone(s):
        return '-'.join(re.findall(r'.*?(?:1)?.*?(\d{3}).*?(\d{3}).*?(\d{4})', s)[0])

    def loadPrankTypes(self):
        url = f'{self.base_url}/api/?a=load_pranks'
        data = {
            "type": "prank",
            "page": None,
            "order_by": "popular",
            "filter_by_id": "false",
        }
        reqs = [
            grequests.post(url, data={**data, 'page': str(p)}, session=self.sess) for p in range(2)
        ]
        resps = grequests.map(reqs, size=2)
        items = {
            "Operator": {
                'audio': None,
                'id': 'operator',
            }
        }
        for resp in resps:
            r = resp.json()
            for prank_item in r:
                items[prank_item['title'].title()] = {
                    'audio': f"https://prankhotline.com/sounds/pranks/{prank_item['location']}.mp3",
                    'id': prank_item['id'],
                }
        return items

    def operatorPrank(self, number1, number2, prankId='operator'):
        # normalize phone numbers
        number1, number2 = self.normalize_phone(number1), self.normalize_phone(number2)
        print('Pranking', number1, 'from', number2)
        # set headers
        self.sess.headers.update(self.account_api_headers)
        self.sess.headers['Referer'] = f'{self.base_url}/pickprank/2phones/'
        # send prank request
        prank_data = {
            "dest_number": number1,
            "spoof_number": number2,
            "prank_sound_id": prankId,
            "prank_watermark": "false",
        }
        resp = self.sess.post(f"{self.base_url}/api/?a=send_prank", data=prank_data).json()
        # if there was an error, check if tokens were changed
        if not resp.get('success'):
            self.setTokens()
            return print('Error:', resp)
        self.tokens -= 1
        prankid = resp['prankid']
        print('Prank ID:', prankid)
        print('-' * 20)
        print(resp['details'])
        # start checking status
        while True:
            resp = self.sess.post(
                f"{self.base_url}/api/?a=get_call_status", data={'prankid': prankid}
            ).json()
            print(
                f'Status: "{resp["status"]}"'
                + (
                    # print details if status isnt dialing
                    f' | Details: "{resp["details"]}"'
                    if resp['status'] != 'call_status_dialing'
                    else ''
                )
            )
            if resp.get('reaction_link'):
                print('Reaction saved:', resp['reaction_link'])
                audio = (
                    b64decode(
                        "aHR0cHM6Ly9jZG5zZWN1cmUucHJhbmtob3RsaW5lLmNvbS9zb3VuZHMvcmVhY3Rpb25z"
                    ).decode()
                    + f'/{prankid}.mp3'
                )
                print(f'Audio link: {audio}')
                return resp['reaction_link']
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                return


def promptPrankId(pranker: Pranker):
    pranks = pranker.loadPrankTypes()
    opts = list(pranks.keys())
    # prompt for prank type
    questions = [
        inquirer.List(
            "prankTitle",
            message="Choose a prank type",
            choices=opts,
            default="Operator",
        )
    ]
    try:
        prankTitle = inquirer.prompt(questions, raise_keyboard_interrupt=True)['prankTitle']
    except KeyboardInterrupt:
        sys.exit(0)
    # print audio link if exists
    pranks[prankTitle]['audio'] and print('Audio:', pranks[prankTitle]['audio'])
    prankId = pranks[prankTitle]['id']
    print('ID:', prankId)
    return prankId


if __name__ == '__main__':
    prankId = None
    p = Pranker()
    while True:
        p.buildSession()
        if not prankId:
            prankId = promptPrankId(p)
        while p.tokens > 0:
            print(p.tokens, 'token(s) remaining')
            try:
                prompt = inquirer.text(message="Dest #, Spoof # (or ENTER to go back)")
            except KeyboardInterrupt:
                sys.exit(0)
            if not prompt.strip():
                prankId = promptPrankId(p)
                continue
            # parse phone numbers
            nums = re.findall(
                r'(.*?1?.*?\d{3}.*?\d{3}.*?\d{4}.*?)(.*?1?.*?\d{3}.*?\d{3}.*?\d{4}.*?)',
                prompt,
            )
            if not nums:
                print('Invalid input.', end=' ')
                continue
            p.operatorPrank(*nums[0], prankId=prankId)
        p.deleteSavedSession()
