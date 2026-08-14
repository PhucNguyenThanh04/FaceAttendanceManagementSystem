import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';
import { CalendarDays, Clock3, X } from 'lucide-react-native';
import { useState } from 'react';
import { Platform, StyleSheet, Text, TouchableOpacity, View, useColorScheme } from 'react-native';

import { Colors } from '@/constants/theme';
import { formatDate, parseDateKey, parseTimeKey, toDateKey, toTimeKey } from '@/lib/date';

type Props = {
  disabled?: boolean;
  allowClear?: boolean;
  label: string;
  maximumDate?: Date;
  minimumDate?: Date;
  mode: 'date' | 'time';
  onChange: (value: string) => void;
  value: string;
};

export function DateTimeField({
  disabled,
  allowClear,
  label,
  maximumDate,
  minimumDate,
  mode,
  onChange,
  value,
}: Props) {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'dark' ? 'dark' : 'light'];
  const [visible, setVisible] = useState(false);
  const selected = mode === 'date' ? parseDateKey(value || toDateKey(new Date())) : parseTimeKey(value);

  const handleChange = (event: DateTimePickerEvent, date?: Date) => {
    if (Platform.OS === 'android' || event.type === 'dismissed') setVisible(false);
    if (event.type === 'dismissed' || !date) return;
    onChange(mode === 'date' ? toDateKey(date) : toTimeKey(date));
  };

  return (
    <View style={styles.group}>
      <Text style={[styles.label, { color: colors.textSecondary }]}>{label}</Text>
      <View style={[styles.field, { backgroundColor: colors.backgroundElement, opacity: disabled ? 0.55 : 1 }]}>
        <TouchableOpacity
          accessibilityHint={`Mở bộ chọn ${mode === 'date' ? 'ngày' : 'giờ'}`}
          accessibilityRole="button"
          disabled={disabled}
          onPress={() => setVisible(true)}
          style={styles.fieldAction}>
          {mode === 'date' ? <CalendarDays color="#2563eb" size={19} /> : <Clock3 color="#2563eb" size={19} />}
          <Text style={[styles.value, { color: value ? colors.text : colors.textSecondary }]}>
            {value
              ? mode === 'date'
                ? formatDate(value, { day: '2-digit', month: '2-digit', year: 'numeric' })
                : value
              : mode === 'date'
                ? 'Chọn ngày'
                : 'Không thay đổi'}
          </Text>
        </TouchableOpacity>
        {allowClear && value && !disabled ? (
          <TouchableOpacity accessibilityLabel="Xóa giá trị" accessibilityRole="button" onPress={() => onChange('')} style={styles.clearButton}>
            <X color={colors.textSecondary} size={18} />
          </TouchableOpacity>
        ) : null}
      </View>
      {visible ? (
        <DateTimePicker
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          maximumDate={maximumDate}
          minimumDate={minimumDate}
          mode={mode}
          onChange={handleChange}
          value={selected}
        />
      ) : null}
      {visible && Platform.OS === 'ios' ? (
        <TouchableOpacity onPress={() => setVisible(false)} style={styles.doneButton}>
          <Text style={styles.doneText}>Xong</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  doneButton: { alignSelf: 'flex-end', paddingHorizontal: 10, paddingVertical: 7 },
  doneText: { color: '#2563eb', fontSize: 14, fontWeight: '800' },
  clearButton: { alignItems: 'center', justifyContent: 'center', minHeight: 44, minWidth: 36 },
  field: { alignItems: 'center', borderRadius: 10, flexDirection: 'row', minHeight: 50, paddingHorizontal: 8 },
  fieldAction: { alignItems: 'center', flex: 1, flexDirection: 'row', gap: 10, minHeight: 50, paddingHorizontal: 5 },
  group: { gap: 8, marginBottom: 16 },
  label: { fontSize: 13, fontWeight: '700' },
  value: { flex: 1, fontSize: 15, fontWeight: '600' },
});
