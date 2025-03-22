import os
import sys
import time
import json
import mmap
import socket
import struct
import random
import string
import argparse
import threading
import hashlib
import bencodepy
import urllib.parse
from hashlib import sha1
from threading import Thread
from urllib.parse import urlparse, parse_qs, urlencode

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

# --- CÁC HẰNG SỐ & THAM SỐ CỦA Peer wire protocol https://wiki.theory.org/BitTorrentSpecification#Peer_wire_protocol_.28TCP.29 ---
PSTR = "BitTorrent protocol"           # Protocol identifier
PSTRLEN = len(PSTR)                    # Độ dài của pstr
RESERVED = b'\x00' * 8                 # 8 byte dành riêng, mặc định là 0
HANDSHAKE_LEN = 49 + PSTRLEN           # Tổng độ dài handshake
TIMEOUT = 5                            # Timeout kết nối (giây)

# Các message ID theo protocol:
MSG_CHOKE = 0
MSG_UNCHOKE = 1
MSG_INTERESTED = 2
MSG_NOT_INTERESTED = 3
MSG_REQUEST = 6
MSG_PIECE = 7

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

    print('Client ID {} connecting to {}:{:d}'.format(id, serverip, serverport))

    client_socket = socket.socket()
    client_socket.connect((serverip, serverport))

    print('Client ID {:d} connect success to {}:{:d}'.format(id, serverip, serverport))

    while True:
        print_gui()
        command = input("")

        if command == "1":
            upload_file_to_local()
        elif command == "2":
            #info_hash = get_list_info_hash
            register_with_tracker(serverip,serverport,magnet_list,id,peerport)
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

def generate_peer_id():
    prefix = b"-PY0001-"  # Định danh client (PY = Python client, 0001 = phiên bản 1.0.0)
    random_part = ''.join(random.choices(string.digits + string.ascii_letters, k=12))  # 12 ký tự ngẫu nhiên
    peer_id = prefix + random_part.encode()
    return peer_id

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

def create_magnet_uri(info_hash, display_name="Unknown", tracker=None):
    base = f"magnet:?xt=urn:btih:{info_hash}"
    
    # Thêm tên file (dn) nếu có
    params = {}
    if display_name:
        params["dn"] = display_name

    # Thêm tracker (tr) nếu có
    if tracker:
        params["tr"] = tracker

    # Ghép các tham số vào URL
    query_string = urlencode(params)
    
    return base + "&" + query_string if query_string else base


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
magnet_list = []

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

    magnet = create_magnet_uri(info_hash_magnet,name_file,TRACKER_ADDRESS)
    magnet_list.append(magnet)

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

# function 2: Register with tracker
def register_with_tracker(tracker_host, tracker_port, magnet, peer_id, port):
    """
    Gửi yêu cầu đăng ký với Tracker bằng HTTP GET
    """
    # Xây dựng URL query
    query = f"magnet={magnet}&peer_id={peer_id}&port={port}&uploaded=0&downloaded=0&left=0&event=started"
    request = f"GET /announce?{query} HTTP/1.1\r\nHost: {tracker_host}\r\nConnection: close\r\n\r\n"

    # Kết nối đến Tracker qua socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((tracker_host, tracker_port))
        s.sendall(request.encode())

        # Nhận phản hồi từ Tracker
        response = s.recv(4096).decode()
        print(f"Phản hồi từ Tracker:\n{response}")

# ===============================================================================================
# ============== HELPER FUNCTION FOR FUNCTION 5 =======================================================
# ===============================================================================================

# --- Hàm tải dữ liệu piece từ file ---
def load_piece_data(piece_name):
    """Đọc dữ liệu của piece từ file"""
    file_path = os.path.join("data/pieces_data", piece_name)
    if not os.path.exists(file_path):
        print(f"Lỗi: Piece {piece_name} không tồn tại!")
        return None
    with open(file_path, "rb") as f:
        return f.read()

