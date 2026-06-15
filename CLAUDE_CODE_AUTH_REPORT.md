# Bao cao ban giao cho Claude Code - Face Attendance Management System

## 1. Muc dich bao cao

Bao cao nay dung de trinh bay nhanh voi Claude Code ve hien trang du an `FaceAttendanceManagementSystem`, dac biet la module xac thuc trong `api-service/src/api/v1/features/auth`. Muc tieu la giup Claude Code nam duoc boi canh, kien truc, luong nghiep vu, diem manh, rui ro hien co va cac viec nen uu tien xu ly tiep theo.

## 2. Tong quan du an

Du an la he thong cham cong bang nhan dien khuon mat, gom nhieu thanh phan:

- `api-service`: Backend FastAPI chinh, xu ly nguoi dung, phan quyen, nhan su, ca lam, cham cong, ho so khuon mat, upload avatar va tich hop AI service.
- `ai-service`: Dich vu AI lien quan den dang ky/nhan dien khuon mat.
- `web-dashboard`: Dashboard web, kha nang cao dung cho admin/HR/manager.
- `mobile_app`: Ung dung mobile, kha nang cao dung cho nhan vien.
- `rag-chatbox`: Thanh phan chatbot/RAG, hien dang co nhieu thay doi chua commit.
- `infrastructure`: Docker compose, dockerfile, monitoring, Qdrant storage.
- `monitoring`: Prometheus/Grafana dashboard va alert.

Backend chinh la FastAPI, su dung PostgreSQL, Redis, SQLAlchemy async, Alembic, JWT, bcrypt/passlib, fastapi-mail va httpx.

## 3. Cac file lien quan truc tiep den Auth

- `api-service/src/api/v1/features/auth/service.py`: Lop `AuthService`, chua toan bo business logic cho login, refresh, logout, get me, change password, request OTP, verify OTP, verify reset token va reset password.
- `api-service/src/api/v1/features/auth/auth_repo.py`: Lop `AuthRepo`, truy van user, luu/rotate/xoa refresh token, doi mat khau.
- `api-service/src/api/v1/features/auth/controller.py`: Dinh nghia route `/auth/*`.
- `api-service/src/api/v1/features/auth/schemas.py`: Pydantic schema request/response va validate mat khau/OTP.
- `api-service/src/core/security/authentication.py`: Tao/decode access token, refresh token, hash password, hash refresh token, hash reset token, blacklist key.
- `api-service/src/core/dependencies/auth.py`: Dependency `get_current_user`, check JWT, Redis blacklist, token version, account status va role.
- `api-service/src/api/v1/features/users/models.py`: Model `User` va `Role`, co cac cot `token_version`, `refresh_token_hash`, `refresh_token_expires_at`, `refresh_token_created_at`.
- `api-service/src/core/configs/settings.py`: Cau hinh JWT, Redis, mail, OTP, password reset, CORS.

## 4. Kien truc auth hien tai

Module auth dang di theo mo hinh 3 lop:

- Controller: chi nhan request, inject dependency va goi service.
- Service: xu ly nghiep vu, validate trang thai user, tao token, luu Redis, gui email.
- Repo: thao tac database thong qua SQLAlchemy async session.

Access token la JWT co cac claim:

- `sub`: user id.
- `role`: role cua user.
- `token_version`: phien ban token hien tai cua user.
- `jti`: id rieng cua access token.
- `type`: `access`.
- `iat`, `exp`: thoi diem tao va het han.

Refresh token la chuoi random sinh bang `secrets.token_urlsafe(64)`, khong luu plain text trong DB. He thong luu `refresh_token_hash` bang HMAC-SHA256 voi `REFRESH_TOKEN_SECRET_KEY`.

Reset password token va OTP cung khong luu plain text. OTP/reset token duoc hash bang HMAC-SHA256 va luu trong Redis theo TTL.

## 5. Cac endpoint auth hien co

Base prefix: `/api/v1/auth`

