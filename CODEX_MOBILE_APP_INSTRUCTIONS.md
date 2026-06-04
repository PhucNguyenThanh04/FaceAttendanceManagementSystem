# CODEX_MOBILE_APP_INSTRUCTIONS.md

## Mục tiêu

Bạn là coding agent phụ trách **mobile app** cho project `FaceAttendanceManagementSystem`.

Nhiệm vụ của bạn là viết mobile app chuẩn, dễ maintain, type-safe, theo kiến trúc feature-based.

Mobile app dùng cho hệ thống chấm công khuôn mặt, quản lý nhân viên, xem lịch sử chấm công, gửi đơn nghỉ phép, xem thông báo và cập nhật thông tin cá nhân.

**Tuyệt đối không thay đổi backend và không thay đổi frontend web.**

Backend gồm:

- `api-service`
- `ai-service`
- FastAPI business logic
- PostgreSQL models
- Redis logic
- Qdrant logic
- Alembic migrations
- Docker backend configs

Frontend web nếu đã có cũng không được chỉnh sửa trừ khi task yêu cầu rõ ràng.

Nếu cần hiểu API contract, chỉ được **đọc** backend hoặc frontend web để tham khảo, không được sửa.

---

## Phạm vi được phép chỉnh sửa

Chỉ được tạo/sửa file trong khu vực mobile app.

Nếu project đã có folder mobile, chỉ làm trong folder đó, ví dụ:

```txt
mobile/
mobile-app/
app-mobile/
react-native-app/
```

Nếu chưa có mobile app, hãy tạo folder:

```txt
mobile/
```

Stack mặc định khuyến nghị:

```txt
React Native + TypeScript + Expo
```

Nếu user hoặc project đã chọn React Native CLI, hãy giữ theo React Native CLI, không tự ý đổi sang Expo.

---

## Phạm vi KHÔNG được phép chỉnh sửa

Không được sửa, xóa, format, rename, move hoặc refactor bất kỳ file nào thuộc backend hoặc frontend web.

Các folder/file cấm chỉnh sửa:

```txt
api-service/
ai-service/
backend/
frontend/
web/
client/
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
Web frontend code
Docker backend config
```

Nếu cần thêm biến môi trường cho mobile, chỉ tạo/sửa:

```txt
mobile/.env
mobile/.env.example
```

Không sửa `.env` của backend hoặc frontend web.

---

## Nguyên tắc làm việc

Trước khi code, hãy kiểm tra cấu trúc project.

Nếu đã có mobile app:

1. Giữ nguyên stack hiện tại.
2. Không rewrite toàn bộ nếu không cần.
3. Follow convention đang có.
4. Chỉ cải thiện đúng phần được yêu cầu.
5. Không tự ý đổi navigation, state management hoặc UI library nếu app đã ổn định.

Nếu chưa có mobile app:

1. Tạo mobile app bằng React Native + TypeScript.
2. Ưu tiên Expo nếu không có yêu cầu native đặc biệt.
3. Dùng cấu trúc feature-based.
4. Chuẩn bị sẵn navigation, API client, auth flow, storage, permission camera và layout cơ bản.

---

## Stack mobile khuyến nghị

Ưu tiên:

```txt
React Native
TypeScript
Expo
Expo Router hoặc React Navigation
TanStack Query
Axios
React Hook Form
Zod
Zustand
Expo SecureStore
Expo Camera
Expo Image Picker nếu cần
```

Nếu dùng Expo:

```txt
expo
expo-router hoặc @react-navigation/native
expo-secure-store
expo-camera
expo-image-picker
```

Nếu dùng React Native CLI:

```txt
@react-navigation/native
react-native-keychain
react-native-vision-camera hoặc react-native-camera-kit
```

Không thêm dependency mới nếu chưa thật sự cần.

---

## File structure mobile chuẩn

Nếu tạo mới mobile app, dùng structure này:

```txt
mobile/
├── app/                         # nếu dùng Expo Router
│   ├── _layout.tsx
│   ├── index.tsx
│   ├── login.tsx
│   ├── (tabs)/
│   │   ├── _layout.tsx
│   │   ├── home.tsx
│   │   ├── attendance.tsx
│   │   ├── leave.tsx
│   │   └── profile.tsx
│   └── face-checkin.tsx
│
├── src/
│   ├── app/
│   │   ├── providers.tsx
│   │   └── query-client.ts
│   │
│   ├── assets/
│   │   ├── images/
│   │   └── icons/
│   │
│   ├── components/
│   │   ├── ui/
│   │   │   ├── AppButton.tsx
│   │   │   ├── AppInput.tsx
│   │   │   ├── AppText.tsx
│   │   │   ├── AppCard.tsx
│   │   │   ├── LoadingView.tsx
│   │   │   ├── ErrorView.tsx
│   │   │   └── EmptyState.tsx
│   │   │
│   │   └── layout/
│   │       ├── Screen.tsx
│   │       ├── AuthGuard.tsx
│   │       └── AppHeader.tsx
│   │
│   ├── features/
│   │   ├── auth/
│   │   ├── profile/
│   │   ├── employees/
│   │   ├── attendance/
│   │   ├── face-checkin/
│   │   ├── face-enrollment/
│   │   ├── leave/
│   │   ├── corrections/
│   │   ├── notifications/
│   │   └── settings/
│   │
│   ├── lib/
│   │   ├── axios.ts
│   │   ├── storage.ts
│   │   ├── permissions.ts
│   │   ├── date.ts
│   │   └── utils.ts
│   │
│   ├── stores/
│   │   └── auth.store.ts
│   │
│   ├── constants/
│   │   ├── routes.ts
│   │   ├── permissions.ts
│   │   └── config.ts
│   │
│   ├── types/
│   │   └── common.types.ts
│   │
│   └── styles/
│       ├── colors.ts
│       ├── spacing.ts
│       └── typography.ts
│
├── .env.example
├── app.json
├── package.json
├── tsconfig.json
└── README.md
```

Nếu không dùng Expo Router mà dùng React Navigation, dùng structure:

```txt
mobile/
├── src/
│   ├── navigation/
│   │   ├── RootNavigator.tsx
│   │   ├── AuthNavigator.tsx
│   │   ├── AppNavigator.tsx
│   │   └── TabNavigator.tsx
│   │
│   ├── screens/
│   ├── features/
│   ├── components/
│   ├── lib/
│   ├── stores/
│   ├── constants/
│   ├── types/
│   └── styles/
│
├── App.tsx
└── package.json
```

---

## Cấu trúc chuẩn cho mỗi feature

Mỗi feature nên có cấu trúc:

```txt
features/
└── attendance/
    ├── api/
    │   └── attendance.api.ts
    │
    ├── components/
    │   ├── AttendanceCard.tsx
    │   ├── AttendanceHistoryList.tsx
    │   └── AttendanceStatusBadge.tsx
    │
    ├── hooks/
    │   ├── useTodayAttendance.ts
    │   ├── useAttendanceHistory.ts
    │   └── useCreateAttendanceCorrection.ts
    │
    ├── screens/
    │   ├── AttendanceScreen.tsx
    │   └── AttendanceDetailScreen.tsx
    │
    ├── schemas/
    │   └── attendance.schema.ts
    │
    ├── types/
    │   └── attendance.types.ts
    │
    └── index.ts
```

Ý nghĩa:

```txt
api/          gọi backend
components/   UI riêng của feature
hooks/        data fetching, mutation, mobile logic
screens/      màn hình mobile
schemas/      validate form bằng zod
types/        TypeScript type/interface
index.ts      export gọn
```

---

## Feature nên có cho app chấm công

Với hệ thống của project này, mobile app nên chia feature như sau:

```txt
features/
├── auth/
├── profile/
├── attendance/
├── face-checkin/
├── face-enrollment/
├── leave/
├── corrections/
├── notifications/
└── settings/
```

Nếu mobile app dành cho HR/admin, có thể thêm:

```txt
features/
├── employees/
├── departments/
├── positions/
└── approvals/
```

Nếu mobile app chỉ dành cho nhân viên, không cần build CRUD admin đầy đủ.

---

## Quy tắc viết component mobile

Component phải:

1. Là function component.
2. Dùng TypeScript.
3. Không gọi API trực tiếp trong component.
4. Không chứa business logic phức tạp.
5. Không dùng `any` nếu có thể tránh.
6. Props phải có type rõ ràng.
7. Tách component UI dùng lại vào `components/ui`.
8. Tách component nghiệp vụ vào `features/<feature>/components`.

Ví dụ tốt:

