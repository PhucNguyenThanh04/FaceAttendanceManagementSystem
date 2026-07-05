# BÁO CÁO CHI TIẾT DỰ ÁN: FACE ATTENDANCE MANAGEMENT SYSTEM
*(Hệ Thống Quản Lý Chấm Công Bằng Nhận Diện Khuôn Mặt Tích Hợp Trợ Lý Ảo)*

---

## 1. Tổng Quan Dự Án
Dự án **Face Attendance Management System** là một hệ thống toàn diện được thiết kế để tự động hóa quy trình chấm công, quản lý nhân sự (HR), quản lý ca làm việc, duyệt phép, và hỗ trợ tra cứu chính sách thông minh thông qua công nghệ trí tuệ nhân tạo (AI). 

Hệ thống được thiết kế theo kiến trúc microservices/dịch vụ phân tán bao gồm backend API trung tâm, dịch vụ xử lý AI nhận diện khuôn mặt thời gian thực, hệ thống Agentic RAG hỗ trợ hỏi đáp chính sách nhân sự và một trang tổng quan (dashboard) dành cho quản trị viên và cổng thông tin cho nhân viên.

---

## 2. Sơ Đồ Kiến Trúc Hệ Thống Chi Tiết

Dưới đây là sơ đồ kiến trúc hệ thống mô tả chi tiết luồng xử lý và tương tác giữa các lớp Client, dịch vụ Backend API, dịch vụ AI nhận diện, dịch vụ trợ lý ảo Agentic RAG và các hệ thống lưu trữ/bên thứ ba:

```mermaid
graph TD
    %% Styling
    classDef client fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef service fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    classDef datastore fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    classDef external fill:#fce4ec,stroke:#880e4f,stroke-width:2px;

    subgraph ClientLayer["Lớp Client & Thiết Bị Ngoại Vi"]
        Web["React Web Dashboard <br/> React Router / Zustand / Tailwind"]:::client
        Mobile["Mobile Application <br/> Flutter / React Native"]:::client
        Camera["IP Camera / Video Feed <br/> RTSP Stream / Local Webcam"]:::client
    end

    subgraph GatewayCore["Lớp Nghiệp Vụ Chính (api-service - FastAPI)"]
        API["FastAPI Gateway / Router"]:::service
        AuthService["Auth Service <br/> JWT / OTP / Blacklist"]:::service
        HRService["HR & Staff Service <br/> Departments / Positions"]:::service
        ShiftService["Work Shift Service <br/> Calendar / Rostering"]:::service
        AttService["Attendance Service <br/> Record Calculator"]:::service
        LeavesService["Leaves & Corrections <br/> Approval Workflows"]:::service
        DocService["Document Service <br/> ACL Permissions"]:::service
    end

    subgraph AIServiceLayer["Lớp Xử Lý Nhận Diện (attendance-service - FastAPI)"]
        AI_Server["FastAPI AI Server"]:::service
        CV_Pipe["OpenCV Pipe Processor"]:::service
        AntiSpoof["Liveness Detector <br/> Silent Face Anti Spoofing"]:::service
        Embedder["Face Embedder Model"]:::service
        AttWorker["Attendance Worker <br/> Realtime Frame Consumer"]:::service
    end

    subgraph RAGLayer["Lớp Trợ Lý Trí Tuệ Nhân Tạo (agentic-rag - FastAPI)"]
        RAG_Server["FastAPI RAG Service"]:::service
        Supervisor["ReAct Supervisor Agent"]:::service
        Executor["Tool Executor"]:::service
        Tools["Tool Registry <br/> VectorSearch / APIService / AskUser"]:::service
        Chunker["Legal Chunker & Loader <br/> PDF/Docx Parser"]:::service
        EmbedRerank["Embed & Rerank Pipe <br/> BGE-M3 & Reranker v2"]:::service
    end

    subgraph DataStoreLayer["Lớp Cơ Sở Dữ Liệu & Bộ Nhớ Đệm"]
        Postgres[("PostgreSQL 15 <br/> Relational Data")]:::datastore
        Redis[("Redis 7 Cache <br/> Sessions / OTP / Pending States")]:::datastore
        Qdrant[("Qdrant Vector DB <br/> face_profiles / company_policy")]:::datastore
    end

    subgraph ExternalServices["Dịch Vụ Ngoại Vi"]
        Gemini["Google Gemini API <br/> Gemini 1.5 / Flash / Pro"]:::external
        SMTP["SMTP Email Server <br/> OTP Notifications"]:::external
    end

    %% Connect Layer
    Web <-->|HTTP REST / JSON| API
    Mobile <-->|HTTP REST / JSON| API
    Camera -->|RTSP / Frames| AttWorker

    %% api-service connections
    API --> AuthService
    API --> HRService
    API --> ShiftService
    API --> AttService
    API --> LeavesService
    API --> DocService

    AuthService <--> Redis
    AuthService --> SMTP
    
    HRService <--> Postgres
    ShiftService <--> Postgres
    AttService <--> Postgres
    LeavesService <--> Postgres
    DocService <--> Postgres

    %% attendance-service connections
    AI_Server --> CV_Pipe
    CV_Pipe --> AntiSpoof
    CV_Pipe --> Embedder
    AttWorker --> CV_Pipe
    Embedder -->|Search & Match Vectors| Qdrant
    AttWorker -->|POST Raw Events| API

    %% agentic-rag connections
    API <-->|Trigger Chats & Sync| RAG_Server
    RAG_Server --> Supervisor
    Supervisor <--> Executor
    Executor --> Tools
    Tools -->|Vector Search| Qdrant
    Tools -->|HTTP Query Staff/Att| API
    Supervisor <-->|Call LLM JSON/Stream| Gemini
    
    %% Redis caching for RAG
    Supervisor <-->|Save/Resume Pending State| Redis

    %% Documents ingestion
    RAG_Server --> Chunker
    Chunker --> EmbedRerank
    EmbedRerank -->|Upsert Sparse/Dense Vectors| Qdrant
end
```