# --- PHẦN PEER THREAD PEER: YÊU CẦU TẢI PIECE CỦA PEER CLIENT ---
def download_piece_from_peer_client(peer_ip, peer_port, info_hash, client_peer_id,
                               piece_index, begin, piece_size): 
    """
    Client kết nối tới peer khác và tải một block (một phần của piece) theo giao thức Peer Wire.
    
    Các tham số:
      - peer_ip, peer_port: địa chỉ của peer cung cấp dữ liệu.
      - info_hash: 20-byte SHA1 hash của torrent (bytes).
      - client_peer_id: 20-byte định danh của peer client (bytes).
      - piece_index: số thứ tự của piece (int).
      - begin: offset bắt đầu trong piece (int). begin mặc định = 0 vì ta sẽ gửi luôn piece chứ không phải block
      - piece_size: độ dài piece cần tải (int).
    
    Trả về: piece_data (bytes) nếu tải thành công, raise Exception nếu lỗi.
    """

    # Tạo socket TCP và kết nối tới peer
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    s.connect((peer_ip, peer_port))

    # --- Step 1: Handshake ---
    # handshake = <pstrlen><pstr><reserved><info_hash><peer_id>
    handshake = struct.pack("!B", PSTRLEN) + PSTR.encode() + RESERVED + info_hash + client_peer_id
    s.sendall(handshake)
    handshake_resp = s.recv(HANDSHAKE_LEN)
    if len(handshake_resp) < HANDSHAKE_LEN:
        s.close()
        raise Exception("Handshake không thành công: không nhận đủ dữ liệu")
    # Kiểm tra info_hash trong handshake (nằm sau pstrlen+pstr+reserved)
    offset = 1 + PSTRLEN + 8
    if handshake_resp[offset:offset+20] != info_hash:
        s.close()
        raise Exception("Info hash không khớp trong handshake")

     # --- Step 2: Thiết lập trạng thái ban đầu ---
    # Theo spec, ban đầu:
    # am_choking = True, am_interested = False, peer_choking = True, peer_interested = False
    am_choking = True
    am_interested = False
    peer_choking = True
    peer_interested = False

     # --- Step 3: Gửi Interested message ---
    # Message: <length=1><msg id=2>
    interested = struct.pack("!IB", 1, MSG_INTERESTED)
    s.sendall(interested)
    am_interested = True

     # --- Step 4: Chờ nhận message unchoke ---
    while True:
        raw_len = s.recv(4)
        if len(raw_len) < 4:
            s.close()
            raise Exception("Không nhận đủ length prefix cho message")
        msg_len = struct.unpack("!I", raw_len)[0]
        if msg_len == 0:
            continue  # keep-alive
        msg = b""
        while len(msg) < msg_len:
            chunk = s.recv(msg_len - len(msg))
            if not chunk:
                break
            msg += chunk
        if len(msg) < msg_len:
            s.close()
            raise Exception("Không nhận đủ dữ liệu của message")
        msg_id = msg[0]
        if msg_id == MSG_UNCHOKE:
            peer_choking = False
            break
        # Nếu nhận được message choke, cập nhật trạng thái
        elif msg_id == MSG_CHOKE:
            peer_choking = True

    if peer_choking:
        s.close()
        raise Exception("Peer vẫn đang chặn (choking); không thể tải block.")

    # --- Step 5: Gửi Request message ---
    # Request message: <length=13><msg id=6><piece index (4 bytes)><begin (4 bytes)><block length (4 bytes)>
    request_payload = struct.pack("!III", piece_index, begin, piece_size)
    request_msg = struct.pack("!IB", 13, MSG_REQUEST) + request_payload
    s.sendall(request_msg)

   # --- Step 6: Nhận Piece message ---
    # Piece message: <length prefix><msg id=7><piece index (4 bytes)><begin (4 bytes)><block data>
    raw = s.recv(4)
    if len(raw) < 4:
        s.close()
        raise Exception("Không nhận được length prefix cho piece message")
    piece_msg_length = struct.unpack("!I", raw)[0]
    payload = b""
    while len(payload) < piece_msg_length:
        chunk = s.recv(piece_msg_length - len(payload))
        if not chunk:
            break
        payload += chunk
    if len(payload) < piece_msg_length:
        s.close()
        raise Exception("Không nhận đủ dữ liệu cho piece message")
    if payload[0] != MSG_PIECE:
        s.close()
        raise Exception("Đã mong đợi piece message (id=7) nhưng nhận được id khác")
    # Giải mã piece message: [id(1) | piece index(4) | begin(4) | block data]
    received_piece_index = struct.unpack("!I", payload[1:5])[0]
    received_begin = struct.unpack("!I", payload[5:9])[0]
    piece_data = payload[9:]
    if received_piece_index != piece_index or received_begin != begin:
        s.close()
        raise Exception("Thông tin piece nhận không khớp với yêu cầu")
    s.close()

    return piece_data

