# Sơ đồ Use Case hệ thống chấm công khuôn mặt

File nguồn: [`face-attendance-use-case.puml`](./face-attendance-use-case.puml).
Ảnh PNG: [`face-attendance-use-case.png`](./face-attendance-use-case.png).

Đây là **UML Use Case Diagram tổng quan theo vai trò**. Sơ đồ được rút gọn để dễ trình bày và thể hiện:

- **Actor:** bốn vai trò hiện có gồm Admin, HR, Manager và Employee.
- **System boundary:** Hệ thống quản lý chấm công khuôn mặt.
- **Use case:** Bốn nhóm chức năng chính của mỗi vai trò.
- **Association:** Đường nối giữa từng vai trò và chức năng tương ứng.
- **Ghi chú chung:** Cả bốn vai trò đều có xác thực tài khoản, quản lý mật khẩu và sử dụng trợ lý AI.
- **Phạm vi Manager:** Chỉ xem và xử lý dữ liệu của team được giao quản lý.

## Căn cứ từ hệ thống hiện tại

- Vai trò được khai báo tại `api-service/src/api/v1/shared/enums.py`.
- Quyền API được kiểm tra bằng `require_roles(...)` trong các controller của `api-service`.
- Chức năng quản trị được đối chiếu với router và menu trong `web-dashboard`.
- Chức năng Employee được đối chiếu với các màn hình attendance, leave, chat và profile trong `mobile_app`.
- Camera và các service nội bộ không được đưa vào sơ đồ này vì không phải vai trò người dùng.

## Cách xem hoặc xuất ảnh

Mở file `.puml` bằng plugin PlantUML của IntelliJ/PyCharm hoặc VS Code, sau đó chọn **Preview** hoặc **Export Diagram** để xuất PNG/SVG/PDF.

Nếu đã cài PlantUML CLI, có thể xuất SVG bằng:

```bash
plantuml -tsvg docs/diagrams/face-attendance-use-case.puml
```
