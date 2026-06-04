# CODEX_FRONTEND_INSTRUCTIONS.md

## Mục tiêu

Bạn là coding agent phụ trách **frontend React** cho project `FaceAttendanceManagementSystem`.

Nhiệm vụ của bạn là viết frontend chuẩn, dễ maintain, type-safe, theo kiến trúc feature-based.

**Tuyệt đối không thay đổi backend.**

Backend gồm các service như:

- `api-service`
- `ai-service`
- database schema
- migrations
- business logic FastAPI
- routers, services, repositories backend
- Docker/backend configs

Nếu cần hiểu API, chỉ được **đọc** backend để tham khảo contract, không được sửa.

---

## Phạm vi được phép chỉnh sửa

Bạn chỉ được phép tạo/sửa file trong các khu vực frontend, ví dụ:

```txt
frontend/
web/
client/
src/
```

Tùy theo project thực tế, nếu frontend nằm ở folder cụ thể, chỉ làm trong folder đó.

Nếu chưa có frontend, hãy tạo folder:

```txt
frontend/
```

với stack mặc định:

```txt
React + TypeScript + Vite
```

---

## Phạm vi KHÔNG được phép chỉnh sửa

Không được sửa, xóa, format, rename, move hoặc refactor bất kỳ file nào thuộc backend.

Các folder/file cấm chỉnh sửa:

```txt
api-service/
ai-service/
backend/
alembic/
migrations/
docker-compose.yml
Dockerfile
.env
.env.example
requirements.txt
pyproject.toml
poetry.lock
Pipfile
run.py
main.py
src/core/
src/features/  nếu nằm trong backend
```

Không được tự ý thay đổi:

```txt
PostgreSQL schema
Redis config
Qdrant config
JWT logic
FastAPI routers
FastAPI services
FastAPI repositories
SQLAlchemy models
Alembic migrations
AI-service endpoints
```

Nếu cần thêm biến môi trường cho frontend, chỉ tạo/sửa:

```txt
frontend/.env.example
frontend/.env
```

Không sửa `.env` của backend.

---

## Nguyên tắc làm việc

Trước khi code, hãy kiểm tra cấu trúc project.

Nếu đã có frontend:

1. Giữ nguyên stack hiện tại.
2. Không rewrite toàn bộ nếu không cần.
3. Follow convention đang có.
4. Chỉ cải thiện đúng phần được yêu cầu.

Nếu chưa có frontend:

1. Tạo frontend bằng React + TypeScript + Vite.
2. Dùng cấu trúc feature-based.
3. Chuẩn bị sẵn routing, API client, layout, auth flow cơ bản.

---

## Stack frontend khuyến nghị

Sử dụng:

```txt
React
TypeScript
Vite
React Router
TanStack Query
Axios
React Hook Form
Zod
Zustand
Tailwind CSS
```

Nếu project đã dùng UI library khác, không tự ý thay đổi.

Không thêm dependency mới nếu chưa thật sự cần.

---

## File structure frontend chuẩn

Nếu tạo mới frontend, dùng structure này:

