import React, { useEffect } from 'react';
import { ActivityIndicator, Text, TouchableOpacity, View, useColorScheme } from 'react-native';
import { DarkTheme, DefaultTheme, ThemeProvider, type ErrorBoundaryProps } from 'expo-router';
import { useAuthStore } from '@/stores/auth.store';
import AppTabs from '@/components/app-tabs';
import LoginScreen from '@/components/LoginScreen';
import { onSessionExpired } from '@/lib/session-events';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

export function ErrorBoundary({ retry }: ErrorBoundaryProps) {
  return (
    <View style={{ alignItems: 'center', backgroundColor: '#fff', flex: 1, gap: 10, justifyContent: 'center', padding: 28 }}>
      <Text style={{ color: '#0f172a', fontSize: 20, fontWeight: '800', textAlign: 'center' }}>Ứng dụng gặp sự cố</Text>
      <Text style={{ color: '#64748b', fontSize: 13, lineHeight: 19, textAlign: 'center' }}>Không thể hiển thị màn hình này. Dữ liệu của bạn không bị ảnh hưởng.</Text>
      <TouchableOpacity accessibilityRole="button" onPress={retry} style={{ backgroundColor: '#2563eb', borderRadius: 11, marginTop: 8, paddingHorizontal: 18, paddingVertical: 12 }}>
        <Text style={{ color: '#fff', fontSize: 14, fontWeight: '800' }}>Tải lại màn hình</Text>
      </TouchableOpacity>
    </View>
  );
}

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const { clearSession, isAuthenticated, isLoading, restoreSession } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(() => onSessionExpired(clearSession), [clearSession]);

  if (isLoading) {
    const isDark = colorScheme === 'dark';
    return (
      <View style={{
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: isDark ? '#000000' : '#ffffff'
      }}>
        <ActivityIndicator size="large" color={isDark ? '#ffffff' : '#000000'} />
      </View>
    );
  }

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <SafeAreaProvider>
        <StatusBar style="auto" />
        {isAuthenticated ? <AppTabs /> : <LoginScreen />}
      </SafeAreaProvider>
    </ThemeProvider>
  );
}
