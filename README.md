# 2620-replication

## Code Design

Once again, we started working through a Google Doc which can be viewed [here](https://docs.google.com/document/d/1kj1Fqxw5QKV8bQl7oWOsw4X2q1sRYClHn55qfDBnAxY/edit?usp=sharing). However, all information is also provided below.

### General Structure

All possible server hosts and ports are listed in the `ips.config` file, which is not on the GitHub repo but is created locally. The vision is to have multiple servers, with "child" servers deferring to a "lead" server. Clients will all be connected to the lead server, and the lead server will propagate any changes (accounts being created and deleted, messages being sent and deleted) to the other servers. This way, if a child server disconnects, there are no issues. However, if the lead server disconnects, the child servers must determine which server is the new lead server and then defer to them for updates. Clients will search for the new lead server to reconnect and resume normal activity. In order to detect when the lead server has disconnected, the child servers will send "marco" queries to the lead server, which the lead server must respond to with "polo" in order to confirm that it is still alive -- this functions as a heartbeat check. Additionally, child servers send "heart" queries to each other, but this query doesn't have a response (otherwise there's the possibility of a deadlock happening if two servers send a "heart" check to each other and wait for the other's response).

### Client Side

At the beginning, the client must:
- Scan `ips.config` for all server locations
- Try connecting to each and use "ask_lead" query in order to find leader
- If no servers found, keep cycling (wait 0.5 seconds to save computation)

When the client wants to make a request to the server, it must:
- Catch errors when communicating with the server (to detect lead server crashing)
- Perform the same action of cycling through server locations to find the leader as above

### Server Side

At the beginning, the server must:
- Scan config for all active server locations
- If no servers: current server is the leader, read from users{k}.json or start empty
- Otherwise: sign in with other servers via "server_login" command, use output to find leader

Note that since this allows a new server to sign on at any point in time, this allows us to satisfy the extra credit requirement of adding new servers to the set of replicas -- it's possible to use this system to initialize arbitrarily many memory replicas.

To facilitate this process, we have some new variables:
- `server_sockets`: sockets connected to other servers (mainly for lead server to propagate changes to children)
- `server_hosts`: host and port of each server being tracked
- `leader_socket`: socket connected to leader (or None if this server is the leader)
- `leader_host`: host and port of the leader
- `is_leader`: whether the current process is the lead server

During the regular loop of checking for events from the selector, we need to make two changes:
- The selector must have a timeout of one second, to make way for the marco-polo heartbeat check
- After processing selector events, if a second has passed since the last heartbeat check, perform another heartbeat check

Additionally, we created new commands to facilitate communication between processes:
- "ask_lead": asks if current process is the leader
    - params: N/A
    - response: "leader": "True" or "False", "lead_host": IP address, "lead_port": port number
- "server_login": registers new server
    - params: "host": IP address, "port": port number
    - response: "leader": "True" or "False"
- "full_update": asks for all accounts and messages so far
    - params: N/A
    - response: "users": {dictionary of data}
- "new_acct": indicate to servers that new account has been created
    - params: "username", "password"
    - response: N/A
- "new_msg": indicate to servers that new message has been sent
    - params: "username", "recipient", "message", "id"
    - response: N/A
- "new_delete": indicate that messages have been deleted
    - params: "username", "ids"
    - response: N/A
- "new_delete_acct": indicate that an account has been deleted
    - params: "username"
    - response: N/A
- "marco": check if leader is alive
    - params: N/A
    - response: "polo"
    - if non-leader receives marco: become leader
- "heart": check if a child server is slive
    - params: N/A
    - response: N/A

Finally, if the lead server crashes and the children must decide who the new leader is, I created a pretty primitive scheme of just picking the server with the minimum value of (host, port).

## Usage

First, the `ips.config` file must be generated. I chose to represent it using json, so a Python script may be necessary to construct it in json format. Here's the script I used:

```py
import json 

data = [("127.0.0.1", 54400), ("127.0.0.1", 54401), ("127.0.0.1", 54402)]
with open('ips.config', 'w') as file:
    json.dump(data, file, indent=4)
```

Then, the `server_json.py` program runs with three arguments: the host address, the port number, and a number `k`. Server instances will write to `users{k}.json`, so I used 1, 2, and 3 to get the copies of my data in files `users1.json`, `users2.json`, and `users3.json`. As an example:

```
python3 server_json.py 127.0.0.1 54400 1
```

Finally, the `client_gui.py` program does not require any arguments. However, make sure the `ips.config` file is correct and updated before running:

```
python3 client_gui.py
```

## Testing Methodology

When running manual tests, we had servers output all communications received and sent in order to confirm appropriate behavior. Here are the list of things we checked:
- The first server becomes the leader
- Child servers connect to the leader when initialized
- All child servers send marco-polo heartbeat checks approximately every second
- A child server can terminate without significant consequences
- When the lead server terminates, another server resumes the leader role and responds to marco-polo checks
- Clients wait for a server to spawn and connect to the lead server
- Client communications go through the lead server
- Updates are propagated to child servers via newly created commands
- Updates are propagated to json files for permanent storage
- When the lead server terminates, clients wait for a new leader to be chosen and connect to the new lead server.

Additionally, we ran automated tests. These do not test crashing behavior - it is possible to automatically test this, but we found manual tests to be enough. Instead, our automated tests fill the role of testing the new commands added to our communication protocol. This ensures that we can correctly identify which server is the leader, and propagate changes from the lead server to child servers.