```txt
frontend/
├── public/
├── src/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── router.tsx
│   │   └── providers.tsx
│   │
│   ├── assets/
│   │   ├── images/
│   │   └── icons/
│   │
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Badge.tsx
│   │   │   └── Loading.tsx
│   │   │
│   │   └── layout/
│   │       ├── AppLayout.tsx
│   │       ├── Sidebar.tsx
│   │       ├── Header.tsx
│   │       └── ProtectedRoute.tsx
│   │
│   ├── features/
│   │   ├── auth/
│   │   ├── employees/
│   │   ├── departments/
│   │   ├── positions/
│   │   ├── department-managers/
│   │   ├── face-profiles/
│   │   ├── attendance/
│   │   ├── leave/
│   │   ├── corrections/
│   │   ├── audit-logs/
│   │   ├── notifications/
│   │   └── settings/
│   │
│   ├── lib/
│   │   ├── axios.ts
│   │   ├── query-client.ts
│   │   └── utils.ts
│   │
│   ├── stores/
│   │   └── auth.store.ts
│   │
│   ├── constants/
│   │   ├── routes.ts
│   │   └── permissions.ts
│   │
│   ├── types/
│   │   └── common.types.ts
│   │
│   ├── styles/
│   │   └── globals.css
│   │
│   └── main.tsx
│
├── .env.example
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

---

## Cấu trúc chuẩn cho mỗi feature

Mỗi feature nên có cấu trúc:

```txt
features/
└── employees/
    ├── api/
    │   └── employee.api.ts
    │
    ├── components/
    │   ├── EmployeeTable.tsx
    │   ├── EmployeeForm.tsx
    │   ├── EmployeeDetailCard.tsx
    │   └── EmployeeStatusBadge.tsx
    │
    ├── hooks/
    │   ├── useEmployees.ts
    │   ├── useEmployeeDetail.ts
    │   ├── useCreateEmployee.ts
    │   └── useUpdateEmployee.ts
    │
    ├── pages/
    │   ├── EmployeeListPage.tsx
    │   ├── EmployeeDetailPage.tsx
    │   └── EmployeeCreatePage.tsx
    │
    ├── schemas/
    │   └── employee.schema.ts
    │
    ├── types/
    │   └── employee.types.ts
    │
    └── index.ts
```

Ý nghĩa:

```txt
api/         gọi backend
components/  UI thuộc riêng feature
hooks/       logic data fetching/mutation
pages/       màn hình route
schemas/     validate form bằng zod
types/       TypeScript type/interface
index.ts     export gọn
```

---

## Quy tắc viết component

Component phải:

1. Là function component.
2. Dùng TypeScript.
3. Không chứa business logic phức tạp.
4. Không gọi API trực tiếp trong component.
5. Không để file quá dài.
6. Không dùng `any` nếu có thể tránh.
7. Props phải có type rõ ràng.

Ví dụ tốt:

```tsx
type EmployeeTableProps = {
  employees: Employee[];
  onView?: (employeeId: string) => void;
};

export function EmployeeTable({ employees, onView }: EmployeeTableProps) {
  return (
    <div>
      {employees.map((employee) => (
        <div key={employee.employee_id}>
          <span>{employee.full_name}</span>
          <button onClick={() => onView?.(employee.employee_id)}>
            View
          </button>
        </div>
      ))}
    </div>
  );
}
```

Không viết component kiểu:

```tsx
export default function Component() {
  // fetch trực tiếp
  // xử lý business logic
  // validate thủ công dài
  // render UI quá nhiều
}
```

---

## Quy tắc gọi API

Tất cả API call phải đặt trong:

```txt
features/<feature-name>/api/
```

Ví dụ:

```ts
import { api } from "@/lib/axios";
import type { Employee, CreateEmployeePayload } from "../types/employee.types";

export const employeeApi = {
  getEmployees: async (): Promise<Employee[]> => {
    const res = await api.get("/staff/employees");
    return res.data;
  },

  getEmployeeById: async (employeeId: string): Promise<Employee> => {
    const res = await api.get(`/staff/employees/${employeeId}`);
    return res.data;
  },

  createEmployee: async (
    payload: CreateEmployeePayload
  ): Promise<Employee> => {
    const res = await api.post("/staff/employees", payload);
    return res.data;
  },

  updateEmployee: async (
    employeeId: string,
    payload: Partial<CreateEmployeePayload>
  ): Promise<Employee> => {
    const res = await api.patch(`/staff/employees/${employeeId}`, payload);
    return res.data;
  },
};
```

Không gọi `fetch` hoặc `axios` trực tiếp trong page/component.

---

## Axios config

Tạo file:

```txt
src/lib/axios.ts
```

Nội dung mẫu:

```ts
import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});
```

Frontend env:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Không đọc hoặc sửa env backend.

---

## Quy tắc data fetching

Dùng TanStack Query cho server state.

Ví dụ:

```ts
import { useQuery } from "@tanstack/react-query";
import { employeeApi } from "../api/employee.api";

export function useEmployees() {
  return useQuery({
    queryKey: ["employees"],
    queryFn: employeeApi.getEmployees,
  });
}
```

Mutation:

```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { employeeApi } from "../api/employee.api";

