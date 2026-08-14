import { Platform } from 'react-native';

// For Android emulator, localhost is 10.0.2.2.
// For iOS simulator, localhost is 127.0.0.1.
// For web development, it's 127.0.0.1.
// Change this to your server's LAN IP when testing on physical devices (e.g. http://192.168.1.50:8000/api/v1)
const getFallbackApiUrl = () => {
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000/api/v1';
  }
  return 'http://localhost:8000/api/v1';
};

export const APP_CONFIG = {
  API_BASE_URL: process.env.EXPO_PUBLIC_API_BASE_URL || getFallbackApiUrl(),
};
