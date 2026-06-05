import { useEffect, useMemo, useState } from 'react';
import type { Key } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message
} from 'antd';
import type { ColumnsType, TableRowSelection } from 'antd/es/table/interface';
import * as echarts from 'echarts';
import MetricCard from '../components/MetricCard';
import {
  batchResolveFinanceRecords,
  batchReconcileFinanceRecords,
  fetchFinanceRecords,
  fetchFinanceSummary,
  fetchPaymentRecords,
  fetchProfitTrend,
  fetchPromotionLoss,
  fetchStoreSettlement,
  resolveFinanceRecord,
  reconcileFinanceRecord,
  type CategoryProfit,
  type FinanceRecord,
  type FinanceSummary,
  type FinanceTrendPoint,
  type PaymentRecord,
  type ProductProfitRank,
  type PromotionLoss,
  type StoreSettlement
} from '../api/finance';

const ALL = '全部';
const CLOSED_STATUSES = ['已处理', '已关闭', '已对账', '已平账'];

const emptySummary: FinanceSummary = {
  today_order_amount: 0,
  today_payment_amount: 0,
  today_difference_amount: 0,
  pending_difference_count: 0,
  settled_count: 0,
  gross_profit: 0,
  gross_profit_rate: 0,
  promotion_discount_amount: 0
};

function safeNumber(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function money(value: unknown) {
  return `¥${safeNumber(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`;
}

function percent(value: unknown) {
  return `${safeNumber(value).toFixed(1)}%`;
}

function formatDate(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10) || '-';
  return date.toLocaleString('zh-CN');
}

function statusColor(status: string) {
  if (['已对账', '已处理', '已平账', '成功', '良好'].includes(status)) return 'green';
  if (['待对账', '待确认', '正常'].includes(status)) return 'blue';
  if (['待处理', '需关注'].includes(status)) return 'orange';
  if (['存在差异', '失败', '已退款', '异常', '已关闭'].includes(status)) return 'red';
  return 'default';
}

