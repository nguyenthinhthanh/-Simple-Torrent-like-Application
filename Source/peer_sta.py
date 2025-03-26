import os
import sys
import ast
import time
import json
import mmap
import math
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
PSTR = "BitTorrent protocol"         # Protocol identifier
PSTRLEN = len(PSTR)                    # Độ dài của pstr
RESERVED = b'\x00' * 8                 # 8 byte dành riêng, mặc định là 0
HANDSHAKE_LEN = 49 + PSTRLEN           # Tổng độ dài handshake
TIMEOUT = 5                            # Timeout kết nối (giây)

# Các message ID theo protocol:
MSG_CHOKE = 0
MSG_UNCHOKE = 1
MSG_INTERESTED = 2
MSG_NOT_INTERESTED = 3
MSG_BITFIELD   = 5
MSG_REQUEST = 6
MSG_PIECE = 7
MSG_END = 8  # Tin nhắn kết thúc giao tiếp

# ===============================================================================================
# ================ SERVER FUNCTION ==============================================================
# ===============================================================================================

event = threading.Event()  # Create an event to sync thread

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

def handle_peer_to_peer_communication(addr, conn, hostid):
    # handle_get_piece_list_request_from_peer_client(conn,hostid)

    result = handle_download_request_from_peer_client(conn,hostid)

    return result

# New peer connect to tracker
def new_server_incoming(addr, conn, hostid):
    print(addr)

    handle_get_piece_list_request_from_peer_client(conn,hostid)

    while True:
        try:
            # This command receives data from the client (up to 1024 bytes at a time).
            # conn.recv(1024) is blocking → Server will wait until it receives data from the client.
            """
            Need to do here handle communication between peer server and peer client
            """
            result = handle_download_request_from_peer_client(conn,hostid)
            if(result == False):
               break

        except Exception:
            print('Error occured!')
            break

# Server wait for peer connect
def thread_server(hostip, port, hostid):
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
        nconn = Thread(target=new_server_incoming, args=(addr, conn, hostid))
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

    print('Client ID {} connecting to {}:{:d}'.format(id, serverip, serverport))

    client_socket = socket.socket()
    client_socket.connect((serverip, serverport))


    print('Client ID {} connect success to {}:{}'.format(id, serverip, serverport))

    while True:
        print_gui()
        command = input("")

        if command == "1":
            upload_file_to_local()
        elif command == "2":
            #info_hash = get_list_info_hash
            register_with_tracker(client_socket,serverip,serverport,magnet_list,id,peerport)
        elif command == "3":
            get_list_shared_files(client_socket,serverip,serverport,id)
        elif command == "4":
            # Just for testing
            info_hash_test = "60194213e559cd3409ef8fcb57ed37592e472819"
            get_peer_list(client_socket,serverip,serverport,id,info_hash_test)
        elif command == "5":
            download_file(client_socket,serverip,serverport,id)
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

def load_file_info(info_hash):
    filename = f"data/files_info/{info_hash}.json"
    #print(f"File name info {filename}")
    try:
        with open(filename, "r") as file:
            file_info = json.load(file)
            return file_info  # Trả về toàn bộ dictionary file_info
    except FileNotFoundError:
        print("Không tìm thấy file info!")
        return None

def save_piece_data(piece_name, piece_data):
    fs = open(f"data/pieces_data/{piece_name}", "wb")
    fs.write(piece_data)
    fs.close()

def print_file_info(file_info):
    print(
        f"info_hash({file_info['info_hash']}) - {file_info['size']} bytes - {file_info['piece_count']} piece(s) - {file_info['name']}"
    )

# Function to parse a magnet URI
def parse_magnet_uri(magnet_link):
    """
    Phân tích magnet URI và trả về các thông tin:
      - info_hash: mã hash của file
      - display_name: tên file (nếu có, mặc định là "Unknown")
      - tracker_url: URL của tracker (nếu có)
      - file_size: kích thước file (xl) theo byte (nếu có, dưới dạng int, nếu không có thì None)
    """
    parsed = urlparse(magnet_link)
    params = parse_qs(parsed.query)
    
    # Trích xuất info_hash từ xt
    xt_values = params.get('xt', [])
    if xt_values:
        info_hash = xt_values[0].split(":")[-1]
    else:
        info_hash = ""
    
    # Trích xuất display name (dn)
    display_name = params.get('dn', ['Unknown'])[0]
    
    # Trích xuất tracker URL (tr)
    tracker_url = params.get('tr', [''])[0]
    
    # Trích xuất file size (xl)
    xl_value = params.get('xl', [None])[0]
    try:
        file_size = int(xl_value) if xl_value is not None else None
    except ValueError:
        file_size = None
    
    return info_hash, display_name, tracker_url, file_size

