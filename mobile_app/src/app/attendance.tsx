import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  useColorScheme,
  Modal,
  TextInput,
  TouchableOpacity,
  Alert,
  ScrollView,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuthStore } from '@/stores/auth.store';
import { api } from '@/lib/axios';
import { Colors } from '@/constants/theme';
import {
  Check,
  Clock,
  AlertTriangle,
  HelpCircle,
  Plus,
  X,
  RefreshCw,
  AlertCircle,
  BarChart3,
  ScanFace,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react-native';
import type { AttendanceRecord, MonthlyReport } from '@/types/api';
import { DateTimeField } from '@/components/ui/date-time-field';
import { FeedbackState } from '@/components/ui/feedback-state';
import { RequestDetailModal } from '@/components/ui/request-detail-modal';
import { getApiErrorMessage } from '@/lib/api-error';
import { toDateKey, toTimeKey } from '@/lib/date';

interface CorrectionRequest {
  request_id: string;
  employee_id: string;
  attendance_record_id: string | null;
  requested_check_in: string | null;
  requested_check_out: string | null;
  reason: string;
  status: string;
  rejection_reason: string | null;
  created_at: string;
}

interface AttendanceEvent {
  event_id: string;
  event_type: 'check_in' | 'check_out';
  event_time: string;
  confidence_score: number | null;
  anti_spoof_score: number | null;
  is_accepted: boolean;
  rejection_reason: string | null;
}

interface CorrectionLog {
  log_id: number;
  action: string;
  comment: string | null;
  created_at: string;
}

export default function AttendanceScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'unspecified' ? 'light' : scheme];
  const isDarkMode = scheme === 'dark';
  const insets = useSafeAreaInsets();

  const { employee } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'history' | 'report' | 'events' | 'corrections'>('history');
  const [loading, setLoading] = useState(false);
  
  // Data lists
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [corrections, setCorrections] = useState<CorrectionRequest[]>([]);
  const [events, setEvents] = useState<AttendanceEvent[]>([]);
  const [monthlyReport, setMonthlyReport] = useState<MonthlyReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reportMonth, setReportMonth] = useState(() => new Date());

  // Modal & Form state
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<AttendanceRecord | null>(null);
  const [editingCorrection, setEditingCorrection] = useState<CorrectionRequest | null>(null);
  const [workDate, setWorkDate] = useState('');
  const [checkInTime, setCheckInTime] = useState('');
  const [checkOutTime, setCheckOutTime] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailCorrection, setDetailCorrection] = useState<CorrectionRequest | null>(null);
  const [detailLogs, setDetailLogs] = useState<CorrectionLog[]>([]);

  // Local stats calculated from last 30 days of records
  const [stats, setStats] = useState({
    present: 0,
    late: 0,
    earlyLeave: 0,
  });

  const fetchData = useCallback(async () => {
    if (!employee) return;
    try {
      setLoading(true);
      setError(null);
      
      // 1. Fetch last 30 days of attendance records
      const toDate = new Date();
      const fromDate = new Date();
      fromDate.setDate(toDate.getDate() - 30);

      const fromStr = toDateKey(fromDate);
      const toStr = toDateKey(toDate);
      const now = reportMonth;
      const [recordsResult, correctionsResult, reportResult, eventsResult] = await Promise.allSettled([
        api.get<AttendanceRecord[]>('/attendance/records', {
          params: { employee_id: employee.employee_id, work_date_from: fromStr, work_date_to: toStr, page_size: 100 },
        }),
        api.get('/corrections/requests', {
          params: { employee_id: employee.employee_id, page_size: 100 },
        }),
        api.get<MonthlyReport>(`/reports/monthly/${employee.employee_id}`, {
          params: { month: now.getMonth() + 1, year: now.getFullYear() },
        }),
        api.get<AttendanceEvent[]>('/attendance/events', {
          params: { employee_id: employee.employee_id, page: 1, page_size: 100 },
        }),
      ]);

      const fetchedRecords = recordsResult.status === 'fulfilled' ? recordsResult.value.data : [];
      setRecords(fetchedRecords);

      // Compute stats
      let present = 0;
      let late = 0;
      let earlyLeave = 0;

      fetchedRecords.forEach((r: AttendanceRecord) => {
        if (r.status === 'present') present++;
        else if (r.status === 'late') {
          present++;
          late++;
        } else if (r.status === 'early_leave') {
          present++;
          earlyLeave++;
        } else if (r.status === 'late_and_early_leave') {
          present++;
          late++;
          earlyLeave++;
        }
      });

      setStats({ present, late, earlyLeave });

      setCorrections(correctionsResult.status === 'fulfilled' ? correctionsResult.value.data?.items || [] : []);
      setMonthlyReport(reportResult.status === 'fulfilled' ? reportResult.value.data : null);
      setEvents(eventsResult.status === 'fulfilled' ? eventsResult.value.data || [] : []);

      if (recordsResult.status === 'rejected') {
        setError(getApiErrorMessage(recordsResult.reason, 'Không thể tải bảng công.'));
      }

    } catch (err) {
      setError(getApiErrorMessage(err, 'Không thể tải dữ liệu chấm công.'));
    } finally {
      setLoading(false);
    }
  }, [employee, reportMonth]);

  useFocusEffect(useCallback(() => { fetchData(); }, [fetchData]));

  // Handle opening modal from a record
  const handleOpenCorrectionForRecord = (record: AttendanceRecord) => {
    setEditingCorrection(null);
    setSelectedRecord(record);
    const dateOnly = record.work_date.split('T')[0];
    setWorkDate(dateOnly);
    
    // Pre-fill times if they exist, formatting to HH:MM
    if (record.check_in_time) {
      const cin = new Date(record.check_in_time);
      setCheckInTime(toTimeKey(cin));
    } else {
      setCheckInTime('');
    }
    
    if (record.check_out_time) {
      const cout = new Date(record.check_out_time);
      setCheckOutTime(toTimeKey(cout));
    } else {
      setCheckOutTime('');
    }

    setReason('');
    setModalVisible(true);
  };

  // Handle opening modal blank
  const handleOpenNewCorrection = () => {
    setEditingCorrection(null);
    setSelectedRecord(null);
    setWorkDate(toDateKey(new Date()));
    setCheckInTime('');
    setCheckOutTime('');
    setReason('');
    setModalVisible(true);
  };

  const handleOpenEditCorrection = (request: CorrectionRequest) => {
    setSelectedRecord(null);
    setEditingCorrection(request);
    const basis = request.requested_check_in || request.requested_check_out || request.created_at;
    setWorkDate(basis.split('T')[0]);
    setCheckInTime(
      request.requested_check_in
        ? toTimeKey(new Date(request.requested_check_in))
        : '',
    );
    setCheckOutTime(
      request.requested_check_out
        ? toTimeKey(new Date(request.requested_check_out))
        : '',
    );
    setReason(request.reason);
    setModalVisible(true);
  };

  // Submit Correction Request
  const handleSubmitCorrection = async () => {
    if (!workDate || !reason.trim()) {
      Alert.alert('Lỗi', 'Vui lòng nhập ngày và lý do chỉnh sửa.');
      return;
    }

    if (!checkInTime && !checkOutTime) {
      Alert.alert('Lỗi', 'Vui lòng nhập ít nhất một trong hai giờ: Giờ vào mới hoặc Giờ ra mới.');
      return;
    }

    // Date format validation YYYY-MM-DD
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(workDate)) {
      Alert.alert('Lỗi', 'Định dạng ngày phải là YYYY-MM-DD.');
      return;
    }

    // Time format validation HH:MM
    const timeRegex = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
    if (checkInTime && !timeRegex.test(checkInTime)) {
      Alert.alert('Lỗi', 'Định dạng giờ vào phải là HH:MM (Ví dụ: 08:30).');
      return;
    }
    if (checkOutTime && !timeRegex.test(checkOutTime)) {
      Alert.alert('Lỗi', 'Định dạng giờ ra phải là HH:MM (Ví dụ: 17:30).');
      return;
    }

    if (checkInTime && checkOutTime && checkOutTime < checkInTime) {
      Alert.alert('Giờ chưa hợp lệ', 'Giờ ra phải sau giờ vào.');
      return;
    }

    if (reason.trim().length < 3) {
      Alert.alert('Lỗi', 'Lý do chỉnh sửa phải có ít nhất 3 ký tự.');
      return;
    }

    try {
      setSubmitting(true);

      // Construct datetimes (naive local format: YYYY-MM-DDTHH:MM:00)
      const requested_check_in = checkInTime ? `${workDate}T${checkInTime}:00` : null;
      const requested_check_out = checkOutTime ? `${workDate}T${checkOutTime}:00` : null;

      const payload = {
        attendance_record_id: selectedRecord ? selectedRecord.record_id : null,
        requested_check_in,
        requested_check_out,
        reason: reason.trim(),
      };

      if (editingCorrection) {
        await api.patch(`/corrections/requests/${editingCorrection.request_id}`, {
          reason: payload.reason,
          requested_check_in: payload.requested_check_in,
          requested_check_out: payload.requested_check_out,
        });
      } else {
        await api.post('/corrections/requests', payload);
      }
      Alert.alert(
        'Thành công',
        editingCorrection ? 'Đã cập nhật yêu cầu sửa công.' : 'Đã nộp yêu cầu sửa công.',
      );
      setModalVisible(false);
      fetchData();
    } catch (err: unknown) {
      Alert.alert('Không thể gửi yêu cầu', getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleShowCorrectionLogs = async (request: CorrectionRequest) => {
    try {
      setDetailCorrection(request);
      setDetailLogs([]);
      setDetailVisible(true);
      setDetailLoading(true);
      const [detailResponse, logsResponse] = await Promise.all([
        api.get<CorrectionRequest>(`/corrections/requests/${request.request_id}`),
        api.get<CorrectionLog[]>(`/corrections/requests/${request.request_id}/logs`),
      ]);
      setDetailCorrection(detailResponse.data);
      setDetailLogs(logsResponse.data);
    } catch (error) {
      setDetailVisible(false);
      Alert.alert('Không thể tải chi tiết', getApiErrorMessage(error));
    } finally {
      setDetailLoading(false);
    }
  };

  // Cancel Correction Request
  const handleCancelCorrection = (requestId: string) => {
    Alert.alert(
      'Hủy đơn yêu cầu',
      'Bạn có chắc chắn muốn hủy đơn yêu cầu chỉnh sửa công này không?',
      [
        { text: 'Hủy bỏ', style: 'cancel' },
        {
          text: 'Đồng ý',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.post(`/corrections/requests/${requestId}/cancel`);
              Alert.alert('Thành công', 'Đã hủy đơn yêu cầu thành công.');
              fetchData();
            } catch (err: unknown) {
              Alert.alert('Không thể hủy đơn', getApiErrorMessage(err));
            }
          },
        },
      ]
    );
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'present':
        return <View style={[styles.badge, { backgroundColor: '#d1fae5' }]}><Text style={[styles.badgeText, { color: '#065f46' }]}>Đúng giờ</Text></View>;
      case 'late':
        return <View style={[styles.badge, { backgroundColor: '#fef3c7' }]}><Text style={[styles.badgeText, { color: '#92400e' }]}>Đi muộn</Text></View>;
      case 'early_leave':
        return <View style={[styles.badge, { backgroundColor: '#fee2e2' }]}><Text style={[styles.badgeText, { color: '#991b1b' }]}>Về sớm</Text></View>;
      case 'late_and_early_leave':
        return <View style={[styles.badge, { backgroundColor: '#ffedd5' }]}><Text style={[styles.badgeText, { color: '#c2410c' }]}>Muộn & Sớm</Text></View>;
      case 'absent':
        return <View style={[styles.badge, { backgroundColor: '#f3f4f6' }]}><Text style={[styles.badgeText, { color: '#374151' }]}>Vắng mặt</Text></View>;
      case 'on_leave':
        return <View style={[styles.badge, { backgroundColor: '#ede9fe' }]}><Text style={[styles.badgeText, { color: '#6d28d9' }]}>Nghỉ phép</Text></View>;
      case 'holiday':
        return <View style={[styles.badge, { backgroundColor: '#dbeafe' }]}><Text style={[styles.badgeText, { color: '#1d4ed8' }]}>Ngày lễ</Text></View>;
      case 'missing_check_in':
        return <View style={[styles.badge, { backgroundColor: '#fee2e2' }]}><Text style={[styles.badgeText, { color: '#991b1b' }]}>Thiếu giờ vào</Text></View>;
      case 'missing_check_out':
        return <View style={[styles.badge, { backgroundColor: '#fee2e2' }]}><Text style={[styles.badgeText, { color: '#991b1b' }]}>Thiếu giờ ra</Text></View>;
      case 'manually_edited':
        return <View style={[styles.badge, { backgroundColor: '#e0e7ff' }]}><Text style={[styles.badgeText, { color: '#3730a3' }]}>Đã điều chỉnh</Text></View>;
      
      // Corrections statuses
      case 'pending':
        return <View style={[styles.badge, { backgroundColor: '#fef3c7' }]}><Text style={[styles.badgeText, { color: '#92400e' }]}>Chờ duyệt</Text></View>;
      case 'approved':
        return <View style={[styles.badge, { backgroundColor: '#d1fae5' }]}><Text style={[styles.badgeText, { color: '#065f46' }]}>Đã duyệt</Text></View>;
      case 'rejected':
        return <View style={[styles.badge, { backgroundColor: '#fee2e2' }]}><Text style={[styles.badgeText, { color: '#991b1b' }]}>Bị từ chối</Text></View>;
      case 'cancelled':
        return <View style={[styles.badge, { backgroundColor: '#f3f4f6' }]}><Text style={[styles.badgeText, { color: '#374151' }]}>Đã hủy</Text></View>;
      default:
        return <View style={[styles.badge, { backgroundColor: '#e0e7ff' }]}><Text style={[styles.badgeText, { color: '#3730a3' }]}>{status}</Text></View>;
    }
  };

  const isCurrentReportMonth =
    reportMonth.getMonth() === new Date().getMonth() &&
    reportMonth.getFullYear() === new Date().getFullYear();

  const changeReportMonth = (offset: number) => {
    setReportMonth((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1));
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'present':
        return <View style={[styles.iconWrapper, { backgroundColor: '#10b981' }]}><Check size={16} color="#ffffff" /></View>;
      case 'late':
      case 'early_leave':
      case 'late_and_early_leave':
        return <View style={[styles.iconWrapper, { backgroundColor: '#f59e0b' }]}><Clock size={16} color="#ffffff" /></View>;
      case 'absent':
        return <View style={[styles.iconWrapper, { backgroundColor: '#ef4444' }]}><AlertTriangle size={16} color="#ffffff" /></View>;
      case 'on_leave':
      case 'holiday':
        return <View style={[styles.iconWrapper, { backgroundColor: '#7c3aed' }]}><Check size={16} color="#ffffff" /></View>;
      default:
        return <View style={[styles.iconWrapper, { backgroundColor: '#9ca3af' }]}><HelpCircle size={16} color="#ffffff" /></View>;
    }
  };

  const renderRecordItem = ({ item }: { item: AttendanceRecord }) => {
    const checkIn = item.check_in_time
      ? new Date(item.check_in_time).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
      : '--:--';
    const checkOut = item.check_out_time
      ? new Date(item.check_out_time).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
      : '--:--';

    const formattedDate = new Date(item.work_date).toLocaleDateString('vi-VN', {
      weekday: 'short',
      month: 'numeric',
      day: 'numeric',
    });

    const isMissing = item.status === 'absent' || !item.check_in_time || !item.check_out_time;

    return (
      <TouchableOpacity
        style={[styles.recordRow, { borderBottomColor: colors.backgroundElement }]}
        onPress={() => handleOpenCorrectionForRecord(item)}>
        <View style={styles.recordLeft}>
          {getStatusIcon(item.status)}
          <View style={styles.dateBlock}>
            <Text style={[styles.recordDate, { color: colors.text }]}>{formattedDate}</Text>
            <Text style={[styles.recordTimes, { color: colors.textSecondary }]}>
              {checkIn} - {checkOut}
            </Text>
          </View>
        </View>
        <View style={styles.recordRight}>
          {getStatusBadge(item.status)}
          {item.worked_minutes > 0 ? (
            <Text style={[styles.workTimeText, { color: colors.textSecondary }]}>
              {Math.round((item.worked_minutes / 60) * 10) / 10} giờ công
            </Text>
          ) : isMissing ? (
            <Text style={[styles.requestCorrectionText, { color: isDarkMode ? '#60a5fa' : '#2563eb' }]}>
              Yêu cầu sửa công
            </Text>
          ) : null}
        </View>
      </TouchableOpacity>
    );
  };

  const renderCorrectionItem = ({ item }: { item: CorrectionRequest }) => {
    const reqDate = item.requested_check_in 
      ? item.requested_check_in.split('T')[0] 
      : item.requested_check_out 
        ? item.requested_check_out.split('T')[0] 
        : item.created_at.split('T')[0];

    const formattedDate = new Date(reqDate).toLocaleDateString('vi-VN', {
      weekday: 'short',
      month: 'numeric',
      day: 'numeric',
      year: 'numeric',
    });

    const cin = item.requested_check_in
      ? new Date(item.requested_check_in).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
      : 'Không đổi';

    const cout = item.requested_check_out
      ? new Date(item.requested_check_out).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
      : 'Không đổi';

    const isPending = item.status === 'pending';

    return (
      <TouchableOpacity
        onPress={() => handleShowCorrectionLogs(item)}
        style={[styles.correctionCard, { backgroundColor: colors.backgroundElement, borderColor: colors.backgroundSelected }]}>
        <View style={styles.correctionHeader}>
          <Text style={[styles.correctionDate, { color: colors.text }]}>Ngày công: {formattedDate}</Text>
          {getStatusBadge(item.status)}
        </View>

        <Text style={[styles.correctionTimes, { color: colors.textSecondary }]}>
          Giờ vào mới: {cin} | Giờ ra mới: {cout}
        </Text>

        <Text style={[styles.correctionReason, { color: colors.text }]}>
          Lý do: {item.reason}
        </Text>

        {item.status === 'rejected' && item.rejection_reason && (
          <View style={styles.rejectionBox}>
            <AlertCircle size={14} color="#ef4444" />
            <Text style={styles.rejectionText}>Từ chối: {item.rejection_reason}</Text>
          </View>
        )}

        {isPending && (
          <View style={styles.correctionActions}>
            <TouchableOpacity
              style={[styles.cancelBtn, { backgroundColor: colors.backgroundSelected }]}
              onPress={() => handleOpenEditCorrection(item)}>
              <Text style={[styles.cancelBtnText, { color: colors.text }]}>Sửa đơn</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.cancelBtn}
              onPress={() => handleCancelCorrection(item.request_id)}>
              <Text style={styles.cancelBtnText}>Hủy đơn</Text>
            </TouchableOpacity>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const renderEventItem = ({ item }: { item: AttendanceEvent }) => (
    <View style={[styles.eventCard, { backgroundColor: colors.backgroundElement }]}>
      <View style={styles.eventHeader}>
        <ScanFace size={19} color={item.is_accepted ? '#059669' : '#dc2626'} />
        <Text style={[styles.eventTitle, { color: colors.text }]}>
          {item.event_type === 'check_in' ? 'Nhận diện vào ca' : item.event_type === 'check_out' ? 'Nhận diện ra ca' : 'Sự kiện chưa xác định'}
        </Text>
        {getStatusBadge(item.is_accepted ? 'approved' : 'rejected')}
      </View>
      <Text style={[styles.eventMeta, { color: colors.textSecondary }]}>
        {new Date(item.event_time).toLocaleString('vi-VN')}
      </Text>
      <Text style={[styles.eventMeta, { color: colors.textSecondary }]}>
        Tin cậy: {item.confidence_score == null ? '-' : `${(item.confidence_score * 100).toFixed(1)}%`}
        {' · '}Chống giả mạo: {item.anti_spoof_score == null ? '-' : `${(item.anti_spoof_score * 100).toFixed(1)}%`}
      </Text>
      {item.rejection_reason ? <Text style={styles.rejectionText}>{item.rejection_reason}</Text> : null}
    </View>
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + 12 }]}> 
      <View style={styles.header}>
        <View>
          <Text style={[styles.screenTitle, { color: colors.text }]}>Chấm công</Text>
          <Text style={[styles.screenSubtitle, { color: colors.textSecondary }]}>Theo dõi giờ làm và yêu cầu điều chỉnh</Text>
        </View>
        <TouchableOpacity accessibilityLabel="Tải lại" accessibilityRole="button" disabled={loading} onPress={fetchData} style={styles.refreshButton}>
          <RefreshCw size={20} color={colors.text} />
        </TouchableOpacity>
      </View>

      {/* Segment Tab Toggle */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={[styles.tabToggleRow, { backgroundColor: colors.backgroundElement }]}>
        <TouchableOpacity
          style={[
            styles.tabToggleButton,
            activeTab === 'history' && [styles.tabToggleActiveButton, { backgroundColor: colors.backgroundSelected }],
          ]}
          onPress={() => setActiveTab('history')}>
          <Text
            style={[
              styles.tabToggleText,
              { color: colors.textSecondary },
              activeTab === 'history' && { color: colors.text, fontWeight: 'bold' },
            ]}>
            Lịch sử công
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.tabToggleButton,
            activeTab === 'report' && [styles.tabToggleActiveButton, { backgroundColor: colors.backgroundSelected }],
          ]}
          onPress={() => setActiveTab('report')}>
          <Text style={[styles.tabToggleText, { color: activeTab === 'report' ? colors.text : colors.textSecondary }]}>
            Báo cáo tháng
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.tabToggleButton,
            activeTab === 'events' && [styles.tabToggleActiveButton, { backgroundColor: colors.backgroundSelected }],
          ]}
          onPress={() => setActiveTab('events')}>
          <Text style={[styles.tabToggleText, { color: activeTab === 'events' ? colors.text : colors.textSecondary }]}>
            Nhận diện
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.tabToggleButton,
            activeTab === 'corrections' && [styles.tabToggleActiveButton, { backgroundColor: colors.backgroundSelected }],
          ]}
          onPress={() => setActiveTab('corrections')}>
          <Text
            style={[
              styles.tabToggleText,
              { color: colors.textSecondary },
              activeTab === 'corrections' && { color: colors.text, fontWeight: 'bold' },
            ]}>
            Đơn sửa công
          </Text>
        </TouchableOpacity>
      </ScrollView>

      {error ? (
        <View style={styles.errorBanner}>
          <AlertCircle color="#dc2626" size={17} />
          <Text style={styles.errorBannerText}>{error}</Text>
          <TouchableOpacity accessibilityRole="button" onPress={fetchData}>
            <Text style={styles.retryText}>Thử lại</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {activeTab === 'history' ? (
        <>
          {/* Stats Summary Cards */}
          <View style={styles.statsRow}>
            <View style={[styles.statBox, { backgroundColor: colors.backgroundElement }]}>
              <Text style={[styles.statNum, { color: '#10b981' }]}>{stats.present}</Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Ngày công</Text>
            </View>
            <View style={[styles.statBox, { backgroundColor: colors.backgroundElement }]}>
              <Text style={[styles.statNum, { color: '#f59e0b' }]}>{stats.late}</Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Đi muộn</Text>
            </View>
            <View style={[styles.statBox, { backgroundColor: colors.backgroundElement }]}>
              <Text style={[styles.statNum, { color: '#ef4444' }]}>{stats.earlyLeave}</Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Về sớm</Text>
            </View>
          </View>

          {loading ? (
            <ActivityIndicator size="large" color={colors.text} style={styles.loader} />
          ) : (
            <FlatList
              data={records}
              keyExtractor={(item) => item.record_id}
              renderItem={renderRecordItem}
              refreshControl={<RefreshControl refreshing={loading} onRefresh={fetchData} tintColor="#2563eb" />}
              contentContainerStyle={styles.listContainer}
              ListEmptyComponent={
                <View style={styles.emptyContainer}>
                  <FeedbackState description="Bảng công sẽ xuất hiện sau khi hệ thống ghi nhận ca làm việc." title="Chưa có dữ liệu chấm công" />
                </View>
              }
            />
          )}
        </>
      ) : activeTab === 'report' ? (
        <ScrollView contentContainerStyle={styles.listContainer}>
          <View style={[styles.monthPicker, { backgroundColor: colors.backgroundElement }]}> 
            <TouchableOpacity accessibilityLabel="Tháng trước" accessibilityRole="button" onPress={() => changeReportMonth(-1)} style={styles.monthButton}>
              <ChevronLeft color={colors.text} size={20} />
            </TouchableOpacity>
            <Text style={[styles.monthLabel, { color: colors.text }]}>Tháng {reportMonth.getMonth() + 1}/{reportMonth.getFullYear()}</Text>
            <TouchableOpacity
              accessibilityLabel="Tháng sau"
              accessibilityRole="button"
              disabled={isCurrentReportMonth}
              onPress={() => changeReportMonth(1)}
              style={[styles.monthButton, { opacity: isCurrentReportMonth ? 0.3 : 1 }]}> 
              <ChevronRight color={colors.text} size={20} />
            </TouchableOpacity>
          </View>
          {monthlyReport ? (
            <>
              <View style={styles.statsRow}>
                <View style={[styles.statBox, { backgroundColor: colors.backgroundElement }]}>
                  <Text style={[styles.statNum, { color: '#10b981' }]}>{monthlyReport.present_days}</Text>
                  <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Có mặt</Text>
                </View>
                <View style={[styles.statBox, { backgroundColor: colors.backgroundElement }]}>
                  <Text style={[styles.statNum, { color: '#f59e0b' }]}>{monthlyReport.late_days}</Text>
                  <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Đi muộn</Text>
                </View>
                <View style={[styles.statBox, { backgroundColor: colors.backgroundElement }]}>
                  <Text style={[styles.statNum, { color: '#ef4444' }]}>{monthlyReport.absent_days}</Text>
                  <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Vắng</Text>
                </View>
              </View>
              <View style={[styles.reportCard, { backgroundColor: colors.backgroundElement }]}>
                <BarChart3 size={24} color="#2563eb" />
                <Text style={[styles.reportTitle, { color: colors.text }]}>
                  Báo cáo tháng {monthlyReport.month}/{monthlyReport.year}
                </Text>
                <Text style={[styles.reportLine, { color: colors.textSecondary }]}>
                  Tổng giờ làm: {(monthlyReport.total_worked_minutes / 60).toFixed(1)} giờ
                </Text>
                <Text style={[styles.reportLine, { color: colors.textSecondary }]}>
                  Đi muộn: {monthlyReport.total_late_minutes} phút · Về sớm: {monthlyReport.total_early_leave_minutes} phút
                </Text>
                <Text style={[styles.reportLine, { color: colors.textSecondary }]}>
                  Nghỉ phép: {monthlyReport.on_leave_days} ngày · Ngày lễ: {monthlyReport.holiday_days}
                </Text>
                <Text style={[styles.reportLine, { color: colors.textSecondary }]}>
                  Thiếu check-in/out: {monthlyReport.missing_check_in_days + monthlyReport.missing_check_out_days}
                </Text>
              </View>
            </>
          ) : <Text style={[styles.emptyText, { color: colors.textSecondary }]}>Chưa có báo cáo tháng.</Text>}
        </ScrollView>
      ) : activeTab === 'events' ? (
        <FlatList
          data={events}
          keyExtractor={(item) => item.event_id}
          renderItem={renderEventItem}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={fetchData} tintColor="#2563eb" />}
          contentContainerStyle={styles.listContainer}
          ListEmptyComponent={<FeedbackState description="Các lần nhận diện khuôn mặt sẽ được lưu tại đây." title="Chưa có sự kiện nhận diện" />}
        />
      ) : (
        <>
          {/* Create New Correction Request Trigger Button */}
          <TouchableOpacity
            style={[styles.createButton, { backgroundColor: isDarkMode ? '#3b82f6' : '#2563eb' }]}
            onPress={handleOpenNewCorrection}>
            <Plus size={20} color="#ffffff" style={styles.createBtnIcon} />
            <Text style={styles.createBtnText}>Tạo yêu cầu sửa công</Text>
          </TouchableOpacity>

          {loading ? (
            <ActivityIndicator size="large" color={colors.text} style={styles.loader} />
          ) : (
            <FlatList
              data={corrections}
              keyExtractor={(item) => item.request_id}
              renderItem={renderCorrectionItem}
              refreshControl={<RefreshControl refreshing={loading} onRefresh={fetchData} tintColor="#2563eb" />}
              contentContainerStyle={styles.listContainer}
              ListEmptyComponent={
                <View style={styles.emptyContainer}>
                  <FeedbackState description="Bạn có thể tạo yêu cầu khi giờ vào hoặc giờ ra chưa chính xác." title="Chưa có đơn sửa công" />
                </View>
              }
            />
          )}
        </>
      )}

      {/* Correction Request Modal Form */}
      <Modal visible={modalVisible} animationType="slide" onRequestClose={() => setModalVisible(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={[styles.modalContainer, { backgroundColor: colors.background, paddingTop: insets.top + 8 }]}> 
          <View style={styles.modalHeader}>
            <Text style={[styles.modalTitle, { color: colors.text }]}>
              {editingCorrection ? 'Cập nhật đơn sửa công' : selectedRecord ? 'Sửa giờ công theo ngày' : 'Tạo đơn sửa công mới'}
            </Text>
            <TouchableOpacity onPress={() => setModalVisible(false)}>
              <X size={24} color={colors.text} />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalScroll}>
            <DateTimeField
              disabled={Boolean(selectedRecord || editingCorrection)}
              label="Ngày cần chỉnh sửa *"
              maximumDate={new Date()}
              mode="date"
              onChange={setWorkDate}
              value={workDate}
            />
            <DateTimeField allowClear label="Giờ vào mới · không bắt buộc" mode="time" onChange={setCheckInTime} value={checkInTime} />
            <DateTimeField allowClear label="Giờ ra mới · không bắt buộc" mode="time" onChange={setCheckOutTime} value={checkOutTime} />

            <Text style={[styles.label, { color: colors.textSecondary }]}>Lý do chỉnh sửa *</Text>
            <View style={[styles.inputBox, { backgroundColor: colors.backgroundElement, height: 100 }]}>
              <TextInput
                style={[styles.input, { color: colors.text, textAlignVertical: 'top' }]}
                placeholder="Nhập lý do chi tiết (Ví dụ: quên check-out, thiết bị lỗi...)"
                placeholderTextColor={colors.textSecondary}
                value={reason}
                onChangeText={setReason}
                multiline
                numberOfLines={4}
              />
            </View>

            {submitting ? (
              <ActivityIndicator size="large" color={colors.text} style={styles.modalLoader} />
            ) : (
              <TouchableOpacity
                style={[styles.submitButton, { backgroundColor: isDarkMode ? '#3b82f6' : '#2563eb' }]}
                onPress={handleSubmitCorrection}>
                <Text style={styles.submitButtonText}>{editingCorrection ? 'Lưu thay đổi' : 'Gửi yêu cầu'}</Text>
              </TouchableOpacity>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      </Modal>

      <RequestDetailModal
        loading={detailLoading}
        logs={detailLogs.map((log) => ({ ...log, id: log.log_id }))}
        onClose={() => setDetailVisible(false)}
        rejectionReason={detailCorrection?.rejection_reason}
        rows={detailCorrection ? [
          {
            label: 'Ngày cần sửa',
            value: new Date(detailCorrection.requested_check_in || detailCorrection.requested_check_out || detailCorrection.created_at).toLocaleDateString('vi-VN'),
          },
          {
            label: 'Giờ đề nghị',
            value: `Vào: ${detailCorrection.requested_check_in ? new Date(detailCorrection.requested_check_in).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : 'Không đổi'} · Ra: ${detailCorrection.requested_check_out ? new Date(detailCorrection.requested_check_out).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }) : 'Không đổi'}`,
          },
          { label: 'Lý do', value: detailCorrection.reason },
          { label: 'Ngày gửi', value: new Date(detailCorrection.created_at).toLocaleString('vi-VN') },
        ] : []}
        status={detailCorrection ? getStatusBadge(detailCorrection.status) : undefined}
        title="Yêu cầu sửa công"
        visible={detailVisible}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  refreshButton: {
    padding: 8,
  },
  errorBanner: { alignItems: 'center', backgroundColor: '#fee2e2', borderRadius: 10, flexDirection: 'row', gap: 8, marginBottom: 14, padding: 10 },
  errorBannerText: { color: '#991b1b', flex: 1, fontSize: 12 },
  retryText: { color: '#b91c1c', fontSize: 12, fontWeight: '800' },
  screenTitle: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  screenSubtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  tabToggleRow: {
    flexDirection: 'row',
    height: 48,
    borderRadius: 10,
    padding: 4,
    marginBottom: 20,
    gap: 4,
  },
  tabToggleButton: {
    minWidth: 112,
    paddingHorizontal: 10,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 8,
  },
  tabToggleActiveButton: {
    // Styling defined dynamically through theme
  },
  tabToggleText: {
    fontSize: 14,
    fontWeight: '500',
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  monthPicker: { alignItems: 'center', borderRadius: 12, flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16, paddingHorizontal: 7, paddingVertical: 5 },
  monthButton: { alignItems: 'center', justifyContent: 'center', minHeight: 42, minWidth: 42 },
  monthLabel: { fontSize: 14, fontWeight: '800' },
  statBox: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  statNum: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  statLabel: {
    fontSize: 11,
    marginTop: 4,
    fontWeight: '600',
  },
  listContainer: {
    paddingBottom: 100,
  },
  loader: {
    marginTop: 50,
  },
  recordRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
  },
  recordLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconWrapper: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dateBlock: {
    justifyContent: 'center',
  },
  recordDate: {
    fontSize: 15,
    fontWeight: 'bold',
  },
  recordTimes: {
    fontSize: 12,
    marginTop: 2,
  },
  recordRight: {
    alignItems: 'flex-end',
  },
  requestCorrectionText: {
    fontSize: 11,
    fontWeight: '600',
    marginTop: 4,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    marginBottom: 4,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  workTimeText: {
    fontSize: 11,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 14,
  },
  createButton: {
    flexDirection: 'row',
    height: 52,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  createBtnIcon: {
    marginRight: 6,
  },
  createBtnText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: 'bold',
  },
  correctionCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
  },
  correctionActions: {
    flexDirection: 'row',
    gap: 8,
  },
  correctionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  correctionDate: {
    fontSize: 15,
    fontWeight: 'bold',
  },
  correctionTimes: {
    fontSize: 13,
    marginBottom: 6,
  },
  correctionReason: {
    fontSize: 13,
    marginBottom: 8,
  },
  rejectionBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(239, 68, 68, 0.08)',
    padding: 8,
    borderRadius: 6,
    marginBottom: 10,
  },
  rejectionText: {
    color: '#ef4444',
    fontSize: 12,
    fontWeight: '500',
    flex: 1,
  },
  eventCard: {
    borderRadius: 12,
    marginBottom: 12,
    padding: 14,
  },
  eventHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
  },
  eventTitle: {
    flex: 1,
    fontSize: 14,
    fontWeight: '700',
  },
  eventMeta: {
    fontSize: 12,
    marginTop: 5,
  },
  reportCard: {
    borderRadius: 14,
    gap: 7,
    padding: 18,
  },
  reportTitle: {
    fontSize: 17,
    fontWeight: '800',
  },
  reportLine: {
    fontSize: 13,
    lineHeight: 19,
  },
  cancelBtn: {
    alignSelf: 'flex-start',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    backgroundColor: '#fee2e2',
  },
  cancelBtnText: {
    color: '#ef4444',
    fontSize: 12,
    fontWeight: 'bold',
  },
  modalContainer: {
    flex: 1,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(150, 150, 150, 0.1)',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  modalScroll: {
    padding: 20,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 8,
  },
  inputBox: {
    borderRadius: 8,
    paddingHorizontal: 12,
    height: 48,
    justifyContent: 'center',
    marginBottom: 16,
  },
  input: {
    fontSize: 14,
    height: '100%',
  },
  submitButton: {
    height: 52,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 60,
  },
  submitButtonText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: 'bold',
  },
  modalLoader: {
    marginVertical: 20,
  },
});
