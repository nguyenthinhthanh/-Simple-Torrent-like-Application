import socket
import http.server
import socketserver
from threading import Thread
from urllib.parse import urlparse, parse_qs

# ===============================================================================================
# ============== HELPER FUNCTION ================================================================
# ===============================================================================================

# Function to parse a magnet URI
def parse_magnet_uri(magnet_link):
    # Parse the magnet link
    parsed = urlparse(magnet_link)
    params = parse_qs(parsed.query)
    
    # Extract info hash
    info_hash = params.get('xt')[0].split(":")[-1]
    
    # Extract display name (optional)
    display_name = params.get('dn', ['Unknown'])[0]
    
    # Extract tracker URL (optional)
    tracker_url = params.get('tr', [''])[0]
    
    return info_hash, display_name, tracker_url


# ===============================================================================================
# ============== SERVER FUNCTION ================================================================
# ===============================================================================================

# Danh sách lưu thông tin Peer theo info_hash
peer_list = []
online_file = []

def handle_peer_request(conn, addr):
    """
    Xử lý yêu cầu HTTP từ Peer
    """
    try:
        request = conn.recv(1024).decode()
        print(f"Nhận yêu cầu từ {addr}:\n{request}\n")

        # Lấy dòng đầu tiên của request (HTTP request line)
        request_line = request.split("\r\n")[0]
        method, path, _ = request_line.split()

        # Kiểm tra phương thức HTTP
        if method != "GET":
            response = "HTTP/1.1 405 Method Not Allowed\r\n\r\nMethod Not Allowed"
            conn.sendall(response.encode())
            conn.close()
            return

        # Phân tích URL để lấy tham số query
        parsed_url = urlparse(path)
        params = parse_qs(parsed_url.query)

        # Kiểm tra các tham số bắt buộc
        required_params = ["magnet", "peer_id", "port", "uploaded", "downloaded", "left", "event"]
        if not all(param in params for param in required_params):
            response = "HTTP/1.1 400 Bad Request\r\n\r\nMissing required parameters"
            conn.sendall(response.encode())
            conn.close()
            return

        # Lấy giá trị từ query
        magnet_list = params["magnet"] 
        peer_id = params["peer_id"][0]
        port = params["port"][0]
        event = params["event"][0]

        # Trích xuất info_hash từ mỗi magnet link
        info_hash_list = []
        for magnet in magnet_list:
            info_hash, display_name, tracker_url = parse_magnet_uri(magnet)
            info_hash_list.append(info_hash)
            online_file.append({display_name,magnet})

        # Lưu thông tin Peer cho từng info_hash
        peer_list.append({
            "peer_id": peer_id,
            "port": port,
            "ip": addr[0],
            "info_hash" : info_hash_list,
            "magnet" : magnet_list
        })

        # Gửi phản hồi HTTP
        # Tạo nội dung phản hồi
        response_body = (
            f"Registered peer: {peer_id} on {addr[0]}:{port}\n"
            f"Info Hashes: {', '.join(info_hash_list)}\n"
            "Status: OK\n"
        )

        # Gửi phản hồi HTTP
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "\r\n"
            f"{response_body}"
        )
        conn.sendall(response.encode())
    
    except Exception as e:
        print(f"Lỗi xử lý peer {addr}: {e}")
    
    finally:
        conn.close()

# New peer connect to tracker
def new_connection(addr, conn):
    print(addr)
    while True:
        try:
            # This command receives data from the client (up to 1024 bytes at a time).
            # conn.recv(1024) is blocking → Server will wait until it receives data from the client.
            """
            Need to do here handle communication between tracker and peer
            """
            #data = conn.recv(1024)
            handle_peer_request(conn, addr)
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
def server_program(hostip, port):
    serversocket = socket.socket()                                  # Creat socket server using TCP/IP protocol
    serversocket.bind((hostip, port))                               # Assign socket with host ip and port

    # Put the socket into listen mode to wait for the client to connect.
    # Parameter 10 is the connection queue length, which means that up to 10 clients can wait before being rejected.
    serversocket.listen(10)
    while True:
        # It will wait (blocking) until a client connects.
        # When a client connects, the server creates a new socket (conn) to communicate with that client.
        # addr will contain the client's IP address and port information.
        conn, addr = serversocket.accept()
        nconn = Thread(target=new_connection, args=(addr, conn))
        nconn.start()                                               # Activate the thread                                                                                                

if __name__ == "__main__":
    hostip = get_host_default_interface_ip()
    port = 22236                                                    # Random port from 1024 to 65535
    print("Listening on: {}:{}".format(hostip, port))
    server_program(hostip, port)