def create_magnet_uri(info_hash, display_name="Unknown", tracker=None, file_size=None):
    """
    Tạo magnet URI với các tham số:
      - info_hash: hash của file (bắt buộc)
      - display_name: tên file (dn) [mặc định "Unknown"]
      - tracker: URL của tracker (tr) [tuỳ chọn]
      - file_size: kích thước file, tính theo byte (xl) [tuỳ chọn]
    """
    base = f"magnet:?xt=urn:btih:{info_hash}"
    
    # Tạo dictionary chứa các tham số
    params = {}
    if display_name:
        params["dn"] = display_name
    if tracker:
        params["tr"] = tracker
    if file_size is not None:
        params["xl"] = file_size

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

    magnet = create_magnet_uri(info_hash_magnet,name_file,TRACKER_ADDRESS,size_file)
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
def register_with_tracker(client_socket, tracker_host, tracker_port, magnet, peer_id, port):
    """
    Gửi yêu cầu đăng ký với Tracker bằng HTTP GET
    """
    # Xây dựng URL query
    # Mã hóa magnet để đảm bảo chuỗi query không bị lỗi
    # Mã hóa từng magnet URI
    # magnet_list_encoded = [urllib.parse.quote(m, safe='') for m in magnet]
    # query = f"magnet={magnet_list_encoded}&peer_id={peer_id}&port={port}&uploaded=0&downloaded=0&left=0&event=started"

    magnet_params = "&".join([f"magnet={urllib.parse.quote(m)}" for m in magnet])
    query = f"{magnet_params}&peer_id={peer_id}&port={port}&uploaded=0&downloaded=0&left=0&event=started"

    request = f"GET /announce?{query} HTTP/1.1\r\nHost: {tracker_host}\r\nConnection: close\r\n\r\n"

    # Gửi request đến Tracker qua socket
    client_socket.sendall(request.encode())

    # Nhận phản hồi từ Tracker
    response = client_socket.recv(4096).decode()
    print(f"Phản hồi từ Tracker:\n{response}")

        

# function 3: Get online file list from tracker
def get_list_shared_files(client_socket, tracker_host, tracker_port, peer_id):
    """
    Gửi yêu cầu đến Tracker để xem danh sách các file đang được chia sẻ.
      - peer_id: định danh của peer gửi yêu cầu
      - event=list: hành động lấy danh sách file
    Tracker sẽ phản hồi bằng HTTP.
    """
    # Xây dựng URL query
    query = f"peer_id={peer_id}&event=list"
    request = f"GET /announce?{query} HTTP/1.1\r\nHost: {tracker_host}\r\nConnection: close\r\n\r\n"

    # Kết nối đến Tracker qua socket và gửi request
    client_socket.sendall(request.encode())

    # Nhận phản hồi từ Tracker
    # response = ""
    # while True:
    #     chunk = client_socket.recv(4096)
    #     if not chunk:
    #         break
    #     response += chunk.decode()
    # print("Phản hồi từ Tracker:")
    # print(response)
    # Nhận phản hồi từ Tracker
    response = client_socket.recv(4096).decode()
    print(f"Phản hồi từ Tracker:\n{response}")
        

# ===============================================================================================
# ============== HELPER FUNCTION FOR FUNCTION 5 =================================================
# ===============================================================================================

