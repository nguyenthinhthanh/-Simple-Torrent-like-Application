# P2P File Sharing Application

Mô tả dự án  
- Ứng dụng chia sẻ file kiểu torrent đơn giản, sử dụng kiến trúc tracker-node dựa trên giao thức TCP/IP.  
- Tracker trung tâm lưu trữ thông tin về các node và các file pieces, giúp xác định các nguồn tải file hiệu quả.  
- Hỗ trợ tải file đa hướng (Multi-Directional Data Transfer - MDDT) cho phép tải file từ nhiều nguồn đồng thời bằng cách sử dụng đa luồng.  
- Triển khai giao thức tracker và giao tiếp peer-to-peer đảm bảo việc truyền tải file chính xác và nhanh chóng.

### Table of Contents
- [P2P File Sharing Application](#p2p-file-sharing-application)
- [Chức năng chính](#chức-năng-chính)
- [Yêu cầu phần cứng và phần mềm](#yêu-cầu-phần-cứng-và-phần-mềm)
- [Cách triển khai](#cách-triển-khai)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
- [Tính năng mở rộng](#tính-năng-mở-rộng)
- [Đóng góp](#đóng-góp)
- [Giấy phép](#giấy-phép)

## Chức năng chính
1. **Tracker Server**:  
   - Quản lý thông tin về các node và file pieces.  
   - Gửi danh sách các peer có sẵn cho client khi có yêu cầu tải file.
2. **Peer Node**:  
   - Tải xuống và chia sẻ file pieces từ các node khác.  
   - Hỗ trợ kết nối đa luồng để tăng tốc độ tải file.
3. **Magnet Link & Metainfo File**:  
   - Magnet Link chứa thông tin cơ bản để truy cập metainfo file (tương đương file .torrent).  
   - Metainfo File lưu trữ thông tin về tracker, kích thước piece, số lượng pieces và ánh xạ file.
4. **Multi-Directional Data Transfer (MDDT)**:  
   - Cho phép tải file từ nhiều nguồn (peer) cùng lúc, tối ưu hóa băng thông và thời gian tải file.
5. **Giao thức Tracker & Peer-to-Peer**:  
   - Triển khai các yêu cầu gửi nhận giữa client và tracker, cũng như giữa các peer để đảm bảo truyền tải file hiệu quả.

## Yêu cầu phần cứng và phần mềm
**Phần cứng:**  
- Máy chủ hoặc máy tính chạy Tracker Server.  
- Máy tính hoặc thiết bị kết nối mạng chạy ứng dụng Peer.

**Phần mềm:**  
- Python 3.7 trở lên (hoặc ngôn ngữ lập trình được sử dụng).  
- Các thư viện hỗ trợ như `socket`, `threading` và các thư viện khác cần thiết cho giao tiếp mạng.  
- Hệ điều hành hỗ trợ TCP/IP (Linux, Windows, macOS).

## Cách triển khai
1. **Clone repository:**
   ```bash
   git clone https://github.com/nguyenthinhthanh/-Simple-Torrent-like-Application
   ```
2. **Chạy Tracker Server:**
   ```bash
   python tracker.py
   ```
3. **Chạy Peer Node:**
   ```bash
   python peer_sta.py --server-ip 123.456 --server-port 12345
   ```
## Hướng dẫn sử dụng
- Khởi động Tracker Server trước để các peer có thể kết nối và nhận danh sách các nguồn tải.
- Chạy ứng dụng peer để kết nối đến tracker và bắt đầu tải file từ các nguồn có sẵn.
- Theo dõi tiến trình tải lên và tải xuống thông qua giao diện điều khiển (command-line hoặc GUI nếu có).
- Tính năng mở rộng
- Hỗ trợ tải nhiều torrent cùng lúc: Quản lý đồng thời nhiều tiến trình tải và chia sẻ file.
- Giao diện người dùng (GUI): Phát triển giao diện đồ họa hiển thị thông tin kết nối, tiến trình tải và thống kê chia sẻ file.
- Thuật toán tối ưu hóa lựa chọn peer: Cải tiến thuật toán chọn peer để tăng tốc độ tải và tối ưu băng thông.
## Đóng góp
- Nếu bạn có ý tưởng hoặc muốn cải thiện dự án, hãy mở Pull Request hoặc Issue trên GitHub để cùng thảo luận và phát triển.
## Giấy phép
- NULL
   
