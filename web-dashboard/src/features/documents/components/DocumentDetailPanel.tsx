import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Loading } from '@/components/ui/Loading'
import { StatusMessage } from '@/components/ui/StatusMessage'
import { DocumentStatusBadge } from '@/features/documents/components/DocumentStatusBadge'
import { documentApi } from '@/features/documents/api/document.api'
import { useDocumentDetail } from '@/features/documents/hooks/useDocumentDetail'
import { formatDateTime, getApiErrorMessage } from '@/lib/utils'

type DocumentDetailPanelProps = {
  documentId: string | null
}

export function DocumentDetailPanel({ documentId }: DocumentDetailPanelProps) {
  const [downloadError, setDownloadError] = useState<unknown>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const detailQuery = useDocumentDetail(documentId)
  const document = detailQuery.data

  if (!documentId) {
    return <p className="muted-text">Chọn một tài liệu để xem metadata trong vector store.</p>
  }

  if (detailQuery.isLoading) {
    return <Loading label="Đang tải chi tiết tài liệu" />
  }

  if (detailQuery.isError) {
    return (
      <StatusMessage tone="error">
        {getApiErrorMessage(detailQuery.error, 'Không thể tải chi tiết tài liệu.')}
      </StatusMessage>
    )
  }

  if (!document) {
    return null
  }

  const handleDownload = async () => {
    try {
      setDownloadError(null)
      setIsDownloading(true)
      const blob = await documentApi.downloadDocument(document.id)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = document.file_name
      window.document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      setDownloadError(error)
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="detail-list">
      <div>
        <span>Trạng thái</span>
        <DocumentStatusBadge status={document.status} />
      </div>
      <div>
        <span>ID</span>
        <strong className="mono-cell">{document.id}</strong>
      </div>
      <div>
        <span>File</span>
        <strong>{document.file_name}</strong>
      </div>
      <div>
        <span>Loại</span>
        <strong>{document.file_type.toUpperCase()}</strong>
      </div>
      <div>
        <span>Collection</span>
        <strong className="mono-cell">{document.qdrant_collection}</strong>
      </div>
      <div>
        <span>Chunks</span>
        <strong>{document.chunk_count}</strong>
      </div>
      <div>
        <span>Role</span>
        <strong>{document.allowed_roles.join(', ')}</strong>
      </div>
      <div>
        <span>Ngày tạo</span>
        <strong>{formatDateTime(document.created_at)}</strong>
      </div>
      <Button
        isLoading={isDownloading}
        onClick={handleDownload}
        variant="secondary"
      >
        Tải file an toàn
      </Button>
      {downloadError ? (
        <StatusMessage tone="error">
          {getApiErrorMessage(downloadError, 'Không thể tải tài liệu.')}
        </StatusMessage>
      ) : null}
    </div>
  )
}
