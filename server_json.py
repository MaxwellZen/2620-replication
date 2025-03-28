import socket
import selectors
import types
import json
from fnmatch import fnmatch
import sys
import os
import hashlib
import time

sel = selectors.DefaultSelector()
self_host = None

# dictionary to store user info
users = {}
users_file = None

server_sockets = []
server_hosts = []

leader_socket = None 
leader_host = None
is_leader = False

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
        users.update({data.username: [stable_hash(password), []]})
        data.supplying_pass = False

        propagate_change({"command": "new_acct", "username": data.username, "password": password})

        return {"status": "success", "message": "account created. please login with your new account"}
    return {"status": "error", "message": "should not be supplying password"}

def login(username, password, data):
    """
    Logs in to an account.
    """
    if data.logged_in:
        return {"status": "error", "message": f"already logged into account {data.username}"}
    if username in users:
        if stable_hash(password) == users[username][0]:
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

    propagate_change({"command": "new_msg", "username": data.username, "recipient": recipient, "message": message, "id": str(id + 1)})

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

    propagate_change({"command": "new_delete", "username": data.username, "ids": IDs})

    return {"status": "success", "message": "messages deleted"}

def delete_account(data):
    """
    Deletes the currently logged-in account.
    """
    if not data.logged_in:
        return {"status": "error", "message": "not logged in"}
    
    user = data.username
    users.pop(user)
    data.username = None
    data.logged_in = False

    propagate_change({"command": "new_delete_acct", "username": user})

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

def ask_lead():
    """
    Returns whether or not the current server is the leader, as well as the host and port of the current leader
    """
    return {"status": "success", "leader": ("True" if is_leader else "False"), "lead_host": leader_host[0], "lead_port": leader_host[1]}

