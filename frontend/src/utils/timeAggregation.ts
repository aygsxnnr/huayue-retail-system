export type ChartPeriod = 'day' | 'week' | 'month' | 'quarter';

export const periodOptions = [
  { label: '日', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '季度', value: 'quarter' }
] as const;

function weekOfYear(date: Date) {
  const firstDay = new Date(date.getFullYear(), 0, 1);
  const dayOffset = Math.floor((date.getTime() - firstDay.getTime()) / 86400000);
  return Math.ceil((dayOffset + firstDay.getDay() + 1) / 7);
}

export function timePeriodKey(value: string | Date | null | undefined, period: ChartPeriod, fallbackIndex = 0) {
  if (!value) return '未知';
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return String(value || `未知${fallbackIndex + 1}`);
  const year = date.getFullYear();
  if (period === 'day') {
    return `${year}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }
  if (period === 'week') return `${year}-W${String(weekOfYear(date)).padStart(2, '0')}`;
  if (period === 'month') return `${year}-${String(date.getMonth() + 1).padStart(2, '0')}`;
  return `${year}-Q${Math.floor(date.getMonth() / 3) + 1}`;
}
