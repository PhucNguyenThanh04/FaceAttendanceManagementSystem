import { create } from 'zustand';
import { api } from '@/lib/axios';
import {
  saveAccessToken,
  saveRefreshToken,
  saveUserInfo,
  saveEmployeeInfo,
  getUserInfo,
  getEmployeeInfo,
  clearAllStorage,
  getAccessToken,
} from '@/lib/storage';
import type { AuthUser, Employee } from '@/types/api';
import { getApiErrorMessage } from '@/lib/api-error';

interface AuthState {
  user: AuthUser | null;
  employee: Employee | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  clearSession: () => Promise<void>;
  restoreSession: () => Promise<void>;
  updateEmployee: (employee: Employee) => Promise<void>;
  updateUser: (user: AuthUser) => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  employee: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  clearError: () => set({ error: null }),

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      // 1. Call login endpoint
      const response = await api.post('/auth/login', { email: email.trim().toLowerCase(), password });
      const { access_token, refresh_token } = response.data;

      // 2. Save tokens to secure storage
      await saveAccessToken(access_token);
      await saveRefreshToken(refresh_token);

      // 3. Set temp authorization header to fetch user info
      api.defaults.headers.common.Authorization = `Bearer ${access_token}`;

      // 4. Fetch user info
      const meResponse = await api.get('/auth/me');
      const user = meResponse.data;
      if (user.role_name !== 'employee') {
        await clearAllStorage();
        delete api.defaults.headers.common.Authorization;
        set({
          isLoading: false,
          error: 'Ứng dụng mobile chỉ dành cho tài khoản nhân viên.',
        });
        return false;
      }

      // 5. Fetch employee info
      let employee: Employee | null = null;
      try {
        const empResponse = await api.get('/employees/me');
        employee = empResponse.data;
      } catch {}

      if (!employee) {
        await clearAllStorage();
        delete api.defaults.headers.common.Authorization;
        set({
          isLoading: false,
          error: 'Tài khoản chưa được liên kết với hồ sơ nhân viên. Vui lòng liên hệ HR.',
        });
        return false;
      }

      // 6. Save data to storage
      await saveUserInfo(user);
      if (employee) {
        await saveEmployeeInfo(employee);
      }

      set({
        user,
        employee,
        isAuthenticated: true,
        isLoading: false,
      });
      return true;
    } catch (err: unknown) {
      const errMsg = getApiErrorMessage(
        err,
        'Đăng nhập thất bại. Vui lòng kiểm tra lại tài khoản và mật khẩu.',
      );
      set({ isLoading: false, error: errMsg });
      return false;
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      // Try to call logout on backend (best effort)
      await api.post('/auth/logout');
    } catch {} finally {
      // Clean up local client state
      await clearAllStorage();
      delete api.defaults.headers.common.Authorization;
      set({
        user: null,
        employee: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  clearSession: async () => {
    await clearAllStorage();
    delete api.defaults.headers.common.Authorization;
    set({
      user: null,
      employee: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  },

  restoreSession: async () => {
    set({ isLoading: true });
    try {
      const token = await getAccessToken();
      if (!token) {
        set({ isLoading: false, isAuthenticated: false });
        return;
      }

      // Restore data from storage first for fast loading
      const cachedUser = await getUserInfo();
      const cachedEmp = await getEmployeeInfo();

      if (cachedUser && cachedEmp) {
        set({
          user: cachedUser,
          employee: cachedEmp,
          isAuthenticated: true,
        });
      }

      // Verify token with backend by calling /auth/me
      const meResponse = await api.get('/auth/me');
      const user = meResponse.data;
      if (user.role_name !== 'employee') {
        throw new Error('Mobile app only supports employee accounts');
      }
      await saveUserInfo(user);

      let employee: Employee | null = null;
      try {
        const empResponse = await api.get('/employees/me');
        const fetchedEmployee = empResponse.data as Employee;
        employee = fetchedEmployee;
        await saveEmployeeInfo(fetchedEmployee);
      } catch {}

      if (!employee) throw new Error('Employee profile is not linked');

      set({
        user,
        employee,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      await clearAllStorage();
      set({
        user: null,
        employee: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  updateEmployee: async (employee: Employee) => {
    await saveEmployeeInfo(employee);
    set({ employee });
  },

  updateUser: async (user: AuthUser) => {
    await saveUserInfo(user);
    set({ user });
  },
}));
