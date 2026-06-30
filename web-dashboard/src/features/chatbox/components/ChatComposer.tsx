import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/Button'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { Textarea } from '@/components/ui/Textarea'
import {
  sendMessageSchema,
  type SendMessageFormValues,
} from '@/features/chatbox/schemas/chatbox.schema'
import { getApiErrorMessage } from '@/lib/utils'

type ChatComposerProps = {
  error: unknown
  isError: boolean
  isSending: boolean
  onSend: (message: string) => void
  selectedConversationId: string | null
}

export function ChatComposer({
  error,
  isError,
  isSending,
  onSend,
  selectedConversationId,
}: ChatComposerProps) {
  const {
    formState: { errors },
    handleSubmit,
    register,
    reset,
  } = useForm<SendMessageFormValues>({
    resolver: zodResolver(sendMessageSchema),
    defaultValues: {
      message: '',
    },
  })

  const onSubmit = (values: SendMessageFormValues) => {
    onSend(values.message)
    reset()
  }

  return (
    <form className="chat-composer" onSubmit={handleSubmit(onSubmit)}>
      <Textarea
        error={errors.message?.message}
        id="chat-message-input"
        label={selectedConversationId ? 'Tin nhắn' : 'Tin nhắn đầu tiên'}
        placeholder="Nhập câu hỏi về chính sách, tài liệu hoặc quy trình..."
        rows={4}
        {...register('message')}
      />
      {isError ? (
        <StatusMessage tone="error">
          {getApiErrorMessage(error, 'Không thể gửi tin nhắn.')}
        </StatusMessage>
      ) : null}
      <Button isLoading={isSending} type="submit">
        Gửi
      </Button>
    </form>
  )
}
