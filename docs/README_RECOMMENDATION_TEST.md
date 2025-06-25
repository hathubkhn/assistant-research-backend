# Kiểm tra chức năng Recommendation Papers

Tài liệu này hướng dẫn cách kiểm tra chức năng recommendation papers trong hệ thống.

## Tổng quan về chức năng Recommendation

Hệ thống khuyến nghị paper (recommendation) hoạt động dựa trên các keywords (từ khóa) trong profile của người dùng và keywords của các paper. Cụ thể:

1. Hệ thống trích xuất keywords từ 2 trường trong profile của user:
   - `research_interests`: Lĩnh vực nghiên cứu quan tâm
   - `additional_keywords`: Các từ khóa bổ sung

2. Hệ thống so sánh các keywords này với keywords của các paper trong cơ sở dữ liệu.

3. Các paper có keywords trùng với keywords của user sẽ được đề xuất cho user đó.

## Dữ liệu đã được thêm vào

Đã thực hiện thêm 4-5 papers cho mỗi user trong hệ thống, trong đó có 2-3 papers có cùng keywords để kiểm tra chức năng recommendation. Script `add_papers_for_users.py` đã được chạy để thêm dữ liệu này.

Các paper có các chủ đề đa dạng như:
- AI và Machine Learning
- Computer Vision
- Data Science
- Cybersecurity
- Software Engineering

## Cách kiểm tra chức năng Recommendation

### 1. Đăng nhập vào hệ thống

Đăng nhập vào hệ thống với một trong các tài khoản đã được thêm papers.

### 2. Xem thông báo Recommendations (Notification Bell)

- Nhìn vào icon thông báo (chuông) ở góc trên bên phải
- Sẽ có hiển thị số lượng các paper được đề xuất
- Nhấp vào để xem danh sách các paper được đề xuất

### 3. Kiểm tra trang My Library

- Truy cập vào phần "My Library" 
- Đi đến tab "Recommended" để xem danh sách đầy đủ các paper được đề xuất
- Các paper hiển thị trong danh sách này là các paper có keywords trùng với keywords trong profile của user

### 4. Thử nghiệm thay đổi keywords trong profile

Để kiểm tra tính linh hoạt của chức năng recommendation:

1. Đi đến phần "Profile Settings"
2. Cập nhật các trường `Research Interests` hoặc `Additional Keywords` với các từ khóa mới
3. Quay lại phần "My Library" hoặc Notification Bell để xem các recommendation đã thay đổi chưa

### 5. Thêm paper vào mục yêu thích

Để kiểm tra việc recommendation không hiển thị lại các paper đã được thêm vào mục yêu thích:

1. Ở phần recommendation, thêm một số paper vào mục yêu thích bằng cách nhấn vào biểu tượng sao
2. Làm mới trang và kiểm tra xem các paper đã thêm vào mục yêu thích không còn xuất hiện trong recommendation nữa

## Kiểm tra cho mục đích Debug

Có thể sử dụng các endpoint API sau để kiểm tra:

- `GET /api/my-library/?section=recommended`: Trả về danh sách các paper được đề xuất
- `GET /api/my-library/?section=interesting`: Trả về danh sách các paper đã được đánh dấu yêu thích

## Lưu ý

- Recommendation chỉ hiển thị các paper được thêm trong vòng 30 ngày gần đây
- Recommendation không hiển thị các paper đã được đánh dấu yêu thích
- Mỗi user sẽ thấy các recommendation khác nhau dựa trên keywords trong profile 