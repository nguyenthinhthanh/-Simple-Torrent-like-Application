import bencodepy
from urllib.parse import urlparse, parse_qs
from urllib.parse import urlencode

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

# Function to create a .torrent file (Metainfo)
def create_torrent_file(info_hash, file_name, tracker_url, output_file):
    # Sample torrent metadata (in Bencode format)
    torrent_data = {
        "announce": tracker_url.encode(),  # Tracker URL
        "info": {
            "piece length": 512000,  # Example piece length (512KB)
            "pieces": b"abcd1234efgh5678abcd1234efgh5678",  # Placeholder piece hashes (20-byte SHA-1 hashes)
            "name": file_name.encode(),  # File name
            "length": 1024000  # Example file size (1MB)
        }
    }
    
    # Bencode the data
    encoded_data = bencodepy.encode(torrent_data)
    
    # Write the encoded data to a .torrent file
    with open(output_file, "wb") as f:
        f.write(encoded_data)
    
    print(f"Torrent file '{output_file}' created successfully!")

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

# Example magnet URI
#magnet_link = "magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678&dn=examplefile.txt&tr=http://tracker.example.com/announce"

info_hash_raw = "abcdef1234567890abcdef1234567890abcdef12"
display_name_raw = "example_file.txt"
tracker_raw = "http://tracker.example.com/announce"
file_size_raw = 2 * 1024 * 1024
magnet_link_create = create_magnet_uri(info_hash_raw, display_name_raw, tracker_raw, file_size_raw)
print(magnet_link_create)
magnet_link = input("Nhập magnet link của file cần tải: ").strip()
print(f"Magnet {magnet_link}")

# Step 1: Parse the magnet URI
info_hash, file_name, tracker_url, file_size = parse_magnet_uri(magnet_link)

# Print extracted information
print("Extracted Info:")
print(f"Info Hash: {info_hash}")
print(f"File Name: {file_name}")
print(f"File size: {file_size}")
print(f"Tracker URL: {tracker_url}")

# Step 2: Create a .torrent file using the extracted info
output_file = "examplefile.torrent"
create_torrent_file(info_hash, file_name, tracker_url, output_file)
