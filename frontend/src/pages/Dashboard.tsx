import { useEffect, useMemo, useState } from 'react';
import { Alert, Card, Col, Empty, List, Row, Segmented, Skeleton, Space, Switch, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import * as echarts from 'echarts';
import MetricCard from '../components/MetricCard';
import { fetchDashboard, type DashboardData, type LowStockItem } from '../api/dashboard';
import ResizableTable from '../components/ResizableTable';
import { periodOptions, timePeriodKey, type ChartPeriod } from '../utils/timeAggregation';

interface SalesTrendItem {
  date: string;
  sales_amount: number;
}


interface StoreRankItem {
  rank: number;
  store_name: string;
  sales_amount: number;
  order_count: number;
  status?: string;
}

interface ProductRankItem {
  id: number;
  product_name: string;
  sku_code: string;
  sales_quantity: number;
  sales_amount: number;
  inventory_status: '正常' | '低库存' | '缺货预警';
}

interface TodoItem {
  title: string;
  description: string;
  status: string;
  color: string;
}

const mockSalesTrend: SalesTrendItem[] = [
  { date: '05-29', sales_amount: 1680 },
  { date: '05-30', sales_amount: 2260 },
  { date: '05-31', sales_amount: 1980 },
  { date: '06-01', sales_amount: 3120 },
  { date: '06-02', sales_amount: 2840 },
  { date: '06-03', sales_amount: 3560 },
  { date: '06-04', sales_amount: 3980 }
];

const mockStoreRanks: StoreRankItem[] = [
  { rank: 1, store_name: '上海南京东路店', sales_amount: 4860, order_count: 18, status: '正常营业' },
  { rank: 2, store_name: '杭州湖滨银泰店', sales_amount: 3560, order_count: 14, status: '正常营业' },
  { rank: 3, store_name: '深圳万象天地店', sales_amount: 2980, order_count: 11, status: '正常营业' },
  { rank: 4, store_name: '广州天河城店', sales_amount: 1260, order_count: 5, status: '已关闭' }
];

const mockProductRanks: ProductRankItem[] = [
  { id: 1, product_name: '法式短款针织开衫', sku_code: 'P1001-BE-M', sales_quantity: 28, sales_amount: 5572, inventory_status: '正常' },
  { id: 2, product_name: '通勤直筒西装裤', sku_code: 'P1002-BK-M', sales_quantity: 21, sales_amount: 5439, inventory_status: '低库存' },
  { id: 3, product_name: '都市轻薄夹克', sku_code: 'P2001-GY-L', sales_quantity: 16, sales_amount: 5264, inventory_status: '正常' },
  { id: 4, product_name: '复古方头乐福鞋', sku_code: 'P3001-BR-38', sales_quantity: 12, sales_amount: 3588, inventory_status: '缺货预警' }
];

const mockTodos: TodoItem[] = [
  { title: '低库存预警', description: '部分畅销 SKU 已低于安全库存，请关注补货节奏。', status: '待处理', color: 'orange' },
  { title: '待审核补货申请', description: '上海南京东路店有 2 条补货申请等待审核。', status: '待审核', color: 'blue' },
  { title: '财务对账差异', description: '深圳万象天地店存在 1 笔模拟对账差异。', status: '需核对', color: 'red' },
  { title: '促销活动即将结束', description: '春装上新9折将在近期结束，请评估活动效果。', status: '即将结束', color: 'purple' }
];

function money(value: number) {
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function invalidStore(status?: string) {
  return ['已关闭', '停用', 'closed', 'disabled', 'inactive'].includes(String(status || '').toLowerCase()) || ['已关闭', '停用'].includes(status || '');
}

function aggregateSalesTrend(data: SalesTrendItem[], period: ChartPeriod) {
  const map = new Map<string, number>();
  data.forEach((item, index) => {
    const key = timePeriodKey(`2026-${item.date}`, period, index);
    map.set(key, (map.get(key) || 0) + Number(item.sales_amount || 0));
  });
  return Array.from(map.entries()).map(([date, sales_amount]) => ({ date, sales_amount }));
}

function getInventoryStatus(record: LowStockItem) {
  if (record.quantity <= 0) {
    return { text: '缺货预警', color: 'red' };
  }
  if (record.quantity < record.safety_stock) {
    return { text: '低库存', color: 'orange' };
  }
  return { text: '正常', color: 'green' };
}

function SalesTrendChart({ data }: { data: SalesTrendItem[] }) {
  useEffect(() => {
    const node = document.getElementById('sales-trend-chart');
    if (!node) return;
    const chart = echarts.init(node);
    chart.setOption({
      color: ['#1677ff'],
      tooltip: { trigger: 'axis' },
      grid: { left: 52, right: 24, top: 32, bottom: 38 },
      xAxis: {
        type: 'category',
        data: data.map((item) => item.date),
        boundaryGap: false,
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        name: '销售额',
        axisLabel: { formatter: (value: number) => `${value / 1000}k` },
        splitLine: { lineStyle: { color: '#edf2f7' } }
      },
      series: [
        {
          name: '销售额',
          type: 'line',
          smooth: true,
          symbolSize: 7,
          areaStyle: { color: 'rgba(22, 119, 255, 0.12)' },
          lineStyle: { width: 3 },
          data: data.map((item) => item.sales_amount)
        }
      ]
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [data]);

  return <div id="sales-trend-chart" className="chart-box" />;
}

function MemberRatioChart({ ratio }: { ratio: number }) {
  useEffect(() => {
    const node = document.getElementById('member-ratio-chart');
    if (!node) return;
    const chart = echarts.init(node);
    const percent = Math.round(ratio * 100);
    chart.setOption({
      color: ['#1677ff', '#dbeafe'],
      tooltip: { trigger: 'item' },
      series: [
        {
          name: '会员销售占比',
          type: 'pie',
          radius: ['62%', '82%'],
          label: {
            formatter: '{b}\n{d}%',
            color: '#334155'
          },
          data: [
            { value: percent, name: '会员销售' },
            { value: Math.max(0, 100 - percent), name: '非会员销售' }
          ]
        }
      ]
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [ratio]);

  return <div id="member-ratio-chart" className="chart-box chart-box-small" />;
}

function StoreRankChart({ data }: { data: StoreRankItem[] }) {
  useEffect(() => {
    const node = document.getElementById('store-rank-chart');
    if (!node) return;
    const chart = echarts.init(node);
    const sorted = [...data].sort((a, b) => a.sales_amount - b.sales_amount);
    chart.setOption({
      color: ['#1677ff'],
      tooltip: {
        trigger: 'axis',
        formatter: (params: unknown) => {
          const item = sorted[(params as Array<{ dataIndex: number }>)[0]?.dataIndex ?? 0];
          return `${item.store_name}<br/>门店状态：${item.status || '正常营业'}<br/>销售额：${money(item.sales_amount)}<br/>订单数：${item.order_count}笔`;
        }
      },
      grid: { left: 96, right: 28, top: 24, bottom: 28 },
      xAxis: {
        type: 'value',
        axisLabel: { formatter: (value: number) => `${value / 1000}k` },
        splitLine: { lineStyle: { color: '#edf2f7' } }
      },
      yAxis: {
        type: 'category',
        data: sorted.map((item) => invalidStore(item.status) ? `${item.store_name}（${item.status}）` : item.store_name),
        axisTick: { show: false }
      },
      series: [
        {
          name: '销售额',
          type: 'bar',
          barWidth: 22,
          data: sorted.map((item) => item.sales_amount),
          itemStyle: { borderRadius: [0, 4, 4, 0] },
          label: {
            show: true,
            position: 'right',
            formatter: (params: unknown) => money(Number((params as { value: number }).value))
          }
        }
      ]
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [data]);

  return <div id="store-rank-chart" className="chart-box chart-box-rank" />;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dashboardPeriod, setDashboardPeriod] = useState<ChartPeriod>('day');
  const [includeInvalidStores, setIncludeInvalidStores] = useState(false);

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch(() => setError('看板数据读取失败，请确认后端服务已启动。'))
      .finally(() => setLoading(false));
  }, []);

  const salesTrend = useMemo(() => aggregateSalesTrend(mockSalesTrend, dashboardPeriod), [dashboardPeriod]);
  const storeRanks = useMemo(
    () => mockStoreRanks.filter((item) => includeInvalidStores || !invalidStore(item.status)),
    [includeInvalidStores]
  );
  const productRanks = useMemo(() => mockProductRanks, []);
  const todos = useMemo(() => mockTodos, []);

  const lowStockColumns = useMemo<ColumnsType<LowStockItem>>(
    () => [
      {
        title: '门店',
        render: (_, record) => record.store?.name ?? '-'
      },
      {
        title: '商品',
        render: (_, record) => record.sku?.product?.name ?? '-'
      },
      {
        title: 'SKU',
        render: (_, record) => `${record.sku?.sku_code ?? '-'} / ${record.sku?.color ?? '-'} / ${record.sku?.size ?? '-'}`
      },
      {
        title: '当前库存',
        dataIndex: 'quantity',
        render: (value: number) => <span className={value <= 0 ? 'danger-text' : ''}>{value}</span>
      },
      {
        title: '安全库存',
        dataIndex: 'safety_stock'
      },
      {
        title: '在途',
        dataIndex: 'in_transit'
      },
      {
        title: '库存状态',
        render: (_, record) => {
          const status = getInventoryStatus(record);
          return <Tag color={status.color}>{status.text}</Tag>;
        }
      }
    ],
    []
  );

  const storeRankColumns = useMemo<ColumnsType<StoreRankItem>>(
    () => [
      { title: '排名', dataIndex: 'rank', width: 64, render: (rank: number) => <Tag color="blue">第{rank}名</Tag> },
      { title: '门店名称', render: (_, record) => invalidStore(record.status) ? `${record.store_name}（${record.status}）` : record.store_name },
      { title: '状态', dataIndex: 'status', render: (value: string) => <Tag color={invalidStore(value) ? 'red' : 'green'}>{value || '正常营业'}</Tag> },
      { title: '销售额', dataIndex: 'sales_amount', render: (value: number) => money(value) },
      { title: '成交笔数', dataIndex: 'order_count', render: (value: number) => `${value}笔` }
    ],
    []
  );

  const productRankColumns = useMemo<ColumnsType<ProductRankItem>>(
    () => [
      { title: '商品名称', dataIndex: 'product_name' },
      { title: 'SKU', dataIndex: 'sku_code' },
      { title: '销量', dataIndex: 'sales_quantity', render: (value: number) => `${value}件` },
      { title: '销售额', dataIndex: 'sales_amount', render: (value: number) => money(value) },
      {
        title: '库存状态',
        dataIndex: 'inventory_status',
        render: (value: ProductRankItem['inventory_status']) => {
          const color = value === '缺货预警' ? 'red' : value === '低库存' ? 'orange' : 'green';
          return <Tag color={color}>{value}</Tag>;
        }
      }
    ],
    []
  );

  if (loading) {
    return <Skeleton active paragraph={{ rows: 12 }} />;
  }

  if (error) {
    return <Alert type="error" message={error} showIcon />;
  }

  if (!data) {
    return <Empty description="暂无看板数据" />;
  }

  const { summary } = data;

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>经营总览看板</Typography.Title>
          <Typography.Text type="secondary">销售、库存、会员、财务核心指标总览</Typography.Text>
        </div>
        <Tag color="blue">实时演示数据</Tag>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard title="今日销售额" value={summary.sales_amount} prefix="¥" precision={2} />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard title="成交笔数" value={summary.order_count} suffix="笔" />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard title="客单价" value={summary.average_order_value} prefix="¥" precision={2} />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard title="会员销售占比" value={summary.member_sales_ratio * 100} suffix="%" precision={1} />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard title="缺货SKU数" value={summary.low_stock_sku_count} suffix="个" />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard title="库存周转天数" value={summary.inventory_turnover_days} suffix="天" precision={1} />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard title="毛利额" value={summary.gross_profit} prefix="¥" precision={2} />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <MetricCard title="销售健康度" value={summary.low_stock_sku_count > 6 ? '需关注' : '稳定'} />
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="dashboard-section">
        <Col xs={24} xl={16}>
          <Card title="销售趋势" extra={<Segmented size="small" value={dashboardPeriod} onChange={(value) => setDashboardPeriod(value as ChartPeriod)} options={[...periodOptions]} />}>
            <SalesTrendChart data={salesTrend} />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="会员销售结构">
            <MemberRatioChart ratio={summary.member_sales_ratio} />
            <div className="ratio-note">
              会员销售额占比 {Math.round(summary.member_sales_ratio * 100)}%，当前累计销售额 {money(summary.sales_amount)}。
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} className="dashboard-section">
        <Col xs={24} xl={15}>
          <Card title="门店销售排行" extra={<Space><span>包含无效门店</span><Switch size="small" checked={includeInvalidStores} onChange={setIncludeInvalidStores} /></Space>}>
            {storeRanks.length ? <StoreRankChart data={storeRanks} /> : <Empty description="暂无门店排行数据" />}
            <ResizableTable
              rowKey="rank"
              size="small"
              columns={storeRankColumns}
              dataSource={storeRanks}
              pagination={false}
            />
          </Card>
        </Col>
        <Col xs={24} xl={9}>
          <Card title="预警与待办">
            <List
              itemLayout="horizontal"
              dataSource={todos}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta title={item.title} description={item.description} />
                  <Tag color={item.color}>{item.status}</Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Card title="商品销售排行" className="dashboard-section">
        <ResizableTable
          rowKey="id"
          size="middle"
          columns={productRankColumns}
          dataSource={productRanks}
          pagination={false}
        />
      </Card>

      <Card title="低库存预警" className="dashboard-section">
        <ResizableTable
          rowKey="id"
          size="middle"
          columns={lowStockColumns}
          dataSource={data.low_stock_items}
          pagination={false}
        />
      </Card>
    </div>
  );
}
