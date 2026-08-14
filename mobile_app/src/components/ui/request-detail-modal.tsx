import { ActivityIndicator, Modal, ScrollView, StyleSheet, Text, TouchableOpacity, View, useColorScheme } from 'react-native';
import { CalendarClock, X } from 'lucide-react-native';
import { ReactNode } from 'react';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Colors } from '@/constants/theme';

export type TimelineEntry = {
  action: string;
  comment: string | null;
  created_at: string;
  id: number | string;
};

type Props = {
  loading: boolean;
  logs: TimelineEntry[];
  onClose: () => void;
  rejectionReason?: string | null;
  rows: { label: string; value: string }[];
  status?: ReactNode;
  title: string;
  visible: boolean;
};

const actionLabels: Record<string, string> = {
  approved: 'Đã duyệt',
  cancelled: 'Đã hủy',
  created: 'Đã tạo yêu cầu',
  rejected: 'Đã từ chối',
  updated: 'Đã cập nhật',
};

export function RequestDetailModal({
  loading,
  logs,
  onClose,
  rejectionReason,
  rows,
  status,
  title,
  visible,
}: Props) {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'dark' ? 'dark' : 'light'];
  const insets = useSafeAreaInsets();

  return (
    <Modal animationType="slide" onRequestClose={onClose} presentationStyle="pageSheet" visible={visible}>
      <View style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + 8 }]}> 
        <View style={[styles.header, { borderBottomColor: colors.backgroundElement }]}> 
          <View style={styles.headerCopy}>
            <Text style={[styles.eyebrow, { color: colors.textSecondary }]}>CHI TIẾT YÊU CẦU</Text>
            <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
          </View>
          <TouchableOpacity accessibilityLabel="Đóng" accessibilityRole="button" onPress={onClose} style={styles.closeButton}>
            <X color={colors.text} size={22} />
          </TouchableOpacity>
        </View>

        {loading ? (
          <View style={styles.loading}>
            <ActivityIndicator color="#2563eb" size="large" />
            <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Đang tải lịch sử xử lý…</Text>
          </View>
        ) : (
          <ScrollView contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 30 }]}> 
            {status ? <View style={styles.statusRow}>{status}</View> : null}
            <View style={[styles.summaryCard, { backgroundColor: colors.backgroundElement }]}> 
              {rows.map((row) => (
                <View key={row.label} style={styles.row}>
                  <Text style={[styles.rowLabel, { color: colors.textSecondary }]}>{row.label}</Text>
                  <Text selectable style={[styles.rowValue, { color: colors.text }]}>{row.value}</Text>
                </View>
              ))}
            </View>

            {rejectionReason ? (
              <View style={styles.rejectionBox}>
                <Text style={styles.rejectionLabel}>LÝ DO TỪ CHỐI</Text>
                <Text style={styles.rejectionText}>{rejectionReason}</Text>
              </View>
            ) : null}

            <View style={styles.timelineHeading}>
              <CalendarClock color="#2563eb" size={19} />
              <Text style={[styles.timelineTitle, { color: colors.text }]}>Lịch sử xử lý</Text>
            </View>
            {logs.length ? (
              <View style={styles.timeline}>
                {logs.map((log, index) => (
                  <View key={log.id} style={styles.timelineItem}>
                    <View style={styles.timelineRail}>
                      <View style={styles.timelineDot} />
                      {index < logs.length - 1 ? <View style={styles.timelineLine} /> : null}
                    </View>
                    <View style={styles.timelineCopy}>
                      <Text style={[styles.timelineAction, { color: colors.text }]}>{actionLabels[log.action] ?? log.action}</Text>
                      <Text style={[styles.timelineDate, { color: colors.textSecondary }]}>{new Date(log.created_at).toLocaleString('vi-VN')}</Text>
                      {log.comment ? <Text style={[styles.timelineComment, { color: colors.textSecondary }]}>{log.comment}</Text> : null}
                    </View>
                  </View>
                ))}
              </View>
            ) : (
              <Text style={[styles.noLogs, { color: colors.textSecondary }]}>Yêu cầu chưa có lượt xử lý mới.</Text>
            )}
          </ScrollView>
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  closeButton: { alignItems: 'center', justifyContent: 'center', minHeight: 44, minWidth: 44 },
  container: { flex: 1 },
  content: { padding: 20 },
  eyebrow: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  header: { alignItems: 'center', borderBottomWidth: 1, flexDirection: 'row', paddingBottom: 12, paddingHorizontal: 20 },
  headerCopy: { flex: 1 },
  loading: { alignItems: 'center', flex: 1, gap: 12, justifyContent: 'center' },
  loadingText: { fontSize: 13 },
  noLogs: { fontSize: 13, paddingVertical: 18, textAlign: 'center' },
  rejectionBox: { backgroundColor: '#fee2e2', borderRadius: 12, gap: 5, marginTop: 14, padding: 14 },
  rejectionLabel: { color: '#b91c1c', fontSize: 10, fontWeight: '900', letterSpacing: 0.8 },
  rejectionText: { color: '#991b1b', fontSize: 13, lineHeight: 19 },
  row: { gap: 4 },
  rowLabel: { fontSize: 10, fontWeight: '800', letterSpacing: 0.7, textTransform: 'uppercase' },
  rowValue: { fontSize: 14, fontWeight: '600', lineHeight: 20 },
  statusRow: { alignItems: 'flex-start', marginBottom: 12 },
  summaryCard: { borderRadius: 15, gap: 15, padding: 17 },
  timeline: { marginTop: 2 },
  timelineAction: { fontSize: 14, fontWeight: '800' },
  timelineComment: { fontSize: 12, lineHeight: 18, marginTop: 5 },
  timelineCopy: { flex: 1, paddingBottom: 20 },
  timelineDate: { fontSize: 11, marginTop: 3 },
  timelineDot: { backgroundColor: '#2563eb', borderRadius: 5, height: 10, marginTop: 4, width: 10 },
  timelineHeading: { alignItems: 'center', flexDirection: 'row', gap: 8, marginBottom: 16, marginTop: 24 },
  timelineItem: { flexDirection: 'row', gap: 12 },
  timelineLine: { backgroundColor: '#bfdbfe', flex: 1, marginVertical: 4, width: 2 },
  timelineRail: { alignItems: 'center', width: 12 },
  timelineTitle: { fontSize: 16, fontWeight: '800' },
  title: { fontSize: 19, fontWeight: '800', marginTop: 2 },
});
