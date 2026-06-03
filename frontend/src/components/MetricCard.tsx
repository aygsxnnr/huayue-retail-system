import type { ReactNode } from 'react';
import { Card, Statistic } from 'antd';

interface MetricCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  prefix?: ReactNode;
  precision?: number;
}

export default function MetricCard({ title, value, suffix, prefix, precision }: MetricCardProps) {
  return (
    <Card className="metric-card">
      <Statistic
        title={title}
        value={value}
        suffix={suffix}
        prefix={prefix}
        precision={precision}
      />
    </Card>
  );
}
