import { useMutation, useQueryClient } from '@tanstack/react-query'
import { chatboxApi } from '@/features/chatbox/api/chatbox.api'
import type { ChatMessage, SendMessageResponse } from '@/features/chatbox/types/chatbox.types'

function buildAssistantMessage(data: SendMessageResponse): ChatMessage {
  return {
    ...data.assistant_message,
    ask_user: data.assistant_message.ask_user || data.ask_user,
    citations: data.assistant_message.citations?.length ? data.assistant_message.citations : data.citations,
    options: data.assistant_message.options?.length ? data.assistant_message.options : data.options,
  }
}

function mergeMessages(current: ChatMessage[] | undefined, incoming: ChatMessage[]): ChatMessage[] {
  const messages = current ? [...current] : []

  incoming.forEach((message) => {
    const existingIndex = messages.findIndex((item) => item.id === message.id)
    if (existingIndex >= 0) {
      messages[existingIndex] = message
      return
    }

    messages.push(message)
  })

  return messages
}

export function useSendMessage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: chatboxApi.sendMessage,
    onSuccess: (data, variables) => {
      queryClient.setQueryData<ChatMessage[]>(
        ['chatbox', 'messages', variables.conversationId],
        (current) => mergeMessages(current, [data.user_message, buildAssistantMessage(data)]),
      )
      queryClient.invalidateQueries({ queryKey: ['chatbox', 'conversations'] })
      queryClient.invalidateQueries({ queryKey: ['chatbox', 'messages', variables.conversationId] })
    },
  })
}
