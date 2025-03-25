import socket 
import json
from utils import encode_json
import sys

# grabs host and port from command-line arguments
if len(sys.argv) < 3 or not sys.argv[2].isdigit():
    print("Please provide a host and port for the socket connection")
    print("Example: python3 client_gui.py 127.0.0.1 54400")
    sys.exit(0)

host = sys.argv[1]
port = int(sys.argv[2])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((host, port))
    while True:
        message = input("Enter a message to send to the server: ")
        if message == "exit":
            break 
        # encodes standard command into json format
        try: 
            json_request = encode_json(message)
        except:
            print("ERROR: invalid command")
            continue
        # encodes json format into string to be sent along the wire
        json_str = json.dumps(json_request)
        s.sendall(json_str.encode("utf-8"))
        
        # receives json string and converts back into json
        data = s.recv(1024)
        data = data.decode("utf-8")
        print(f"Received: {data}")