---


## 2. Bài Toán Dự Án Giải Quyết
Hệ thống ra đời nhằm giải quyết các bất cập lớn trong công tác quản lý nhân sự truyền thống tại doanh nghiệp:
*   **Gian lận chấm công (Buddy Punching):** Ngăn chặn triệt để tình trạng chấm công hộ bằng việc sử dụng nhận diện khuôn mặt kết hợp công nghệ chống giả mạo bằng hình ảnh hoặc video (Liveness Detection/Anti-Spoofing).
*   **Sai sót và tốn thời gian chấm công thủ công:** Tự động ghi nhận thời gian chấm công từ các luồng camera giám sát trực tiếp, giảm thiểu sai sót từ việc nhập liệu thủ công của bộ phận HR.
*   **Quản lý lịch trình ca làm phức tạp:** Hỗ trợ cấu hình ca linh hoạt (ca hành chính, ca kíp, ca gãy), tự động tính toán thời gian đi muộn/về sớm dựa trên ca làm việc được phân công.
*   **Quy trình phê duyệt nghỉ phép cồng kềnh:** Số hóa toàn bộ quy trình gửi đơn xin nghỉ phép, đơn sửa công và quy trình phê duyệt đa cấp của Manager/HR.
*   **Quá tải trong giải đáp thắc mắc nội quy/chính sách:** Tích hợp chatbot Agent RAG giúp nhân viên tự động tra cứu nhanh chính sách công ty (ngày phép, chế độ thai sản, quy định trang phục,...) thông qua ngôn ngữ tự nhiên.

---

## 3. Các Tính Năng Đã Hoàn Thành

