import json
import socket
import http.server
import socketserver
from threading import Thread
from urllib.parse import urlparse, parse_qs

# ===============================================================================================
# ============== HELPER FUNCTION ================================================================
# ===============================================================================================

TRACKER_ADDRESS = None

def set_tracker_address(hostip, port):
    global TRACKER_ADDRESS 
    TRACKER_ADDRESS = "http://{}:{}".format(hostip, port)

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


# ===============================================================================================
# ============== SERVER FUNCTION ================================================================
# ===============================================================================================

# Danh sách lưu thông tin Peer theo info_hash
peer_list = []
online_file = []
# Tạo set để lưu trữ các phần tử đã tồn tại
# existing_entries = set((entry["display_name"], entry["magnet"]) for entry in online_file)


def handle_peer_request(conn, addr):
    """
    Xử lý yêu cầu HTTP từ Peer
    """
    try:
        request = conn.recv(1024).decode()
        print(f"Nhận yêu cầu từ {addr}:\n{request}\n")

        # Lấy dòng đầu tiên của request (HTTP request line)
        request_line = request.split("\r\n")[0]
        if not request_line or len(request_line.split()) < 3:
            print(f"Lỗi: Request không hợp lệ từ {addr}")
            response = "HTTP/1.1 400 Bad Request\r\n\r\nInvalid Request"
            conn.sendall(response.encode())
            return False
        
        method, path, _ = request_line.split()
        print(f"Request line: {request_line}")

        # Kiểm tra phương thức HTTP
        if method != "GET":
            response = "HTTP/1.1 405 Method Not Allowed\r\n\r\nMethod Not Allowed"
            conn.sendall(response.encode())
            #conn.close()
            return False

        # Phân tích URL để lấy tham số query
        parsed_url = urlparse(path)
        params = parse_qs(parsed_url.query)
        print(f"Params: {params}")
        

        # Kiểm tra event để xử lý tương ứng : started, stopped, completed, list
        event = params.get("event", [None])[0]
        if not event:
            print(f"Lỗi: Thiếu tham số 'event' trong request từ {addr}")
            response = "HTTP/1.1 400 Bad Request\r\n\r\nMissing 'event' parameter"
            conn.sendall(response.encode())
            return False
        
        print(f"Event: {event}")        

        if event == "started":
            print(f"Xử lý sự kiện 'started' từ {addr}")
            print(f"Params nhận được: {params}")

            # Kiểm tra các tham số bắt buộc
            required_params = ["magnet", "peer_id", "port", "uploaded", "downloaded", "left", "event"]
            if not all(param in params for param in required_params):
                print(f"Lỗi: Thiếu tham số bắt buộc trong sự kiện 'started'")
                response = "HTTP/1.1 400 Bad Request\r\n\r\nMissing required parameters"
                conn.sendall(response.encode())
                #conn.close()
                return False

            # Lấy giá trị từ query
            magnet_list = params["magnet"] 
            peer_id = params["peer_id"][0]
            port = params["port"][0]
            #event = params["event"][0]
            print(f"Peer {peer_id} đã gửi yêu cầu 'started' trên cổng {port}")

            # Trích xuất info_hash từ mỗi magnet link
            info_hash_list = []
            for magnet in magnet_list:
                #print(f"Magnet {magnet}")
                info_hash, display_name, tracker_url, file_size = parse_magnet_uri(magnet)
                info_hash_list.append(info_hash)
                # online_file.append({display_name,magnet})
                new_entry = {"display_name": display_name, "magnet": magnet}
                if new_entry not in online_file:
                    online_file.append(new_entry)

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
                f"Request peer: {peer_id} on {addr[0]}:{port}\n"
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

        elif event == "updated":
            # Kiểm tra các tham số bắt buộc
            required_params = ["magnet", "peer_id", "port", "uploaded", "downloaded", "left", "event"]
            if not all(param in params for param in required_params):
                response = "HTTP/1.1 400 Bad Request\r\n\r\nMissing required parameters"
                conn.sendall(response.encode())
                #conn.close()
                return False

            # Lấy giá trị từ query
            magnet_list = params["magnet"]
            peer_id = params["peer_id"][0]
            port = params["port"][0]
            uploaded = params["uploaded"][0]
            downloaded = params["downloaded"][0]
            left = params["left"][0]

            # In thông tin cập nhật
            print(f"Peer {peer_id} at {addr[0]}:{port} updated status:")
            print(f"  Uploaded: {uploaded} bytes")
            print(f"  Downloaded: {downloaded} bytes")
            print(f"  Left: {left} bytes")
            print(f"====================================================================")

            # Gửi phản hồi HTTP
            response_body = "Status updated successfully"
            response = f"HTTP/1.1 200 OK\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
            conn.sendall(response.encode())

        elif event == "completed":
            print(f"Xử lý sự kiện 'completed' từ {addr}")

            # Kiểm tra các tham số bắt buộc
            required_params = ["magnet", "peer_id", "port", "uploaded", "downloaded", "left", "event"]
            if not all(param in params for param in required_params):
                print(f"Lỗi: Thiếu tham số bắt buộc trong sự kiện 'completed'")
                response = "HTTP/1.1 400 Bad Request\r\n\r\nMissing required parameters"
                conn.sendall(response.encode())
                return False

            # Lấy giá trị từ query
            magnet_list = params["magnet"]
            peer_id = params["peer_id"][0]
            port = params["port"][0]
            uploaded = params["uploaded"][0]
            downloaded = params["downloaded"][0]
            left = params["left"][0]

            # In thông tin hoàn thành
            print(f"Peer {peer_id} tại {addr[0]}:{port} đã hoàn thành tải file:")
            print(f"  Uploaded: {uploaded} bytes")
            print(f"  Downloaded: {downloaded} bytes")
            print(f"  Left: {left} bytes")
            print(f"====================================================================")

            # Kiểm tra xem peer đã tồn tại trong danh sách `peer_list` chưa
            peer_exists = False
            for peer in peer_list:
                if peer["peer_id"] == peer_id and peer["port"] == port and peer["ip"] == addr[0]:
                    peer_exists = True
                    break

            # Nếu peer đã tồn tại, đánh dấu là Seeder
            if peer_exists:
                print(f"Peer {peer_id} đã tồn tại trong danh sách và được đánh dấu là Seeder.")
            else:
                # Nếu peer chưa có trong danh sách, thêm mới với trạng thái Seeder
                peer_list.append({
                    "peer_id": peer_id,
                    "port": port,
                    "ip": addr[0],
                    "info_hash": [],
                    "magnet": magnet_list
                })
                print(f"Peer {peer_id} đã được thêm vào danh sách với trạng thái Seeder.")

            # Cập nhật `online_file`: nếu file chưa có trong danh sách, thêm vào
            for magnet in magnet_list:
                info_hash, display_name, tracker_url, file_size = parse_magnet_uri(magnet)
                new_entry = {"display_name": display_name, "magnet": magnet}
                if new_entry not in online_file:
                    online_file.append(new_entry)
                    print(f"File '{display_name}' đã được thêm vào danh sách online_file.")
                else:
                    print(f"File '{display_name}' đã tồn tại trong danh sách online_file.")

            # Gửi phản hồi HTTP
            response_body = "Peer marked as seeder successfully"
            response = f"HTTP/1.1 200 OK\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
            conn.sendall(response.encode())
            
        elif event == "completed":
            print(f"Xử lý sự kiện 'completed' từ {addr}")

            # Kiểm tra các tham số bắt buộc
            required_params = ["magnet", "peer_id", "port", "uploaded", "downloaded", "left", "event"]
            if not all(param in params for param in required_params):
                print(f"Lỗi: Thiếu tham số bắt buộc trong sự kiện 'completed'")
                response = "HTTP/1.1 400 Bad Request\r\n\r\nMissing required parameters"
                conn.sendall(response.encode())
                return False

            # Lấy giá trị từ query
            magnet_list = params["magnet"]
            peer_id = params["peer_id"][0]
            port = params["port"][0]
            uploaded = params["uploaded"][0]
            downloaded = params["downloaded"][0]
            left = params["left"][0]

            # In thông tin hoàn thành
            print(f"Peer {peer_id} tại {addr[0]}:{port} đã hoàn thành tải file:")
            print(f"  Uploaded: {uploaded} bytes")
            print(f"  Downloaded: {downloaded} bytes")
            print(f"  Left: {left} bytes")
            print(f"====================================================================")

            # Kiểm tra xem peer đã tồn tại trong danh sách `peer_list` chưa
            peer_exists = False
            for peer in peer_list:
                if peer["peer_id"] == peer_id and peer["port"] == port and peer["ip"] == addr[0]:
                    peer_exists = True
                    break

            # Nếu peer đã tồn tại, đánh dấu là Seeder
            if peer_exists:
                print(f"Peer {peer_id} đã tồn tại trong danh sách và được đánh dấu là Seeder.")
            else:
                # Nếu peer chưa có trong danh sách, thêm mới với trạng thái Seeder
                peer_list.append({
                    "peer_id": peer_id,
                    "port": port,
                    "ip": addr[0],
                    "info_hash": [],
                    "magnet": magnet_list
                })
                print(f"Peer {peer_id} đã được thêm vào danh sách với trạng thái Seeder.")

            # Cập nhật `online_file`: nếu file chưa có trong danh sách, thêm vào
            for magnet in magnet_list:
                info_hash, display_name, tracker_url, file_size = parse_magnet_uri(magnet)
                new_entry = {"display_name": display_name, "magnet": magnet}
                if new_entry not in online_file:
                    online_file.append(new_entry)
                    print(f"File '{display_name}' đã được thêm vào danh sách online_file.")
                else:
                    print(f"File '{display_name}' đã tồn tại trong danh sách online_file.")

            # Gửi phản hồi HTTP
            response_body = "Peer marked as seeder successfully"
            response = f"HTTP/1.1 200 OK\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
            conn.sendall(response.encode())

        elif event == "list":

            # Kiểm tra các tham số bắt buộc
            required_params = ["peer_id","event"]
            if not all(param in params for param in required_params):
                response = "HTTP/1.1 400 Bad Request\r\n\r\nMissing required parameters"
                conn.sendall(response.encode())
                #conn.close()
                return False
            # return handle_event_list(conn, addr, params)
            peer_id = params["peer_id"][0]

            # Gửi phản hồi HTTP
            # Tạo nội dung phản hồi
            # Chuyển đổi danh sách file thành JSON string
            file_list_json = json.dumps(online_file, indent=4)

            response_body = (
                f"Request peer: {peer_id} on {addr[0]}\n"
                f"Online file list: {file_list_json}\n"
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
        elif event == "get_peer_list":
            # return handle_event_get_peer_list(conn, addr, params)
            # Kiểm tra các tham số bắt buộc
            required_params = ["peer_id","info_hash","event"]
            if not all(param in params for param in required_params):
                response = "HTTP/1.1 400 Bad Request\r\n\r\nMissing required parameters"
                conn.sendall(response.encode())
                #conn.close()
                return False
            
            peer_id = params["peer_id"][0]
            info_hash = params["info_hash"][0]

            # Gửi phản hồi HTTP
            # Tạo nội dung phản hồi
            # Lọc danh sách để lấy những peer có info_hash trùng khớp với yêu cầu
            filtered_peers = []
            for p in peer_list:
                # Kiểm tra nếu info_hash yêu cầu có nằm trong list info_hash của p
                if info_hash in p["info_hash"] and p["peer_id"] != peer_id:
                    filtered_peers.append({
                        "peer_id": p["peer_id"],
                        "port": p["port"],
                        "ip": p["ip"]
                    })

            # Tạo phản hồi tracker: trả về tracker id và danh sách các peer phù hợp
            response_dict = {
                "tracker": TRACKER_ADDRESS,
                "peers": filtered_peers
            }
            response_body = json.dumps(response_dict)

            response_body = (
                f"Request peer: {peer_id} on {addr[0]}\n"
                f"Peer list: {response_dict}\n"
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
        else:
            response_body = "Invalid event"
            response = f"HTTP/1.1 400 Bad Request\r\nContent-Length: {len(response_body)}\r\n\r\n{response_body}"
            conn.sendall(response.encode())
            #conn.close()
            return False
        
        return True
    
    except Exception as e:
        print(f"Lỗi xử lý peer {addr}: {e}")
        print(f"Request từ peer: {request}")  # Log toàn bộ request để kiểm tra
        response = "HTTP/1.1 500 Internal Server Error\r\n\r\nServer Error"
        conn.sendall(response.encode())
        return False
    
    # finally:
    #     #conn.close()
    #     return True

# New peer connect to tracker
def new_connection(addr, conn):
    
    print(f"Client connected {addr}")
    while True:
        try:
            # This command receives data from the client (up to 1024 bytes at a time).
            # conn.recv(1024) is blocking → Server will wait until it receives data from the client.
            """
            Need to do here handle communication between tracker and peer
            """
            #data = conn.recv(1024)
            result = handle_peer_request(conn, addr)
            if result == False:
                break

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
    set_tracker_address(hostip,port)

    print("Listening on: {}:{}".format(hostip, port))
    server_program(hostip, port)
