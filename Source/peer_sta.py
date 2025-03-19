import sys
import time
import mmap
import socket
import argparse
import threading
from threading import Thread

# ===============================================================================================
# ================ SERVER FUNCTION ==============================================================
# ===============================================================================================

event = threading.Event()  # Create an event to sync thread

# New peer connect to tracker
def new_server_incoming(addr, conn):
    print(addr)
    while True:
        try:
            # This command receives data from the client (up to 1024 bytes at a time).
            # conn.recv(1024) is blocking → Server will wait until it receives data from the client.
            """
            Need to do here handle communication between tracker and peer
            """
            data = conn.recv(1024)
        except Exception:
            print('Error occured!')
            break

# Try to connect google dns for get ip value of server
def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# Server wait for peer connect
def thread_server(hostip, port):
    serversocket = socket.socket()                                  # Creat socket server using TCP/IP protocol
    serversocket.bind((hostip, port))                               # Assign socket with host ip and port

    # Put the socket into listen mode to wait for the client to connect.
    # Parameter 10 is the connection queue length, which means that up to 10 clients can wait before being rejected.
    serversocket.listen(10)
    print("Peer server listening on: {}:{}".format(hostip, port))
    event.set()                                                     # Send signal for client thread

    while True:
        # It will wait (blocking) until a client connects.
        # When a client connects, the server creates a new socket (conn) to communicate with that client.
        # addr will contain the client's IP address and port information.
        conn, addr = serversocket.accept()
        nconn = Thread(target=new_server_incoming, args=(addr, conn))
        nconn.start()                                               # Activate the thread


# ===============================================================================================
# ================ CLIENT FUNCTION ==============================================================
# ===============================================================================================

def new_connection(tid, host, port):
    print('Thread ID {:d} connecting to {}:{:d}'.format(tid, host, port))

    client_socket = socket.socket()
    client_socket.connect((host, port))

    # Demo sleep time for fun (dummy command)
    for i in range(0,3):
        print('Let me, ID={:d} sleep in {:d}s'.format(tid,3-i))
        time.sleep(1)

    print('OK! I am ID={:d} done here'.format(tid))

def connect_server(threadnum, host, port):
    # Create "threadnum" of Thread to parallely connect
    threads = [Thread(target=new_connection, args=(i, host, port)) for i in range(0, threadnum)]
    
    [t.start() for t in threads]

    # TODO: wait for all threads to finish
    [t.join() for t in threads]

def thread_client(id, serverip, serverport, peerip, peerport):
    event.wait()                                                    # Wait signal for server thread

    print('Client thread ID {:d} connecting to {}:{:d}'.format(id, serverip, serverport))

    # client_socket = socket.socket()
    # client_socket.connect((serverip, serverport))

    # print('Client thread ID {:d} connect success to {}:{:d}'.format(id, serverip, serverport))

    while True:
        print_gui()
        command = input("")

        if command == "1":
            function1()
        elif command == "2":
            function2()
        elif command == "3":
            function3()
        elif command == "4":
            function4()
        elif command == "5":
            function5()
        elif command == "6":
            sys.exit()
        else:
            print('Error function number, try again')
            print_gui()
            continue


# ===============================================================================================
# ================ AGENCY FUNCTION ==============================================================
# ===============================================================================================

def thread_agent(time_fetching, filepath):
    print(filepath)

    with open(filepath, mode="w+", encoding="utf-8") as f:
        f.truncate(100)
        f.close()

    while True:
        with open(filepath, mode="r+", encoding="utf-8") as file_obj:
            with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_READ) as mmap_obj:
                text = mmap_obj.read()
                print(text.decode('utf-8'))
            file_obj.close()

        if True:  # TODO: Cần thay thế True bằng điều kiện kiểm tra
            with open(filepath, mode="w+", encoding="utf-8") as wfile_obj:
                wfile_obj.truncate(0)
                wfile_obj.truncate(100)
                with mmap.mmap(wfile_obj.fileno(), length=0, access=mmap.ACCESS_WRITE) as mmap_wobj:
                    text = 'done'
                    mmap_wobj.write(text.encode('utf-8'))
                wfile_obj.close()

        time.sleep(time_fetching)

    exit()


# ===============================================================================================
# ==============PEER TO TRACKER FUNCTION=========================================================
# ===============================================================================================

def function1():
    print("Function 1 do")
    return

def function2():
    print("Function 2 do")
    return

def function3():
    print("Function 3 do")
    return

def function4():
    print("Function 4 do")
    return

def function5():
    print("Function 5 do")
    return

# ===============================================================================================
# =========================== UX/UI =============================================================
# ===============================================================================================

def print_gui():
    print("\nFUNCTION LIST")
    print("1 - function 1")
    print("2 - function 2")
    print("3 - function 3")
    print("4 - function 4")
    print("5 - function 5")
    print("6 - Exit")
    print("Enter the function number: ")


# ===============================================================================================
# ================ MAIN FUCNTION ================================================================
# ===============================================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='node',
        description='Node connect to predeclared server',
        epilog='<-- !!! It requires the server is running and listening !!!'
    )
    parser.add_argument('--server-ip')
    parser.add_argument('--server-port', type=int)
    #parser.add_argument('--agent-path')

    args = parser.parse_args()
    serverip = args.server_ip
    serverport = args.server_port
    #agentpath = args.agent_path

    peerip = get_host_default_interface_ip()
    peerport = 33357

    tserver = Thread(target=thread_server, args=(peerip,peerport))
    tclient = Thread(target=thread_client, args=(1, serverip, serverport, peerip, peerport))
    #tagent = Thread(target=thread_agent, args=(2, agentpath))

    tserver.start()
    tclient.start()

    tclient.join()
    #tagent.start()

    #Never completed
    tserver.join()
