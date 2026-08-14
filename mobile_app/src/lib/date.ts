export function toDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function parseDateKey(value: string) {
  const [year, month, day] = value.split('-').map(Number);
  const parsed = new Date(year, month - 1, day);
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
}

export function toTimeKey(date: Date) {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

export function parseTimeKey(value: string) {
  const parsed = new Date();
  const [hours, minutes] = value.split(':').map(Number);
  parsed.setHours(Number.isFinite(hours) ? hours : 8, Number.isFinite(minutes) ? minutes : 0, 0, 0);
  return parsed;
}

export function formatDate(value: string, options?: Intl.DateTimeFormatOptions) {
  return parseDateKey(value.slice(0, 10)).toLocaleDateString('vi-VN', options);
}
