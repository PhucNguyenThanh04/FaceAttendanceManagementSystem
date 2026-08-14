import { CircleAlert, Inbox, RefreshCw } from 'lucide-react-native';
import { ReactNode } from 'react';
import { StyleSheet, Text, TouchableOpacity, View, useColorScheme } from 'react-native';

import { Colors } from '@/constants/theme';

type Props = {
  actionLabel?: string;
  description: string;
  icon?: ReactNode;
  onAction?: () => void;
  title: string;
  tone?: 'empty' | 'error';
};

export function FeedbackState({
  actionLabel = 'Thử lại',
  description,
  icon,
  onAction,
  title,
  tone = 'empty',
}: Props) {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'dark' ? 'dark' : 'light'];
  const accent = tone === 'error' ? '#dc2626' : '#64748b';
  return (
    <View accessibilityLiveRegion="polite" style={styles.container}>
      {icon ?? (tone === 'error' ? <CircleAlert color={accent} size={34} /> : <Inbox color={accent} size={34} />)}
      <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
      <Text style={[styles.description, { color: colors.textSecondary }]}>{description}</Text>
      {onAction ? (
        <TouchableOpacity accessibilityRole="button" onPress={onAction} style={styles.action}>
          <RefreshCw color="#2563eb" size={16} />
          <Text style={styles.actionText}>{actionLabel}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  action: { alignItems: 'center', flexDirection: 'row', gap: 7, marginTop: 5, minHeight: 44, paddingHorizontal: 12 },
  actionText: { color: '#2563eb', fontSize: 14, fontWeight: '800' },
  container: { alignItems: 'center', gap: 7, justifyContent: 'center', paddingHorizontal: 28, paddingVertical: 48 },
  description: { fontSize: 13, lineHeight: 19, maxWidth: 320, textAlign: 'center' },
  title: { fontSize: 16, fontWeight: '800', textAlign: 'center' },
});