def server_login(host, port):
    """
    Facilitates addition of new server
    """
    print(f"server login from {(host, port)}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    server_sockets.append(sock)
    server_hosts.append((host, port))
    return {"status": "success", "leader": ("True" if is_leader else "False")}

def full_update():
    """
    sends back full database of users and messages
    """
    return {"status": "success", "users": users}

def new_acct(username, password):
    """
    updates persistent store with new account
    """
    users.update({username: [stable_hash(password), []]})

    with open(users_file, 'w') as file:
        json.dump(users, file)

    return {"status": "success"}

def new_msg(username, recipient, message, id):
    """
    updates persistent store with new message
    """
    users[recipient][1].append([username, id, False, message])
    
    with open(users_file, 'w') as file:
        json.dump(users, file)

    return {"status": "success"}

def new_delete(username, IDs):
    """
    updates persistent store with message deletes
    """
    messages = users[username][1]
    
    updated_messages = [msg for msg in messages if msg[1] not in IDs]
    users[username][1] = updated_messages
    
    with open(users_file, 'w') as file:
        json.dump(users, file)

    return {"status": "success"}

def new_delete_acct(username):
    """
    updates persistent store with deleted account
    """
    users.pop(username)

    with open(users_file, 'w') as file:
        json.dump(users, file)

    return {"status": "success"}

def marco():
    """
    Responds to the call as a leader, or becomes a leader if receiving the call as a non-leader
    """
    global leader_socket, leader_host, is_leader
    if not is_leader:
        print("becoming leader:")
        is_leader = True 
        leader_socket = None 
        leader_host = self_host 
    return {"status": "polo"}

def propagate_change(request):
    """
    Propagates a change to other servers. This has two nuances:
    1) we construct a list of servers that are still alive
    2) we do not wait for a response from other servers, since this leads to deadlock
    """
    global users, users_file, server_sockets, server_hosts
    print("propagating change", request)

    with open(users_file, 'w') as file:
        json.dump(users, file)

    new_sockets = []
    new_hosts = []
    for i in range(len(server_sockets)):
        try:
            sock = server_sockets[i]
            send_request(sock, request, False)
            new_sockets.append(server_sockets[i])
            new_hosts.append(server_hosts[i])
        except:
            continue 

    server_sockets = new_sockets 
    server_hosts = new_hosts 

def handle_command(request, data):
    """
    Handles incoming commands from the client.
    """
    print("request:", request)
    command = request.get("command")

    if not is_leader and command in ["create_account", "supply_pass", "login", "list_accounts", "send", "read", "delete_msg", "delete_account", "logout", "num_msg"]:
        return {"status": "ERROR: not leading server", "lead_host": leader_host[0], "lead_post": leader_host[1]}
    
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
        case "ask_lead":
            return ask_lead()
        case "server_login":
            return server_login(request.get('host'), request.get('port'))
        case "full_update":
            return full_update()
        case "new_acct":
            return new_acct(request.get('username'), request.get('password'))
        case "new_msg":
            return new_msg(request.get('username'), request.get('recipient'), request.get('message'), request.get('id'))
        case "new_delete":
            return new_delete(request.get('username'), request.get('ids'))
        case "new_delete_acct":
            return new_delete_acct(request.get('username'))
        case "marco":
            return marco()
        case "heart":
            return
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
    try:
        sock = key.fileobj
    except:
        print("key:", key)
        print("type(key.fileobj):", type(key.fileobj))
    data = key.data
    
    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(1024)
            if recv_data:
                request = json.loads(recv_data.decode("utf-8"))
                response = handle_command(request, data)
                print("response:", response)
                if response is not None:
                    data.inb += json.dumps(response).encode("utf-8")
            else:
                print(f"Closing connection to {data.addr}")
                sel.unregister(sock)
                sock.close()
        except:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.inb:
            sent = sock.send(data.inb)
            print("sent:", sent)
            data.inb = b""

def main():
    global self_host, users, users_file, server_hosts, server_sockets, leader_socket, leader_host, is_leader

    # grabs host and port from command-line arguments
    if len(sys.argv) < 4 or not sys.argv[2].isdigit():
        print("Please provide a host and port and file for the socket connection")
        print("Example: python3 client_gui.py 127.0.0.1 54400 1")
        return

    # read command line arguments
    host = sys.argv[1]
    port = int(sys.argv[2])
    self_host = (host, port)
    users_file = "users" + sys.argv[3] + ".json"

    # generate listening socket
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((host, port))
    lsock.listen()
    print("Listening on", (host, port))

    # load potential server hosts and loop through them
    servers = []
    with open('ips.config', 'r') as file:
        servers = json.load(file)

    for (host2, port2) in servers:
        if host2 == host and port2 == port:
            continue
        try:
            # try connecting to host
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host2, port2))
            server_sockets.append(sock)
            server_hosts.append((host2, port2))

            # log in as a server and set leader if found
            data = send_request(sock, {"command": "server_login", "host": host, "port": port})
            if data['leader'] == 'True':
                leader_socket = sock 
                leader_host = (host2,port2)
        except:
            continue

    if len(server_sockets) == 0:
        # if this is the first server: become the leader and load users
        print("becoming leader:")
        is_leader = True
        leader_host = (host, port)
        if os.path.exists(users_file):
            with open(users_file, 'r') as file:
                users = json.load(file)
        else:
            with open(users_file, 'w') as file:
                json.dump(users, file)
    else:
        # update users from leader
        is_leader = False
        data = send_request(leader_socket,{"command": "full_update"})
        users = data['users']
        with open(users_file, 'w') as file:
            json.dump(users, file)

    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)

    last_check = 0
    try:
        while True:
            # wait at most one second to process events
            events = sel.select(timeout=1)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask)
            
            # if a second has passed since the last marco-polo check, run another
            if not is_leader and time.time() - last_check > 1:
                last_check = time.time()
                new_sockets = []
                new_hosts = []
                for i in range(len(server_sockets)):
                    try:
                        sock = server_sockets[i]
                        send_request(sock, {"command": "heart"}, False)
                        new_sockets.append(server_sockets[i])
                        new_hosts.append(server_hosts[i])
                    except:
                        continue
                server_sockets = new_sockets 
                server_hosts = new_hosts
                print("server_hosts", server_hosts)

                try:
                    send_request(leader_socket, {"command": "marco"})
                except:
                    # if the leader is gone, decide on the new leader
                    # server_hosts.remove(leader_host)
                    if leader_host in server_hosts:
                        index = server_hosts.index(leader_host)
                        server_hosts.pop(index)
                        server_sockets.pop(index)
                    leader_socket = None 
                    leader_host = None
                    if len(server_hosts) == 0 or self_host < min(server_hosts):
                        # become the new leader
                        is_leader = True 
                        leader_host = self_host 
                        print("becoming leader:")
                    else:
                        # connect to the new leader
                        is_leader = False
                        leader_host = min(server_hosts)
                        leader_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        leader_socket.connect(leader_host)
                        send_request(leader_socket, {"command": "marco"})

    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()

if __name__ == "__main__":
    main()