### 3.1. Phân Hệ Xác Thực & Bảo Mật (Auth Module)
*   **Đăng nhập/Đăng xuất bảo mật:** Sử dụng cơ chế Token JWT (Access Token thời gian ngắn) kết hợp Refresh Token lưu trữ dạng mã hóa HMAC-SHA256 dưới cơ sở dữ liệu.
*   **Cơ chế xoay vòng Refresh Token (Rotation):** Mỗi lần refresh token sẽ sinh ra một cặp token mới giúp giảm thiểu rủi ro bị đánh cắp token.
*   **Hệ thống Blacklist và Revocation:** Khi người dùng logout, Access Token sẽ bị đưa vào danh sách đen trên Redis để vô hiệu hóa ngay lập tức. Đổi mật khẩu sẽ tự động tăng `token_version` để thu hồi toàn bộ token cũ đang hoạt động.
*   **Khôi phục mật khẩu thông qua OTP Email:** Quy trình gửi mã OTP xác nhận khôi phục mật khẩu qua Email an toàn, lưu trữ OTP hash tạm thời trên Redis có cài đặt TTL và giới hạn số lần thử (rate limit).

### 3.2. Quản Lý Nhân Sự & Tổ Chức (Staff & User Module)
*   **Quản lý nhân viên (Employees):** Thông tin hồ sơ chi tiết, mã nhân viên, trạng thái tài khoản hoạt động/ngừng hoạt động.
*   **Cơ cấu tổ chức (Departments & Positions):** Quản lý danh mục phòng ban, chức vụ và sơ đồ quản lý trực tiếp (Manager - Subordinate).
*   **Phân quyền hệ thống (Roles):** Hỗ trợ phân quyền chặt chẽ (`admin`, `hr`, `manager`, `employee`).

### 3.3. Nhận Diện Khuôn Mặt Chấm Công (AI & Attendance Core)
*   **Đăng ký hồ sơ khuôn mặt (Face Onboarding):** Hỗ trợ luồng onboarding chụp hình từ xa, kiểm tra ảnh đạt chuẩn chất lượng, trích xuất vector khuôn mặt và lưu trữ vào Qdrant Vector Database.
*   **Chống giả mạo thời gian thực (Anti-Spoofing):** Tích hợp mô hình Silent-Face-Anti-Spoofing nhằm phát hiện ảnh chụp hoặc video giả lập qua màn hình điện thoại/máy tính.
*   **Ghi nhận sự kiện chấm công tự động:** Pipeline ML tự động nhận dạng khuôn mặt từ luồng camera trực tiếp, đối soát vector đặc trưng với Qdrant và bắn sự kiện ghi nhận chấm công về hệ thống lõi.

### 3.4. Trợ Lý Trả Lời Chính Sách Thông Minh (Agentic RAG)
*   **Tìm kiếm kết hợp (Hybrid Search):** Kết hợp tìm kiếm ngữ nghĩa (Semantic dense vectors) và tìm kiếm từ khóa (Sparse BM25 vectors) trên mô hình BGE-M3.
*   **Duyệt lọc ngữ cảnh an toàn:** Lọc tài liệu theo quyền của người dùng đăng nhập (`allowed_roles`), đảm bảo nhân viên thông thường không thể truy cập các tài liệu mật của quản trị viên.
*   **ReAct Agent Supervisor Loop:** Điều phối luồng xử lý thông minh thông qua Supervisor Agent. Agent tự động phân tích câu hỏi để lựa chọn công cụ phù hợp (`vector_search` tìm chính sách, `employee_query` tìm thông tin nhân sự, `attendance_query` truy vấn giờ chấm công, hoặc `ask_user` để tương tác hỏi thêm thông tin).
*   **Streaming SSE Response:** Trả lời người dùng theo cơ chế streaming ký tự thời gian thực, có đi kèm trích dẫn tài liệu tham khảo (citations).

### 3.5. Giao Diện Quản Trị & Cổng Nhân Viên (Web Dashboard)
*   Trang tổng quan thống kê trạng thái chấm công của nhân viên hàng ngày.
*   Trang quản lý hồ sơ nhân viên, sơ đồ tổ chức, danh mục ca làm việc.
*   Giao diện chatbox trò chuyện trực quan với Trợ lý ảo RAG.

---

## 4. Tiến Độ Hiện Tại & Kế Hoạch Tiếp Theo