export function useCreateEmployee() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: employeeApi.createEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });
}
```

Không dùng `useEffect` để fetch data nếu có thể dùng TanStack Query.

---

## Quy tắc form

Dùng:

```txt
react-hook-form
zod
@hookform/resolvers
```

Schema đặt trong:

```txt
features/<feature-name>/schemas/
```

Ví dụ:

```ts
import { z } from "zod";

export const createEmployeeSchema = z.object({
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(8, "Mật khẩu tối thiểu 8 ký tự"),
  full_name: z.string().min(1, "Vui lòng nhập họ tên"),
  department_id: z.coerce.number().min(1),
  position_id: z.coerce.number().min(1),
  phone: z.string().optional(),
});

export type CreateEmployeeFormValues = z.infer<typeof createEmployeeSchema>;
```

---

## Quy tắc auth

Auth nên tách trong feature:

```txt
features/auth/
├── api/
├── components/
├── hooks/
├── pages/
├── schemas/
└── types/
```

Auth store đặt ở:

```txt
src/stores/auth.store.ts
```

Store chỉ lưu những thứ cần thiết:

```txt
user
accessToken
isAuthenticated
login()
logout()
setUser()
```

Không lưu dữ liệu nhạy cảm không cần thiết.

Nếu backend dùng httpOnly cookie cho refresh token, frontend không cố đọc refresh token.

---

## Quy tắc permission

Frontend chỉ ẩn/hiện UI theo role.

Không coi frontend permission là bảo mật thật.

Tạo file:

```txt
src/constants/permissions.ts
```

Ví dụ:

```ts
export const permissions = {
  employees: {
    create: ["admin", "hr"],
    update: ["admin", "hr"],
    delete: ["admin"],
    read: ["admin", "hr"],
  },
  attendance: {
    readSelf: ["employee"],
    readAll: ["admin", "hr"],
  },
} as const;
```

Backend vẫn là nơi kiểm tra quyền cuối cùng.

---

## Quy tắc routing

Tạo router ở:

```txt
src/app/router.tsx
```

Ví dụ:

```tsx
import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { EmployeeListPage } from "@/features/employees/pages/EmployeeListPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <AppLayout />,
    children: [
      {
        path: "employees",
        element: <EmployeeListPage />,
      },
    ],
  },
]);
```

Route path nên đặt trong:

```txt
src/constants/routes.ts
```

---

## Quy tắc import

Dùng alias:

```ts
import { Button } from "@/components/ui/Button";
import { employeeApi } from "@/features/employees/api/employee.api";
```

Không dùng import dài kiểu:

```ts
import { Button } from "../../../components/ui/Button";
```

Nếu chưa có alias, cấu hình:

`tsconfig.json`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

`vite.config.ts`:

```ts
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

---

## Quy tắc TypeScript

Không dùng `any` trừ khi thật sự bắt buộc.

Ưu tiên:

```ts
type
interface
unknown thay vì any
Partial<T>
Pick<T>
Omit<T>
```

API response phải có type rõ ràng.

Ví dụ:

```ts
export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
```

---

## Quy tắc UI

UI component dùng chung đặt trong:

```txt
src/components/ui/
```

Ví dụ:

```txt
Button.tsx
Input.tsx
Select.tsx
Modal.tsx
Table.tsx
Badge.tsx
Pagination.tsx
Loading.tsx
```

Component nghiệp vụ không được đặt trong `components/ui`.

Ví dụ sai:

```txt
components/ui/EmployeeTable.tsx
```

Ví dụ đúng:

```txt
features/employees/components/EmployeeTable.tsx
```

---

## Quy tắc error handling

API error phải được xử lý ở hook hoặc page.

Hiển thị lỗi thân thiện cho người dùng.

Không để app crash vì response lỗi.

Ví dụ:

```tsx
if (isError) {
  return <div>Không thể tải danh sách nhân viên.</div>;
}
```

Không hiển thị raw stack trace cho user.

---

## Quy tắc loading state

Mỗi page gọi API phải có loading state.

Ví dụ:

```tsx
if (isLoading) {
  return <Loading />;
}
```

Không render bảng rỗng khi data vẫn đang loading.

---

## Quy tắc empty state

Nếu không có data, hiển thị message rõ ràng.

Ví dụ:

