import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  TextInput,
  Alert,
  ScrollView,
  useColorScheme,
  RefreshControl,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAuthStore } from '@/stores/auth.store';
import { api } from '@/lib/axios';
import { Colors } from '@/constants/theme';
import { Plus, X, AlertCircle, RefreshCw } from 'lucide-react-native';
import { DateTimeField } from '@/components/ui/date-time-field';
import { FeedbackState } from '@/components/ui/feedback-state';
import { RequestDetailModal } from '@/components/ui/request-detail-modal';
import { getApiErrorMessage } from '@/lib/api-error';
import { formatDate, parseDateKey, toDateKey } from '@/lib/date';

interface LeaveBalance {
  year: number;
  total_allowed_days: number;
  total_used_days: number;
  total_remaining_days: number;
  items: {
    leave_type_id: number;
    name: string;
    code: string;
    used_days: number;
    remaining_days: number | null;
  }[];
}

interface LeaveRequest {
  request_id: string;
  leave_type_id: number;
  start_date: string;
  end_date: string;
  time_type: string;
  total_days: number;
  reason: string;
  status: string;
  created_at: string;
  rejection_reason?: string;
}

interface LeaveApprovalLog {
  log_id: number;
  action: string;
  comment: string | null;
  created_at: string;
}

interface LeaveType {
  leave_type_id: number;
  name: string;
  code: string;
  description: string | null;
  is_active?: boolean;
}

