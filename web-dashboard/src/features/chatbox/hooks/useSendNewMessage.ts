import { useMutation, useQueryClient } from '@tanstack/react-query'
import { chatboxApi } from '@/features/chatbox/api/chatbox.api'
import type {
  ChatMessage,
  Conversation,
  NewMessageResponse,
} from '@/features/chatbox/types/chatbox.types'

function buildAssistantMessage(data: NewMessageResponse): ChatMessage {
  return {
    ...data.assistant_message,
    ask_user: data.assistant_message.ask_user || data.ask_user,
    citations: data.assistant_message.citations?.length ? data.assistant_message.citations : data.citations,
    options: data.assistant_message.options?.length ? data.assistant_message.options : data.options,
  }
}

function mergeConversations(
  current: Conversation[] | undefined,
  conversation: Conversation,
): Conversation[] {
  const conversations = current ? [...current] : []
  const existingIndex = conversations.findIndex((item) => item.id === conversation.id)
  if (existingIndex >= 0) {
    conversations[existingIndex] = conversation
    return conversations
  }

  return [conversation, ...conversations]
}

export function useSendNewMessage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: chatboxApi.sendNewMessage,
    onSuccess: (data) => {
      queryClient.setQueryData<Conversation[]>(
        ['chatbox', 'conversations'],
        (current) => mergeConversations(current, data.conversation),
      )
      queryClient.setQueryData<ChatMessage[]>(
        ['chatbox', 'messages', data.conversation.id],
        [data.user_message, buildAssistantMessage(data)],
      )
      queryClient.invalidateQueries({ queryKey: ['chatbox', 'conversations'] })
      queryClient.invalidateQueries({ queryKey: ['chatbox', 'messages', data.conversation.id] })
    },
  })
}