```tsx
if (!employees.length) {
  return <div>Chưa có nhân viên nào.</div>;
}
```

---

## Quy tắc đặt tên

Dùng PascalCase cho component:

```txt
EmployeeTable.tsx
EmployeeForm.tsx
LoginPage.tsx
```

Dùng camelCase cho function:

```txt
getEmployees
createEmployee
handleSubmit
```

Dùng kebab-case hoặc camelCase cho folder, nhưng phải thống nhất.

Khuyến nghị folder feature dùng kebab-case:

```txt
face-profiles
audit-logs
department-managers
```

---

## Quy tắc export

Mỗi feature nên có `index.ts`.

Ví dụ:

```ts
export * from "./pages/EmployeeListPage";
export * from "./pages/EmployeeCreatePage";
export * from "./types/employee.types";
```

Không export mọi thứ nếu không cần.

---

## Quy tắc không được làm

Không được:

1. Sửa backend.
2. Sửa migration.
3. Sửa database schema.
4. Sửa Docker backend.
5. Sửa `.env` backend.
6. Hard-code API URL trong component.
7. Gọi API trực tiếp trong component.
8. Dùng `any` bừa bãi.
9. Viết file quá dài.
10. Gom toàn bộ component vào một folder chung.
11. Tạo global state cho mọi thứ.
12. Dùng `useEffect` để fetch data khi có thể dùng TanStack Query.
13. Viết CSS inline quá nhiều.
14. Tự ý đổi endpoint backend.
15. Tự ý đổi response contract backend.

---

## Khi cần backend API contract

Nếu cần biết endpoint backend:

1. Được phép đọc file backend.
2. Không được sửa file backend.
3. Nếu contract chưa rõ, tạo type frontend dựa trên response hiện tại.
4. Nếu endpoint chưa tồn tại, tạo frontend với TODO rõ ràng.

Ví dụ TODO:

```ts
// TODO: Backend endpoint is not implemented yet.
// Expected endpoint: GET /api/v1/staff/employees
```

Không tự tạo hoặc sửa backend endpoint.

---

## Checklist trước khi hoàn thành task

Trước khi kết thúc, hãy kiểm tra:

```txt
[ ] Không sửa backend
[ ] Không sửa migration
[ ] Không sửa Docker backend
[ ] Không sửa .env backend
[ ] Code frontend chạy được
[ ] Không có TypeScript error
[ ] Component có props type rõ ràng
[ ] API call nằm trong api/
[ ] Data fetching nằm trong hooks/
[ ] Page chỉ ghép layout + component
[ ] Có loading state
[ ] Có error state
[ ] Có empty state nếu cần
[ ] Không dùng any bừa bãi
[ ] Không hard-code API URL
[ ] Không phá structure hiện tại
```

---

## Yêu cầu khi trả lời sau khi code

Sau khi hoàn thành code, hãy báo cáo ngắn gọn:

```txt
Đã làm:
- ...

Không đụng tới:
- backend
- migrations
- docker backend
- env backend

Cách chạy:
- ...

Ghi chú:
- ...
```

Nếu có file backend bị thay đổi ngoài ý muốn, phải rollback ngay trước khi kết thúc.

---

## Prompt ngắn để dùng trực tiếp với Codex

Bạn có thể dùng prompt này khi giao task:

```txt
Hãy viết frontend React + TypeScript cho project này theo file CODEX_FRONTEND_INSTRUCTIONS.md.

Chỉ được tạo/sửa code trong frontend.
Không được sửa api-service, ai-service, backend, migrations, docker backend hoặc env backend.

Dùng feature-based architecture.
API call đặt trong features/<feature>/api.
Data fetching dùng TanStack Query trong hooks.
Form dùng react-hook-form + zod.
Routing đặt trong src/app/router.tsx.
Shared UI đặt trong src/components/ui.
Layout đặt trong src/components/layout.

Nếu cần hiểu backend API, chỉ đọc backend để tham khảo, không sửa.
Nếu endpoint backend chưa có, tạo TODO ở frontend, không tự sửa backend.

Sau khi làm xong, báo cáo danh sách file frontend đã tạo/sửa và xác nhận không đụng backend.
```

