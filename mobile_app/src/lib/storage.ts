import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import type { AuthUser, Employee } from '@/types/api';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_INFO_KEY = 'user_info';
const EMPLOYEE_INFO_KEY = 'employee_info';

const isWeb = Platform.OS === 'web';

export async function saveAccessToken(token: string) {
  if (isWeb) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
  }
}

export async function getAccessToken(): Promise<string | null> {
  if (isWeb) {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } else {
    try {
      return await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
    } catch {
      return null;
    }
  }
}

export async function removeAccessToken() {
  if (isWeb) {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  } else {
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  }
}

export async function saveRefreshToken(token: string) {
  if (isWeb) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
  }
}

export async function getRefreshToken(): Promise<string | null> {
  if (isWeb) {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } else {
    try {
      return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
    } catch {
      return null;
    }
  }
}

export async function removeRefreshToken() {
  if (isWeb) {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } else {
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  }
}

export async function saveUserInfo(user: AuthUser) {
  const userStr = JSON.stringify(user);
  if (isWeb) {
    localStorage.setItem(USER_INFO_KEY, userStr);
  } else {
    await SecureStore.setItemAsync(USER_INFO_KEY, userStr);
  }
}

export async function getUserInfo(): Promise<AuthUser | null> {
  let userStr: string | null = null;
  if (isWeb) {
    userStr = localStorage.getItem(USER_INFO_KEY);
  } else {
    try {
      userStr = await SecureStore.getItemAsync(USER_INFO_KEY);
    } catch {}
  }
  try {
    return userStr ? (JSON.parse(userStr) as AuthUser) : null;
  } catch {
    await removeUserInfo();
    return null;
  }
}

export async function removeUserInfo() {
  if (isWeb) {
    localStorage.removeItem(USER_INFO_KEY);
  } else {
    await SecureStore.deleteItemAsync(USER_INFO_KEY);
  }
}

export async function saveEmployeeInfo(employee: Employee) {
  const empStr = JSON.stringify(employee);
  if (isWeb) {
    localStorage.setItem(EMPLOYEE_INFO_KEY, empStr);
  } else {
    await SecureStore.setItemAsync(EMPLOYEE_INFO_KEY, empStr);
  }
}

export async function getEmployeeInfo(): Promise<Employee | null> {
  let empStr: string | null = null;
  if (isWeb) {
    empStr = localStorage.getItem(EMPLOYEE_INFO_KEY);
  } else {
    try {
      empStr = await SecureStore.getItemAsync(EMPLOYEE_INFO_KEY);
    } catch {}
  }
  try {
    return empStr ? (JSON.parse(empStr) as Employee) : null;
  } catch {
    await removeEmployeeInfo();
    return null;
  }
}

export async function removeEmployeeInfo() {
  if (isWeb) {
    localStorage.removeItem(EMPLOYEE_INFO_KEY);
  } else {
    await SecureStore.deleteItemAsync(EMPLOYEE_INFO_KEY);
  }
}

export async function clearAllStorage() {
  await removeAccessToken();
  await removeRefreshToken();
  await removeUserInfo();
  await removeEmployeeInfo();
}
