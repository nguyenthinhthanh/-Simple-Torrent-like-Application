import bencodepy
from urllib.parse import urlparse, parse_qs

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

# Example magnet URI
magnet_link = "magnet:?xt=urn:btih:1234567890abcdef1234567890abcdef12345678&dn=examplefile.txt&tr=http://tracker.example.com/announce"

# Step 1: Parse the magnet URI
info_hash, file_name, tracker_url = parse_magnet_uri(magnet_link)

# Print extracted information
print("Extracted Info:")
print(f"Info Hash: {info_hash}")
print(f"File Name: {file_name}")
print(f"Tracker URL: {tracker_url}")

# Step 2: Create a .torrent file using the extracted info
output_file = "examplefile.torrent"
create_torrent_file(info_hash, file_name, tracker_url, output_file)
