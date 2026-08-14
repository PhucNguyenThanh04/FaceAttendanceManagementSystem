import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Image,
  useColorScheme,
} from 'react-native';
import { useAuthStore } from '@/stores/auth.store';
import { Colors } from '@/constants/theme';
import { Lock, User, Eye, EyeOff, ArrowLeft } from 'lucide-react-native';
import { api } from '@/lib/axios';
import { getApiErrorMessage } from '@/lib/api-error';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function LoginScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'unspecified' ? 'light' : scheme];
  const insets = useSafeAreaInsets();

  const { login, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [resetStep, setResetStep] = useState<'request' | 'verify' | 'confirm' | null>(null);
  const [otp, setOtp] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [resetSucceeded, setResetSucceeded] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      return;
    }
    await login(email, password);
  };

  const isDarkMode = scheme === 'dark';

  const handlePasswordReset = async () => {
    try {
      setResetLoading(true);
      setResetMessage(null);
      if (resetStep === 'request') {
        await api.post('/auth/password-reset/request-otp', {
          email: email.trim().toLowerCase(),
        });
        setResetStep('verify');
        setResetMessage('Mã OTP đã được gửi đến email của bạn.');
      } else if (resetStep === 'verify') {
        const response = await api.post('/auth/password-reset/verify-otp', {
          email: email.trim().toLowerCase(),
          otp,
        });
        setResetToken(response.data.reset_token);
        setResetStep('confirm');
        setResetMessage('OTP hợp lệ. Hãy đặt mật khẩu mới.');
      } else if (resetStep === 'confirm') {
        await api.post('/auth/password-reset/confirm', {
          new_password: newPassword,
          reset_token: resetToken,
        });
        setPassword('');
        setOtp('');
        setNewPassword('');
        setResetStep(null);
        setResetMessage(null);
        setResetSucceeded(true);
      }
    } catch (resetError) {
      setResetMessage(getApiErrorMessage(resetError, 'Không thể xử lý yêu cầu. Vui lòng thử lại.'));
    } finally {
      setResetLoading(false);
    }
  };

  if (resetStep) {
    const canSubmit =
      resetStep === 'request'
        ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())
        : resetStep === 'verify'
          ? /^\d{6}$/.test(otp)
          : newPassword.length >= 8 && /[A-Za-z]/.test(newPassword) && /\d/.test(newPassword);

    return (
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={[styles.container, { backgroundColor: colors.background }]}>
        <ScrollView
          contentContainerStyle={[styles.scrollContainer, { paddingBottom: insets.bottom + 24, paddingTop: insets.top + 24 }]}
          keyboardShouldPersistTaps="handled">
          <View style={styles.formSection}>
            <TouchableOpacity accessibilityRole="button" style={styles.backButton} onPress={() => setResetStep(null)}>
              <ArrowLeft size={18} color={colors.text} />
              <Text style={[styles.backText, { color: colors.text }]}>Quay lại đăng nhập</Text>
            </TouchableOpacity>
            <Text style={[styles.resetTitle, { color: colors.text }]}>Khôi phục mật khẩu</Text>
            <Text style={[styles.resetSubtitle, { color: colors.textSecondary }]}>
              {resetStep === 'request'
                ? 'Nhập email để nhận mã OTP.'
                : resetStep === 'verify'
                  ? 'Nhập mã OTP gồm 6 chữ số.'
                  : 'Mật khẩu mới cần ít nhất 8 ký tự, gồm chữ và số.'}
            </Text>
            {resetMessage ? (
              <View style={styles.infoContainer}>
                <Text style={styles.infoText}>{resetMessage}</Text>
              </View>
            ) : null}
            {resetStep === 'request' ? (
              <TextInput
                autoCapitalize="none"
                autoComplete="email"
                keyboardType="email-address"
                onChangeText={setEmail}
                placeholder="nhanvien@congty.vn"
                placeholderTextColor={colors.textSecondary}
                style={[styles.resetInput, { backgroundColor: colors.backgroundElement, color: colors.text }]}
                value={email}
              />
            ) : null}
            {resetStep === 'verify' ? (
              <TextInput
                keyboardType="number-pad"
                autoComplete="one-time-code"
                maxLength={6}
                onChangeText={setOtp}
                placeholder="000000"
                placeholderTextColor={colors.textSecondary}
                style={[styles.resetInput, { backgroundColor: colors.backgroundElement, color: colors.text }]}
                value={otp}
              />
            ) : null}
            {resetStep === 'confirm' ? (
              <TextInput
                onChangeText={setNewPassword}
                autoComplete="new-password"
                placeholder="Mật khẩu mới"
                placeholderTextColor={colors.textSecondary}
                secureTextEntry
                style={[styles.resetInput, { backgroundColor: colors.backgroundElement, color: colors.text }]}
                value={newPassword}
              />
            ) : null}
            <TouchableOpacity
              accessibilityRole="button"
              disabled={!canSubmit || resetLoading}
              onPress={handlePasswordReset}
              style={[
                styles.loginButton,
                { backgroundColor: isDarkMode ? '#3b82f6' : '#2563eb' },
                (!canSubmit || resetLoading) && styles.disabledButton,
              ]}>
              {resetLoading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.loginButtonText}>
                  {resetStep === 'request' ? 'Gửi OTP' : resetStep === 'verify' ? 'Xác minh OTP' : 'Đặt mật khẩu mới'}
                </Text>
              )}
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={[styles.container, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={[styles.scrollContainer, { paddingBottom: insets.bottom + 24, paddingTop: insets.top + 24 }]}
        keyboardShouldPersistTaps="handled">
        <View style={styles.headerSection}>
          <Image
            source={require('@/assets/images/icon.png')}
            style={styles.logo}
            resizeMode="contain"
          />
          <Text style={[styles.title, { color: colors.text }]}>Hệ thống Chấm công</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Dành cho Nhân viên — Xác thực khuôn mặt AI
          </Text>
        </View>

        <View style={styles.formSection}>
          {resetSucceeded ? (
            <View accessibilityLiveRegion="polite" style={styles.successContainer}>
              <Text style={styles.successText}>Mật khẩu đã được đặt lại. Bạn có thể đăng nhập ngay.</Text>
            </View>
          ) : null}
          {error ? (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Email đăng nhập</Text>
          <View style={[styles.inputContainer, { backgroundColor: colors.backgroundElement, borderColor: colors.backgroundSelected }]}>
            <User size={20} color={colors.textSecondary} style={styles.inputIcon} />
            <TextInput
              style={[styles.input, { color: colors.text }]}
              placeholder="nhanvien@congty.vn"
              placeholderTextColor={colors.textSecondary}
              value={email}
              onChangeText={(text) => {
                setEmail(text);
                clearError();
              }}
              autoCapitalize="none"
              autoComplete="email"
              autoCorrect={false}
              keyboardType="email-address"
              returnKeyType="next"
            />
          </View>

          {/* Password Input */}
          <Text style={[styles.inputLabel, { color: colors.textSecondary, marginTop: 16 }]}>Mật khẩu</Text>
          <View style={[styles.inputContainer, { backgroundColor: colors.backgroundElement, borderColor: colors.backgroundSelected }]}>
            <Lock size={20} color={colors.textSecondary} style={styles.inputIcon} />
            <TextInput
              style={[styles.input, { color: colors.text }]}
              placeholder="Nhập mật khẩu..."
              placeholderTextColor={colors.textSecondary}
              value={password}
              onChangeText={(text) => {
                setPassword(text);
                clearError();
              }}
              secureTextEntry={!showPassword}
              autoComplete="current-password"
              autoCapitalize="none"
              autoCorrect={false}
              onSubmitEditing={handleLogin}
              returnKeyType="done"
            />
            <TouchableOpacity
              accessibilityLabel={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
              accessibilityRole="button"
              onPress={() => setShowPassword(!showPassword)}
              style={styles.eyeIcon}>
              {showPassword ? (
                <EyeOff size={20} color={colors.textSecondary} />
              ) : (
                <Eye size={20} color={colors.textSecondary} />
              )}
            </TouchableOpacity>
          </View>

          {/* Submit Button */}
          <TouchableOpacity
            accessibilityRole="button"
            style={[
              styles.loginButton,
              { backgroundColor: isDarkMode ? '#3b82f6' : '#2563eb' },
              (!email.trim() || !password.trim() || isLoading) && styles.disabledButton,
            ]}
            onPress={handleLogin}
            disabled={!email.trim() || !password.trim() || isLoading}>
            {isLoading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.loginButtonText}>Đăng nhập</Text>
            )}
          </TouchableOpacity>
          <TouchableOpacity
            accessibilityRole="button"
            onPress={() => {
              setResetSucceeded(false);
              setResetMessage(null);
              setResetStep('request');
            }}
            style={styles.forgotButton}>
            <Text style={[styles.forgotText, { color: isDarkMode ? '#60a5fa' : '#2563eb' }]}>
              Quên mật khẩu?
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.footerSection}>
          <Text style={[styles.footerText, { color: colors.textSecondary }]}>
            Gặp sự cố? Liên hệ phòng Nhân sự (HR) để được hỗ trợ.
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  headerSection: {
    alignItems: 'center',
    marginBottom: 40,
  },
  logo: {
    width: 90,
    height: 90,
    marginBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  formSection: {
    width: '100%',
    maxWidth: 450,
    alignSelf: 'center',
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    height: 52,
  },
  inputIcon: {
    marginRight: 10,
  },
  input: {
    flex: 1,
    height: '100%',
    fontSize: 15,
  },
  eyeIcon: {
    padding: 4,
  },
  loginButton: {
    height: 52,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 28,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  disabledButton: {
    opacity: 0.6,
  },
  loginButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  errorContainer: {
    backgroundColor: '#fee2e2',
    borderWidth: 1,
    borderColor: '#fca5a5',
    padding: 12,
    borderRadius: 10,
    marginBottom: 20,
  },
  errorText: {
    color: '#dc2626',
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  footerSection: {
    marginTop: 50,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 13,
    textAlign: 'center',
  },
  forgotButton: {
    alignItems: 'center',
    paddingVertical: 14,
  },
  forgotText: {
    fontSize: 14,
    fontWeight: '700',
  },
  backButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    flexDirection: 'row',
    gap: 7,
    marginBottom: 28,
  },
  backText: {
    fontSize: 14,
    fontWeight: '700',
  },
  resetTitle: {
    fontSize: 25,
    fontWeight: '800',
  },
  resetSubtitle: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 22,
    marginTop: 7,
  },
  resetInput: {
    borderRadius: 12,
    fontSize: 15,
    minHeight: 52,
    paddingHorizontal: 14,
  },
  infoContainer: {
    backgroundColor: '#dbeafe',
    borderRadius: 10,
    marginBottom: 16,
    padding: 12,
  },
  infoText: {
    color: '#1d4ed8',
    fontSize: 13,
  },
  successContainer: {
    backgroundColor: '#dcfce7',
    borderColor: '#86efac',
    borderRadius: 10,
    borderWidth: 1,
    marginBottom: 20,
    padding: 12,
  },
  successText: {
    color: '#166534',
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
  },
});
