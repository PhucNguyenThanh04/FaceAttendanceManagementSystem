import { CalendarDays, Clock3 } from 'lucide-react-native';
import { StyleSheet, Text, TextInput, View, useColorScheme } from 'react-native';

import { Colors } from '@/constants/theme';

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

export function DateTimeField({ disabled, label, mode, onChange, value }: Props) {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'dark' ? 'dark' : 'light'];
  return (
    <View style={styles.group}>
      <Text style={[styles.label, { color: colors.textSecondary }]}>{label}</Text>
      <View style={[styles.field, { backgroundColor: colors.backgroundElement, opacity: disabled ? 0.55 : 1 }]}>
        {mode === 'date' ? <CalendarDays color="#2563eb" size={19} /> : <Clock3 color="#2563eb" size={19} />}
        <TextInput
          accessibilityLabel={label}
          editable={!disabled}
          maxLength={mode === 'date' ? 10 : 5}
          onChangeText={onChange}
          placeholder={mode === 'date' ? 'YYYY-MM-DD' : 'HH:MM'}
          placeholderTextColor={colors.textSecondary}
          style={[styles.input, { color: colors.text }]}
          value={value}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  field: { alignItems: 'center', borderRadius: 10, flexDirection: 'row', gap: 10, minHeight: 50, paddingHorizontal: 13 },
  group: { gap: 8, marginBottom: 16 },
  input: { flex: 1, fontSize: 15, minHeight: 48, outlineStyle: 'none' } as never,
  label: { fontSize: 13, fontWeight: '700' },
});