#  --- Hàm phân tích respone peer list từ tracker ---
def extract_filtered_peers(response_body):
    """
    Trích xuất danh sách peers chia sẻ file info_hash từ phản hồi của Tracker.
    - response_body: chuỗi phản hồi HTTP từ Tracker.
    - Trả về danh sách peers (list of dict).
    """
    try:
        # Tìm vị trí phần JSON bắt đầu (sau 'Peer list:')
        start_idx = response_body.find("Peer list:") + len("Peer list:")
        # Lấy phần dữ liệu chứa dict sau "Peer list:" cho đến hết dòng
        dict_str = response_body[start_idx:].split("\n", 1)[0].strip()
        
        # Dùng ast.literal_eval để chuyển đổi chuỗi thành đối tượng Python
        response_dict = ast.literal_eval(dict_str)

        # Trích xuất danh sách filtered_peers từ key "peers"
        peers = response_dict.get("peers", [])

        return peers
    except Exception as e:
        print(f"Lỗi khi phân tích phản hồi: {e}")
        return []

# function 4: get_peer_list
#  --- Hàm peer yêu cầu tracker trả về danh sách peer đang chia sẻ file có info_hash ---
def get_peer_list(client_socket, tracker_host, tracker_port, peer_id, info_hash):
    """
    Gửi yêu cầu đến Tracker để lấy danh sách các peer đang có file dựa theo info_hash.
    Yêu cầu được gửi qua HTTP GET với các tham số:
      - peer_id: định danh của peer gửi yêu cầu
      - info_hash: chuỗi (hoặc hash) định danh file (torrent) cần tìm các peer
      - event=get_peer_list: báo hiệu muốn lấy danh sách peer (để tracker trả về danh sách peer)
    """
    # Xây dựng URL query
    query = f"peer_id={peer_id}&info_hash={info_hash}&event=get_peer_list"
    request = (
        f"GET /announce?{query} HTTP/1.1\r\n"
        f"Host: {tracker_host}\r\n"
        "Connection: close\r\n\r\n"
    )
    
    # Kết nối đến Tracker qua socket và gửi request
     # Kết nối đến Tracker qua socket và gửi request
    client_socket.sendall(request.encode())

    # Nhận phản hồi từ Tracker
    response = client_socket.recv(4096).decode()
    print(f"Phản hồi peer list từ Tracker:\n{response}")

    return response

# --- Hàm tải dữ liệu piece từ file ---
def load_piece_data(piece_name):
    """Đọc dữ liệu của piece từ file"""
    file_path = os.path.join("data/pieces_data", piece_name)
    if not os.path.exists(file_path):
        print(f"Lỗi: Piece {piece_name} không tồn tại!")
        return None
    with open(file_path, "rb") as f:
        return f.read()
    
def create_bitfield(info_hash, total_pieces, pieces_dir="data/pieces_data"):
    """
    Tạo bitfield cho torrent dựa vào các file piece có trong thư mục pieces_dir.
    
    Tham số:
      - info_hash: chuỗi (str) đại diện cho info_hash của torrent.
      - total_pieces: tổng số pieces của torrent (int).
      - pieces_dir: thư mục chứa file piece (mặc định là "data/pieces_data").
    
    Trả về:
      - bitfield dưới dạng bytes, với mỗi bit biểu diễn tình trạng của piece tương ứng.
    """
    # Tạo danh sách chứa chỉ số của các piece hiện có
    available_pieces = set()
    
    try:
        files = os.listdir(pieces_dir)
    except Exception as e:
        raise Exception(f"Không truy cập được thư mục {pieces_dir}: {e}")
    
    # Duyệt qua các file trong thư mục
    for filename in files:
        # Kiểm tra file có bắt đầu bằng info_hash + "_" không
        if filename.startswith(info_hash + "_"):
            try:
                # Phần sau dấu gạch dưới chính là piece index
                piece_index_str = filename.split("_", 1)[1]
                piece_index = int(piece_index_str)
                available_pieces.add(piece_index)
            except Exception as e:
                # Nếu không chuyển đổi được, bỏ qua file đó
                continue

    # Tính số byte cần cho bitfield
    bitfield_length = math.ceil(total_pieces / 8)
    bitfield_array = bytearray(bitfield_length)
    
    # Đặt bit = 1 nếu piece i có trong available_pieces
    for i in range(total_pieces):
        if i in available_pieces:
            byte_index = i // 8
            bit_index = 7 - (i % 8)  # Dùng thứ tự từ MSB đến LSB
            bitfield_array[byte_index] |= (1 << bit_index)
    
    return bytes(bitfield_array)