- `POST /login`: Dang nhap bang email/password, tra ve access token va refresh token.
- `POST /refresh`: Doi refresh token cu lay cap token moi, co rotate refresh token.
- `POST /logout`: Blacklist access token hien tai trong Redis va xoa refresh token trong DB.
- `GET /me`: Lay thong tin user dang dang nhap.
- `POST /change-password`: Doi mat khau khi da dang nhap, yeu cau old password, revoke refresh token va tang `token_version`.
- `POST /password-reset/request-otp`: Gui OTP reset password qua email.
- `POST /password-reset/verify-otp`: Xac thuc OTP va cap reset token tam thoi.
- `POST /password-reset/verify-token`: Kiem tra reset token con hop le khong.
- `POST /password-reset/confirm`: Doi mat khau bang reset token, revoke refresh token va tang `token_version`.

## 6. Luong nghiep vu chi tiet

### 6.1. Login

1. Normalize email bang `strip().lower()`.
2. Tim user theo email trong DB, load kem role bang `selectinload`.
3. Verify password bang bcrypt/passlib.
4. Kiem tra user status phai la `active`.
5. Tao access token co `token_version` hien tai.
6. Tao refresh token va tinh ngay het han.
7. Luu hash refresh token vao user, cap nhat `last_login_at`.
8. Tra ve token pair.

### 6.2. Refresh token

1. Hash refresh token nguoi dung gui len.
2. Tim user co `refresh_token_hash` tuong ung.
3. Kiem tra user active.
4. Kiem tra `refresh_token_expires_at`.
5. Neu refresh token het han, xoa session trong DB.
6. Tao access token moi.
7. Tao refresh token moi va rotate trong DB.
8. Tra ve token pair moi.

### 6.3. Logout

1. Decode access token de lay `jti` va `exp`.
2. Neu token hop le va chua het han, luu key blacklist vao Redis den het TTL con lai.
3. Xoa refresh token trong DB nhung khong tang `token_version`.
4. Tra ve message logout thanh cong.

### 6.4. Change password

1. Verify old password.
2. Validate new password tu schema: toi thieu 8 ky tu, co chu cai va chu so, khac old password.
3. Hash mat khau moi.
4. Cap nhat password hash.
5. Revoke refresh token va tang `token_version` de vo hieu hoa access token cu.

### 6.5. Forgot password bang OTP

Request OTP:

1. Normalize email.
2. Kiem tra lock key trong Redis.
3. Neu email khong ton tai, tra ve response generic de tranh leak email.
4. Sinh OTP 6 chu so.
5. Hash OTP va luu record Redis gom `user_id`, `otp_hash`, `attempts`.
6. Gui email OTP.
7. Neu gui mail loi, xoa OTP key va tra loi loi server.

Verify OTP:

1. Kiem tra lock key.
2. Lay OTP record tu Redis.
3. Hash OTP input va so sanh voi hash da luu.
4. Neu sai, tang attempts; qua gioi han thi xoa OTP va tao lock key.
5. Neu dung, tao reset token, hash reset token va luu Redis theo TTL.
6. Xoa OTP key va lock key.
7. Tra ve reset token cho client.

Confirm reset password:

1. Hash reset token nguoi dung gui len.
2. Lay token payload tu Redis.
3. Tim user theo `user_id`.
4. Hash password moi.
5. Cap nhat password, revoke refresh token va tang `token_version`.
6. Xoa reset token key.

## 7. Cau hinh quan trong

Trong `settings.py` va `.env.example`:

