# Dashboard đơn giản cho báo cáo siêu thị

## Dự án tập trung vào xây dựng và triển khai Dashboard từ một hệ thống quản trị cơ bản, phục vụ cho phân tích chuyên sâu trong vận hành siêu thị.

## Mục tiêu
* **Tự triển khai hệ thống quản trị cơ bản (Đăng nhập/ Đăng xuất).**
* **Làm việc với hệ quản trị cơ sở dữ liêu quan hệ (PostgreSQL).**
* **Viết API truy vấn tích hợp tính toán (Aggregation) tối ưu.**
* **Xây dựng màn hình hiện thị báo cáo dạng biểu đồ trực quan (Dashboard).**

## Chi tiết

### 1. Cơ sở dữ liệu và nhập liệu
* Triển khai PostgreSQL và pgAdmin trên Docker.
* Thiết kế cấu trúc bảng để chứa dữ liệu.
* Import dữ liệu từ file CSV vào cơ sở dữ liệu bằng pgAdmin.

### 2. Backend API
* Bảng users phục vụ tính năng Auth (mã hóa trường mật khẩu).
* API Auth bao gồm: API login (xác thực tài khoản, trả về JWT Token), API logout (vô hiệu hóa tài khoản, xóa cookie hoặc xóa session phía client)
* API Reports lấy dữ liệu để vẽ biểu đồ


## 3. Frontend UI & tích hợp
* Màn hình Login: Hiển thị giao diện nhập email/password (thông báo lỗi nếu sai thông tin đăng nhập, không cho phép vào trang Dashboard bằng URL).
* Màn hình Dashboard: Hiển thị ba thẻ dữ liệu **Doanh thu - Lợi nhuận - Số đơn hàng**. Vẽ các biểu đồ đường, biểu đồ cột, biểu đồ tròn phục vụ báo cáo.
* Nút Logout: Xóa token khỏi bộ nhớ (LocalStorage/Cookie) và chuyển hướng về Màn hình Login.

---

Một số báo cáo đã được triển khai sẵn:
- Tổng số đơn hàng, doanh thu, lợi nhuận.
- Khu vực có nhiều khách nhất theo thứ tự giảm dần.
- Tỉ trọng phân khúc khách hàng.
- Hiệu suất danh mục sản phẩm.