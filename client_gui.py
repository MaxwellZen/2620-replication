import socket 
import tkinter as tk
from tkinter import *
from tkinter import scrolledtext
from tkinter import ttk
from utils import encode_request, decode_request
import emoji
import sys
import json

USE_JSON = True

"""
ChatApp: wrapper for the tkinter GUI. 

The GUI is composed of the following 7 menus:
- greeting: offers option to create new account or login
- login: prompts user for username and password
- create_user: prompts user for new username
- create_pass: prompts user for new password
- readmsg: displays emails for logged-in user
- selectuser: allows user to select another user to send an email to
- sendmsg: prompts user to write an email

Most of the variables and functions are named after their relevant menu, but 
that might not be true for some of the earlier variables

Relevant usage is displayed in main method below - all other functions are only
there to support the main loop.
"""

class ChatApp:
    def __init__(self, host, port, use_json):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.use_json = use_json
        
        # general information about user
        self.username = None
        self.readmsg_start = 1
        self.num_msg = 0
        self.reading_msg = False

        # root node
        self.root = Tk()
        self.root.title("Email.com")
        self.root.geometry('450x500')

        # greeting menu
        self.greeting_label = Label(text = "Welcome to email.com")
        self.login_menu_button = Button(self.root, text = "Login", command=self.greeting_to_login)
        self.register_menu_button = Button(self.root, text = "Create Account", command=self.greeting_to_create_user)
        self.greeting_created_label = Label(text = "Account created; please log in with your new account", fg='green')

        # login menu
        self.username_label = Label(text = "Username:")
        self.password_label = Label(text = "Password:")
        self.username_entry = Entry(self.root, width=20)
        self.password_entry = Entry(self.root, width=20)
        self.login_menu_back_button = Button(self.root, text = "Back to Menu", command=self.login_to_greeting)
        self.login_menu_login_button = Button(self.root, text = "Login", command=self.login_account)
        self.login_menu_not_user = Label(text = "Username does not exist; please create a new account", fg = 'red')
        self.login_menu_wrong_pass = Label(text = "Password is incorrect; please try again", fg = 'red')

        # create_user menu
        self.create_user_label = Label(self.root, text = "Input Your New Username:")
        self.create_user_create_button = Button(self.root, text = "Create Username", command = self.create_new_user)
        self.create_user_back_button = Button(self.root, text = "Back to Menu", command=self.create_user_to_greeting)
        self.create_user_again_label = Label(self.root, text = "Username taken; please log in or choose another username", fg='red')

        # create_pass menu
        self.create_pass_label = Label(self.root, text = "Input Your New Password:")
        self.create_pass_create_button = Button(self.root, text = "Create Password", command = self.create_new_pass)
        self.create_pass_back_button = Button(self.root, text = "Back to Menu", command=self.create_pass_to_greeting)

        # readmsg menu
        self.readmsg_senders = []
        self.readmsg_texts = []
        self.readmsg_ids = []
        self.readmsg_deletes = []
        self.readmsg_nomsg = Label(self.root, text = "No messages to show (that's tough)")
        self.readmsg_showing_frame = ttk.Frame(self.root)
        self.readmsg_showing = Label(self.readmsg_showing_frame, text = "")
        self.readmsg_leftbutton = Button(self.readmsg_showing_frame, text = "<", command=self.readmsg_scroll_left)
        self.readmsg_rightbutton = Button(self.readmsg_showing_frame, text = ">", command=self.readmsg_scroll_right)
        self.readmsg_showing.pack(side='left')
        self.readmsg_leftbutton.pack(side='left')
        self.readmsg_rightbutton.pack(side='left')
        self.readmsg_send_button = Button(self.root, text = "Send Message", command=self.readmsg_to_selectuser)
        self.readmsg_logout_button = Button(self.root, text = "Log Out", command=self.logout)
        self.readmsg_deleteacct_button = Button(self.root, text = "Delete Account", command=self.deleteacct)

        # selectuser menu
        self.selectuser_search_entry = Entry(self.root, width=20)
        self.selectuser_search_button = Button(self.root, text = "Search", command = self.selectuser_search)
        self.selectuser_start = 1
        self.selectuser_end = 0
        self.selectuser_showing = Label(text = "")
        self.selectuser_leftbutton = Button(self.root, text = "<", command=self.selectuser_scroll_left)
        self.selectuser_rightbutton = Button(self.root, text = ">", command = self.selectuser_scroll_right)
        self.selectuser_numusers = 0
        self.selectuser_users = []
        self.selectuser_sendbuttons = []
        self.selectuser_backbutton = Button(self.root, text = "Back", command = self.selectuser_to_readmsg)

        # sendmsg menu
        self.sendmsg_user = None
        self.sendmsg_compose_label = Label(text = "")
        self.sendmsg_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=40, height=8)
        self.sendmsg_sendbutton = Button(self.root, text = "Send Email", command = self.sendmsg)
        self.sendmsg_backbutton = Button(self.root, text = "Back", command = self.sendmsg_to_readmsg)

    # sets up greeting page and kicks off main loop
    def main_loop(self):
        self.setup_greeting()
        self.readmsg_update()
        self.root.mainloop()

    # updates messages once per second if the window is currently on the readmsg menu
    def readmsg_update(self):
        if self.reading_msg:
            self.close_readmsg()
            self.setup_readmsg()
            self.root.update_idletasks()
        self.root.after(1000, self.readmsg_update)

    """
    All of these functions serve the same core roles, which are described here (instead of one-by-one):
    setup_[menu]: sets up the elements for [menu] (ie packing elements into window)
    close_[menu]: hides all elements for [menu]
    [menu1]_to_[menu2]: wrapper function for the transition from [menu1] to [menu2] (close menu1, setup menu2, update window)
    """
    def setup_login(self):
        self.username_label.pack()
        self.username_entry.pack()
        self.password_label.pack()
        self.password_entry.pack()
        self.login_menu_login_button.pack()
        self.login_menu_back_button.pack()

    def close_login(self):
        self.username_label.pack_forget()
        self.username_entry.pack_forget()
        self.username_entry.delete(0, 'end')
        self.password_label.pack_forget()
        self.password_entry.pack_forget()
        self.password_entry.delete(0, 'end')
        self.login_menu_login_button.pack_forget()
        self.login_menu_back_button.pack_forget()
        self.login_menu_not_user.pack_forget()
        self.login_menu_wrong_pass.pack_forget()
    
    def reset_login(self):
        self.username_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.login_menu_not_user.pack_forget()
        self.login_menu_wrong_pass.pack_forget()

    def setup_greeting(self):
        self.greeting_label.pack()
        self.register_menu_button.pack()
        self.login_menu_button.pack()
    
    def close_greeting(self):
        self.greeting_label.pack_forget()
        self.login_menu_button.pack_forget()
        self.register_menu_button.pack_forget()
        self.greeting_created_label.pack_forget()

    def setup_create_user(self):
        self.username_label.pack()
        self.username_entry.pack()
        self.create_user_create_button.pack()
        self.create_user_back_button.pack()

    def close_create_user(self):
        self.username_label.pack_forget()
        self.username_entry.pack_forget()
        self.username_entry.delete(0, 'end')
        self.create_user_create_button.pack_forget()
        self.create_user_back_button.pack_forget()
        self.create_user_again_label.pack_forget()

    def setup_create_pass(self):
        self.create_pass_label.pack()
        self.password_entry.pack()
        self.create_pass_create_button.pack()
        self.create_pass_back_button.pack()
    
    def close_create_pass(self):
        self.create_pass_label.pack_forget()
        self.password_entry.pack_forget()
        self.password_entry.delete(0,'end')
        self.create_pass_create_button.pack_forget()
        self.create_pass_back_button.pack_forget()

    def setup_readmsg(self):
        # query number of messages
        if self.use_json:
            request = {"command": "num_msg"}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
            self.num_msg = int(data['message'])
        else:
            message = "num_msg".encode('utf-8')
            self.sock.sendall(message)
            data = self.sock.recv(1024).decode('utf-8')
            self.num_msg = int(data)


        if self.readmsg_start > 1 and self.num_msg < self.readmsg_start:
            self.readmsg_start -= 5

        if self.num_msg == 0:
            self.readmsg_nomsg.pack()
        else:
            upper_bound = min(self.readmsg_start+4, self.num_msg)

            if self.use_json:
                request = {"command": "read", "count": str(upper_bound)}
                message = json.dumps(request).encode('utf-8')
                self.sock.sendall(message)
                data = json.loads(self.sock.recv(1024).decode('utf-8'))
                args = [data['count']]
                for msg in data['messages']:
                    args.extend([msg['sender'], msg['id'], msg['message']])
            else:
                message = encode_request("read", [str(upper_bound)]).encode('utf-8')
                self.sock.sendall(message)
                data = self.sock.recv(1024).decode('utf-8')
                args = decode_request(data)
            upper_bound = int(args[0])
            self.readmsg_showing.configure(text = f"Showing {self.readmsg_start}-{upper_bound} of {self.num_msg}:")
            self.readmsg_showing_frame.pack()
            if self.readmsg_start == 1:
                self.readmsg_leftbutton.configure(state='disabled')
            # self.readmsg_leftbutton.pack()
            if upper_bound == self.num_msg:
                self.readmsg_rightbutton.configure(state='disabled')
            # self.readmsg_rightbutton.pack()

            # num_showing = upper_bound - self.readmsg_start + 1
            for i in range(self.readmsg_start - 1, upper_bound):
                index = 1 + 3*i
                cur_sender = Label(text = f"From: {args[index]}")
                cur_text = Label(text = args[index+2], wraplength=300)
                cur_delete = Button(self.root, text = emoji.emojize(":wastebasket:"), command = self.deletemsg_wrapper(int(args[index+1])))

                cur_sender.pack()
                cur_text.pack()
                cur_delete.pack()

                self.readmsg_senders.append(cur_sender)
                self.readmsg_texts.append(cur_text)
                self.readmsg_deletes.append(cur_delete)
                self.readmsg_ids.append(int(args[index+1]))
            
        self.readmsg_send_button.pack()
        self.readmsg_logout_button.pack()
        self.readmsg_deleteacct_button.pack()
        self.reading_msg = True

    def close_readmsg(self):
        self.readmsg_nomsg.pack_forget()
        # self.readmsg_showing.pack_forget()
        # self.readmsg_leftbutton.pack_forget()
        self.readmsg_leftbutton.configure(state='normal')
        # self.readmsg_rightbutton.pack_forget()
        self.readmsg_rightbutton.configure(state='normal')
        self.readmsg_showing_frame.pack_forget()

        for sender in self.readmsg_senders: sender.destroy()
        for text in self.readmsg_texts: text.destroy()
        for delete in self.readmsg_deletes: delete.destroy()

        self.readmsg_send_button.pack_forget()
        self.readmsg_logout_button.pack_forget()
        self.readmsg_deleteacct_button.pack_forget()

        self.readmsg_senders = []
        self.readmsg_texts = []
        self.readmsg_deletes = []
        self.readmsg_ids = []
        self.reading_msg = False

    def setup_selectuser(self):
        self.selectuser_search_entry.pack()
        self.selectuser_search_button.pack()
        self.selectuser_showing.pack()
        self.selectuser_leftbutton.pack()
        self.selectuser_rightbutton.pack()

        self.selectuser_fill_users()
        self.selectuser_view_users()

    def close_selectuser(self):
        self.selectuser_search_entry.delete(0,'end')
        self.selectuser_search_entry.pack_forget()
        self.selectuser_search_button.pack_forget()
        self.selectuser_start = 1
        self.selectuser_end = 0
        self.selectuser_showing.pack_forget()
        self.selectuser_leftbutton.pack_forget()
        self.selectuser_rightbutton.pack_forget()
        self.selectuser_numusers = 0
        for user in self.selectuser_users: user.destroy()
        self.selectuser_users = []
        for button in self.selectuser_sendbuttons: button.destroy()
        self.selectuser_sendbuttons = []
        self.selectuser_backbutton.pack_forget()

    def setup_sendmsg(self, user):
        print(f"sendmsg with user [{user}]")
        self.sendmsg_user = user
        self.sendmsg_compose_label.configure(text = f"Compose email to: {user}")
        self.sendmsg_compose_label.pack()
        self.sendmsg_text.pack()
        self.sendmsg_sendbutton.pack()
        self.sendmsg_backbutton.pack()

    def close_sendmsg(self):
        self.sendmsg_user = None
        self.sendmsg_compose_label.pack_forget()
        self.sendmsg_text.delete('1.0','end')
        self.sendmsg_text.pack_forget()
        self.sendmsg_sendbutton.pack_forget()
        self.sendmsg_backbutton.pack_forget()

    def greeting_to_login(self):
        self.close_greeting()
        self.setup_login()
        self.root.update_idletasks()

    def login_to_greeting(self):
        self.close_login()
        self.setup_greeting()
        self.root.update_idletasks()

    def create_user_to_greeting(self):
        self.close_create_user()
        self.setup_greeting()
        self.root.update_idletasks()
    
    def greeting_to_create_user(self):
        self.close_greeting()
        self.setup_create_user()
        self.root.update_idletasks()

    def create_pass_to_greeting(self):
        self.close_create_pass()
        self.setup_greeting()
        self.root.update_idletasks()

    def create_user_to_create_pass(self):
        self.close_create_user()
        self.setup_create_pass()
        self.root.update_idletasks()

    def login_to_readmsg(self):
        self.close_login()
        self.setup_readmsg()
        self.root.update_idletasks()

    def readmsg_to_selectuser(self):
        self.close_readmsg()
        self.setup_selectuser()
        self.root.update_idletasks()

    def selectuser_to_readmsg(self):
        self.close_selectuser()
        self.setup_readmsg()
        self.root.update_idletasks()

    def selectuser_to_sendmsg(self, user):
        self.close_selectuser()
        self.setup_sendmsg(user)
        self.root.update_idletasks()

    def selectuser_to_sendmsg_wrapper(self, user):
        return lambda : self.selectuser_to_sendmsg(user)

    def sendmsg_to_readmsg(self):
        self.close_sendmsg()
        self.setup_readmsg()
        self.root.update_idletasks()

    # performs login functionality
    def login_account(self):
        if self.use_json:
            request = {"command": "login", "username": self.username_entry.get(), "password": self.password_entry.get()}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
            if data['status'] == 'success':
                data = "SUCCESS: logged in"
            else:
                data = data['message']
        else:
            message = encode_request("login", [self.username_entry.get(), self.password_entry.get()])
            message = message.encode("utf-8")
            self.sock.sendall(message)
            data = self.sock.recv(1024)
            data = data.decode("utf-8")
        if data == "SUCCESS: logged in":
            self.login_to_readmsg()
        elif data == "password is incorrect. please try again":
            self.reset_login()
            self.login_menu_wrong_pass.pack()
            self.root.update_idletasks()
        elif data == "username does not exist. please create a new account":
            self.reset_login()
            self.login_menu_not_user.pack()
            self.root.update_idletasks()
        else:
            print(data)
            self.root.destroy()

    # sends new username request to server
    def create_new_user(self):
        if self.use_json:
            request = {"command": "create_account", "username": self.username_entry.get()}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
            data = data['message']
        else:
            message = encode_request("create_account", [self.username_entry.get()])
            message = message.encode("utf-8")
            self.sock.sendall(message)
            data = self.sock.recv(1024)
            data = data.decode("utf-8")
        if data == "username taken. please login with your password":
            self.create_user_again_label.pack()
            self.root.update_idletasks()
        elif data == "enter password to create new account":
            self.username = self.username_entry.get()
            self.create_user_to_create_pass()
        else:
            print(data)
            self.root.destroy()

    # sends new password request to server
    def create_new_pass(self):
        if self.use_json:
            request = {"command": "supply_pass", "password": self.password_entry.get()}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
            if data['status'] == 'success':
                data = "SUCCESS: account created. please login with your new account"
            else:
                data = data['message']
        else:
            message = encode_request("supply_pass", [self.password_entry.get()])
            message = message.encode("utf-8")
            self.sock.sendall(message)
            data = self.sock.recv(1024)
            data = data.decode("utf-8")
        if data == "SUCCESS: account created. please login with your new account":
            self.create_pass_to_greeting()
            self.greeting_created_label.pack()
            self.root.update_idletasks()
        else:
            print(data)
            self.root.destroy()

    # changes which emails are being viewed (goes from n+5 to n)
    def readmsg_scroll_left(self):
        self.readmsg_start -= 5
        self.close_readmsg()
        self.setup_readmsg()
        self.root.update_idletasks()

    # changes which emails are being viewed (goes from n to n+5)
    def readmsg_scroll_right(self):
        self.readmsg_start += 5
        self.close_readmsg()
        self.setup_readmsg()
        self.root.update_idletasks()

    # sends logout request to server
    def logout(self):
        if self.use_json:
            request = {"command": "logout"}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
        else:
            message = "logout".encode('utf-8')
            self.sock.sendall(message)
            data = self.sock.recv(1024)
            data = data.decode("utf-8")

        self.username = None 
        self.readmsg_start = 1
        self.num_msg = 0
        self.reading_msg = False 

        self.close_readmsg()
        self.setup_greeting()
        self.root.update_idletasks()

    # sends delete_account request to server
    def deleteacct(self):
        if self.use_json:
            request = {"command": "delete_account"}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
        else:
            message = "delete_account".encode('utf-8')
            self.sock.sendall(message)
            data = self.sock.recv(1024)
            data = data.decode("utf-8")

        self.username = None 
        self.readmsg_start = 1
        self.num_msg = 0
        self.reading_msg = False 

        self.close_readmsg()
        self.setup_greeting()
        self.root.update_idletasks()

    # sends deletemsg request to server
    def deletemsg(self, msgid):
        if self.use_json:
            request = {"command": "delete_msg", "ids": [str(msgid)]}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
        else:
            message = encode_request("delete_msg", [str(msgid)])
            message = message.encode("utf-8")
            self.sock.sendall(message)
            data = self.sock.recv(1024)
            data = data.decode("utf-8")

        self.num_msg -= 1

        self.close_readmsg()
        self.setup_readmsg()
        self.root.update_idletasks()

    # wrapper function: produces lambda function to attach to delete button command
    def deletemsg_wrapper(self, msgid):
        return lambda : self.deletemsg(msgid)

    # performs new search for users
    def selectuser_fill_users(self):
        if self.use_json:
            request = {"command": "list_accounts", "pattern": self.selectuser_search_entry.get() + "*"}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
            users = [str(data['count'])] + data['accounts']
        else:
            message = encode_request("list_accounts", [self.selectuser_search_entry.get() + "*"]).encode('utf-8')
            self.sock.sendall(message)
            data = self.sock.recv(1024)
            data = data.decode('utf-8')
            users = decode_request(data)

        self.selectuser_numusers = int(users[0])
        users = users[1:]
        self.selectuser_numusers = len(users)
        self.selectuser_start = 1
        self.selectuser_end = min(len(users), 5)

        # reset previous users
        for user in self.selectuser_users: user.destroy()
        for button in self.selectuser_sendbuttons: button.destroy()
        self.selectuser_users = []
        self.selectuser_sendbuttons = []

        for user in users:
            user_label = Label(text = user)
            user_button = Button(self.root, text = emoji.emojize(":airplane:"), command=self.selectuser_to_sendmsg_wrapper(user))
            self.selectuser_users.append(user_label)
            self.selectuser_sendbuttons.append(user_button)

    # updates the user view (for example, when iterating through users)
    def selectuser_view_users(self):
        self.selectuser_backbutton.pack_forget()
        
        if self.selectuser_numusers == 0:
            self.selectuser_showing.configure(text = "No users to show")
            self.selectuser_leftbutton.configure(state='disabled')
            self.selectuser_rightbutton.configure(state='disabled')
        else:
            self.selectuser_showing.configure(text = f"Showing {self.selectuser_start}-{self.selectuser_end} of {self.selectuser_numusers}")
            if self.selectuser_start == 1:
                self.selectuser_leftbutton.configure(state='disabled')
            else:
                self.selectuser_leftbutton.configure(state='normal')
            if self.selectuser_end == len(self.selectuser_users):
                self.selectuser_rightbutton.configure(state='disabled')
            else:
                self.selectuser_rightbutton.configure(state='normal')

            for i in range(self.selectuser_start - 1, self.selectuser_end):
                self.selectuser_users[i].pack()
                self.selectuser_sendbuttons[i].pack()
            
            self.selectuser_backbutton.pack()

    # wrapper function to search for users then view users
    def selectuser_search(self):
        self.selectuser_fill_users()
        self.selectuser_view_users()
        self.root.update_idletasks()

    # iterate through users (n+5 to n)
    def selectuser_scroll_left(self):
        for i in range(self.selectuser_start - 1, self.selectuser_end):
            self.selectuser_users[i].pack_forget()
            self.selectuser_sendbuttons[i].pack_forget()

        self.selectuser_start -= 5
        self.selectuser_end = min(self.selectuser_start + 4, self.selectuser_numusers)
        self.selectuser_view_users()
        self.root.update_idletasks()

    # iterate through users (n to n+5)
    def selectuser_scroll_right(self):
        for i in range(self.selectuser_start - 1, self.selectuser_end):
            self.selectuser_users[i].pack_forget()
            self.selectuser_sendbuttons[i].pack_forget()

        self.selectuser_start += 5
        self.selectuser_end = min(self.selectuser_start + 4, self.selectuser_numusers)
        self.selectuser_view_users()
        self.root.update_idletasks()

    # send message to another user
    def sendmsg(self):
        if self.use_json:
            request = {"command": "send", "recipient": self.sendmsg_user, "message": self.sendmsg_text.get('1.0','end-1c')}
            message = json.dumps(request).encode('utf-8')
            self.sock.sendall(message)
            data = json.loads(self.sock.recv(1024).decode('utf-8'))
        else:
            message = encode_request("send", [self.sendmsg_user, self.sendmsg_text.get('1.0','end-1c')]).encode('utf-8')
            self.sock.sendall(message)
            data = self.sock.recv(1024)
            data = data.decode("utf-8")

        self.close_sendmsg()
        self.setup_readmsg()
        self.root.update_idletasks()

def main():
    if len(sys.argv) < 3 or not sys.argv[2].isdigit():
        print("Please provide a host and port for the socket connection")
        print("Example: python3 client_gui.py 127.0.0.1 54400")
        return

    host = sys.argv[1]
    port = int(sys.argv[2])

    chatapp = ChatApp(host, port, USE_JSON)
    chatapp.main_loop()

if __name__ == "__main__":
    main()