- `JWT_SECRET_KEY`: Secret dung ky access token.
- `REFRESH_TOKEN_SECRET_KEY`: Secret dung hash refresh token va reset token.
- `JWT_ALGORITHM`: Thuat toan JWT.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Mac dinh example la 30 phut.
- `REFRESH_TOKEN_EXPIRE_DAYS`: Mac dinh example la 7 ngay.
- `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`: Mac dinh 15 phut.
- `OTP_EXPIRE_MINUTES`: Mac dinh 5 phut.
- `OTP_MAX_ATTEMPTS`: Mac dinh 5 lan.
- `OTP_LOCK_MINUTES`: Mac dinh 3 phut.
- Redis session DB mac dinh: `REDIS_DB_SESSION=0`.
- Redis attendance DB mac dinh: `REDIS_DB_ATTENDANCE=1`.

## 8. Diem manh hien co

- Refresh token khong luu plain text, chi luu hash HMAC.
- Access token co `jti` de blacklist khi logout.
- Access token co `token_version`, giup revoke hang loat token cu khi doi/reset mat khau.
- Refresh token co rotate moi lan refresh.
- Password reset OTP va reset token luu Redis co TTL.
- Response request OTP cho email khong ton tai la generic, tranh email enumeration.
- Doi mat khau revoke refresh token va tang `token_version`.
- Auth dependency co check Redis blacklist va account status.
- Controller kha mong, logic nghiep vu nam trong service.

## 9. Rui ro va van de can Claude Code kiem tra

### 9.1. Trung lap method trong `AuthService`

Trong `service.py` co 2 lan khai bao:

```python
@staticmethod
def _session_id_from_hash(token_hash: str) -> str:
    return token_hash[:24]
```

Method nay hien khong duoc dung. Nen xoa neu that su khong can, hoac dung cho logging/session id neu co ke hoach quan ly nhieu session.

### 9.2. Chua co rate limit login trong service/middleware

`settings.py` co cac bien:

- `login_rate_limit_ip_max_attempts`
- `login_rate_limit_user_max_attempts`
- `login_rate_limit_window_seconds`

Nhung trong `AuthService.login` hien chua thay ap dung rate limit. Day la rui ro brute force password.

### 9.3. Race condition voi refresh token

Refresh token dang rotate bang cach tim user theo token cu roi cap token moi. Neu 2 request refresh chay dong thoi, can kiem tra co the tao ra tinh huong ca hai request deu thanh cong hay khong. Nen can nhac row lock (`SELECT FOR UPDATE`) hoac co che atomic compare-and-update.

### 9.4. Reset token co the dung nhieu lan neu request dong thoi

`reset_password_with_token` doc Redis token, cap nhat DB, sau do moi delete token. Neu 2 request confirm cung reset token gan nhu dong thoi, can kiem tra kha nang reuse token. Giai phap: Redis GETDEL neu Redis version ho tro, hoac transaction/Lua script.

### 9.5. OTP verify chua xu ly JSON loi

`verify_password_reset_otp`, `verify_reset_token`, `reset_password_with_token` dung `json.loads(raw)`. Neu Redis data bi hong/khong dung format, request co the gay loi 500. Nen catch `json.JSONDecodeError`, xoa key hong va tra loi BadRequest hop ly.

### 9.6. Kiem tra role trong `get_current_user`

`get_current_user` query `select(User).where(User.user_id == user_id)` khong load role. Trong `require_roles`, code dung `current_user.role.name`. Tuy relationship role la `lazy="selectin"` trong model, nhung trong async SQLAlchemy viec lazy load co the gay loi neu truy cap ngoai greenlet/context phu hop. Nen test endpoint co `require_roles`, hoac sua query load role bang `selectinload(User.role)`.

### 9.7. File va naming trong repo

- Goc repo co file `README.md ` bi du khoang trang cuoi ten, file rong.
- Goc repo co `Claude.md` rong.
- Co nhieu file `__pycache__` dang nam trong cay source.
- `src/utils/exeptions.py` co ve bi sai chinh ta, nen doi thanh `exceptions.py` neu co thoi gian refactor an toan.
- `api-service/src/api/v1/shared/respone.py` co ve sai chinh ta, can kiem tra import truoc khi doi.
- `uploads_avartar` co ve sai chinh ta, can kiem tra anh huong route/import truoc khi doi.

