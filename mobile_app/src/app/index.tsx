import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  useColorScheme,
} from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  Bot,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileText,
  Fingerprint,
  LogOut,
  TriangleAlert,
} from 'lucide-react-native';

import { Colors } from '@/constants/theme';
import { api } from '@/lib/axios';
import { useAuthStore } from '@/stores/auth.store';
import type {
  AttendanceRecord,
  AttendanceSummary,
  CurrentShift,
  FaceProfile,
  Holiday,
} from '@/types/api';

import { toDateKey } from '@/lib/date';

function formatTime(value?: string | null) {
  return value
    ? new Date(value).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
    : '--:--';
}

const faceLabels: Record<FaceProfile['status'], string> = {
  active: 'Đã kích hoạt',
  failed: 'Đăng ký lỗi',
  pending: 'Chờ xử lý',
  revoked: 'Đã thu hồi',
};

export default function HomeScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'unspecified' ? 'light' : scheme];
  const isDark = scheme === 'dark';
  const insets = useSafeAreaInsets();
  const { employee, logout } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [shift, setShift] = useState<CurrentShift | null>(null);
  const [record, setRecord] = useState<AttendanceRecord | null>(null);
  const [summary, setSummary] = useState<AttendanceSummary | null>(null);
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [faceProfile, setFaceProfile] = useState<FaceProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    if (!employee) return;
    const today = new Date();
    const todayValue = toDateKey(today);
    const monthStart = toDateKey(new Date(today.getFullYear(), today.getMonth(), 1));

    try {
      setError(null);
      const [shiftResult, recordResult, summaryResult, holidayResult, faceResult] =
        await Promise.allSettled([
          api.get<CurrentShift>(`/employees/${employee.employee_id}/current-shift`, {
            params: { as_of: todayValue },
          }),
          api.get<AttendanceRecord[]>('/attendance/records', {
            params: {
              employee_id: employee.employee_id,
              work_date_from: todayValue,
              work_date_to: todayValue,
            },
          }),
          api.get<AttendanceSummary>('/attendance/records/summary', {
            params: {
              employee_id: employee.employee_id,
              work_date_from: monthStart,
              work_date_to: todayValue,
            },
          }),
          api.get<Holiday[]>('/holidays', { params: { year: today.getFullYear() } }),
          api.get<FaceProfile>(`/face-profiles/employee/${employee.employee_id}`),
        ]);

      setShift(shiftResult.status === 'fulfilled' ? shiftResult.value.data : null);
      setRecord(
        recordResult.status === 'fulfilled' ? recordResult.value.data[0] ?? null : null,
      );
      setSummary(summaryResult.status === 'fulfilled' ? summaryResult.value.data : null);
      setFaceProfile(faceResult.status === 'fulfilled' ? faceResult.value.data : null);

      if (holidayResult.status === 'fulfilled') {
        const upcoming = holidayResult.value.data
          .filter((holiday) => holiday.holiday_date >= todayValue)
          .sort((a, b) => a.holiday_date.localeCompare(b.holiday_date))
          .slice(0, 3);
        setHolidays(upcoming);
      } else {
        setHolidays([]);
      }

      if (recordResult.status === 'rejected' && summaryResult.status === 'rejected') {
        setError('Không thể tải dữ liệu chấm công. Vui lòng thử lại.');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [employee]);

  useFocusEffect(
    useCallback(() => {
      fetchDashboard();
    }, [fetchDashboard]),
  );

  const handleLogout = () => {
    Alert.alert('Đăng xuất', 'Bạn muốn kết thúc phiên đăng nhập?', [
      { text: 'Ở lại', style: 'cancel' },
      { text: 'Đăng xuất', style: 'destructive', onPress: logout },
    ]);
  };

  const upcomingHolidayText = holidays.length
    ? `${holidays[0].name} · ${new Date(`${holidays[0].holiday_date}T00:00:00`).toLocaleDateString('vi-VN')}`
    : 'Chưa có ngày lễ sắp tới';

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={[styles.content, { paddingTop: insets.top + 14 }]}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => {
            setRefreshing(true);
            fetchDashboard();
          }}
          tintColor={colors.text}
        />
      }>
      <View style={styles.header}>
        <View style={styles.headerCopy}>
          <Text style={[styles.eyebrow, { color: colors.textSecondary }]}>XIN CHÀO</Text>
          <Text style={[styles.name, { color: colors.text }]}>
            {employee?.full_name ?? 'Nhân viên'}
          </Text>
          <Text style={[styles.code, { color: colors.textSecondary }]}>
            {employee?.employee_code ?? 'Chưa liên kết hồ sơ'}
          </Text>
        </View>
        <TouchableOpacity
          accessibilityLabel="Đăng xuất"
          accessibilityRole="button"
          onPress={handleLogout}
          style={[styles.iconButton, { backgroundColor: colors.backgroundElement }]}>
          <LogOut size={20} color="#ef4444" />
        </TouchableOpacity>
      </View>

      <View style={[styles.datePill, { backgroundColor: colors.backgroundElement }]}>
        <CalendarDays size={18} color="#2563eb" />
        <Text style={[styles.dateText, { color: colors.text }]}>
          {new Date().toLocaleDateString('vi-VN', {
            day: 'numeric',
            month: 'long',
            weekday: 'long',
            year: 'numeric',
          })}
        </Text>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color="#2563eb" style={styles.loader} />
      ) : (
        <>
          {error ? (
            <View style={styles.errorBox}>
              <TriangleAlert size={18} color="#dc2626" />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <View style={[styles.primaryCard, { backgroundColor: isDark ? '#172033' : '#eff6ff' }]}>
            <View style={styles.cardHeading}>
              <View>
                <Text style={[styles.cardEyebrow, { color: '#2563eb' }]}>CA HÔM NAY</Text>
                <Text style={[styles.shiftName, { color: colors.text }]}>
                  {shift?.shift.name ?? 'Không có lịch phân ca'}
                </Text>
              </View>
              <Clock3 size={26} color="#2563eb" />
            </View>
            {shift ? (
              <Text style={[styles.shiftTime, { color: colors.textSecondary }]}>
                {shift.shift.start_time.slice(0, 5)} – {shift.shift.end_time.slice(0, 5)}
              </Text>
            ) : null}
            <View style={[styles.divider, { backgroundColor: colors.backgroundSelected }]} />
            <View style={styles.timeGrid}>
              <View style={styles.timeCell}>
                <Text style={[styles.timeLabel, { color: colors.textSecondary }]}>CHECK-IN</Text>
                <Text style={[styles.timeValue, { color: record?.check_in_time ? '#059669' : colors.text }]}>
                  {formatTime(record?.check_in_time)}
                </Text>
              </View>
              <View style={styles.timeCell}>
                <Text style={[styles.timeLabel, { color: colors.textSecondary }]}>CHECK-OUT</Text>
                <Text style={[styles.timeValue, { color: record?.check_out_time ? '#059669' : colors.text }]}>
                  {formatTime(record?.check_out_time)}
                </Text>
              </View>
            </View>
            <View style={styles.notice}>
              <CheckCircle2 size={16} color="#2563eb" />
              <Text style={[styles.noticeText, { color: colors.textSecondary }]}>
                Chấm công được ghi nhận tại thiết bị nhận diện của công ty.
              </Text>
            </View>
          </View>

          <Text style={[styles.sectionTitle, { color: colors.text }]}>Tháng này</Text>
          <View style={styles.statsGrid}>
            <View style={[styles.statCard, { backgroundColor: colors.backgroundElement }]}>
              <Text style={[styles.statValue, { color: '#059669' }]}>{summary?.present_days ?? 0}</Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Có mặt</Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: colors.backgroundElement }]}>
              <Text style={[styles.statValue, { color: '#d97706' }]}>{summary?.late_days ?? 0}</Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Đi muộn</Text>
            </View>
            <View style={[styles.statCard, { backgroundColor: colors.backgroundElement }]}>
              <Text style={[styles.statValue, { color: '#dc2626' }]}>{summary?.absent_days ?? 0}</Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Vắng</Text>
            </View>
          </View>

          <View style={styles.infoGrid}>
            <View style={[styles.infoCard, { backgroundColor: colors.backgroundElement }]}>
              <Fingerprint size={22} color={faceProfile?.status === 'active' ? '#059669' : '#d97706'} />
              <Text style={[styles.infoTitle, { color: colors.text }]}>Khuôn mặt</Text>
              <Text style={[styles.infoCaption, { color: colors.textSecondary }]}>
                {faceProfile ? faceLabels[faceProfile.status] : 'Chưa đăng ký'}
              </Text>
            </View>
            <View style={[styles.infoCard, { backgroundColor: colors.backgroundElement }]}>
              <CalendarDays size={22} color="#7c3aed" />
              <Text style={[styles.infoTitle, { color: colors.text }]}>Ngày lễ</Text>
              <Text style={[styles.infoCaption, { color: colors.textSecondary }]}>
                {upcomingHolidayText}
              </Text>
            </View>
          </View>

          <Text style={[styles.sectionTitle, { color: colors.text }]}>Truy cập nhanh</Text>
          <View style={styles.quickGrid}>
            <TouchableOpacity
              accessibilityRole="button"
              style={[styles.quickCard, { backgroundColor: colors.backgroundElement }]}
              onPress={() => router.push('/attendance')}>
              <Clock3 size={22} color="#2563eb" />
              <Text style={[styles.quickTitle, { color: colors.text }]}>Bảng công</Text>
              <Text style={[styles.quickCaption, { color: colors.textSecondary }]}>
                Báo cáo và sửa công
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              style={[styles.quickCard, { backgroundColor: colors.backgroundElement }]}
              onPress={() => router.push('/leaves')}>
              <FileText size={22} color="#d97706" />
              <Text style={[styles.quickTitle, { color: colors.text }]}>Nghỉ phép</Text>
              <Text style={[styles.quickCaption, { color: colors.textSecondary }]}>
                Số dư và đơn nghỉ
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              style={[styles.quickCard, { backgroundColor: colors.backgroundElement }]}
              onPress={() => router.push('/chat')}>
              <Bot size={22} color="#7c3aed" />
              <Text style={[styles.quickTitle, { color: colors.text }]}>Trợ lý AI</Text>
              <Text style={[styles.quickCaption, { color: colors.textSecondary }]}>
                Hỏi quy chế công ty
              </Text>
            </TouchableOpacity>
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, paddingBottom: 120 },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 18 },
  headerCopy: { flex: 1 },
  eyebrow: { fontSize: 11, fontWeight: '700', letterSpacing: 1.2 },
  name: { fontSize: 25, fontWeight: '800', marginTop: 3 },
  code: { fontSize: 13, marginTop: 2 },
  iconButton: { alignItems: 'center', borderRadius: 12, height: 44, justifyContent: 'center', width: 44 },
  datePill: { alignItems: 'center', borderRadius: 12, flexDirection: 'row', gap: 9, padding: 12 },
  dateText: { flex: 1, fontSize: 14, fontWeight: '600', textTransform: 'capitalize' },
  loader: { marginVertical: 80 },
  errorBox: { alignItems: 'center', backgroundColor: '#fee2e2', borderRadius: 10, flexDirection: 'row', gap: 8, marginTop: 16, padding: 12 },
  errorText: { color: '#b91c1c', flex: 1, fontSize: 13 },
  primaryCard: { borderRadius: 18, marginTop: 18, padding: 20 },
  cardHeading: { alignItems: 'flex-start', flexDirection: 'row', justifyContent: 'space-between' },
  cardEyebrow: { fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  shiftName: { fontSize: 20, fontWeight: '800', marginTop: 3 },
  shiftTime: { fontSize: 14, marginTop: 6 },
  divider: { height: 1, marginVertical: 18 },
  timeGrid: { flexDirection: 'row' },
  timeCell: { flex: 1 },
  timeLabel: { fontSize: 11, fontWeight: '700' },
  timeValue: { fontSize: 25, fontWeight: '800', marginTop: 3 },
  notice: { alignItems: 'center', flexDirection: 'row', gap: 8, marginTop: 18 },
  noticeText: { flex: 1, fontSize: 12, lineHeight: 17 },
  sectionTitle: { fontSize: 18, fontWeight: '800', marginBottom: 12, marginTop: 24 },
  statsGrid: { flexDirection: 'row', gap: 10 },
  statCard: { alignItems: 'center', borderRadius: 14, flex: 1, paddingVertical: 16 },
  statValue: { fontSize: 23, fontWeight: '800' },
  statLabel: { fontSize: 12, fontWeight: '600', marginTop: 3 },
  infoGrid: { flexDirection: 'row', gap: 10, marginTop: 18 },
  infoCard: { borderRadius: 14, flex: 1, minHeight: 112, padding: 14 },
  infoTitle: { fontSize: 14, fontWeight: '800', marginTop: 10 },
  infoCaption: { fontSize: 11, lineHeight: 16, marginTop: 3 },
  quickGrid: { gap: 10 },
  quickCard: { borderRadius: 14, minHeight: 82, padding: 15 },
  quickTitle: { fontSize: 15, fontWeight: '800', marginTop: 9 },
  quickCaption: { fontSize: 12, marginTop: 2 },
});
