import os
import sys
import time
import json
import mmap
import socket
import argparse
import threading
import hashlib
import bencodepy
import urllib.parse
from hashlib import sha1
from threading import Thread


base_dir = "data"

# Kiểm tra thư mục "data" tồn tại
if os.path.exists(base_dir):
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)  # Xóa từng file

if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists("data/files_info"):
    os.makedirs("data/files_info")
if not os.path.exists("data/pieces_data"):
    os.makedirs("data/pieces_data")
if not os.path.exists("data/export_files"):
    os.makedirs("data/export_files")
if not os.path.exists("data/torrent_file"):
    os.makedirs("data/torrent_file")


# ===============================================================================================
# ================ GL0BAL PARAMETER ==============================================================
# ===============================================================================================

# Configure the size of each piece (512KB)
PIECE_SIZE = 512 * 1024
TRACKER_ADDRESS = None

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
    #event.wait()                                                    # Wait signal for server thread

    print('Client ID {:d} connecting to {}:{:d}'.format(id, serverip, serverport))

    # client_socket = socket.socket()
    # client_socket.connect((serverip, serverport))

    # print('Client ID {:d} connect success to {}:{:d}'.format(id, serverip, serverport))

    while True:
        print_gui()
        command = input("")

        if command == "1":
            upload_file_to_local();
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
# ============== HELPER FUNCTION ================================================================
# ===============================================================================================

def set_tracker_address(hostip, port):
    global TRACKER_ADDRESS 
    TRACKER_ADDRESS = "http://{}:{}".format(hostip, port)

# Lưu file info để giao tiếp peer to peer, tên file là hash code của info (info_hash)
def save_file_info(file_info):
    file = open(f"data/files_info/{file_info['info_hash']}.json", "w")
    file.write(json.dumps(file_info))
    file.close()

def save_piece_data(piece_name, piece_data):
    fs = open(f"data/pieces_data/{piece_name}", "wb")
    fs.write(piece_data)
    fs.close()

def print_file_info(file_info):
    print(
        f"info_hash({file_info['info_hash']}) - {file_info['size']} bytes - {file_info['piece_count']} piece(s) - {file_info['name']}"
    )

# ===============================================================================================
# ============== HELPER FUNCTION FOR FUNCTION 1 =================================================
# ===============================================================================================

def calculate_piece_hashes(byte_array, piece_length):
    """Tính toán SHA-1 hash của các mảnh (piece) của file và nối lại thành một chuỗi nhị phân."""
    piece_hashes = b"".join(hashlib.sha1(byte_array[i:i+piece_length]).digest() 
                             for i in range(0, len(byte_array), piece_length))
    return piece_hashes  # Trả về chuỗi nhị phân chứa các SHA-1 hash 20 byte nối nhau

# ===============================================================================================
# ============== PEER TO TRACKER FUNCTION =======================================================
# ===============================================================================================

# Function 1: Add files from the computer to local storage, prepare to register with tracker
def upload_file_to_local():
    file_path = input("\nEnter the file path want to share : ")
    if not os.path.exists(file_path):
        print("The file does not exist")
        return
    if not os.path.isfile(file_path):
        print("This path is not a file")
        return

    # Đọc lấy dữ liệu file cần thêm vào mạng
    file = open(file_path, "rb")
    byte_array = file.read()
    file.close()

    # Tính toán các thuộc tính đại diện cho dữ liệu của File
    name_file = os.path.basename(file_path).split("/")[-1]
    name_without_ext, _ = os.path.splitext(name_file)
    size_file = len(byte_array)
    piece_count = (size_file // PIECE_SIZE) + 1

    ############### Create torrent file ###############
    output_dir = "data/torrent_file"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{name_without_ext}_torrent.torrent")

    # Pieces hash for torrent file
    pieces = calculate_piece_hashes(byte_array, PIECE_SIZE)
    #pieces = b"abcd1234efgh5678abcd1234efgh5678"

    # info field in file torrent
    info = {
            "piece length": PIECE_SIZE,                     # Example piece length (512KB)
            "pieces": pieces,                               # Placeholder piece hashes (20-byte SHA-1 hashes)
            "name": name_file.encode(),                     # File name
            "length": size_file                             # File size 
        }
    
    torrent_data = {
        "announce": TRACKER_ADDRESS.encode(),               # Tracker URL
        "info": info
    }

    # Bencode the data
    encoded_data = bencodepy.encode(torrent_data)
    
    # Write the encoded data to a .torrent file
    with open(output_file, "wb") as f:
        f.write(encoded_data)
    
    print(f"Torrent file '{output_file}' created successfully!")

    ############### Store info file ###############
    
    # Bencode dictionary info
    encoded_info = bencodepy.encode(info)

    # Tính SHA-1 hash của phần info đã bencode cho magnet link
    info_hash_magnet = hashlib.sha1(encoded_info).hexdigest()  # Convert to hex

    # Tính SHA-1 hash của phần info đã bencode
    info_hash_torrent = hashlib.sha1(encoded_info).digest()
    # URL encode info_hash cho torrent file
    info_hash_encoded = urllib.parse.quote(info_hash_torrent)

    # Lưu info của file để sau này giao tiếp peer to peer
    file_info = {
        "info_hash": info_hash_magnet,
        "name": name_file,
        "size": size_file,
        "piece_count": piece_count,
    }
    save_file_info(file_info)

    # Cắt thành các piece và lưu dữ liệu từng piece
    for i in range(piece_count):
        begin = i * PIECE_SIZE
        end = (i + 1) * PIECE_SIZE
        if end > size_file:
            end = size_file
        piece_data = byte_array[begin:end]
        piece_name = f"{info_hash_magnet}_{i}"
        save_piece_data(piece_name, piece_data)

    print("Add file successfully!")
    print_file_info(file_info)
    print("\n")
    return

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

    set_tracker_address(serverip,serverport)

    peerid = 1                                          #random peer id
    peerip = get_host_default_interface_ip()
    peerport = 33357

    tserver = Thread(target=thread_server, args=(peerip,peerport))
    tclient = Thread(target=thread_client, args=(peerid,serverip,serverport,peerip,peerport))
    #tagent = Thread(target=thread_agent, args=(2, agentpath))

    #tserver.start()
    tclient.start()

    tclient.join()
    #tagent.start()

    #Never completed
    #tserver.join()