```tsx
import { Pressable, Text, View } from "react-native";
import type { AttendanceRecord } from "../types/attendance.types";

type AttendanceCardProps = {
  record: AttendanceRecord;
  onPress?: (recordId: string) => void;
};

export function AttendanceCard({ record, onPress }: AttendanceCardProps) {
  return (
    <Pressable onPress={() => onPress?.(record.attendance_id)}>
      <View>
        <Text>{record.date}</Text>
        <Text>{record.status}</Text>
      </View>
    </Pressable>
  );
}
```

Không viết component kiểu:

```tsx
export default function Screen() {
  // gọi axios trực tiếp
  // xử lý token trực tiếp
  // xử lý business logic dài
  // render UI quá lớn
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
import type {
  AttendanceRecord,
  CheckInPayload,
  CheckInResponse,
} from "../types/attendance.types";

export const attendanceApi = {
  getTodayAttendance: async (): Promise<AttendanceRecord> => {
    const res = await api.get("/attendance/today");
    return res.data;
  },

  getAttendanceHistory: async (): Promise<AttendanceRecord[]> => {
    const res = await api.get("/attendance/history");
    return res.data;
  },

  checkIn: async (payload: CheckInPayload): Promise<CheckInResponse> => {
    const res = await api.post("/attendance/check-in", payload);
    return res.data;
  },
};
```

Không gọi `fetch`, `axios`, hoặc `api` trực tiếp trong screen/component.

---

## Axios config mobile

Tạo file:

```txt
src/lib/axios.ts
```

Ví dụ:

```ts
import axios from "axios";
import { getAccessToken } from "@/lib/storage";

export const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_BASE_URL,
  timeout: 30000,
});

api.interceptors.request.use(async (config) => {
  const token = await getAccessToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});
```

Mobile env:

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.10:8000/api/v1
```

Không dùng `localhost` cho mobile device thật.

Ghi chú:

```txt
- Android emulator có thể dùng http://10.0.2.2:8000
- iOS simulator có thể dùng http://localhost:8000
- Điện thoại thật phải dùng IP LAN của máy chạy backend
```

Không sửa `.env` backend.

---

## Quy tắc lưu token

Không lưu token bằng biến global.

Nếu dùng Expo, ưu tiên:

```txt
expo-secure-store
```

Tạo file:

```txt
src/lib/storage.ts
```

Ví dụ:

```ts
import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "access_token";

export async function saveAccessToken(token: string) {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
}