### 4.1. Trạng Thế Tiến Độ
*   **Core Backend (FastAPI):** Hoàn thành khoảng **80%**. Các API CRUD cốt lõi cho Nhân sự, Ca làm, Tài khoản, Face Profile, Chat RAG và Onboarding đã đi vào hoạt động ổn định (~70 endpoints hoạt động).
*   **AI Service (ML Pipeline):** Hoàn thành **90%** các thuật toán nhận diện và liveness detection.
*   **RAG Service:** Hoàn thành **85%** phần khung agent ReAct, tìm kiếm ngữ nghĩa, và streaming.
*   **Web Dashboard:** Đang trong quá trình hoàn thiện giao diện các module nâng cao và tích hợp API.

### 4.2. Các Nhiệm Vụ Cần Hoàn Thiện Tiếp Theo (Kế Hoạch)
Theo phân tích nghiệp vụ, các module dưới đây đã có sẵn Models & Schemas cấu trúc dữ liệu nhưng đang thiếu Service xử lý logic và API Controller:

1.  **Hệ Thống Nghỉ Phép (Leaves Management - 11 Endpoints):**
    *   Tạo đơn xin nghỉ phép, hủy đơn.
    *   Quy trình phê duyệt/từ chối đơn xin nghỉ phép của Manager/HR.
    *   Tính toán số ngày nghỉ phép còn lại của từng nhân viên (`leaves/balance`).
2.  **Sửa Công / Giải Trình Chấm Công (Attendance Corrections - 7 Endpoints):**
    *   Đăng ký đơn giải trình khi quên chấm công hoặc lỗi nhận diện.
    *   Phê duyệt đơn và tự động cập nhật giờ chấm công chính xác vào bảng công (`attendance_records`).
3.  **Bảng Công Thống Kê (Attendance Records - 4 Endpoints):**
    *   Chuyển đổi các sự kiện quét camera thô (`Events`) thành bảng công chính thức hàng ngày (`Records`) hiển thị trạng thái Đi muộn / Về sớm / Vắng mặt.
    *   Cung cấp API sửa đổi bảng công thủ công dành cho bộ phận HR.
4.  **Hệ Thống Thông Báo (Notifications - 7 Endpoints):**
    *   Gửi thông báo đẩy về phê duyệt nghỉ phép, sửa công, hoặc cảnh báo đi muộn đến từng tài khoản.
5.  **Nhật Ký Hệ Thống (Audit Logs - 3 Endpoints):**
    *   Ghi vết toàn bộ thao tác nhạy cảm (thêm/sửa/xóa nhân viên, thay đổi lương, thay đổi cấu hình ca làm) của Admin.
6.  **Gia Cố Bảo Mật & Tối Ưu:**
    *   Tích hợp bộ giới hạn tần suất đăng nhập (Login Rate Limit) dựa trên địa chỉ IP và tài khoản bằng Redis.
    *   Giải quyết triệt để vấn đề Race Condition khi xoay vòng Refresh Token bằng cơ chế Row Lock trên Database.
    *   Tối ưu hóa câu lệnh truy vấn nạp phân quyền nhanh (`selectinload(User.role)`) trong FastAPI dependencies.

---

## 5. Kiến Trúc Kỹ Thuật (Tech Stack)

*   **Backend Services:** FastAPI, Python 3.10+, SQLAlchemy (Async), Alembic, Pydantic v2.
*   **AI/ML Pipelines:** OpenCV, PyTorch, Silent-Face-Anti-Spoofing, ThreadPoolExecutor ( ML Serialization).
*   **Databases & Caches:**
    *   *PostgreSQL 15:* Lưu trữ cơ sở dữ liệu quan hệ nghiệp vụ.
    *   *Redis 7:* Quản lý session, cache, khóa đồng bộ, OTP và rate limiting.
    *   *Qdrant Cloud/Local:* Lưu trữ và tìm kiếm vector khuôn mặt cùng vector ngữ nghĩa tài liệu chính sách.
*   **Frontend Client:** React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand, Axios, React Hook Form.
*   **Infrastructure & DevOps:** Docker, Docker Compose, Prometheus (Monitoring), Grafana (Dashboards).
