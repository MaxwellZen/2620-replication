import socket
import selectors
import types
import json
from fnmatch import fnmatch
import sys
import os
import hashlib
import time

DELAY = 0.1

def stable_hash(s):
    """
    hash function that preserves stability, allows updating password across servers
    """
    return hashlib.sha256(s.encode()).hexdigest()

def send_request(sock, request, getdata = True):
    print("sending request", request)
    message = json.dumps(request).encode('utf-8')
    sock.sendall(message)
    if getdata:
        data = json.loads(sock.recv(1024).decode('utf-8'))
        print("received:", data)
        return data
    else:
        return "sent"
    
socks = [0] * 3
for i in range(3):
    socks[i] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socks[i].connect(('127.0.0.1', 54400 + i))

data = send_request(socks[0], {"command": "ask_lead"})
assert(data['leader'] == 'True' and data['lead_host'] == '127.0.0.1' and data['lead_port'] == 54400)
data = send_request(socks[1], {"command": "ask_lead"})
assert(data['leader'] == 'False' and data['lead_host'] == '127.0.0.1' and data['lead_port'] == 54400)

data = send_request(socks[0], {"command": "marco"})
assert(data['status'] == 'polo')

data = send_request(socks[0], {"command": "create_account", "username": "maxwell"})
data = send_request(socks[0], {"command": "supply_pass", "password": "maxwellpass"})

# check that acount creation has propagated
time.sleep(DELAY)
data = send_request(socks[2], {"command": "full_update"})
assert(data['users']['maxwell'] == [stable_hash("maxwellpass"), []])

data = send_request(socks[0], {"command": "create_account", "username": "andrew"})
data = send_request(socks[0], {"command": "supply_pass", "password": "andrewpass"})

# check that acount creation has propagated
time.sleep(DELAY)
data = send_request(socks[1], {"command": "full_update"})
assert(data['users']['maxwell'] == [stable_hash("maxwellpass"), []])
assert(data['users']['andrew'] == [stable_hash("andrewpass"), []])

data = send_request(socks[0], {"command": "login", "username": "maxwell", "password": "maxwellpass"})
data = send_request(socks[0], {"command": "send", "recipient": "maxwell", "message": "me myself and i"})

# check that message has been sent
time.sleep(DELAY)
data = send_request(socks[2], {"command": "full_update"})
assert(data['users']['maxwell'] == [stable_hash("maxwellpass"), [["maxwell", "0", False, "me myself and i"]]])
assert(data['users']['andrew'] == [stable_hash("andrewpass"), []])

data = send_request(socks[0], {"command": "delete_msg", "ids": ["0"]})

# check that message has been deleted
time.sleep(DELAY)
data = send_request(socks[1], {"command": "full_update"})
assert(data['users']['maxwell'] == [stable_hash("maxwellpass"), []])
assert(data['users']['andrew'] == [stable_hash("andrewpass"), []])

data = send_request(socks[0], {"command": "delete_account"})

# check that account has been deleted
time.sleep(DELAY)
data = send_request(socks[2], {"command": "full_update"})
assert('maxwell' not in data['users'])
assert(data['users']['andrew'] == [stable_hash("andrewpass"), []])

print("tests passed!")