export async function getAccessToken() {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function removeAccessToken() {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
}
```

Nếu backend dùng httpOnly refresh token, mobile không cố đọc refresh token.

Nếu backend trả refresh token cho mobile, lưu refresh token bằng SecureStore hoặc Keychain, không lưu bằng AsyncStorage.

---

## Quy tắc auth

Auth nên tách trong:

```txt
features/auth/
├── api/
├── components/
├── hooks/
├── screens/
├── schemas/
└── types/
```

Auth store đặt ở:

```txt
src/stores/auth.store.ts
```

Auth store chỉ lưu:

```txt
user
accessToken nếu cần cache tạm
isAuthenticated
isLoading
login()
logout()
setUser()
restoreSession()
```

Không lưu password.

Không log token ra console.

Không hard-code tài khoản test trong source code.

---

## Quy tắc data fetching

Dùng TanStack Query cho server state.

Ví dụ:

```ts
import { useQuery } from "@tanstack/react-query";
import { attendanceApi } from "../api/attendance.api";

export function useTodayAttendance() {
  return useQuery({
    queryKey: ["attendance", "today"],
    queryFn: attendanceApi.getTodayAttendance,
  });
}
```

Mutation:

```ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { attendanceApi } from "../api/attendance.api";

export function useCheckIn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: attendanceApi.checkIn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attendance"] });
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

Ví dụ login schema:

```ts
import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Email không hợp lệ"),
  password: z.string().min(1, "Vui lòng nhập mật khẩu"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
```

---

## Quy tắc navigation

Nếu dùng Expo Router:

```txt
app/
├── _layout.tsx
├── login.tsx
├── face-checkin.tsx
└── (tabs)/
    ├── _layout.tsx
    ├── home.tsx
    ├── attendance.tsx
    ├── leave.tsx
    └── profile.tsx
```

Nếu dùng React Navigation:

```txt
src/navigation/
├── RootNavigator.tsx
├── AuthNavigator.tsx
├── AppNavigator.tsx
└── TabNavigator.tsx
```

Route name nên đặt trong:

```txt
src/constants/routes.ts
```

Ví dụ:

```ts
export const routes = {
  login: "/login",
  home: "/",
  attendance: "/attendance",
  faceCheckIn: "/face-checkin",
  leave: "/leave",
  profile: "/profile",
} as const;
```

---

## Quy tắc camera và face check-in

Feature chấm công khuôn mặt nên nằm trong:

```txt
features/face-checkin/
```

Cấu trúc:

```txt
features/
└── face-checkin/
    ├── components/
    │   ├── CameraPreview.tsx
    │   ├── FaceCaptureGuide.tsx
    │   └── CaptureButton.tsx
    │
    ├── hooks/
    │   ├── useCameraPermission.ts
    │   └── useFaceCheckIn.ts
    │
    ├── screens/
    │   └── FaceCheckInScreen.tsx
    │
    ├── api/
    │   └── face-checkin.api.ts
    │
    ├── types/
    │   └── face-checkin.types.ts
    │
    └── index.ts
```

Quy tắc:

1. Luôn xin quyền camera trước khi mở camera.
2. Nếu user từ chối quyền, hiển thị hướng dẫn mở quyền trong Settings.
3. Không upload ảnh liên tục không kiểm soát.
4. Không lưu ảnh khuôn mặt local nếu không cần.
5. Nếu phải lưu tạm, xóa sau khi gửi thành công hoặc thất bại.
6. Không log ảnh, base64 ảnh, embedding hoặc dữ liệu sinh trắc học.
7. Không xử lý anti-spoof hoặc embedding ở mobile nếu backend/ai-service đã làm.
8. Mobile chỉ capture ảnh và gửi lên API theo contract.

---

## Quy tắc face enrollment

Feature đăng ký khuôn mặt nên nằm trong:

```txt
features/face-enrollment/
```

Cấu trúc:

```txt
features/
└── face-enrollment/
    ├── api/
    │   └── face-enrollment.api.ts
    │
    ├── components/
    │   ├── EnrollmentProgress.tsx
    │   ├── CaptureInstruction.tsx
    │   └── EnrollmentCamera.tsx
    │
    ├── hooks/
    │   ├── useStartEnrollmentSession.ts
    │   ├── useUploadEnrollmentImage.ts
    │   ├── useCommitEnrollment.ts
    │   └── useCancelEnrollment.ts
    │
    ├── screens/
    │   ├── FaceEnrollmentStartScreen.tsx
    │   └── FaceEnrollmentCaptureScreen.tsx
    │
    ├── types/
    │   └── face-enrollment.types.ts
    │
    └── index.ts
```

Quy tắc:

1. Không tự tạo user ở mobile nếu backend đã có flow onboarding.
2. Không tự quyết định embedding hợp lệ ở mobile.
3. Chỉ hiển thị kết quả backend trả về.
4. Nếu backend yêu cầu 10 ảnh, mobile quản lý progress theo response backend.
5. Nếu session hết hạn, báo user bắt đầu lại.
6. Nếu cancel, gọi endpoint cancel session.
7. Nếu commit thành công, xóa ảnh tạm nếu có.

---

## Quy tắc upload ảnh

Khi gửi ảnh lên backend, ưu tiên `multipart/form-data`.

Ví dụ:

```ts
export async function uploadFaceImage(uri: string, sessionId: string) {
  const formData = new FormData();

  formData.append("session_id", sessionId);
  formData.append("image", {
    uri,
    name: "face.jpg",
    type: "image/jpeg",
  } as unknown as Blob);

  const res = await api.post("/face-profiles/enrollment/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return res.data;
}
```

Không convert ảnh sang base64 nếu không cần, vì base64 làm payload lớn hơn.

---

## Quy tắc location nếu dùng cho chấm công

Nếu app dùng GPS để kiểm tra vị trí chấm công:

1. Xin quyền location rõ ràng.
2. Chỉ lấy location khi user bấm check-in/check-out.
3. Không track background nếu không có yêu cầu rõ ràng.
4. Không lưu location local nếu không cần.
5. Không log tọa độ chính xác ra console.
6. Backend là nơi xác thực vị trí cuối cùng.

Feature location helper đặt trong:

```txt
src/lib/location.ts
```

---

## Quy tắc notification

Feature notification nằm trong:

```txt
features/notifications/
```

Nếu dùng push notification:

1. Không hard-code Expo push token.
2. Không log token production.
3. Gửi device token lên backend qua API nếu backend hỗ trợ.
4. Nếu backend chưa hỗ trợ, tạo TODO frontend, không sửa backend.
5. Xin quyền notification theo đúng UX.

---

## Quy tắc offline/cache

Không tự build offline phức tạp nếu chưa được yêu cầu.

Có thể dùng TanStack Query cache cho UX tốt hơn.

Không cho phép chấm công offline nếu backend chưa có flow xác thực offline.

Nếu cần offline mode, phải ghi TODO và không tự thay đổi backend.

---

## Quy tắc UI/UX mobile

Mỗi screen nên có:

```txt
loading state
error state
empty state nếu cần
pull-to-refresh nếu là danh sách
keyboard handling nếu có form
safe area handling
```

Dùng `SafeAreaView` hoặc wrapper `Screen`.

Ví dụ:

```tsx
import { SafeAreaView, ScrollView } from "react-native";

type ScreenProps = {
  children: React.ReactNode;
};

export function Screen({ children }: ScreenProps) {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <ScrollView keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}
```

Không để nội dung bị che bởi notch, status bar hoặc keyboard.

---

## Quy tắc styling

Có thể dùng một trong các hướng sau:

```txt
StyleSheet
NativeWind
Tamagui
React Native Paper
```

Nếu project đã có style system, giữ nguyên.

Nếu tạo mới, ưu tiên đơn giản:

```txt
StyleSheet + theme constants
```

Tạo:

```txt
src/styles/colors.ts
src/styles/spacing.ts
src/styles/typography.ts
```

Ví dụ:

```ts
export const colors = {
  primary: "#2563eb",
  danger: "#dc2626",
  text: "#111827",
  mutedText: "#6b7280",
  background: "#f9fafb",
  card: "#ffffff",
} as const;
```

Không hard-code màu lặp lại khắp app.

---

## Quy tắc TypeScript

Không dùng `any` trừ khi thật sự bắt buộc.

Ưu tiên:

```txt
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
export type ApiResponse<T> = {
  data: T;
  message?: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};
```

---

## Quy tắc import

Dùng alias:

```ts
import { AppButton } from "@/components/ui/AppButton";
import { attendanceApi } from "@/features/attendance/api/attendance.api";
```

Không dùng import dài kiểu:

```ts
import { AppButton } from "../../../components/ui/AppButton";
```

Nếu chưa có alias, cấu hình `tsconfig.json`:

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

Nếu dùng Expo, cấu hình Babel nếu cần.

---

## Quy tắc error handling

API error phải được xử lý thân thiện.

Không để app crash vì response lỗi.

Ví dụ:

```tsx
if (isError) {
  return <ErrorView message="Không thể tải dữ liệu chấm công." />;
}
```

Không hiển thị raw stack trace cho user.

Không log dữ liệu nhạy cảm.

---

## Quy tắc security/privacy mobile

Vì app có dữ liệu sinh trắc học và chấm công, phải tuân thủ:

1. Không log access token.
2. Không log refresh token.
3. Không log ảnh khuôn mặt.
4. Không log embedding.
5. Không log payload sinh trắc học.
6. Không lưu ảnh khuôn mặt local nếu không cần.
7. Không lưu password.
8. Không hard-code API key.
9. Không hard-code tài khoản test.
10. Không commit `.env` thật nếu có secret.
11. Không tự bypass TLS/SSL cho production.
12. Không dùng dữ liệu mock trong production screen nếu backend đã có API.

---

## Quy tắc role/permission

Mobile frontend chỉ ẩn/hiện UI theo role.

Không coi mobile permission là bảo mật thật.

Ví dụ:

```ts
export const permissions = {
  attendance: {
    checkIn: ["employee", "hr", "admin"],
    readSelf: ["employee", "hr", "admin"],
    readAll: ["hr", "admin"],
  },
  leave: {
    create: ["employee"],
    approve: ["hr", "admin"],
  },
  employees: {
    read: ["hr", "admin"],
    create: ["hr", "admin"],
    update: ["hr", "admin"],
  },
} as const;
```

Backend vẫn là nơi kiểm tra quyền cuối cùng.

---

## Quy tắc khi backend API chưa có

Nếu cần endpoint nhưng backend chưa có:

1. Không sửa backend.
2. Không tự tạo endpoint.
3. Tạo TODO rõ ràng trong mobile code.
4. Viết type dự kiến nếu cần.
5. Có thể mock tạm trong file riêng nếu user yêu cầu, nhưng phải đánh dấu rõ.

Ví dụ:

```ts
// TODO: Backend endpoint is not implemented yet.
// Expected endpoint: GET /api/v1/attendance/today
```

Không giấu TODO trong logic production.

---

## Quy tắc không được làm

Không được:

1. Sửa backend.
2. Sửa frontend web.
3. Sửa migration.
4. Sửa database schema.
5. Sửa Docker backend.
6. Sửa `.env` backend.
7. Hard-code API URL trong screen/component.
8. Gọi API trực tiếp trong screen/component.
9. Dùng `any` bừa bãi.
10. Viết file quá dài.
11. Gom toàn bộ component vào một folder chung.
12. Tạo global state cho mọi thứ.
13. Dùng `useEffect` để fetch data khi có thể dùng TanStack Query.
14. Lưu token bằng biến global.
15. Lưu password.
16. Log token, ảnh mặt, embedding hoặc dữ liệu nhạy cảm.
17. Tự ý đổi endpoint backend.
18. Tự ý đổi response contract backend.
19. Tự ý build offline check-in nếu backend chưa hỗ trợ.
20. Tự ý xử lý embedding/anti-spoof ở mobile nếu ai-service đã phụ trách.

---

## Checklist trước khi hoàn thành task

Trước khi kết thúc, hãy kiểm tra:

```txt
[ ] Chỉ sửa mobile app
[ ] Không sửa backend
[ ] Không sửa frontend web
[ ] Không sửa migration
[ ] Không sửa Docker backend
[ ] Không sửa .env backend
[ ] Code mobile chạy được
[ ] Không có TypeScript error
[ ] Component có props type rõ ràng
[ ] API call nằm trong features/<feature>/api
[ ] Data fetching nằm trong hooks
[ ] Screen chỉ ghép layout + component
[ ] Có loading state
[ ] Có error state
[ ] Có empty state nếu cần
[ ] Không dùng any bừa bãi
[ ] Không hard-code API URL trong screen
[ ] Không log dữ liệu nhạy cảm
[ ] Không lưu ảnh mặt local nếu không cần
[ ] Không phá structure hiện tại
```

---

## Yêu cầu khi trả lời sau khi code

Sau khi hoàn thành code, hãy báo cáo ngắn gọn:

```txt
Đã làm:
- ...

File mobile đã tạo/sửa:
- ...

Không đụng tới:
- backend
- frontend web
- migrations
- docker backend
- env backend

Cách chạy:
- ...

Ghi chú:
- ...
```

Nếu có file backend hoặc frontend web bị thay đổi ngoài ý muốn, phải rollback ngay trước khi kết thúc.

---

## Prompt ngắn để dùng trực tiếp với Codex

Bạn có thể dùng prompt này khi giao task:

```txt
Hãy viết mobile app React Native + TypeScript cho project này theo file CODEX_MOBILE_APP_INSTRUCTIONS.md.

Chỉ được tạo/sửa code trong mobile.
Không được sửa api-service, ai-service, backend, frontend web, migrations, docker backend hoặc env backend.

Nếu chưa có mobile app, tạo folder mobile với React Native + TypeScript + Expo.
Dùng feature-based architecture.
API call đặt trong features/<feature>/api.
Data fetching dùng TanStack Query trong hooks.
Form dùng react-hook-form + zod.
Auth token lưu bằng SecureStore.
Camera/face check-in đặt trong feature face-checkin.
Face enrollment đặt trong feature face-enrollment.
Shared UI đặt trong src/components/ui.
Layout wrapper đặt trong src/components/layout.

Nếu cần hiểu backend API, chỉ đọc backend để tham khảo, không sửa.
Nếu endpoint backend chưa có, tạo TODO ở mobile, không tự sửa backend.

Sau khi làm xong, báo cáo danh sách file mobile đã tạo/sửa và xác nhận không đụng backend/frontend web.
```

---

## Prompt cực ngắn

```txt
Làm mobile app theo CODEX_MOBILE_APP_INSTRUCTIONS.md. 
Chỉ sửa folder mobile. 
Không sửa backend, frontend web, migrations, docker hoặc env backend.
```
