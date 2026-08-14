import axios from 'axios';

type ValidationIssue = { msg?: string };

export function getApiErrorMessage(
  error: unknown,
  fallback = 'Đã có lỗi xảy ra. Vui lòng thử lại.',
) {
  if (!axios.isAxiosError(error)) return fallback;

  if (!error.response) {
    return 'Không thể kết nối đến máy chủ. Hãy kiểm tra mạng và thử lại.';
  }

  const detail = error.response.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const message = detail
      .map((issue: ValidationIssue) => issue.msg)
      .filter(Boolean)
      .join('\n');
    if (message) return message;
  }

  if (error.response.status >= 500) {
    return 'Máy chủ đang gặp sự cố. Vui lòng thử lại sau.';
  }
  return fallback;
}