export default function LeavesScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'unspecified' ? 'light' : scheme];
  const isDarkMode = scheme === 'dark';
  const insets = useSafeAreaInsets();

  const { employee } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [balance, setBalance] = useState<LeaveBalance | null>(null);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Modal & Form State
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<LeaveRequest | null>(null);
  const [selectedType, setSelectedType] = useState<number | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reason, setReason] = useState('');
  const [timeType, setTimeType] = useState('full_day');
  const [submitting, setSubmitting] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailRequest, setDetailRequest] = useState<LeaveRequest | null>(null);
  const [detailLogs, setDetailLogs] = useState<LeaveApprovalLog[]>([]);

  const fetchData = useCallback(async () => {
    if (!employee) return;
    try {
      setLoading(true);
      setError(null);
      const [balanceResult, requestsResult, typesResult] = await Promise.allSettled([
        api.get(`/leaves/balance/${employee.employee_id}`),
        api.get('/leaves/requests', { params: { employee_id: employee.employee_id, page_size: 100 } }),
        api.get('/leaves/types'),
      ]);
      if (balanceResult.status === 'fulfilled') setBalance(balanceResult.value.data);
      if (requestsResult.status === 'fulfilled') setRequests(requestsResult.value.data.items || []);
      if (typesResult.status === 'fulfilled') {
        const activeTypes = (typesResult.value.data || []).filter(
          (type: LeaveType) => type.is_active !== false,
        );
        setLeaveTypes(activeTypes);
        if (activeTypes.length > 0) {
          setSelectedType((current) => current ?? activeTypes[0].leave_type_id);
        }
      }
      if (requestsResult.status === 'rejected') {
        setError(getApiErrorMessage(requestsResult.reason, 'Không thể tải danh sách đơn nghỉ phép.'));
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Không thể tải dữ liệu nghỉ phép.'));
    } finally {
      setLoading(false);
    }
  }, [employee]);

  useFocusEffect(useCallback(() => { fetchData(); }, [fetchData]));

  const handleOpenNewRequest = () => {
    setSelectedRequest(null);
    if (leaveTypes.length > 0) {
      setSelectedType(leaveTypes[0].leave_type_id);
    } else {
      setSelectedType(null);
    }
    const today = toDateKey(new Date());
    setStartDate(today);
    setEndDate(today);
    setReason('');
    setTimeType('full_day');
    setModalVisible(true);
  };

  const handleOpenEditRequest = (request: LeaveRequest) => {
    setSelectedRequest(request);
    setSelectedType(request.leave_type_id);
    setStartDate(request.start_date);
    setEndDate(request.end_date);
    setReason(request.reason);
    setTimeType(request.time_type);
    setModalVisible(true);
  };

  const handleSubmitRequest = async () => {
    if (!selectedType || !startDate || !endDate || !reason.trim()) {
      Alert.alert('Lỗi', 'Vui lòng điền đầy đủ các thông tin bắt buộc.');
      return;
    }

    // Simple date format validation YYYY-MM-DD
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(startDate) || !dateRegex.test(endDate)) {
      Alert.alert('Ngày chưa hợp lệ', 'Ngày cần có định dạng YYYY-MM-DD.');
      return;
    }

    if (parseDateKey(endDate) < parseDateKey(startDate)) {
      Alert.alert('Ngày chưa hợp lệ', 'Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.');
      return;
    }

    if ((timeType === 'morning' || timeType === 'afternoon') && startDate !== endDate) {
      Alert.alert('Ngày chưa hợp lệ', 'Nghỉ nửa ngày chỉ áp dụng trong cùng một ngày.');
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        leave_type_id: selectedType,
        start_date: startDate,
        end_date: endDate,
        time_type: timeType,
        reason: reason.trim(),
      };

      if (selectedRequest) {
        // Edit Mode
        await api.patch(`/leaves/requests/${selectedRequest.request_id}`, payload);
        Alert.alert('Thành công', 'Đã cập nhật đơn xin nghỉ phép thành công.');
      } else {
        // Create Mode
        await api.post('/leaves/requests', payload);
        Alert.alert('Thành công', 'Đã nộp đơn xin nghỉ phép thành công.');
      }

      setModalVisible(false);
      // Reset form
      setReason('');
      setStartDate('');
      setEndDate('');
      setSelectedRequest(null);
      fetchData();
    } catch (err: unknown) {
      Alert.alert('Không thể gửi đơn', getApiErrorMessage(err, 'Vui lòng thử lại.'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelRequest = (requestId: string) => {
    Alert.alert(
      'Hủy đơn',
      'Bạn có chắc chắn muốn hủy đơn xin nghỉ phép này không?',
      [
        { text: 'Hủy bỏ', style: 'cancel' },
        {
          text: 'Đồng ý',
          style: 'destructive',
          onPress: async () => {
            try {
              await api.post(`/leaves/requests/${requestId}/cancel`);
              Alert.alert('Thành công', 'Đã hủy đơn thành công.');
              fetchData();
            } catch (err: unknown) {
              Alert.alert('Không thể hủy đơn', getApiErrorMessage(err));
            }
          },
        },
      ]
    );
  };

  const handleShowRequestDetail = async (request: LeaveRequest) => {
    try {
      setDetailRequest(request);
      setDetailLogs([]);
      setDetailVisible(true);
      setDetailLoading(true);
      const [detailResponse, logsResponse] = await Promise.all([
        api.get<LeaveRequest>(`/leaves/requests/${request.request_id}`),
        api.get<LeaveApprovalLog[]>(`/leaves/requests/${request.request_id}/logs`),
      ]);
      setDetailRequest(detailResponse.data);
      setDetailLogs(logsResponse.data);
    } catch (error) {
      setDetailVisible(false);
      Alert.alert('Không thể tải chi tiết', getApiErrorMessage(error));
    } finally {
      setDetailLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <View style={[styles.badge, { backgroundColor: '#fef3c7' }]}><Text style={[styles.badgeText, { color: '#92400e' }]}>Đang chờ duyệt</Text></View>;
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

  const renderRequestItem = ({ item }: { item: LeaveRequest }) => {
    const typeName = leaveTypes.find(t => t.leave_type_id === item.leave_type_id)?.name || 'Nghỉ phép';
    const isPending = item.status === 'pending';

    return (
      <TouchableOpacity
        onPress={() => handleShowRequestDetail(item)}
        style={[styles.reqCard, { backgroundColor: colors.backgroundElement, borderColor: colors.backgroundSelected }]}>
        <View style={styles.reqHeader}>
          <Text style={[styles.reqType, { color: colors.text }]}>{typeName}</Text>
          {getStatusBadge(item.status)}
        </View>

        <Text style={[styles.reqDates, { color: colors.textSecondary }]}>
          {formatDate(item.start_date)} → {formatDate(item.end_date)} · {item.total_days} ngày
        </Text>
        <Text style={[styles.reqReason, { color: colors.text }]}>Lý do: {item.reason}</Text>

        {item.status === 'rejected' && item.rejection_reason && (
          <View style={styles.rejectionBox}>
            <AlertCircle size={14} color="#ef4444" />
            <Text style={styles.rejectionText}>Từ chối: {item.rejection_reason}</Text>
          </View>
        )}

        {isPending && (
          <View style={styles.actionRow}>
            <TouchableOpacity
              style={[styles.actionBtn, { backgroundColor: colors.backgroundSelected }]}
              onPress={() => handleOpenEditRequest(item)}>
              <Text style={[styles.actionBtnText, { color: colors.text }]}>Sửa đơn</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionBtn, { backgroundColor: '#fee2e2' }]}
              onPress={() => handleCancelRequest(item.request_id)}>
              <Text style={[styles.actionBtnText, { color: '#ef4444' }]}>Hủy đơn</Text>
            </TouchableOpacity>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + 12 }]}> 
      <View style={styles.header}>
        <View>
          <Text style={[styles.screenTitle, { color: colors.text }]}>Nghỉ phép</Text>
          <Text style={[styles.screenSubtitle, { color: colors.textSecondary }]}>Quản lý số phép và nộp đơn nghỉ</Text>
        </View>
        <TouchableOpacity accessibilityLabel="Tải lại" accessibilityRole="button" disabled={loading} onPress={fetchData} style={styles.refreshButton}>
          <RefreshCw size={20} color={colors.text} />
        </TouchableOpacity>
      </View>

      {/* Leave Balance Section */}
      {balance && (
        <View style={[styles.balanceCard, { backgroundColor: isDarkMode ? '#1e293b' : '#eff6ff' }]}>
          <Text style={[styles.balanceTitle, { color: isDarkMode ? '#60a5fa' : '#2563eb' }]}>Tổng quan phép năm {balance.year}</Text>
          <View style={styles.balanceGrid}>
            <View style={styles.balanceBox}>
              <Text style={[styles.balanceNum, { color: colors.text }]}>{balance.total_allowed_days}</Text>
              <Text style={[styles.balanceLabel, { color: colors.textSecondary }]}>Được nghỉ</Text>
            </View>
            <View style={styles.balanceBox}>
              <Text style={[styles.balanceNum, { color: '#f59e0b' }]}>{balance.total_used_days}</Text>
              <Text style={[styles.balanceLabel, { color: colors.textSecondary }]}>Đã sử dụng</Text>
            </View>
            <View style={styles.balanceBox}>
              <Text style={[styles.balanceNum, { color: '#10b981' }]}>{balance.total_remaining_days}</Text>
              <Text style={[styles.balanceLabel, { color: colors.textSecondary }]}>Còn lại</Text>
            </View>
          </View>
        </View>
      )}

      {/* Actions */}
      <TouchableOpacity
        accessibilityRole="button"
        disabled={!leaveTypes.length}
        style={[styles.createButton, { backgroundColor: isDarkMode ? '#3b82f6' : '#2563eb' }]}
        onPress={handleOpenNewRequest}>
        <Plus size={20} color="#ffffff" style={styles.createBtnIcon} />
        <Text style={styles.createBtnText}>Tạo đơn nghỉ phép</Text>
      </TouchableOpacity>

      <Text style={[styles.listTitle, { color: colors.text }]}>Lịch sử đơn nghỉ phép</Text>

      {loading && requests.length === 0 ? (
        <ActivityIndicator size="large" color={colors.text} style={styles.loader} />
      ) : error ? (
        <FeedbackState
          description="Dữ liệu hiện tại chưa thể đồng bộ với máy chủ."
          onAction={fetchData}
          title={error}
          tone="error"
        />
      ) : (
        <FlatList
          data={requests}
          keyExtractor={(item) => item.request_id}
          renderItem={renderRequestItem}
          refreshControl={<RefreshControl refreshing={loading} onRefresh={fetchData} tintColor="#2563eb" />}
          contentContainerStyle={styles.listContainer}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <FeedbackState description="Các đơn mới sẽ xuất hiện tại đây để bạn theo dõi trạng thái." title="Chưa có đơn nghỉ phép" />
            </View>
          }
        />
      )}

      {/* New/Edit Request Modal */}
      <Modal visible={modalVisible} animationType="slide" onRequestClose={() => setModalVisible(false)}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={[styles.modalContainer, { backgroundColor: colors.background, paddingTop: insets.top + 8 }]}> 
          <View style={styles.modalHeader}>
            <Text style={[styles.modalTitle, { color: colors.text }]}>
              {selectedRequest ? 'Cập nhật đơn nghỉ phép' : 'Đơn xin nghỉ phép mới'}
            </Text>
            <TouchableOpacity onPress={() => setModalVisible(false)}>
              <X size={24} color={colors.text} />
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.modalScroll}>
            {/* Leave Type Select */}
            <Text style={[styles.label, { color: colors.textSecondary }]}>Loại nghỉ phép *</Text>
            <View style={styles.typeSelectorRow}>
              {leaveTypes.map((type) => {
                const isSelected = selectedType === type.leave_type_id;
                return (
                  <TouchableOpacity
                    key={type.leave_type_id}
                    style={[
                      styles.typeOption,
                      { backgroundColor: colors.backgroundElement, borderColor: colors.backgroundSelected },
                      isSelected && { borderColor: isDarkMode ? '#60a5fa' : '#2563eb', borderWidth: 2 },
                    ]}
                    onPress={() => setSelectedType(type.leave_type_id)}>
                    <Text style={[styles.typeOptionText, { color: colors.text }, isSelected && { fontWeight: 'bold' }]}>
                      {type.name}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Time Type Select */}
            <Text style={[styles.label, { color: colors.textSecondary }]}>Thời gian nghỉ *</Text>
            <View style={styles.typeSelectorRow}>
              {[
                { id: 'full_day', label: 'Cả ngày' },
                { id: 'morning', label: 'Sáng' },
                { id: 'afternoon', label: 'Chiều' },
              ].map((t) => {
                const isSelected = timeType === t.id;
                return (
                  <TouchableOpacity
                    key={t.id}
                    style={[
                      styles.typeOption,
                      { backgroundColor: colors.backgroundElement, borderColor: colors.backgroundSelected },
                      isSelected && { borderColor: isDarkMode ? '#60a5fa' : '#2563eb', borderWidth: 2 },
                    ]}
                    onPress={() => {
                      setTimeType(t.id);
                      if (t.id !== 'full_day' && startDate) setEndDate(startDate);
                    }}>
                    <Text style={[styles.typeOptionText, { color: colors.text }, isSelected && { fontWeight: 'bold' }]}>
                      {t.label}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            <DateTimeField
              label="Từ ngày *"
              minimumDate={selectedRequest ? undefined : new Date()}
              mode="date"
              onChange={(value) => {
                setStartDate(value);
                if (!endDate || parseDateKey(endDate) < parseDateKey(value) || timeType !== 'full_day') setEndDate(value);
              }}
              value={startDate}
            />
            <DateTimeField
              disabled={timeType !== 'full_day'}
              label="Đến ngày *"
              minimumDate={parseDateKey(startDate)}
              mode="date"
              onChange={setEndDate}
              value={endDate}
            />

            {selectedType ? (
              <Text style={[styles.balanceHint, { color: colors.textSecondary }]}> 
                {(() => {
                  const item = balance?.items.find((entry) => entry.leave_type_id === selectedType);
                  return item?.remaining_days == null
                    ? 'Loại nghỉ này không giới hạn số dư.'
                    : `Số dư hiện tại: ${item.remaining_days} ngày`;
                })()}
              </Text>
            ) : null}

            {/* Reason */}
            <Text style={[styles.label, { color: colors.textSecondary }]}>Lý do xin nghỉ *</Text>
            <View style={[styles.inputBox, { backgroundColor: colors.backgroundElement, height: 100 }]}>
              <TextInput
                style={[styles.input, { color: colors.text, textAlignVertical: 'top' }]}
                placeholder="Nhập lý do nghỉ chi tiết..."
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
                onPress={handleSubmitRequest}>
                <Text style={styles.submitButtonText}>
                  {selectedRequest ? 'Cập nhật đơn' : 'Gửi đơn'}
                </Text>
              </TouchableOpacity>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      </Modal>

      <RequestDetailModal
        loading={detailLoading}
        logs={detailLogs.map((log) => ({ ...log, id: log.log_id }))}
        onClose={() => setDetailVisible(false)}
        rejectionReason={detailRequest?.rejection_reason}
        rows={detailRequest ? [
          { label: 'Thời gian nghỉ', value: `${formatDate(detailRequest.start_date)} → ${formatDate(detailRequest.end_date)} (${detailRequest.total_days} ngày)` },
          { label: 'Hình thức', value: detailRequest.time_type === 'full_day' ? 'Cả ngày' : detailRequest.time_type === 'morning' ? 'Buổi sáng' : 'Buổi chiều' },
          { label: 'Lý do', value: detailRequest.reason || 'Không có lý do' },
          { label: 'Ngày gửi', value: new Date(detailRequest.created_at).toLocaleString('vi-VN') },
        ] : []}
        status={detailRequest ? getStatusBadge(detailRequest.status) : undefined}
        title={detailRequest ? leaveTypes.find((type) => type.leave_type_id === detailRequest.leave_type_id)?.name ?? 'Đơn nghỉ phép' : 'Đơn nghỉ phép'}
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
    marginBottom: 20,
  },
  refreshButton: {
    padding: 8,
  },
  screenTitle: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  screenSubtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  balanceCard: {
    borderRadius: 14,
    padding: 16,
    marginBottom: 20,
  },
  balanceTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  balanceGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  balanceBox: {
    alignItems: 'center',
  },
  balanceNum: {
    fontSize: 22,
    fontWeight: 'bold',
  },
  balanceLabel: {
    fontSize: 11,
    marginTop: 4,
  },
  createButton: {
    flexDirection: 'row',
    height: 52,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  createBtnIcon: {
    marginRight: 6,
  },
  createBtnText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: 'bold',
  },
  listTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  listContainer: {
    paddingBottom: 100,
  },
  loader: {
    marginTop: 50,
  },
  reqCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
  },
  reqHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  reqType: {
    fontSize: 15,
    fontWeight: 'bold',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: 'bold',
  },
  reqDates: {
    fontSize: 13,
    marginBottom: 6,
  },
  reqReason: {
    fontSize: 13,
    marginBottom: 12,
  },
  rejectionBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(239, 68, 68, 0.08)',
    padding: 8,
    borderRadius: 6,
    marginBottom: 12,
  },
  rejectionText: {
    color: '#ef4444',
    fontSize: 12,
    fontWeight: '500',
    flex: 1,
  },
  actionRow: {
    flexDirection: 'row',
    gap: 10,
  },
  actionBtn: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionBtnText: {
    fontSize: 13,
    fontWeight: 'bold',
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
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 14,
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
  balanceHint: { fontSize: 12, fontWeight: '600', marginBottom: 14, marginTop: -5 },
  label: {
    fontSize: 13,
    fontWeight: '600',
    marginBottom: 8,
  },
  typeSelectorRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginBottom: 16,
  },
  typeOption: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    borderWidth: 1,
  },
  typeOptionText: {
    fontSize: 13,
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