# --- PHẦN PEER THREAD PEER: YÊU CẦU TẢI PIECE CỦA PEER CLIENT ---
def download_piece_from_peer_server(client_socket, info_hash, client_peer_id,
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
    # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # s.settimeout(TIMEOUT)
    # s.connect((peer_ip, peer_port))

    try:
        # --- Step 1: Handshake ---
        # handshake = <pstrlen><pstr><reserved><info_hash><peer_id>
        handshake = struct.pack("!B", PSTRLEN) + PSTR.encode() + RESERVED + info_hash + client_peer_id
        client_socket.sendall(handshake)
        handshake_resp = client_socket.recv(HANDSHAKE_LEN)
        if len(handshake_resp) < HANDSHAKE_LEN:
            client_socket.close()
            raise Exception("Handshake không thành công: không nhận đủ dữ liệu")
        # Kiểm tra info_hash trong handshake (nằm sau pstrlen+pstr+reserved)
        offset = 1 + PSTRLEN + 8
        if handshake_resp[offset:offset+20] != info_hash:
            client_socket.close()
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
        client_socket.sendall(interested)
        am_interested = True

        # --- Step 4: Chờ nhận message unchoke ---
        while True:
            raw_len = client_socket.recv(4)
            if len(raw_len) < 4:
                client_socket.close()
                raise Exception("Không nhận đủ length prefix cho message")
            msg_len = struct.unpack("!I", raw_len)[0]
            if msg_len == 0:
                continue  # keep-alive
            msg = b""
            while len(msg) < msg_len:
                chunk = client_socket.recv(msg_len - len(msg))
                if not chunk:
                    break
                msg += chunk
            if len(msg) < msg_len:
                client_socket.close()
                raise Exception("Không nhận đủ dữ liệu của message")
            msg_id = msg[0]
            if msg_id == MSG_UNCHOKE:
                peer_choking = False
                break
            # Nếu nhận được message choke, cập nhật trạng thái
            elif msg_id == MSG_CHOKE:
                peer_choking = True

        if peer_choking:
            client_socket.close()
            raise Exception("Peer vẫn đang chặn (choking); không thể tải block.")

        # --- Step 5: Gửi Request message ---
        # Request message: <length=13><msg id=6><piece index (4 bytes)><begin (4 bytes)><block length (4 bytes)>
        request_payload = struct.pack("!III", piece_index, begin, piece_size)
        request_msg = struct.pack("!IB", 13, MSG_REQUEST) + request_payload
        client_socket.sendall(request_msg)

        # --- Step 6: Nhận Piece message ---
        # Piece message: <length prefix><msg id=7><piece index (4 bytes)><begin (4 bytes)><block data>
        raw = client_socket.recv(4)
        if len(raw) < 4:
            client_socket.close()
            raise Exception("Không nhận được length prefix cho piece message")
        piece_msg_length = struct.unpack("!I", raw)[0]
        payload = b""
        while len(payload) < piece_msg_length:
            chunk = client_socket.recv(piece_msg_length - len(payload))
            if not chunk:
                break
            payload += chunk
        if len(payload) < piece_msg_length:
            client_socket.close()
            raise Exception("Không nhận đủ dữ liệu cho piece message")
        if payload[0] != MSG_PIECE:
            client_socket.close()
            raise Exception("Đã mong đợi piece message (id=7) nhưng nhận được id khác")
        # Giải mã piece message: [id(1) | piece index(4) | begin(4) | block data]
        received_piece_index = struct.unpack("!I", payload[1:5])[0]
        received_begin = struct.unpack("!I", payload[5:9])[0]
        piece_data = payload[9:]
        if received_piece_index != piece_index or received_begin != begin:
            client_socket.close()
            raise Exception("Thông tin piece nhận không khớp với yêu cầu")
        #client_socket.close()
    except Exception as e:
        client_socket.close()
        raise Exception("Lỗi khi tải piece từ peer: " + str(e))

    return piece_data

# --- PHẦN PEER THREAD SERVER: PHẢN HỒI YÊU CẦU TẢI PIECE CỦA PEER CLIENT ---
def handle_download_request_from_peer_client(client_socket, server_peer_id):
    """
    Hàm xử lý kết nối từ một client (peer khác yêu cầu piece).
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
        # Chuyển bytes thành chuỗi hex
        info_hash_str = client_info_hash.hex()
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
                piece_name = f"{info_hash_str}_{piece_index}"     # Thay "info_hash_" bằng hash thực tế
                piece_data = load_piece_data(piece_name)

                if piece_data is None:
                    print("Piece none data")
                    return False  # Không có dữ liệu để gửi
                # Lấy đoạn dữ liệu từ begin đến begin+req_block_length
                # block_data = piece_data[begin:begin+req_block_length]

                # --- Gửi Piece message ---
                # Piece message: <length prefix><msg id=7><piece index (4)><begin (4)><block data>
                piece_msg_payload = struct.pack("!I", piece_index) + struct.pack("!I", begin) + piece_data
                piece_msg = struct.pack("!IB", 9 + len(piece_data), MSG_PIECE) + piece_msg_payload
                client_socket.sendall(piece_msg)
                print(f"Đã gửi piece {piece_index} dữ liệu cho {client_peer_id}")

                break
            elif msg_id == MSG_END:
                # In log để debug
                print("Client đã gửi End message.")
                return False
            else:
                raise Exception("Message không được xử lý: không phải Interested hoặc Request")
            
        return True
        
    except Exception as e:
        print("Lỗi xử lý yêu cầu tải piece từ client download piece:", e)
        return False
    # finally:
    #     client_socket.close()

# --- PHẦN PEER THREAD PEER: YÊU CẦU DANH SÁCH PIECE MÀ PEER SERVER CÓ ---
def get_piece_list_from_peer_server(client_socket, peer_server_host, peer_server_port, peer_id, info_hash, total_pieces):
    """
    Hàm xử gửi yêu cầu đến peer khác lấy piece list.
    Thực hiện:
      1. Gửi message yêu cầu
      2. Nhận piece list

    Tham số:
      - client_socket: socket peer client kết nối với peer server.
      - peer_server_host: ip của peer server cung cấp piece chia sẻ.
      - peer_server_port: port của peer server cung cấp piece chia sẻ.
      - peer_id, peer_port: ip, port của client peer
      - info_hash: 20-byte hash torrent (bytes).

    Trả về:
      - Một danh sách các chỉ số piece mà peer có (ví dụ: [0, 1, 3, 5, ...]).
        Nếu không nhận được bitfield, trả về danh sách rỗng.
    """
    try: 
        # --- Step 1: Handshake ---
        # Tạo handshake: <pstrlen><pstr><reserved><info_hash><peer_id>
        handshake = struct.pack("!B", PSTRLEN) + PSTR.encode() + RESERVED + info_hash + peer_id
        client_socket.sendall(handshake)

        # Nhận handshake phản hồi
        handshake_resp = client_socket.recv(HANDSHAKE_LEN)
        if len(handshake_resp) < HANDSHAKE_LEN:
            client_socket.close()
            raise Exception("Handshake không thành công: không nhận đủ dữ liệu")
        
        # Kiểm tra info_hash (nằm sau 1+pstrlen+8 byte)
        offset = 1 + PSTRLEN + 8
        if handshake_resp[offset:offset+20] != info_hash:
            client_socket.close()
            raise Exception("Info hash không khớp trong handshake")
        
        # --- Step 2: Nhận Bitfield ---
        # Bitfield message có định dạng:
        # <length prefix (4 byte)> <message id (1 byte = 5)> <bitfield payload>
        raw_len = client_socket.recv(4)
        if len(raw_len) < 4:
            client_socket.close()
            raise Exception("Không nhận đủ length prefix cho message")
        msg_len = struct.unpack("!I", raw_len)[0]

        # Nếu msg_len == 0, đó là keep-alive, ta cần chờ message khác
        while msg_len == 0:
            raw_len = client_socket.recv(4)
            if len(raw_len) < 4:
                client_socket.close()
                raise Exception("Không nhận đủ length prefix cho message")
            msg_len = struct.unpack("!I", raw_len)[0]

        msg = b""
        while len(msg) < msg_len:
            chunk = client_socket.recv(msg_len - len(msg))
            if not chunk:
                break
            msg += chunk
        if len(msg) < msg_len:
            client_socket.close()
            raise Exception("Không nhận đủ dữ liệu cho message")

        # Kiểm tra message id
        msg_id = msg[0]
        if msg_id != MSG_BITFIELD:
            # Nếu không phải bitfield, có thể là message khác (ví dụ "have")
            # Trong trường hợp này, ta trả về danh sách rỗng hoặc có thể xử lý thêm
            client_socket.close()
            raise Exception(f"Đã mong đợi bitfield (id=5) nhưng nhận được id={msg_id}")

        # Phần payload của bitfield: các byte sau 1 byte message id
        bitfield = msg[1:]
        # --- Step 3: Chuyển Bitfield thành danh sách các chỉ số piece ---
        piece_list = []
        bit_index = 0
        for byte in bitfield:
            for i in range(7, -1, -1):
                if bit_index >= total_pieces:
                    break
                if (byte >> i) & 1:
                    piece_list.append(bit_index)
                bit_index += 1
        # client_socket.close()
        return piece_list
    except Exception as e:
        client_socket.close()
        raise Exception("Lỗi khi lấy danh sách piece từ peer: " + str(e))


# --- PHẦN PEER THREAD SERVER: PHẢN HỒI YÊU CẦU DANH SÁCH PIECE ---
def handle_get_piece_list_request_from_peer_client(client_socket, server_peer_id):
    """
    Hàm xử lý khi peer khác yêu cầu piece list.
    Thực hiện:
      1. Nhận message yêu cầu
      2. Kiểm tra info hash để chỉ trả về những piece của file info_hash đó
      3. Gửi message phản hồi.

    Tham số:
      - client_socket: socket peer client kết nối với peer server.
    """
    
    try:
        #client_socket.settimeout(TIMEOUT)

        # --- Nhận handshake từ client ---
        handshake = client_socket.recv(HANDSHAKE_LEN)
        if len(handshake) < HANDSHAKE_LEN:
            raise Exception("Handshake không đủ dữ liệu")
        # Kiểm tra info_hash (nằm sau 1 + pstrlen + 8 byte)
        offset = 1 + PSTRLEN + 8
        client_info_hash = handshake[offset:offset+20]
        # Chuyển bytes thành chuỗi hex
        info_hash_str = client_info_hash.hex()
        client_peer_id = handshake[1 + PSTRLEN + 8 + 20:]  # 20 byte cuối là peer_id

        # --- Gửi handshake phản hồi ---
        # Sử dụng cùng info_hash và server_peer_id của server
        response_handshake = struct.pack("!B", PSTRLEN) + PSTR.encode() + RESERVED + client_info_hash + server_peer_id
        client_socket.sendall(response_handshake)

        # --- Gửi Bitfield ---
        # message Bitfield theo định dạng: <length prefix (4 byte)> <message id (1 byte = 5)> <bitfield payload>
        file_info = load_file_info(info_hash_str)
        if file_info:
            total_pieces = file_info.get("piece_count")  # Lấy giá trị piece_count

        bitfield = create_bitfield(info_hash_str, total_pieces, pieces_dir="data/pieces_data")

        msg_id = MSG_BITFIELD
        payload = struct.pack("!B", msg_id) + bitfield
        length_prefix = struct.pack("!I", len(payload))
        client_socket.sendall(length_prefix + payload)

        print(f"[{server_peer_id}] Đã gửi bitfield cho {client_peer_id}.")
    except Exception as e:
        print("Lỗi xử lý yêu cầu tải piece từ client get piece list:", e)
    

# ===============================================================================================
# ============== PEER TO PEER FUNCTION ==========================================================
# ===============================================================================================

# Các cấu trúc toàn cục để lưu trữ tiến trình tải
downloaded_pieces = {}  # {piece_index: bytes}
request_queue = set()   # Tập các piece đang được yêu cầu
lock = threading.Lock() # Để đồng bộ truy cập dữ liệu chia sẻ

# --- PHẦN PEER THREAD PEER: GỬI STOP MESSAGE ---
def stop_peer_to_peer_communicate(client_socket, info_hash, client_peer_id):
    """
    Peer client yêu cầu dừng giao tiếp với peer server
    
    Các tham số:
      - client_socket: socket giao tiếp giữa peer client và peer server
      - info_hash: 20-byte SHA1 hash của torrent (bytes).
      - client_peer_id: 20-byte định danh của peer client (bytes).
    """

    # Tạo socket TCP và kết nối tới peer
    # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # s.settimeout(TIMEOUT)
    # s.connect((peer_ip, peer_port))

    try:
        # --- Step 1: Handshake ---
        # handshake = <pstrlen><pstr><reserved><info_hash><peer_id>
        handshake = struct.pack("!B", PSTRLEN) + PSTR.encode() + RESERVED + info_hash + client_peer_id
        client_socket.sendall(handshake)
        handshake_resp = client_socket.recv(HANDSHAKE_LEN)
        if len(handshake_resp) < HANDSHAKE_LEN:
            client_socket.close()
            raise Exception("Handshake không thành công: không nhận đủ dữ liệu")
        # Kiểm tra info_hash trong handshake (nằm sau pstrlen+pstr+reserved)
        offset = 1 + PSTRLEN + 8
        if handshake_resp[offset:offset+20] != info_hash:
            client_socket.close()
            raise Exception("Info hash không khớp trong handshake")

        # --- Step 2: Gửi End message để kết thúc giao tiếp ---
        end_msg = struct.pack("!IB", 1, MSG_END)
        client_socket.sendall(end_msg)
    except Exception as e:
        client_socket.close()
        raise Exception("Lỗi khi tải piece từ peer: " + str(e))

# thread download for download file function
def download_worker(peer_server, peer_client_id, info_hash_file, total_piece_file):
        # Tạo socket TCP và kết nối tới peer
        peer_to_peer_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #peer_to_peer_s.settimeout(TIMEOUT)
        peer_to_peer_s.connect((peer_server['ip'], int(peer_server['port'])))

        piece_list = get_piece_list_from_peer_server(peer_to_peer_s,peer_server['ip'], peer_server['port'], peer_client_id, info_hash_file, total_piece_file)

        while True:
            with lock:
                # Lọc ra các piece có sẵn mà chưa tải và chưa được request
                remaining_pieces = piece_list - downloaded_pieces.keys() - request_queue
                if not remaining_pieces:
                    print(f"Peer {peer_client_id} không còn piece khả dụng để tải.")
                    stop_peer_to_peer_communicate(peer_to_peer_s,info_hash_file,peer_client_id)
                    break

                # Chọn một piece để tải
                piece_index = remaining_pieces.pop()
                request_queue.add(piece_index)

            if peer_to_peer_s.fileno() == -1:
                print(f"Socket đã đóng tại piece index {piece_index}")
                break

            # Thực hiện tải piece từ peer
            piece_data = download_piece_from_peer_server(peer_to_peer_s,info_hash_file,peer_client_id,piece_index,0,PIECE_SIZE)
            
            with lock:
                request_queue.remove(piece_index)
                if piece_data:
                    downloaded_pieces[piece_index] = piece_data
                    print(f"Tải thành công piece {piece_index}")
                else:
                    print(f"[!] Không thể tải piece {piece_index}, sẽ thử lại từ peer khác.")

        peer_to_peer_s.close()

# Function 5: Peer downloading file from multi peer
def download_file(client_socket, tracker_host, tracker_port, self_peer_id):
    """
    Hàm thực hiện tải file yêu cầu từ peer đến peer khác
    Thực hiện:
        1. Người dùng nhập vào magnet link để tải file
        2. Peer gửi yêu cầu lấy danh sách peer đang chia sẻ file dựa vào info_hash trong magnet link
        3. Peer multi kết nối với peer khác trong danh sách và yêu cầu lấy danh sách những piece nó có
            3.1 Gửi yêu cầu toàn bộ peer list để lấy danh sách những piece mà mỗi peer có
            3.2 Với mỗi peer, một thread (worker) sẽ chạy và tìm những pieces mà peer có mà chưa được tải và chưa có trong request_queue.
            3.3 Khi tìm thấy, worker sẽ thêm piece vào request_queue và gọi hàm tải từ peer đó (hàm download_piece_from_peer).
            3.4 Nếu tải thành công, dữ liệu được lưu vào downloaded_pieces và piece được gỡ khỏi request_queue.
            3.5 Nếu tải thất bại (ví dụ do disconnect), piece sẽ bị gỡ khỏi request_queue để có thể được tải lại bởi một worker khác.
        # Magnet link not torrent file 4. Tải piece và kiểm tra Hash để chắc piece tải đúng
        5. Ghép file hoàn chỉnh
        6. Xuất file
        7. Seeder
    Tham số:
        - client_socket: socket kết nối với tracker.
        - tracker_host: địa chỉ ip của tracker
        - tracker_port: port giao tiếp với tracker
        - self_peer_id: id của peer yêu cầu tải file
        - self_peer_port: port của peer yêu cầu tải file
    """

    # 1. Người dùng nhập vào magnet link để tải file
    magnet_link = input("Enter magnet link of file want to download: ").strip()

    #Parse the magnet URI
    info_hash, file_name, tracker_url, file_size = parse_magnet_uri(magnet_link)

    info_hash_byte = bytes.fromhex(info_hash)

    # Print extracted information
    print("Extracted Info:")
    print(f"Info Hash: {info_hash}")
    print(f"File Name: {file_name}")
    print(f"File Size: {file_size}")
    print(f"Tracker URL: {tracker_url}")

    total_pieces = (file_size // PIECE_SIZE) + 1

    #  2. Peer gửi yêu cầu lấy danh sách peer đang chia sẻ file dựa vào info_hash trong magnet link
    # Tách header và body dựa trên chuỗi phân cách "\r\n\r\n"
    response = get_peer_list(client_socket,tracker_host,tracker_port,self_peer_id,info_hash)
    header, response_body = response.split("\r\n\r\n", 1)
    peer_list_info_hash = extract_filtered_peers(response_body)

    # In kết quả peer list
    print(f"Danh sách peer list {info_hash} từ phản hồi Tracker:")
    for peer in peer_list_info_hash:
        print(f"Peer ID: {peer['peer_id']}, IP: {peer['ip']}, Port: {peer['port']}")

    if not peer_list_info_hash:
        print(f"File {file_name} không còn được chia sẻ trong mạng")
        return None

    # 3. Peer multi kết nối với peer khác trong danh sách và yêu cầu lấy danh sách những piece nó có
    threads = []
    # Khởi chạy worker cho từng peer trong danh sách (loại bỏ chính peer của mình)
    for peer in peer_list_info_hash:
        if peer["peer_id"] == self_peer_id:
            continue
        t = threading.Thread(target=download_worker, args=(peer, self_peer_id, info_hash_byte, total_pieces))
        t.start()
        threads.append(t)

    # Chờ tất cả các thread hoàn thành
    for t in threads:
        t.join()

    if len(downloaded_pieces) < total_pieces:
        print("Tải file không thành công: chưa đủ pieces.")
        return None
    else:
        print(f"Tải file {file_name} thành công")

    # 5. Ghép file hoàn chỉnh && # 6. Xuất file
    export_dir = "data/export_files"
    os.makedirs(export_dir, exist_ok=True)

    # Đường dẫn đầy đủ của file
    file_path = os.path.join("data/export_files", file_name)

    # Ghi dữ liệu vào file
    with open(file_path, "wb") as output_file:
        for i in range(total_pieces):
            output_file.write(downloaded_pieces[i])

    # 7. Seeder

    # 8. Clear
    downloaded_pieces.clear()  # Xóa toàn bộ dữ liệu đã tải
    request_queue.clear()      # Xóa toàn bộ các yêu cầu piece


# ===============================================================================================
# =========================== UX/UI =============================================================
# ===============================================================================================

def print_gui():
    print("\nFUNCTION LIST")
    print("1 - Add a file want to share")
    print("2 - Peer register with tracker")
    print("3 - Get online file list")
    print("4 - Get peer list, just for test")
    print("5 - Download file")
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

    tserver = Thread(target=thread_server, args=(peerip,peerport,peerid))
    tclient = Thread(target=thread_client, args=(peerid,serverip,serverport,peerip,peerport))
    #tagent = Thread(target=thread_agent, args=(2, agentpath))

    tserver.start()
    tclient.start()

    tclient.join()
    #tagent.start()

    #Never completed
    tserver.join()
