import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  useColorScheme,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Image } from 'expo-image';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  BriefcaseBusiness,
  Camera,
  Fingerprint,
  KeyRound,
  LogOut,
  Mail,
  MapPin,
  Phone,
  Save,
  Eye,
  EyeOff,
  Pencil,
  UserRound,
  X,
} from 'lucide-react-native';
import { useFocusEffect } from 'expo-router';

import { APP_CONFIG } from '@/constants/config';
import { Colors } from '@/constants/theme';
import { api } from '@/lib/axios';
import { useAuthStore } from '@/stores/auth.store';
import type { AuthUser, Employee, FaceProfile } from '@/types/api';
import { getApiErrorMessage } from '@/lib/api-error';
import { DateTimeField } from '@/components/ui/date-time-field';

const faceLabels: Record<FaceProfile['status'], string> = {
  active: 'Đang hoạt động',
  failed: 'Đăng ký thất bại',
  pending: 'Đang chờ xử lý',
  revoked: 'Đã bị thu hồi',
};

const genderLabels: Record<NonNullable<Employee['gender']>, string> = {
  female: 'Nữ',
  male: 'Nam',
  other: 'Khác',
};

export default function ProfileScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'unspecified' ? 'light' : scheme];
  const isDark = scheme === 'dark';
  const insets = useSafeAreaInsets();
  const { employee, user, logout, updateEmployee, updateUser } = useAuthStore();
  const [email, setEmail] = useState(user?.email ?? '');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [faceProfile, setFaceProfile] = useState<FaceProfile | null>(null);
  const [loadingFace, setLoadingFace] = useState(false);
  const [savingEmail, setSavingEmail] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [profileModalVisible, setProfileModalVisible] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [gender, setGender] = useState<Employee['gender']>(null);

  const fetchFaceProfile = useCallback(async () => {
    if (!employee) return;
    try {
      setLoadingFace(true);
      const response = await api.get<FaceProfile>(
        `/face-profiles/employee/${employee.employee_id}`,
      );
      setFaceProfile(response.data);
    } catch {
      setFaceProfile(null);
    } finally {
      setLoadingFace(false);
    }
  }, [employee]);

  useFocusEffect(useCallback(() => { fetchFaceProfile(); }, [fetchFaceProfile]));

  const handlePickAvatar = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Cần quyền truy cập', 'Hãy cho phép ứng dụng đọc thư viện ảnh.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      allowsEditing: true,
      aspect: [1, 1],
      mediaTypes: ['images'],
      quality: 0.75,
    });
    if (result.canceled || !result.assets[0]) return;

    try {
      setUploadingAvatar(true);
      const asset = result.assets[0];
      const formData = new FormData();
      formData.append('file', {
        name: asset.fileName ?? 'avatar.jpg',
        type: asset.mimeType ?? 'image/jpeg',
        uri: asset.uri,
      } as unknown as Blob);
      const uploadResponse = await api.post<{ image_url: string }>('/upload/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const profileResponse = await api.patch<Employee>('/employees/me', {
        avatar_url: uploadResponse.data.image_url,
      });
      await updateEmployee(profileResponse.data);
      Alert.alert('Đã cập nhật ảnh', 'Ảnh đại diện đã được đồng bộ với hồ sơ của bạn.');
    } catch (error) {
      Alert.alert('Không thể tải ảnh', getApiErrorMessage(error, 'Vui lòng thử lại.'));
    } finally {
      setUploadingAvatar(false);
    }
  };

  const handleOpenProfileEditor = () => {
    if (!employee) return;
    setPhone(employee.phone ?? '');
    setAddress(employee.address ?? '');
    setDateOfBirth(employee.date_of_birth ?? '');
    setGender(employee.gender);
    setProfileModalVisible(true);
  };

  const handleUpdateProfile = async () => {
    if (!employee) return;
    const normalizedPhone = phone.trim().replace(/[\s.-]/g, '');
    if (normalizedPhone && !/^\+?[0-9]{8,15}$/.test(normalizedPhone)) {
      Alert.alert('Số điện thoại chưa hợp lệ', 'Hãy nhập từ 8 đến 15 chữ số.');
      return;
    }

    try {
      setSavingProfile(true);
      const response = await api.patch<Employee>('/employees/me', {
        address: address.trim() || null,
        date_of_birth: dateOfBirth || null,
        gender,
        phone: normalizedPhone || null,
      });
      await updateEmployee(response.data);
      setProfileModalVisible(false);
      Alert.alert('Đã cập nhật', 'Thông tin cá nhân của bạn đã được lưu.');
    } catch (error) {
      Alert.alert('Không thể cập nhật hồ sơ', getApiErrorMessage(error));
    } finally {
      setSavingProfile(false);
    }
  };

  const handleUpdateEmail = async () => {
    if (!user || !email.trim()) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      Alert.alert('Email chưa hợp lệ', 'Vui lòng kiểm tra lại địa chỉ email.');
      return;
    }
    try {
      setSavingEmail(true);
      const response = await api.patch<AuthUser>(`/users/${user.user_id}`, {
        email: email.trim().toLowerCase(),
      });
      await updateUser(response.data);
      Alert.alert('Thành công', 'Email đăng nhập đã được cập nhật.');
    } catch (error) {
      Alert.alert('Không thể cập nhật', getApiErrorMessage(error, 'Vui lòng thử lại.'));
    } finally {
      setSavingEmail(false);
    }
  };

  const handleChangePassword = async () => {
    if (!oldPassword || !newPassword || !confirmPassword) {
      Alert.alert('Thiếu thông tin', 'Vui lòng nhập đủ ba trường mật khẩu.');
      return;
    }
    if (newPassword !== confirmPassword) {
      Alert.alert('Mật khẩu không khớp', 'Hai lần nhập mật khẩu mới phải giống nhau.');
      return;
    }
    if (newPassword.length < 8 || !/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
      Alert.alert('Mật khẩu chưa đủ mạnh', 'Cần ít nhất 8 ký tự, gồm chữ và số.');
      return;
    }
    try {
      setSavingPassword(true);
      await api.post('/auth/change-password', {
        new_password: newPassword,
        old_password: oldPassword,
      });
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      Alert.alert('Thành công', 'Mật khẩu đã được thay đổi.');
    } catch (error) {
      Alert.alert('Không thể đổi mật khẩu', getApiErrorMessage(error, 'Vui lòng thử lại.'));
    } finally {
      setSavingPassword(false);
    }
  };

  const avatarSource = () => {
    if (!employee?.avatar_url) return require('@/assets/images/icon.png');
    if (/^https?:\/\//.test(employee.avatar_url)) return { uri: employee.avatar_url };
    return {
      uri: `${APP_CONFIG.API_BASE_URL.replace(/\/api\/v1\/?$/, '')}${employee.avatar_url}`,
    };
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={[styles.content, { paddingTop: insets.top + 14 }]}
      keyboardShouldPersistTaps="handled">
      <View style={styles.profileHeader}>
        <TouchableOpacity onPress={handlePickAvatar} disabled={uploadingAvatar}>
          <Image contentFit="cover" source={avatarSource()} style={styles.avatar} transition={180} />
          <View style={styles.avatarAction}>
            {uploadingAvatar ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Camera color="#fff" size={16} />
            )}
          </View>
        </TouchableOpacity>
        <Text style={[styles.name, { color: colors.text }]}>
          {employee?.full_name ?? 'Nhân viên'}
        </Text>
        <Text style={[styles.code, { color: colors.textSecondary }]}>
          {employee?.employee_code ?? 'Chưa liên kết hồ sơ'}
        </Text>
      </View>

      <View style={[styles.section, { backgroundColor: colors.backgroundElement }]}> 
        <View style={styles.sectionTitleRow}>
          <Text style={[styles.sectionTitle, { color: colors.text }]}>Hồ sơ nhân viên</Text>
          <TouchableOpacity
            accessibilityLabel="Chỉnh sửa hồ sơ cá nhân"
            accessibilityRole="button"
            onPress={handleOpenProfileEditor}
            style={styles.editProfileButton}>
            <Pencil color="#2563eb" size={15} />
            <Text style={styles.editProfileText}>Chỉnh sửa</Text>
          </TouchableOpacity>
        </View>
        <InfoRow
          icon={<BriefcaseBusiness size={18} color="#2563eb" />}
          label="Ngày bắt đầu làm việc"
          value={employee?.hire_date ? new Date(`${employee.hire_date}T00:00:00`).toLocaleDateString('vi-VN') : 'Chưa cập nhật'}
          colors={colors}
        />
        <InfoRow icon={<Phone size={18} color="#059669" />} label="Điện thoại" value={employee?.phone ?? 'Chưa cập nhật'} colors={colors} />
        <InfoRow icon={<MapPin size={18} color="#d97706" />} label="Địa chỉ" value={employee?.address ?? 'Chưa cập nhật'} colors={colors} />
        <InfoRow
          icon={<UserRound size={18} color="#7c3aed" />}
          label="Ngày sinh / Giới tính"
          value={`${employee?.date_of_birth ? new Date(`${employee.date_of_birth}T00:00:00`).toLocaleDateString('vi-VN') : 'Chưa cập nhật'} · ${employee?.gender ? genderLabels[employee.gender] : 'Chưa cập nhật'}`}
          colors={colors}
        />
        <InfoRow
          icon={<Fingerprint size={18} color={faceProfile?.status === 'active' ? '#059669' : '#d97706'} />}
          label="Hồ sơ khuôn mặt"
          value={loadingFace ? 'Đang kiểm tra...' : faceProfile ? faceLabels[faceProfile.status] : 'Chưa đăng ký'}
          colors={colors}
        />
      </View>

      <View style={[styles.section, { backgroundColor: colors.backgroundElement }]}>
        <View style={styles.sectionHeading}>
          <Mail size={19} color="#2563eb" />
          <Text style={[styles.sectionTitle, { color: colors.text }]}>Email đăng nhập</Text>
        </View>
        <TextInput
          autoCapitalize="none"
          keyboardType="email-address"
          onChangeText={setEmail}
          placeholder="email@congty.vn"
          placeholderTextColor={colors.textSecondary}
          style={[styles.input, { backgroundColor: colors.background, color: colors.text }]}
          value={email}
        />
        <TouchableOpacity
          disabled={savingEmail || email.trim().toLowerCase() === user?.email.toLowerCase()}
          onPress={handleUpdateEmail}
          style={[styles.button, styles.secondaryButton, { opacity: savingEmail ? 0.6 : 1 }]}>
          {savingEmail ? <ActivityIndicator color="#2563eb" /> : <Save size={17} color="#2563eb" />}
          <Text style={styles.secondaryButtonText}>Lưu email</Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.section, { backgroundColor: colors.backgroundElement }]}>
        <View style={styles.sectionHeading}>
          <KeyRound size={19} color="#7c3aed" />
          <Text style={[styles.sectionTitle, { color: colors.text }]}>Đổi mật khẩu</Text>
        </View>
        <PasswordInput label="Mật khẩu hiện tại" value={oldPassword} onChangeText={setOldPassword} colors={colors} />
        <PasswordInput label="Mật khẩu mới" value={newPassword} onChangeText={setNewPassword} colors={colors} />
        <PasswordInput label="Xác nhận mật khẩu mới" value={confirmPassword} onChangeText={setConfirmPassword} colors={colors} />
        <TouchableOpacity
          disabled={savingPassword}
          onPress={handleChangePassword}
          style={[styles.button, { backgroundColor: isDark ? '#6d28d9' : '#7c3aed' }]}>
          {savingPassword ? <ActivityIndicator color="#fff" /> : <KeyRound size={17} color="#fff" />}
          <Text style={styles.buttonText}>Cập nhật mật khẩu</Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity
        accessibilityRole="button"
        onPress={() =>
          Alert.alert('Đăng xuất', 'Bạn muốn kết thúc phiên đăng nhập?', [
            { text: 'Ở lại', style: 'cancel' },
            { text: 'Đăng xuất', style: 'destructive', onPress: logout },
          ])
        }
        style={styles.logoutButton}>
        <LogOut color="#dc2626" size={19} />
        <Text style={styles.logoutText}>Đăng xuất</Text>
      </TouchableOpacity>

      <Modal
        animationType="slide"
        onRequestClose={() => !savingProfile && setProfileModalVisible(false)}
        presentationStyle="pageSheet"
        visible={profileModalVisible}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={[styles.modalContainer, { backgroundColor: colors.background, paddingTop: insets.top + 8 }]}> 
          <View style={[styles.modalHeader, { borderBottomColor: colors.backgroundElement }]}> 
            <View style={styles.modalHeaderCopy}>
              <Text style={[styles.modalEyebrow, { color: colors.textSecondary }]}>HỒ SƠ CÁ NHÂN</Text>
              <Text style={[styles.modalTitle, { color: colors.text }]}>Cập nhật thông tin</Text>
            </View>
            <TouchableOpacity
              accessibilityLabel="Đóng"
              accessibilityRole="button"
              disabled={savingProfile}
              onPress={() => setProfileModalVisible(false)}
              style={styles.modalCloseButton}>
              <X color={colors.text} size={22} />
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={[styles.modalContent, { paddingBottom: insets.bottom + 30 }]} keyboardShouldPersistTaps="handled">
            <Text style={[styles.formHint, { color: colors.textSecondary }]}>Bạn có thể tự cập nhật thông tin liên hệ và nhân khẩu học. Thông tin công việc do HR quản lý.</Text>

            <View style={styles.inputGroup}>
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Số điện thoại</Text>
              <TextInput
                autoComplete="tel"
                keyboardType="phone-pad"
                maxLength={18}
                onChangeText={setPhone}
                placeholder="Ví dụ: 0912345678"
                placeholderTextColor={colors.textSecondary}
                style={[styles.input, { backgroundColor: colors.backgroundElement, color: colors.text }]}
                value={phone}
              />
            </View>

            <DateTimeField
              allowClear
              label="Ngày sinh"
              maximumDate={new Date()}
              mode="date"
              onChange={setDateOfBirth}
              value={dateOfBirth}
            />

            <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Giới tính</Text>
            <View style={styles.genderRow}>
              {[
                { label: 'Nam', value: 'male' as const },
                { label: 'Nữ', value: 'female' as const },
                { label: 'Khác', value: 'other' as const },
                { label: 'Không cung cấp', value: null },
              ].map((option) => {
                const selected = gender === option.value;
                return (
                  <TouchableOpacity
                    accessibilityRole="radio"
                    accessibilityState={{ selected }}
                    key={option.label}
                    onPress={() => setGender(option.value)}
                    style={[
                      styles.genderOption,
                      { backgroundColor: colors.backgroundElement, borderColor: selected ? '#2563eb' : colors.backgroundSelected },
                    ]}>
                    <Text style={[styles.genderOptionText, { color: selected ? '#2563eb' : colors.text }]}>{option.label}</Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            <View style={styles.inputGroup}>
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Địa chỉ</Text>
              <TextInput
                maxLength={500}
                multiline
                numberOfLines={4}
                onChangeText={setAddress}
                placeholder="Nhập địa chỉ hiện tại"
                placeholderTextColor={colors.textSecondary}
                style={[styles.addressInput, { backgroundColor: colors.backgroundElement, color: colors.text }]}
                textAlignVertical="top"
                value={address}
              />
            </View>

            <TouchableOpacity
              accessibilityRole="button"
              disabled={savingProfile}
              onPress={handleUpdateProfile}
              style={[styles.saveProfileButton, { opacity: savingProfile ? 0.65 : 1 }]}> 
              {savingProfile ? <ActivityIndicator color="#fff" /> : <Save color="#fff" size={18} />}
              <Text style={styles.saveProfileText}>Lưu thông tin</Text>
            </TouchableOpacity>
          </ScrollView>
        </KeyboardAvoidingView>
      </Modal>
    </ScrollView>
  );
}

function InfoRow({
  colors,
  icon,
  label,
  value,
}: {
  colors: typeof Colors.light | typeof Colors.dark;
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <View style={styles.infoRow}>
      {icon}
      <View style={styles.infoCopy}>
        <Text style={[styles.infoLabel, { color: colors.textSecondary }]}>{label}</Text>
        <Text style={[styles.infoValue, { color: colors.text }]}>{value}</Text>
      </View>
    </View>
  );
}

function PasswordInput({
  colors,
  label,
  onChangeText,
  value,
}: {
  colors: typeof Colors.light | typeof Colors.dark;
  label: string;
  onChangeText: (value: string) => void;
  value: string;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <View style={styles.inputGroup}>
      <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>{label}</Text>
      <View style={[styles.passwordField, { backgroundColor: colors.background }]}> 
        <TextInput
          autoCapitalize="none"
          onChangeText={onChangeText}
          placeholder="••••••••"
          placeholderTextColor={colors.textSecondary}
          secureTextEntry={!visible}
          style={[styles.passwordInput, { color: colors.text }]}
          value={value}
        />
        <TouchableOpacity accessibilityLabel={visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'} accessibilityRole="button" onPress={() => setVisible((current) => !current)} style={styles.passwordToggle}>
          {visible ? <EyeOff color={colors.textSecondary} size={18} /> : <Eye color={colors.textSecondary} size={18} />}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, paddingBottom: 120 },
  profileHeader: { alignItems: 'center', marginBottom: 22 },
  avatar: { backgroundColor: '#dbeafe', borderRadius: 54, height: 108, width: 108 },
  avatarAction: { alignItems: 'center', backgroundColor: '#2563eb', borderColor: '#fff', borderRadius: 18, borderWidth: 3, bottom: 0, height: 36, justifyContent: 'center', position: 'absolute', right: 0, width: 36 },
  name: { fontSize: 23, fontWeight: '800', marginTop: 13 },
  code: { fontSize: 13, marginTop: 3 },
  section: { borderRadius: 16, gap: 13, marginBottom: 15, padding: 17 },
  sectionHeading: { alignItems: 'center', flexDirection: 'row', gap: 8 },
  sectionTitleRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  sectionTitle: { fontSize: 17, fontWeight: '800' },
  editProfileButton: { alignItems: 'center', backgroundColor: '#dbeafe', borderRadius: 9, flexDirection: 'row', gap: 5, minHeight: 38, paddingHorizontal: 10 },
  editProfileText: { color: '#1d4ed8', fontSize: 12, fontWeight: '800' },
  infoRow: { alignItems: 'center', flexDirection: 'row', gap: 12 },
  infoCopy: { flex: 1 },
  infoLabel: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  infoValue: { fontSize: 14, fontWeight: '600', marginTop: 2 },
  inputGroup: { gap: 6 },
  inputLabel: { fontSize: 12, fontWeight: '700' },
  input: { borderRadius: 10, fontSize: 14, minHeight: 48, paddingHorizontal: 13 },
  passwordField: { alignItems: 'center', borderRadius: 10, flexDirection: 'row', minHeight: 48 },
  passwordInput: { flex: 1, fontSize: 14, minHeight: 48, paddingHorizontal: 13 },
  passwordToggle: { alignItems: 'center', justifyContent: 'center', minHeight: 44, minWidth: 44 },
  button: { alignItems: 'center', borderRadius: 10, flexDirection: 'row', gap: 8, justifyContent: 'center', minHeight: 48 },
  buttonText: { color: '#fff', fontSize: 14, fontWeight: '800' },
  secondaryButton: { backgroundColor: '#dbeafe' },
  secondaryButtonText: { color: '#1d4ed8', fontSize: 14, fontWeight: '800' },
  logoutButton: { alignItems: 'center', borderColor: '#fecaca', borderRadius: 12, borderWidth: 1, flexDirection: 'row', gap: 8, justifyContent: 'center', minHeight: 50 },
  logoutText: { color: '#dc2626', fontSize: 14, fontWeight: '800' },
  modalContainer: { flex: 1 },
  modalHeader: { alignItems: 'center', borderBottomWidth: 1, flexDirection: 'row', paddingBottom: 12, paddingHorizontal: 20 },
  modalHeaderCopy: { flex: 1 },
  modalEyebrow: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  modalTitle: { fontSize: 20, fontWeight: '800', marginTop: 2 },
  modalCloseButton: { alignItems: 'center', justifyContent: 'center', minHeight: 44, minWidth: 44 },
  modalContent: { gap: 16, padding: 20 },
  formHint: { fontSize: 13, lineHeight: 19, marginBottom: 2 },
  genderRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 2 },
  genderOption: { borderRadius: 10, borderWidth: 1.5, paddingHorizontal: 12, paddingVertical: 10 },
  genderOptionText: { fontSize: 13, fontWeight: '700' },
  addressInput: { borderRadius: 10, fontSize: 14, minHeight: 100, padding: 13 },
  saveProfileButton: { alignItems: 'center', backgroundColor: '#2563eb', borderRadius: 12, flexDirection: 'row', gap: 8, justifyContent: 'center', marginTop: 6, minHeight: 52 },
  saveProfileText: { color: '#fff', fontSize: 15, fontWeight: '800' },
});