# --- PHẦN PEER THREAD SERVER: PHẢN HỒI YÊU CẦU TẢI PIECE CỦA PEER CLIENT ---
def handle_download_request_from_peer_client(client_socket, server_peer_id):
    """
    Hàm xử lý kết nối từ một client (peer khác yêu cầu block).
    Thực hiện:
      1. Nhận handshake, kiểm tra info_hash.
      2. Gửi handshake phản hồi.
      3. Đợi message interested (không bắt buộc bắt đầu, nhưng có thể update trạng thái).
      4. Nhận message request và gửi phản hồi piece message.
    
    Tham số:
      - client_socket: socket kết nối với client.
      - info_hash: 20-byte hash torrent (bytes).
      - server_peer_id: 20-byte định danh của peer server (bytes).
      # - seeded_pieces: dict {piece_index: bytes} chứa dữ liệu đã seed.
    """

    try:
         # --- Nhận handshake từ client ---
        handshake = client_socket.recv(HANDSHAKE_LEN)
        if len(handshake) < HANDSHAKE_LEN:
            raise Exception("Handshake không đủ dữ liệu")
        # Kiểm tra info_hash (nằm sau 1 + pstrlen + 8 byte)
        offset = 1 + PSTRLEN + 8
        client_info_hash = handshake[offset:offset+20]
        client_peer_id = handshake[1 + PSTRLEN + 8 + 20:]  # 20 byte cuối là peer_id

        # --- Gửi handshake phản hồi ---
        # Sử dụng cùng info_hash và server_peer_id của server
        response_handshake = struct.pack("!B", PSTRLEN) + PSTR.encode() + RESERVED + client_info_hash + server_peer_id
        client_socket.sendall(response_handshake)

        # --- Đọc các message từ client ---
        # Ví dụ: chờ nhận message interested (id=2) và message request (id=6)
        # Ta có thể dùng vòng lặp đọc các message. Trong ví dụ này, chỉ xử lý 1 request.
        # Đọc 4 byte length prefix
        while True:
            raw = client_socket.recv(4)
            if len(raw) < 4:
                raise Exception("Không nhận được length prefix")
            msg_length = struct.unpack("!I", raw)[0]
            # Đọc message payload
            payload = b""
            while len(payload) < msg_length:
                chunk = client_socket.recv(msg_length - len(payload))
                if not chunk:
                    break
                payload += chunk
            if len(payload) < msg_length:
                raise Exception("Không nhận đủ dữ liệu message")
            msg_id = payload[0]

            if msg_id == MSG_INTERESTED:
                # In log để debug
                print("Client đã gửi Interested message.")
                # Gửi message unchoke
                unchoke = struct.pack("!IB", 1, MSG_UNCHOKE)
                client_socket.sendall(unchoke)
                # Sau đó, chờ nhận request message
                # Đọc tiếp length prefix cho request
                raw = client_socket.recv(4)
                if len(raw) < 4:
                    raise Exception("Không nhận được length prefix cho request")
                req_length = struct.unpack("!I", raw)[0]
                req_payload = b""
                while len(req_payload) < req_length:
                    chunk = client_socket.recv(req_length - len(req_payload))
                    if not chunk:
                        break
                    req_payload += chunk
                if len(req_payload) < req_length:
                    raise Exception("Không nhận đủ dữ liệu cho request")
                if req_payload[0] != MSG_REQUEST:
                    raise Exception("Không nhận được request message (id=6)")
                # Giải mã request: [id(1) | piece index(4) | begin(4) | block length(4)]
                piece_index = struct.unpack("!I", req_payload[1:5])[0]
                begin = struct.unpack("!I", req_payload[5:9])[0]
                req_block_length = struct.unpack("!I", req_payload[9:13])[0]
                print(f"Nhận request: piece {piece_index}, begin {begin}, length {req_block_length}")

                # Đọc dữ liệu của piece từ file
                piece_name = f"{client_info_hash}_{piece_index}"     # Thay "info_hash_" bằng hash thực tế
                piece_data = load_piece_data(piece_name)

                if piece_data is None:
                    print("Piece none data")
                    return  # Không có dữ liệu để gửi
                # Lấy đoạn dữ liệu từ begin đến begin+req_block_length
                # block_data = piece_data[begin:begin+req_block_length]

                # --- Gửi Piece message ---
                # Piece message: <length prefix><msg id=7><piece index (4)><begin (4)><block data>
                piece_msg_payload = struct.pack("!I", piece_index) + struct.pack("!I", begin) + piece_data
                piece_msg = struct.pack("!IB", 9 + len(piece_data), MSG_PIECE) + piece_msg_payload
                client_socket.sendall(piece_msg)
                print(f"Đã gửi piece {piece_index} dữ liệu cho {client_peer_id}")

                break
            else:
                raise Exception("Message không được xử lý: không phải Interested hoặc Request")
        
    except Exception as e:
        print("Lỗi xử lý kết nối từ client:", e)
    finally:
        client_socket.close()

# ===============================================================================================
# ============== PEER TO PEER FUNCTION ==========================================================
# ===============================================================================================

# Function 5: Peer downloading file from multi peer

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

    peerid = generate_peer_id();                                         #random peer id
    peerip = get_host_default_interface_ip()
    peerport = 33357

    tserver = Thread(target=thread_server, args=(peerip,peerport))
    tclient = Thread(target=thread_client, args=(peerid,serverip,serverport,peerip,peerport))
    #tagent = Thread(target=thread_agent, args=(2, agentpath))

    tserver.start()
    tclient.start()

    tclient.join()
    #tagent.start()

    #Never completed
    tserver.join()
