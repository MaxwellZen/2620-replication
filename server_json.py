import socket
import selectors
import types
import json
from fnmatch import fnmatch
import sys

sel = selectors.DefaultSelector()

# dictionary to store user info
users = {}

def create_account(username, data):
    """
    Creates new account with given username.
    If the username is taken, prompt user to log in.
    """
    if data.logged_in:
        return {"status": "error", "message": f"already logged into account {data.username}"}
    if username in users:
        return {"status": "error", "message": "username taken. please login with your password"}
    else:
        data.username = username
        data.supplying_pass = True
        return {"status": "success", "message": "enter password to create new account"}

def supply_pass(password, data):
    """
    Supplies password for account creation.
    """
    if data.logged_in:
        return {"status": "error", "message": f"already logged into account {data.username}"}
    if data.supplying_pass:
        users.update({data.username: [hash(password), []]})
        data.supplying_pass = False
        return {"status": "success", "message": "account created. please login with your new account"}
    return {"status": "error", "message": "should not be supplying password"}

def login(username, password, data):
    """
    Logs in to an account.
    """
    if data.logged_in:
        return {"status": "error", "message": f"already logged into account {data.username}"}
    if username in users:
        if hash(password) == users[username][0]:
            data.username = username
            data.logged_in = True
            return {"status": "success", "message": "logged in"}
        else:
            return {"status": "error", "message": "password is incorrect. please try again"}
    return {"status": "error", "message": "username does not exist. please create a new account"}

def list_accounts(pattern):
    """
    Lists all accounts matching the given wildcard pattern. Default to all accounts.
    """
    accounts = [user for user in users if fnmatch(user, pattern)]
    count = len(accounts)
    return {"status": "success", "count": count, "accounts": accounts}

def send(recipient, message, data):
    """
    Sends a message to a recipient.
    """
    if not data.logged_in:
        return {"status": "error", "message": "not logged in"}
    if recipient not in users:
        return {"status": "error", "message": "recipient does not exist"}
    messages = users[recipient][1]
    # generate new id that is not currently in use
    id = -1
    for msg in messages:
        id = max(id, int(msg[1]))
    users[recipient][1].append([data.username, str(id + 1), False, message])
    return {"status": "success", "message": "message sent"}

def read(count, data):
    """
    Displays the specified number of unread messages. 
    """
    if not data.logged_in:
        return {"status": "error", "message": "not logged in"}
    all_messages = users[data.username][1]
    count = min(count, len(all_messages))
    to_read = all_messages[len(all_messages) - count:]
    messages = [{"sender": sender, "id": msg_id, "message": msg} for sender, msg_id, _, msg in to_read]
    # display messages in order of most recent to least recent
    messages = list(reversed(messages))
    # mark messages as read
    for i in range(count):
        users[data.username][1][len(all_messages) - count + i][2] = True
    return {"status": "success", "count": count, "messages": messages}

def delete_msg(IDs, data):
    """
    Deletes the messages with the specified IDs. 
    Ignores non-valid or non-existent IDs.
    """
    if not data.logged_in:
        return {"status": "error", "message": "not logged in"}
    messages = users[data.username][1]
    # updated_messages = [msg for msg in messages if msg[1] not in IDs]
    # users[data.username] = (users[data.username][0], updated_messages)
    updated_messages = [msg for msg in messages if msg[1] not in IDs]
    users[data.username][1] = updated_messages
    return {"status": "success", "message": "messages deleted"}

def delete_account(data):
    """
    Deletes the currently logged-in account.
    """
    if not data.logged_in:
        return {"status": "error", "message": "not logged in"}
    users.pop(data.username)
    data.username = None
    data.logged_in = False
    return {"status": "success", "message": "account deleted"}

def logout(data):
    """
    Logs out of the currently logged-in account.
    """
    if not data.logged_in:
        return {"status": "error", "message": "not logged in"}
    data.username = None
    data.logged_in = False
    return {"status": "success", "message": "logged out"}

def num_msg(data):
    """
    Returns the number of unread messages for the logged-in user.
    """
    if not data.logged_in:
        return "ERROR: not logged in"
    return {"status": "success", "message": str(len(users[data.username][1]))}

def handle_command(request, data):
    """
    Handles incoming commands from the client.
    """
    command = request.get("command")
    match command:
        case "create_account":
            return create_account(request.get("username"), data)
        case "supply_pass":
            return supply_pass(request.get("password"), data)
        case "login":
            return login(request.get("username"), request.get("password"), data)
        case "list_accounts":
            pattern = request.get("pattern", "*")
            return list_accounts(pattern)
        case "send":
            return send(request.get("recipient"), request.get("message"), data)
        case "read":
            return read(int(request.get("count")), data)
        case "delete_msg":
            return delete_msg(request.get("ids"), data)
        case "delete_account":
            return delete_account(data)
        case "logout":
            return logout(data)
        case "num_msg":
            return num_msg(data)
        case _:
            return {"status": "error", "message": "invalid command"}

def accept_wrapper(sock):
    """
    Accepts new connections
    """
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"", username=None, logged_in=False, supplying_pass=False)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

def service_connection(key, mask):
    """
    Services existing connections and reads/writes to the connected socket
    """
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)
        if recv_data:
            request = json.loads(recv_data.decode("utf-8"))
            response = handle_command(request, data)
            data.outb += json.dumps(response).encode("utf-8")
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            sent = sock.send(data.outb)
            data.outb = data.outb[sent:]

def main():
    # grabs host and port from command-line arguments
    if len(sys.argv) < 3 or not sys.argv[2].isdigit():
        print("Please provide a host and port for the socket connection")
        print("Example: python3 client_gui.py 127.0.0.1 54400")
        return

    host = sys.argv[1]
    port = int(sys.argv[2])

    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((host, port))
    lsock.listen()
    print("Listening on", (host, port))
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)
    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask)
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()

if __name__ == "__main__":
    main()