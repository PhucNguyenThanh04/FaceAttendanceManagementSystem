# Attendance Viewer

Frontend HTML/CSS/JS tối giản để xem stream và điều khiển attendance worker.

Chạy:

```bash
cd visualize-attendance
python -m http.server 5173
```

Mở:

```text
http://localhost:5173
```

Endpoint gọi:

```text
GET  /api/v1/attendance/status
GET  /api/v1/attendance/stream?fps=10
POST /api/v1/attendance/start
POST /api/v1/attendance/stop
```
