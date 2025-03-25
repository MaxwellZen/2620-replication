
def encode_request(command, args):
    """
    Encodes array of arguments into a standard command.
    """
    request = command
    for arg in args:
        arg2 = ""
        for i in range(len(arg)):
            if arg[i] in "[]\\":
                arg2 += "\\"
            arg2 += arg[i]
        request += " [" + arg2 + "]"
    return request

def decode_request(request):
    """
    Decodes standard command into an array of arguments.
    """
    ind = request.find(' ')

    if ind == -1:
        return [request]
    
    command = request[:ind]
    request = request[ind+1:]
    args = [command]
    arg = ""
    ind = 0
    while ind < len(request):
        if request[ind] == '[':
            ind += 1
        elif request[ind] == ']':
            args.append(arg)
            arg = ""
            ind += 3
        elif request[ind] == '\\':
            arg += request[ind+1]
            ind += 2
        else:
            arg += request[ind]
            ind += 1
    return args

def encode_json(input):
    """
    Encodes standard command into json format.
    """
    args = decode_request(input)
    command = args[0]
    request = {"command": command}
    match command:
        case "create_account":
            request["username"] = args[1]
        case "supply_pass":
            request["password"] = args[1]
        case "login":
            request["username"] = args[1]
            request["password"] = args[2]
        case "list_accounts":
            request["pattern"] = args[1] if len(args) > 1 else "*"
        case "send":
            request["recipient"] = args[1]
            request["message"] = " ".join(args[2:])
        case "read" | "num_msg":
            request["count"] = int(args[1])
        case "delete_msg":
            request["ids"] = args[1:]
        case "delete_account" | "logout":
            pass
        case _:
            raise Exception("ERROR: invalid command")
    return request

def test_encode_request():
    assert(encode_request("abc", ["def", "ghi"]) == "abc [def] [ghi]")
    assert(encode_request("abc", ["[][]\\\\"]) == "abc [\[\]\[\]\\\\\\\\]")
    print("encode_request tests passed")

def test_decode_request():
    assert(decode_request("abc [def] [ghi]") == ["abc", "def", "ghi"])
    assert(decode_request("abc [\[\]\]\]\[\\\\]") == ["abc", "[]]][\\"])
    print("decode_request tests passed")

def test_encode_json():
    assert(encode_json("create_account [abc]") == {"command": "create_account", "username": "abc"})
    assert(encode_json("login [abc] [def]") == {"command": "login", "username": "abc", "password": "def"})
    print("encode_json tests passed")

if __name__ == "__main__":
    test_encode_request()
    test_decode_request()
    test_encode_json()