### 9.8. Worktree dang co nhieu thay doi chua commit

Hien co thay doi chua commit trong:

- `ai-service/app/api/v1/features/register/controller.py`
- Nhieu file trong `rag-chatbox`
- File moi `rag-chatbox/pyproject.toml`
- File moi `rag-chatbox/src/rag/ingestion/indexer.py`
- File moi `rag-chatbox/src/rag/ingestion/chunkers/legachunker.py`
- Thu muc Qdrant storage `infrastructure/compose/storage/qdrant/collections/company_policy/`

Claude Code can tuyet doi khong revert cac thay doi nay neu khong duoc yeu cau.

## 10. De xuat uu tien cong viec tiep theo

Uu tien cao:

1. Them rate limit cho login theo IP va email/user, dung Redis va cac setting da co san.
2. Sua `get_current_user` de load role bang `selectinload(User.role)`, dam bao `require_roles` hoat dong on dinh trong async SQLAlchemy.
3. Lam refresh token rotation an toan hon voi row lock/atomic update.
4. Lam reset token one-time dung nghia bang Redis `GETDEL` hoac Lua transaction.
5. Them test cho login, refresh, logout, change password, password reset OTP.

Uu tien trung binh:

1. Xoa method trung lap/khong dung `_session_id_from_hash`.
2. Catch JSON decode loi cho du lieu Redis.
3. Bo sung logging audit cho login/logout/password change/password reset neu module audit da san sang.
4. Chuan hoa message ngon ngu, hien dang lan Anh/Viet giua cac module.
5. Them `.gitignore`/don dep `__pycache__`, Qdrant local storage neu khong nen commit.

Uu tien thap:

1. Sua naming typo `exeptions`, `respone`, `uploads_avartar` theo ke hoach refactor co test.
2. Hoan thien `README.md` va `Claude.md`.
3. Bo sung tai lieu API auth va flow frontend/mobile.

## 11. Prompt goi y de dua cho Claude Code

Co the dua doan sau cho Claude Code:

```text
Ban hay tiep tuc ho tro toi trong repo FaceAttendanceManagementSystem.

Boi canh:
- Backend chinh nam trong api-service, dung FastAPI async, SQLAlchemy async, PostgreSQL, Redis, JWT, passlib/bcrypt.
- Module auth nam tai api-service/src/api/v1/features/auth.
- Cac file quan trong: service.py, auth_repo.py, controller.py, schemas.py, core/security/authentication.py, core/dependencies/auth.py, users/models.py, core/configs/settings.py.
- Hien da co login, refresh token rotation, logout blacklist access token, get me, change password, forgot password OTP qua email, verify reset token va reset password.

Yeu cau:
1. Doc ky bao cao CLAUDE_CODE_AUTH_REPORT.md va cac file auth lien quan.
2. Khong revert cac thay doi chua commit trong ai-service, rag-chatbox hoac infrastructure neu khong duoc yeu cau.
3. Uu tien sua cac van de auth:
   - Them login rate limit bang Redis dua tren settings da co.
   - Sua get_current_user load role an toan bang selectinload.
   - Kiem tra/sua race condition refresh token rotation.
   - Dam bao reset token chi dung duoc mot lan.
   - Them test phu hop cho cac flow auth.
4. Giu code theo pattern hien co: controller mong, service chua nghiep vu, repo thao tac DB.
5. Sau khi sua, chay test/lint neu du an co cau hinh; neu khong chay duoc, bao ro ly do.
```

## 12. Ket luan

Module auth hien co nen tang kha tot: token duoc hash, access token co blacklist va token version, reset password co OTP va Redis TTL. Tuy nhien, can uu tien gia co cac diem lien quan den bao mat thuc chien: rate limit login, atomic refresh/reset token, test cho cac flow nhay cam va load role an toan trong async SQLAlchemy. Claude Code nen tiep tuc tu cac viec uu tien cao o muc 10.