function timeValue(value?: string | null) {
  if (!value) return 0;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function numberSuffix(value?: string) {
  const digits = String(value || '').replace(/\D/g, '');
  return Number(digits || 0);
}

function financePriority(status: string) {
  const priority: Record<string, number> = {
    存在差异: 1,
    待处理: 2,
    待对账: 3,
    已处理: 4,
    已对账: 5,
    已平账: 5,
    已关闭: 6
  };
  return priority[status] ?? 7;
}

function paymentPriority(status: string) {
  const priority: Record<string, number> = {
    失败: 1,
    待确认: 2,
    已退款: 3,
    成功: 4
  };
  return priority[status] ?? 5;
}

function sortFinanceRecords(data: FinanceRecord[]) {
  return [...data].sort((a, b) => (
    financePriority(a.status) - financePriority(b.status) ||
    timeValue(b.reconciliation_time) - timeValue(a.reconciliation_time) ||
    numberSuffix(b.record_no) - numberSuffix(a.record_no) ||
    b.id - a.id
  ));
}

function sortPayments(data: PaymentRecord[]) {
  return [...data].sort((a, b) => (
    paymentPriority(a.payment_status) - paymentPriority(b.payment_status) ||
    timeValue(b.payment_time) - timeValue(a.payment_time) ||
    numberSuffix(b.payment_no) - numberSuffix(a.payment_no) ||
    b.id - a.id
  ));
}

function resolveBlockReason(record: FinanceRecord) {
  const status = record.status;
  const difference = safeNumber(record.difference_amount);
  if (status === '已处理') return '已处理记录不能重复处理';
  if (status === '已关闭') return '已关闭记录不能操作';
  if (status === '已对账' || status === '已平账') return '已平账记录无需处理';
  if (status === '待对账') return '该记录尚未执行对账，请先点击‘执行对账’。';
  if (status === '存在差异' || status === '待处理') return '';
  if (difference !== 0 && !CLOSED_STATUSES.includes(status)) return '';
  return '无差异金额，无需处理';
}

function canResolve(record: FinanceRecord) {
  return !resolveBlockReason(record);
}

function canReconcile(record: FinanceRecord) {
  return record.status === '待对账';
}

function reconcileButtonText(record: FinanceRecord) {
  return safeNumber(record.difference_amount) === 0 ? '确认平账' : '执行对账';
}

function LineChart({
  id,
  data,
  fields
}: {
  id: string;
  data: FinanceTrendPoint[];
  fields: Array<{ key: keyof FinanceTrendPoint; name: string }>;
}) {
  useEffect(() => {
    const node = document.getElementById(id);
    if (!node) return;
    const chart = echarts.init(node);
    chart.setOption({
      color: ['#1677ff', '#13c2c2', '#faad14'],
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 54, right: 24, top: 42, bottom: 36 },
      xAxis: { type: 'category', data: data.map((item) => item.date), axisTick: { show: false } },
      yAxis: { type: 'value', axisLabel: { formatter: (value: number) => `${value / 1000}k` } },
      series: fields.map((field) => ({
        name: field.name,
        type: 'line',
        smooth: true,
        data: data.map((item) => safeNumber(item[field.key]))
      }))
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [data, fields, id]);

  return data.length ? <div id={id} className="chart-box" /> : <Empty description="暂无图表数据" />;
}

function BarChart({
  id,
  names,
  series
}: {
  id: string;
  names: string[];
  series: Array<{ name: string; data: number[] }>;
}) {
  useEffect(() => {
    const node = document.getElementById(id);
    if (!node) return;
    const chart = echarts.init(node);
    chart.setOption({
      color: ['#1677ff', '#52c41a', '#faad14'],
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 58, right: 24, top: 42, bottom: 42 },
      xAxis: { type: 'category', data: names, axisLabel: { interval: 0, rotate: names.length > 5 ? 20 : 0 } },
      yAxis: { type: 'value', axisLabel: { formatter: (value: number) => `${value / 1000}k` } },
      series: series.map((item) => ({ ...item, type: 'bar', barMaxWidth: 28 }))
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [id, names, series]);

  return names.length ? <div id={id} className="chart-box" /> : <Empty description="暂无图表数据" />;
}

export default function FinanceReconciliation() {
  const [messageApi, contextHolder] = message.useMessage();
  const [summary, setSummary] = useState<FinanceSummary>(emptySummary);
  const [records, setRecords] = useState<FinanceRecord[]>([]);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [trend, setTrend] = useState<FinanceTrendPoint[]>([]);
  const [productRank, setProductRank] = useState<ProductProfitRank[]>([]);
  const [categoryProfit, setCategoryProfit] = useState<CategoryProfit[]>([]);
  const [promotionLoss, setPromotionLoss] = useState<PromotionLoss[]>([]);
  const [storeSettlement, setStoreSettlement] = useState<StoreSettlement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [recordStatus, setRecordStatus] = useState(ALL);
  const [recordStore, setRecordStore] = useState(ALL);
  const [recordKeyword, setRecordKeyword] = useState('');
  const [recordDate, setRecordDate] = useState('');
  const [paymentMethod, setPaymentMethod] = useState(ALL);
  const [paymentStatus, setPaymentStatus] = useState(ALL);
  const [paymentDate, setPaymentDate] = useState('');
  const [selectedRecordKeys, setSelectedRecordKeys] = useState<Key[]>([]);
  const [detailRecord, setDetailRecord] = useState<FinanceRecord | null>(null);
  const [detailPayment, setDetailPayment] = useState<PaymentRecord | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [summaryData, recordData, paymentData, profitData, storeData, promotionData] = await Promise.all([
        fetchFinanceSummary(),
        fetchFinanceRecords(),
        fetchPaymentRecords(),
        fetchProfitTrend(),
        fetchStoreSettlement(),
        fetchPromotionLoss()
      ]);
      setSummary(summaryData || emptySummary);
      setRecords(sortFinanceRecords(recordData || []));
      setPayments(sortPayments(paymentData || []));
      setTrend(profitData?.trend || []);
      setProductRank(profitData?.product_profit_rank || []);
      setCategoryProfit(profitData?.category_profit || []);
      setStoreSettlement(storeData || []);
      setPromotionLoss(promotionData || []);
    } catch {
      setError('财务对账与结算分析数据读取失败，请确认后端服务已启动并已重新 seed。');
      messageApi.error('财务数据读取失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const stores = useMemo(() => Array.from(new Set(records.map((item) => item.store_name).filter(Boolean))), [records]);
  const filteredRecords = useMemo(
    () =>
      sortFinanceRecords(records).filter((item) => (
        (recordStatus === ALL || item.status === recordStatus) &&
        (recordStore === ALL || item.store_name === recordStore) &&
        (!recordKeyword || item.order_no.includes(recordKeyword) || item.record_no.includes(recordKeyword)) &&
        (!recordDate || String(item.reconciliation_time).startsWith(recordDate))
      )),
    [recordDate, recordKeyword, recordStatus, recordStore, records]
  );
  const filteredPayments = useMemo(
    () =>
      sortPayments(payments).filter((item) => (
        (paymentMethod === ALL || item.payment_method === paymentMethod) &&
        (paymentStatus === ALL || item.payment_status === paymentStatus) &&
        (!paymentDate || String(item.payment_time).startsWith(paymentDate))
      )),
    [paymentDate, paymentMethod, paymentStatus, payments]
  );
  const pendingRecords = useMemo(
    () => sortFinanceRecords(records).filter((item) => canResolve(item) || item.status === '待对账' || safeNumber(item.difference_amount) !== 0),
    [records]
  );
  const statusStats = useMemo(() => (
    ['已对账', '存在差异', '待对账', '已处理'].map((status) => ({
      status,
      count: records.filter((item) => item.status === status).length
    }))
  ), [records]);
  const selectedRecords = useMemo(
    () => records.filter((item) => selectedRecordKeys.includes(item.id)),
    [records, selectedRecordKeys]
  );
  const selectedReconcileCount = selectedRecords.filter(canReconcile).length;
  const selectedResolveCount = selectedRecords.filter(canResolve).length;

  const handleResolve = async (record: FinanceRecord) => {
    const reason = resolveBlockReason(record);
    if (reason) {
      messageApi.warning(reason);
      return;
    }
    try {
      await resolveFinanceRecord(record.id);
      messageApi.success('差异已标记为已处理');
      await loadData();
    } catch {
      messageApi.error('标记已处理失败');
    }
  };

  const handleReconcile = async (record: FinanceRecord) => {
    if (!canReconcile(record)) {
      messageApi.warning('只有待对账记录可以执行对账');
      return;
    }
    try {
      const nextRecord = await reconcileFinanceRecord(record.id);
      if (nextRecord.status === '已平账' || nextRecord.status === '已对账') {
        messageApi.success('对账完成，记录已平账。');
      } else {
        messageApi.warning('对账完成，发现差异，请进行差异处理。');
      }
      await loadData();
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      messageApi.error(detail || '执行对账失败');
    }
  };

  const handleBatchResolve = async () => {
    const resolvableIds = records
      .filter((item) => selectedRecordKeys.includes(item.id) && canResolve(item))
      .map((item) => item.id);
    if (!resolvableIds.length) {
      messageApi.warning('请选择可标记已处理的差异记录');
      return;
    }
    try {
      const result = await batchResolveFinanceRecords(resolvableIds);
      if (result.failed_count) {
        messageApi.warning(`已处理 ${result.success_count} 条，${result.failed_count} 条未处理`);
      } else {
        messageApi.success(`已处理 ${result.success_count} 条差异记录`);
      }
      setSelectedRecordKeys([]);
      await loadData();
    } catch {
      messageApi.error('批量标记已处理失败');
    }
  };

  const handleBatchReconcile = async () => {
    const reconcileIds = records
      .filter((item) => selectedRecordKeys.includes(item.id) && canReconcile(item))
      .map((item) => item.id);
    if (!reconcileIds.length) {
      messageApi.warning('请选择待对账记录');
      return;
    }
    try {
      const result = await batchReconcileFinanceRecords(reconcileIds);
      if (result.failed_count) {
        messageApi.warning(`已完成 ${result.success_count} 条对账，${result.failed_count} 条未完成`);
      } else {
        messageApi.success(`已完成 ${result.success_count} 条对账`);
      }
      setSelectedRecordKeys([]);
      await loadData();
    } catch {
      messageApi.error('批量执行对账失败');
    }
  };

  const recordRowSelection: TableRowSelection<FinanceRecord> = {
    selectedRowKeys: selectedRecordKeys,
    onChange: setSelectedRecordKeys,
    getCheckboxProps: (record) => ({
      disabled: !canResolve(record) && !canReconcile(record)
    }),
    renderCell: (_checked, record, _index, originNode) => {
      const reason = canReconcile(record) ? '' : resolveBlockReason(record);
      return reason ? <Tooltip title={reason}>{originNode}</Tooltip> : originNode;
    }
  };

  const recordColumns: ColumnsType<FinanceRecord> = [
    { title: '财务记录号', dataIndex: 'record_no', width: 150 },
    { title: '订单编号', dataIndex: 'order_no', width: 150 },
    { title: '门店', dataIndex: 'store_name', width: 160 },
    { title: '收银员', dataIndex: 'cashier_name', width: 110 },
    { title: '订单金额', dataIndex: 'order_amount', width: 120, render: money, sorter: (a, b) => safeNumber(a.order_amount) - safeNumber(b.order_amount) },
    { title: '支付金额', dataIndex: 'payment_amount', width: 120, render: money, sorter: (a, b) => safeNumber(a.payment_amount) - safeNumber(b.payment_amount) },
    { title: '优惠金额', dataIndex: 'discount_amount', width: 120, render: money },
    {
      title: '差异金额',
      dataIndex: 'difference_amount',
      width: 120,
      render: (value: number) => <span className={safeNumber(value) ? 'danger-text' : ''}>{money(value)}</span>,
      sorter: (a, b) => safeNumber(a.difference_amount) - safeNumber(b.difference_amount)
    },
    { title: '支付方式', dataIndex: 'payment_method', width: 110 },
    { title: '对账状态', dataIndex: 'status', width: 110, render: (value: string) => <Tag color={statusColor(value)}>{value || '-'}</Tag> },
    { title: '对账时间', dataIndex: 'reconciliation_time', width: 160, render: formatDate, sorter: (a, b) => timeValue(a.reconciliation_time) - timeValue(b.reconciliation_time) },
    {
      title: '操作',
      width: 260,
      fixed: 'right',
      render: (_, record) => {
        const reason = resolveBlockReason(record);
        const resolveButton = <Button type="link" disabled={Boolean(reason)}>标记已处理</Button>;
        const reconcileButton = (
          <Popconfirm title={`确认对该记录执行对账吗？`} onConfirm={() => handleReconcile(record)}>
            <Button type="link">{reconcileButtonText(record)}</Button>
          </Popconfirm>
        );
        return (
          <Space>
            <Button type="link" onClick={() => setDetailRecord(record)}>查看详情</Button>
            {canReconcile(record) ? reconcileButton : (
              <Popconfirm title="确认将该差异记录标记为已处理吗？" onConfirm={() => handleResolve(record)} disabled={Boolean(reason)}>
                {reason ? <Tooltip title={reason}>{resolveButton}</Tooltip> : resolveButton}
              </Popconfirm>
            )}
            <Button type="link" onClick={() => messageApi.info(`差异说明：订单与支付差异 ${money(record.difference_amount)}`)}>
              生成差异说明
            </Button>
          </Space>
        );
      }
    }
  ];

  const paymentColumns: ColumnsType<PaymentRecord> = [
    { title: '支付流水号', dataIndex: 'payment_no', width: 160 },
    { title: '订单编号', dataIndex: 'order_no', width: 150 },
    { title: '门店', dataIndex: 'store_name', width: 160 },
    { title: '支付方式', dataIndex: 'payment_method', width: 120 },
    { title: '应付金额', dataIndex: 'payable_amount', width: 120, render: money, sorter: (a, b) => safeNumber(a.payable_amount) - safeNumber(b.payable_amount) },
    { title: '实付金额', dataIndex: 'paid_amount', width: 120, render: money, sorter: (a, b) => safeNumber(a.paid_amount) - safeNumber(b.paid_amount) },
    { title: '支付状态', dataIndex: 'payment_status', width: 110, render: (value: string) => <Tag color={statusColor(value)}>{value || '-'}</Tag> },
    { title: '支付时间', dataIndex: 'payment_time', width: 170, render: formatDate, sorter: (a, b) => timeValue(a.payment_time) - timeValue(b.payment_time) },
    { title: '第三方流水号', dataIndex: 'third_party_no', width: 190 },
    { title: '操作', width: 100, render: (_, record) => <Button type="link" onClick={() => setDetailPayment(record)}>查看</Button> }
  ];

  const productColumns: ColumnsType<ProductProfitRank> = [
    { title: '排名', dataIndex: 'rank', width: 80, render: (value: number) => <Tag color="blue">第{value}名</Tag> },
    { title: '商品名称', dataIndex: 'product_name' },
    { title: 'SKU', dataIndex: 'sku_code' },
    { title: '销售数量', dataIndex: 'sales_quantity' },
    { title: '销售额', dataIndex: 'sales_amount', render: money },
    { title: '成本金额', dataIndex: 'cost_amount', render: money },
    { title: '毛利额', dataIndex: 'gross_profit', render: money },
    { title: '毛利率', dataIndex: 'gross_profit_rate', render: percent }
  ];

  const categoryColumns: ColumnsType<CategoryProfit> = [
    { title: '商品分类', dataIndex: 'category' },
    { title: '销售额', dataIndex: 'sales_amount', render: money },
    { title: '成本金额', dataIndex: 'cost_amount', render: money },
    { title: '毛利额', dataIndex: 'gross_profit', render: money },
    { title: '毛利率', dataIndex: 'gross_profit_rate', render: percent }
  ];

  const promotionColumns: ColumnsType<PromotionLoss> = [
    { title: '活动编号', dataIndex: 'promotion_code' },
    { title: '活动名称', dataIndex: 'promotion_name' },
    { title: '活动类型', dataIndex: 'promotion_type' },
    { title: '参与订单数', dataIndex: 'order_count' },
    { title: '促销前金额', dataIndex: 'original_amount', render: money },
    { title: '优惠金额', dataIndex: 'discount_amount', render: money },
    { title: '实收金额', dataIndex: 'paid_amount', render: money },
    { title: '成本金额', dataIndex: 'cost_amount', render: money },
    { title: '毛利额', dataIndex: 'gross_profit', render: money },
    { title: '毛利率', dataIndex: 'gross_profit_rate', render: percent },
    { title: '活动状态', dataIndex: 'status', render: (value: string) => <Tag color={statusColor(value)}>{value || '-'}</Tag> }
  ];

  const storeColumns: ColumnsType<StoreSettlement> = [
    { title: '门店名称', dataIndex: 'store_name' },
    { title: '销售额', dataIndex: 'sales_amount', render: money },
    { title: '订单数', dataIndex: 'order_count' },
    { title: '客单价', dataIndex: 'average_order_value', render: money },
    { title: '成本金额', dataIndex: 'cost_amount', render: money },
    { title: '毛利额', dataIndex: 'gross_profit', render: money },
    { title: '毛利率', dataIndex: 'gross_profit_rate', render: percent },
    { title: '促销优惠金额', dataIndex: 'promotion_discount_amount', render: money },
    { title: '对账差异金额', dataIndex: 'difference_amount', render: money },
    { title: '结算状态', dataIndex: 'settlement_status', render: (value: string) => <Tag color={statusColor(value)}>{value || '-'}</Tag> }
  ];

  if (error) return <Alert type="error" message={error} showIcon />;

  return (
    <div className="finance-page">
      {contextHolder}
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>财务对账与结算分析</Typography.Title>
          <Typography.Text type="secondary">收银对账、支付流水、差异处理、毛利趋势、促销损益与门店结算分析</Typography.Text>
        </div>
        <Tag color="blue">第七阶段功能</Tag>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}><MetricCard title="今日订单金额" value={safeNumber(summary.today_order_amount)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="今日支付金额" value={safeNumber(summary.today_payment_amount)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="今日对账差异" value={safeNumber(summary.today_difference_amount)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="待处理差异笔数" value={safeNumber(summary.pending_difference_count)} suffix="笔" /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="已平账笔数" value={safeNumber(summary.settled_count)} suffix="笔" /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="毛利额" value={safeNumber(summary.gross_profit)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="毛利率" value={safeNumber(summary.gross_profit_rate)} suffix="%" precision={1} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="促销优惠金额" value={safeNumber(summary.promotion_discount_amount)} prefix="¥" precision={2} /></Col>
      </Row>

      <Card className="inventory-section">
        <Tabs
          items={[
            {
              key: 'overview',
              label: '对账总览',
              children: (
                <>
                  <Row gutter={[16, 16]}>
                    {statusStats.map((item) => (
                      <Col xs={24} sm={12} lg={6} key={item.status}>
                        <Card>
                          <Typography.Text type="secondary">{item.status}</Typography.Text>
                          <Typography.Title level={3}>{item.count}</Typography.Title>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                  <Row gutter={[16, 16]} className="inventory-section">
                    <Col xs={24} lg={12}>
                      <Card title="最近7日订单金额与支付金额趋势">
                        <LineChart id="finance-order-payment-chart" data={trend} fields={[{ key: 'order_amount', name: '订单金额' }, { key: 'payment_amount', name: '支付金额' }]} />
                      </Card>
                    </Col>
                    <Col xs={24} lg={12}>
                      <Card title="最近7日差异金额趋势">
                        <LineChart id="finance-difference-chart" data={trend} fields={[{ key: 'difference_amount', name: '差异金额' }]} />
                      </Card>
                    </Col>
                  </Row>
                  <Card title="待处理差异列表" className="inventory-section">
                    <Table rowKey="id" loading={loading} columns={recordColumns} dataSource={pendingRecords} scroll={{ x: 1700 }} pagination={{ pageSize: 6 }} />
                  </Card>
                </>
              )
            },
            {
              key: 'records',
              label: '收银对账',
              children: (
                <>
                  <Space className="inventory-toolbar" wrap>
                    <Popconfirm
                      title={`确认对选中的 ${selectedReconcileCount} 条待对账记录执行对账吗？`}
                      disabled={!selectedReconcileCount}
                      onConfirm={handleBatchReconcile}
                    >
                      <Button type="primary" disabled={!selectedReconcileCount}>批量执行对账</Button>
                    </Popconfirm>
                    <Popconfirm
                      title={`确认将选中的 ${selectedResolveCount} 条差异记录标记为已处理吗？`}
                      disabled={!selectedResolveCount}
                      onConfirm={handleBatchResolve}
                    >
                      <Button disabled={!selectedResolveCount}>批量标记已处理</Button>
                    </Popconfirm>
                    <Input placeholder="日期 YYYY-MM-DD" value={recordDate} onChange={(event) => setRecordDate(event.target.value)} style={{ width: 160 }} />
                    <Select value={recordStore} onChange={setRecordStore} options={[ALL, ...stores].map((value) => ({ value, label: value }))} style={{ width: 180 }} />
                    <Select value={recordStatus} onChange={setRecordStatus} options={[ALL, '已对账', '存在差异', '待处理', '待对账', '已处理', '已关闭'].map((value) => ({ value, label: value }))} style={{ width: 150 }} />
                    <Input.Search placeholder="订单编号 / 财务记录号" allowClear value={recordKeyword} onChange={(event) => setRecordKeyword(event.target.value)} style={{ width: 240 }} />
                    <Button onClick={() => { setRecordDate(''); setRecordStore(ALL); setRecordStatus(ALL); setRecordKeyword(''); setSelectedRecordKeys([]); }}>重置</Button>
                  </Space>
                  <Table
                    rowKey="id"
                    loading={loading}
                    rowSelection={recordRowSelection}
                    columns={recordColumns}
                    dataSource={filteredRecords}
                    scroll={{ x: 1780 }}
                    pagination={{ pageSize: 8 }}
                  />
                </>
              )
            },
            {
              key: 'payments',
              label: '支付流水',
              children: (
                <>
                  <Space className="inventory-toolbar" wrap>
                    <Select value={paymentMethod} onChange={setPaymentMethod} options={[ALL, '微信支付', '支付宝', '银联卡', '现金'].map((value) => ({ value, label: value }))} style={{ width: 150 }} />
                    <Select value={paymentStatus} onChange={setPaymentStatus} options={[ALL, '成功', '失败', '已退款', '待确认'].map((value) => ({ value, label: value }))} style={{ width: 150 }} />
                    <Input placeholder="日期 YYYY-MM-DD" value={paymentDate} onChange={(event) => setPaymentDate(event.target.value)} style={{ width: 160 }} />
                    <Button onClick={() => { setPaymentMethod(ALL); setPaymentStatus(ALL); setPaymentDate(''); }}>重置</Button>
                  </Space>
                  <Table rowKey="id" loading={loading} columns={paymentColumns} dataSource={filteredPayments} scroll={{ x: 1450 }} pagination={{ pageSize: 8 }} />
                </>
              )
            },
            {
              key: 'profit',
              label: '毛利趋势',
              children: (
                <>
                  <Card title="最近7日销售额、成本金额、毛利额趋势">
                    <LineChart id="finance-profit-trend-chart" data={trend} fields={[{ key: 'sales_amount', name: '销售额' }, { key: 'cost_amount', name: '成本金额' }, { key: 'gross_profit', name: '毛利额' }]} />
                  </Card>
                  <Row gutter={[16, 16]} className="inventory-section">
                    <Col xs={24} lg={14}><Card title="商品毛利排行表"><Table rowKey="rank" columns={productColumns} dataSource={productRank} pagination={{ pageSize: 6 }} /></Card></Col>
                    <Col xs={24} lg={10}><Card title="品类毛利分析表"><Table rowKey="category" columns={categoryColumns} dataSource={categoryProfit} pagination={false} /></Card></Col>
                  </Row>
                </>
              )
            },
            {
              key: 'promotion',
              label: '促销损益',
              children: (
                <>
                  <Row gutter={[16, 16]}>
                    <Col xs={24} lg={12}><Card title="促销优惠金额"><BarChart id="promotion-discount-chart" names={promotionLoss.map((item) => item.promotion_name || '-')} series={[{ name: '优惠金额', data: promotionLoss.map((item) => safeNumber(item.discount_amount)) }]} /></Card></Col>
                    <Col xs={24} lg={12}><Card title="促销带动销售额"><BarChart id="promotion-sales-chart" names={promotionLoss.map((item) => item.promotion_name || '-')} series={[{ name: '实收金额', data: promotionLoss.map((item) => safeNumber(item.paid_amount)) }]} /></Card></Col>
                  </Row>
                  <Card title="促销损益分析表" className="inventory-section"><Table rowKey="promotion_id" columns={promotionColumns} dataSource={promotionLoss} scroll={{ x: 1300 }} /></Card>
                </>
              )
            },
            {
              key: 'store',
              label: '门店结算',
              children: (
                <>
                  <Card title="门店销售额与毛利额对比">
                    <BarChart id="store-settlement-chart" names={storeSettlement.map((item) => item.store_name || '-')} series={[{ name: '销售额', data: storeSettlement.map((item) => safeNumber(item.sales_amount)) }, { name: '毛利额', data: storeSettlement.map((item) => safeNumber(item.gross_profit)) }]} />
                  </Card>
                  <Card title="门店结算分析表" className="inventory-section"><Table rowKey="store_id" columns={storeColumns} dataSource={storeSettlement} scroll={{ x: 1300 }} /></Card>
                </>
              )
            }
          ]}
        />
      </Card>

      <Modal title="财务记录详情" open={Boolean(detailRecord)} onCancel={() => setDetailRecord(null)} footer={<Button onClick={() => setDetailRecord(null)}>关闭</Button>}>
        {detailRecord && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="财务记录号">{detailRecord.record_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="订单编号">{detailRecord.order_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="门店">{detailRecord.store_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="订单金额">{money(detailRecord.order_amount)}</Descriptions.Item>
            <Descriptions.Item label="支付金额">{money(detailRecord.payment_amount)}</Descriptions.Item>
            <Descriptions.Item label="优惠金额">{money(detailRecord.discount_amount)}</Descriptions.Item>
            <Descriptions.Item label="差异金额">{money(detailRecord.difference_amount)}</Descriptions.Item>
            <Descriptions.Item label="对账状态"><Tag color={statusColor(detailRecord.status)}>{detailRecord.status || '-'}</Tag></Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      <Modal title="支付流水详情" open={Boolean(detailPayment)} onCancel={() => setDetailPayment(null)} footer={<Button onClick={() => setDetailPayment(null)}>关闭</Button>}>
        {detailPayment && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="支付流水号">{detailPayment.payment_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="订单编号">{detailPayment.order_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="门店">{detailPayment.store_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="收银员">{detailPayment.cashier_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="支付方式">{detailPayment.payment_method || '-'}</Descriptions.Item>
            <Descriptions.Item label="应付金额">{money(detailPayment.payable_amount)}</Descriptions.Item>
            <Descriptions.Item label="实付金额">{money(detailPayment.paid_amount)}</Descriptions.Item>
            <Descriptions.Item label="支付状态"><Tag color={statusColor(detailPayment.payment_status)}>{detailPayment.payment_status || '-'}</Tag></Descriptions.Item>
            <Descriptions.Item label="支付时间">{formatDate(detailPayment.payment_time)}</Descriptions.Item>
            <Descriptions.Item label="第三方流水号">{detailPayment.third_party_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="关联对账记录号">{detailPayment.finance_record_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="差异金额">{money(detailPayment.difference_amount)}</Descriptions.Item>
            <Descriptions.Item label="备注">{detailPayment.remark || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
