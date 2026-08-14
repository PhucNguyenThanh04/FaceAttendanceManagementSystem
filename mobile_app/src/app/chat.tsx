import React, { useCallback, useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  useColorScheme,
  Alert,
} from 'react-native';
import { useAuthStore } from '@/stores/auth.store';
import { useFocusEffect } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { api } from '@/lib/axios';
import { Colors } from '@/constants/theme';
import { Send, Bot, User, Trash2 } from 'lucide-react-native';
import { FeedbackState } from '@/components/ui/feedback-state';
import { getApiErrorMessage } from '@/lib/api-error';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  options?: string[] | null;
}

const suggestions = [
  'Tôi còn bao nhiêu ngày phép?',
  'Quy định đi muộn như thế nào?',
  'Cách gửi yêu cầu sửa công?',
];

export default function ChatScreen() {
  const scheme = useColorScheme();
  const colors = Colors[scheme === 'unspecified' ? 'light' : scheme];
  const isDarkMode = scheme === 'dark';
  const insets = useSafeAreaInsets();

  const { employee } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const flatListRef = useRef<FlatList>(null);
  const optimisticId = useRef(0);

  const initializeChat = useCallback(async () => {
    if (!employee) return;
    try {
      setLoading(true);
      setError(null);
      // 1. Fetch conversations
      const convRes = await api.get('/chat/');
      const convs = convRes.data || [];

      let activeConvId = null;
      if (convs.length > 0) {
        activeConvId = convs[0].id;
      }

      setConversationId(activeConvId);

      // 2. Fetch messages in that conversation
      if (activeConvId) {
        const msgRes = await api.get(`/chat/${activeConvId}/messages`);
        setMessages(
          (msgRes.data || []).map((message: ChatMessage & { options?: unknown[] }) => ({
            ...message,
            options: message.options?.filter((option): option is string => typeof option === 'string') ?? [],
          })),
        );
      } else {
        setMessages([]);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Không thể mở trợ lý AI.'));
    } finally {
      setLoading(false);
    }
  }, [employee]);

  useFocusEffect(useCallback(() => { initializeChat(); }, [initializeChat]));

  const handleSendMessage = async (suggestedText?: string) => {
    const text = suggestedText ?? inputText;
    if (!text.trim() || sending) return;

    const userQuery = text.trim();
    setInputText('');
    setSending(true);
    setError(null);

    // Optimistically add user message to list
    const tempUserMsg: ChatMessage = {
      id: `optimistic-${++optimisticId.current}`,
      role: 'user',
      content: userQuery,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);

    try {
      const res = conversationId
        ? await api.post(`/chat/${conversationId}/messages`, { message: userQuery })
        : await api.post('/chat/new-message', { message: userQuery });

      if (!conversationId && res.data?.conversation?.id) {
        setConversationId(res.data.conversation.id);
      }

      // Backend returns SendMessageResponse with user_message and assistant_message
      if (res.data && res.data.assistant_message) {
        const assistantMsg: ChatMessage = {
          id: res.data.assistant_message.id,
          role: 'assistant',
          content: res.data.answer || res.data.assistant_message.content,
          created_at: res.data.assistant_message.created_at,
          options: res.data.options || res.data.assistant_message.options,
        };

        setMessages((prev) => {
          // Remove the optimistic user message and append the real backend user + assistant messages
          const filtered = prev.filter((m) => m.id !== tempUserMsg.id);
          const userMsg: ChatMessage = {
            id: res.data.user_message.id,
            role: 'user',
            content: res.data.user_message.content,
            created_at: res.data.user_message.created_at,
          };
          return [...filtered, userMsg, assistantMsg];
        });
      }
    } catch (err) {
      setMessages((prev) => prev.filter((message) => message.id !== tempUserMsg.id));
      setInputText(userQuery);
      setError(getApiErrorMessage(err, 'Trợ lý chưa thể trả lời. Nội dung của bạn đã được giữ lại để thử lại.'));
    } finally {
      setSending(false);
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  };

  const handleResetChat = async () => {
    if (!conversationId) return;
    Alert.alert(
      'Xóa cuộc trò chuyện',
      'Bạn có chắc muốn xóa lịch sử trò chuyện hiện tại và bắt đầu lại không?',
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Xóa',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              await api.delete(`/chat/${conversationId}`);
              setConversationId(null);
              setMessages([]);
              await initializeChat();
            } catch {
              Alert.alert('Lỗi', 'Không thể đặt lại cuộc trò chuyện.');
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const renderMessageItem = ({ item }: { item: ChatMessage }) => {
    const isUser = item.role === 'user';
    return (
      <View style={[styles.msgContainer, isUser ? styles.msgUserAlign : styles.msgAssistantAlign]}>
        {!isUser && (
          <View style={[styles.avatar, { backgroundColor: isDarkMode ? '#2e3135' : '#e0e7ff' }]}>
            <Bot size={16} color={isDarkMode ? '#60a5fa' : '#2563eb'} />
          </View>
        )}
        <View
          style={[
            styles.bubble,
            isUser
              ? [styles.bubbleUser, { backgroundColor: isDarkMode ? '#2563eb' : '#3b82f6' }]
              : [styles.bubbleAssistant, { backgroundColor: colors.backgroundElement }],
          ]}>
          <Text style={[styles.msgText, isUser ? styles.textWhite : { color: colors.text }]}> 
            {item.content}
          </Text>
          {!isUser && item.options?.length ? (
            <View style={styles.optionList}>
              {item.options.map((option) => (
                <TouchableOpacity accessibilityRole="button" key={option} onPress={() => handleSendMessage(option)} style={styles.optionButton}>
                  <Text style={styles.optionText}>{option}</Text>
                </TouchableOpacity>
              ))}
            </View>
          ) : null}
        </View>
        {isUser && (
          <View style={[styles.avatar, { backgroundColor: isDarkMode ? '#2563eb' : '#3b82f6' }]}>
            <User size={16} color="#ffffff" />
          </View>
        )}
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      style={[styles.container, { backgroundColor: colors.background, paddingTop: insets.top + 12 }]}> 
      
      {/* Title Header */}
      <View style={[styles.header, { borderBottomColor: colors.backgroundElement }]}>
        <View style={styles.headerTitleRow}>
          <Text style={[styles.title, { color: colors.text }]}>Trợ lý Quy chế AI</Text>
          {conversationId && (
            <TouchableOpacity accessibilityLabel="Xóa cuộc trò chuyện" accessibilityRole="button" onPress={handleResetChat} style={styles.trashBtn}>
              <Trash2 size={18} color="#ef4444" />
            </TouchableOpacity>
          )}
        </View>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
          Hỏi đáp về bảng công, lịch ca, và chính sách công ty
        </Text>
      </View>

      {loading ? (
        <View style={styles.loaderContainer}>
          <ActivityIndicator size="large" color={colors.text} />
        </View>
      ) : error && messages.length === 0 ? (
        <FeedbackState description="Kiểm tra kết nối mạng rồi thử mở lại cuộc trò chuyện." onAction={initializeChat} title={error} tone="error" />
      ) : (
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={renderMessageItem}
          contentContainerStyle={styles.messageList}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
          ListEmptyComponent={
            <View style={styles.emptyChat}>
              <Bot size={40} color={colors.textSecondary} />
              <Text style={[styles.emptyChatText, { color: colors.textSecondary }]}> 
                Tôi có thể giúp gì cho bạn hôm nay?
              </Text>
              <Text style={[styles.emptyChatCaption, { color: colors.textSecondary }]}>Chọn một câu hỏi gợi ý hoặc nhập câu hỏi riêng.</Text>
              <View style={styles.suggestionList}>
                {suggestions.map((suggestion) => (
                  <TouchableOpacity accessibilityRole="button" key={suggestion} onPress={() => handleSendMessage(suggestion)} style={[styles.suggestionButton, { borderColor: colors.backgroundSelected }]}> 
                    <Text style={[styles.suggestionText, { color: colors.text }]}>{suggestion}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          }
        />
      )}

      {/* Typing Indicator */}
      {sending && (
        <View style={styles.typingIndicator}>
          <ActivityIndicator size="small" color={colors.textSecondary} style={{ marginRight: 8 }} />
          <Text style={{ color: colors.textSecondary, fontSize: 13 }}>Trợ lý đang suy nghĩ...</Text>
        </View>
      )}

      {error && messages.length > 0 ? (
        <View style={styles.errorBar}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      {/* Input Row */}
      <View style={[styles.inputBar, { borderTopColor: colors.backgroundElement, paddingBottom: Math.max(insets.bottom, 12) }]}> 
        <TextInput
          style={[styles.input, { color: colors.text, backgroundColor: colors.backgroundElement }]}
          placeholder="Hỏi trợ lý quy chế..."
          placeholderTextColor={colors.textSecondary}
          value={inputText}
          onChangeText={setInputText}
          multiline
          maxLength={2000}
        />
        <TouchableOpacity
          style={[
            styles.sendButton,
            { backgroundColor: isDarkMode ? '#2563eb' : '#3b82f6' },
            !inputText.trim() && styles.disabledSend,
          ]}
          onPress={() => handleSendMessage()}
          disabled={!inputText.trim() || sending}>
          <Send size={18} color="#ffffff" />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
  },
  headerTitleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  trashBtn: {
    padding: 6,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  subtitle: {
    fontSize: 12,
    marginTop: 2,
  },
  loaderContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  messageList: {
    padding: 16,
    paddingBottom: 40,
  },
  msgContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 16,
    gap: 8,
    maxWidth: '85%',
  },
  msgUserAlign: {
    alignSelf: 'flex-end',
  },
  msgAssistantAlign: {
    alignSelf: 'flex-start',
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  bubble: {
    borderRadius: 16,
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  bubbleUser: {
    borderBottomRightRadius: 2,
  },
  bubbleAssistant: {
    borderBottomLeftRadius: 2,
  },
  msgText: {
    fontSize: 14,
    lineHeight: 20,
  },
  optionList: { gap: 7, marginTop: 10 },
  optionButton: { borderColor: '#93c5fd', borderRadius: 9, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 8 },
  optionText: { color: '#2563eb', fontSize: 13, fontWeight: '700' },
  textWhite: {
    color: '#ffffff',
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 8,
  },
  inputBar: {
    flexDirection: 'row',
    padding: 12,
    borderTopWidth: 1,
    alignItems: 'center',
    gap: 10,
    paddingBottom: Platform.OS === 'ios' ? 24 : 12,
  },
  input: {
    flex: 1,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    fontSize: 14,
    maxHeight: 100,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledSend: {
    opacity: 0.5,
  },
  emptyChat: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 100,
    gap: 12,
  },
  emptyChatText: {
    fontSize: 14,
    fontWeight: '500',
  },
  emptyChatCaption: { fontSize: 12, marginTop: -5, textAlign: 'center' },
  suggestionList: { gap: 8, marginTop: 10, width: '100%' },
  suggestionButton: { borderRadius: 12, borderWidth: 1, paddingHorizontal: 14, paddingVertical: 12 },
  suggestionText: { fontSize: 13, fontWeight: '600', textAlign: 'center' },
  errorBar: { backgroundColor: '#fee2e2', marginHorizontal: 12, paddingHorizontal: 12, paddingVertical: 9, borderRadius: 9 },
  errorText: { color: '#991b1b', fontSize: 12, lineHeight: 17 },
});
