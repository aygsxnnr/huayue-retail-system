import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import * as echarts from 'echarts';
import dayjs from 'dayjs';
import MetricCard from '../components/MetricCard';
import { fetchProducts, type Product } from '../api/products';
import { fetchStores, type Store } from '../api/pos';
import {
  fetchCategoryAnalysis,
  fetchFinanceOverview,
  fetchInventoryHealth,
  fetchProductRanking,
  fetchPromotionEffect,
  fetchReportSummary,
  fetchSalesTrend,
  fetchStorePerformance,
  type CategoryAnalysis,
  type FinanceOverview,
  type FinanceOverviewRecord,
  type InventoryAlert,
  type InventoryHealth,
  type ProductRanking,
  type PromotionEffect,
  type ReportQuery,
  type ReportSummary,
  type SalesTrendPoint,
  type StorePerformance
} from '../api/reports';

const { RangePicker } = DatePicker;
const ALL = '全部';

const emptySummary: ReportSummary = {
  start_date: '',
  end_date: '',
  period: 'day',
  sales_total: 0,
  order_count: 0,
  average_order_value: 0,
  gross_profit: 0,
  gross_profit_rate: 0,
  payment_total: 0,
  difference_amount: 0,
  out_of_stock_sku_count: 0
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

function text(value: unknown) {
  if (value === undefined || value === null || value === '') return '-';
  return String(value);
}

function statusColor(status: string) {
  if (['正常', '已对账', '已平账', '已处理', '成功', '进行中'].includes(status)) return 'green';
  if (['待对账', '未开始'].includes(status)) return 'blue';
  if (['低库存', '待补货', '待处理'].includes(status)) return 'orange';
  if (['缺货预警', '存在差异', '已关闭', '失败', '已停用', '已结束'].includes(status)) return 'red';
  return 'default';
}

function defaultDateRange() {
  return [dayjs().subtract(6, 'day'), dayjs()] as [dayjs.Dayjs, dayjs.Dayjs];
}

function LineChart({ id, data }: { id: string; data: SalesTrendPoint[] }) {
  useEffect(() => {
    const node = document.getElementById(id);
    if (!node || !data.length) return;
    const chart = echarts.init(node);
    chart.setOption({
      color: ['#1677ff', '#52c41a'],
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 56, right: 28, top: 42, bottom: 36 },
      xAxis: { type: 'category', data: data.map((item) => item.date), axisTick: { show: false } },
      yAxis: [
        { type: 'value', name: '销售额', axisLabel: { formatter: (value: number) => `${value / 1000}k` } },
        { type: 'value', name: '订单数' }
      ],
      series: [
        { name: '销售额', type: 'line', smooth: true, data: data.map((item) => safeNumber(item.sales_amount)) },
        { name: '订单数', type: 'bar', yAxisIndex: 1, barMaxWidth: 24, data: data.map((item) => safeNumber(item.order_count)) }
      ]
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [data, id]);

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
    if (!node || !names.length) return;
    const chart = echarts.init(node);
    chart.setOption({
      color: ['#1677ff', '#52c41a', '#faad14'],
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 58, right: 28, top: 42, bottom: 42 },
      xAxis: { type: 'category', data: names, axisLabel: { interval: 0, rotate: names.length > 5 ? 24 : 0 } },
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

function PieChart({ id, data }: { id: string; data: Array<{ status: string; count: number }> }) {
  useEffect(() => {
    const node = document.getElementById(id);
    if (!node || !data.length) return;
    const chart = echarts.init(node);
    chart.setOption({
      color: ['#52c41a', '#faad14', '#ff4d4f', '#1677ff', '#13c2c2'],
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [
        {
          name: '状态分布',
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['50%', '44%'],
          data: data.map((item) => ({ name: item.status, value: safeNumber(item.count) }))
        }
      ]
    });
    const resize = () => chart.resize();
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [data, id]);

  return data.length ? <div id={id} className="chart-box" /> : <Empty description="暂无图表数据" />;
}

function downloadCsv(filename: string, sections: Array<{ title: string; rows: Record<string, unknown>[] }>) {
  const lines: string[] = [];
  sections.forEach((section) => {
    if (!section.rows.length) return;
    lines.push(section.title);
    const headers = Object.keys(section.rows[0]);
    lines.push(headers.join(','));
    section.rows.forEach((row) => {
      lines.push(headers.map((header) => `"${String(row[header] ?? '').replace(/"/g, '""')}"`).join(','));
    });
    lines.push('');
  });
  if (!lines.length) return false;
  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
  return true;
}

export default function ReportsCenter() {
  const [messageApi, contextHolder] = message.useMessage();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>(defaultDateRange());
  const [storeId, setStoreId] = useState<number | undefined>();
  const [categoryId, setCategoryId] = useState<string | undefined>();
  const [period, setPeriod] = useState('day');
  const [stores, setStores] = useState<Store[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [summary, setSummary] = useState<ReportSummary>(emptySummary);
  const [trend, setTrend] = useState<SalesTrendPoint[]>([]);
  const [storePerformance, setStorePerformance] = useState<StorePerformance[]>([]);
  const [categoryAnalysis, setCategoryAnalysis] = useState<CategoryAnalysis[]>([]);
  const [productRanking, setProductRanking] = useState<ProductRanking[]>([]);
  const [inventoryHealth, setInventoryHealth] = useState<InventoryHealth>({ distribution: [], alerts: [] });
  const [promotionEffect, setPromotionEffect] = useState<PromotionEffect[]>([]);
  const [financeOverview, setFinanceOverview] = useState<FinanceOverview>({ distribution: [], records: [] });
  const [loading, setLoading] = useState(true);

  const query = useMemo<ReportQuery>(() => ({
    start_date: dateRange[0].format('YYYY-MM-DD'),
    end_date: dateRange[1].format('YYYY-MM-DD'),
    store_id: storeId,
    category_id: categoryId,
    period
  }), [categoryId, dateRange, period, storeId]);

  const categories = useMemo(
    () => Array.from(new Set(products.map((item) => item.category).filter(Boolean))).sort(),
    [products]
  );

  const loadMeta = async () => {
    try {
      const [storeData, productData] = await Promise.all([fetchStores(), fetchProducts()]);
      setStores(storeData || []);
      setProducts(productData || []);
    } catch {
      messageApi.error('基础筛选数据读取失败');
    }
  };

  const loadReports = async (nextQuery = query) => {
    setLoading(true);
    try {
      const [
        summaryData,
        trendData,
        storeData,
        categoryData,
        productData,
        inventoryData,
        promotionData,
        financeData
      ] = await Promise.all([
        fetchReportSummary(nextQuery),
        fetchSalesTrend(nextQuery),
        fetchStorePerformance(nextQuery),
        fetchCategoryAnalysis(nextQuery),
        fetchProductRanking(nextQuery),
        fetchInventoryHealth(nextQuery),
        fetchPromotionEffect(nextQuery),
        fetchFinanceOverview(nextQuery)
      ]);
      setSummary(summaryData || emptySummary);
      setTrend(trendData || []);
      setStorePerformance(storeData || []);
      setCategoryAnalysis(categoryData || []);
      setProductRanking(productData || []);
      setInventoryHealth(inventoryData || { distribution: [], alerts: [] });
      setPromotionEffect(promotionData || []);
      setFinanceOverview(financeData || { distribution: [], records: [] });
    } catch {
      messageApi.error('报表中心数据读取失败，请确认后端服务已启动并已完成 seed。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMeta();
  }, []);

  useEffect(() => {
    loadReports(query);
  }, []);

  const handleSearch = async () => {
    await loadReports(query);
    messageApi.success('报表数据已刷新');
  };

  const handleReset = async () => {
    const nextRange = defaultDateRange();
    const nextQuery = {
      start_date: nextRange[0].format('YYYY-MM-DD'),
      end_date: nextRange[1].format('YYYY-MM-DD'),
      period: 'day'
    };
    setDateRange(nextRange);
    setStoreId(undefined);
    setCategoryId(undefined);
    setPeriod('day');
    await loadReports(nextQuery);
    messageApi.success('筛选条件已重置');
  };

  const handleExport = () => {
    const ok = downloadCsv(`reports-${dayjs().format('YYYYMMDD')}.csv`, [
      { title: '综合指标', rows: [{ ...summary }] },
      { title: '门店排行', rows: storePerformance as unknown as Record<string, unknown>[] },
      { title: '商品排行', rows: productRanking as unknown as Record<string, unknown>[] },
      { title: '库存预警', rows: inventoryHealth.alerts as unknown as Record<string, unknown>[] },
      { title: '财务概览', rows: financeOverview.records as unknown as Record<string, unknown>[] }
    ]);
    if (ok) messageApi.success('CSV 导出成功');
    else messageApi.warning('当前无可导出数据');
  };

  const storeColumns: ColumnsType<StorePerformance> = [
    { title: '排名', dataIndex: 'rank', width: 80, render: (value) => <Tag color="blue">第{safeNumber(value)}名</Tag> },
    { title: '门店名称', dataIndex: 'store_name', width: 180, render: text },
    { title: '销售额', dataIndex: 'sales_amount', width: 120, render: money, sorter: (a, b) => safeNumber(a.sales_amount) - safeNumber(b.sales_amount) },
    { title: '订单数', dataIndex: 'order_count', width: 100, sorter: (a, b) => safeNumber(a.order_count) - safeNumber(b.order_count) },
    { title: '客单价', dataIndex: 'average_order_value', width: 120, render: money },
    { title: '毛利额', dataIndex: 'gross_profit', width: 120, render: money },
    { title: '毛利率', dataIndex: 'gross_profit_rate', width: 100, render: percent },
    { title: '对账差异金额', dataIndex: 'difference_amount', width: 140, render: (value) => <span className={safeNumber(value) ? 'danger-text' : ''}>{money(value)}</span> }
  ];

  const productColumns: ColumnsType<ProductRanking> = [
    { title: '排名', dataIndex: 'rank', width: 80 },
    { title: '商品编码', dataIndex: 'product_code', width: 120, render: text },
    { title: '商品名称', dataIndex: 'product_name', width: 180, render: text },
    { title: 'SKU', dataIndex: 'sku_code', width: 170, render: text },
    { title: '销量', dataIndex: 'sales_quantity', width: 90 },
    { title: '销售额', dataIndex: 'sales_amount', width: 120, render: money },
    { title: '毛利额', dataIndex: 'gross_profit', width: 120, render: money },
    { title: '毛利率', dataIndex: 'gross_profit_rate', width: 100, render: percent },
    { title: '当前库存', dataIndex: 'current_inventory', width: 100, render: (value) => safeNumber(value) }
  ];

  const categoryColumns: ColumnsType<CategoryAnalysis> = [
    { title: '品类', dataIndex: 'category', render: text },
    { title: '销量', dataIndex: 'sales_quantity' },
    { title: '销售额', dataIndex: 'sales_amount', render: money },
    { title: '毛利额', dataIndex: 'gross_profit', render: money },
    { title: '毛利率', dataIndex: 'gross_profit_rate', render: percent }
  ];

  const inventoryColumns: ColumnsType<InventoryAlert> = [
    { title: '门店', dataIndex: 'store_name', width: 160, render: text },
    { title: '商品', dataIndex: 'product_name', width: 180, render: text },
    { title: 'SKU', dataIndex: 'sku_code', width: 170, render: text },
    { title: '当前库存', dataIndex: 'quantity', width: 100 },
    { title: '安全库存', dataIndex: 'safety_stock', width: 100 },
    { title: '在途库存', dataIndex: 'in_transit', width: 100 },
    { title: '库存状态', dataIndex: 'inventory_status', width: 120, render: (value) => <Tag color={statusColor(value)}>{text(value)}</Tag> },
    { title: '建议补货量', dataIndex: 'suggested_qty', width: 120 }
  ];

  const promotionColumns: ColumnsType<PromotionEffect> = [
    { title: '活动编号', dataIndex: 'promotion_code', width: 120, render: text },
    { title: '活动名称', dataIndex: 'promotion_name', width: 180, render: text },
    { title: '活动类型', dataIndex: 'promotion_type', width: 120, render: text },
    { title: '参与订单数', dataIndex: 'order_count', width: 110 },
    { title: '优惠金额', dataIndex: 'discount_amount', width: 120, render: money },
    { title: '实收金额', dataIndex: 'paid_amount', width: 120, render: money },
    { title: '毛利额', dataIndex: 'gross_profit', width: 120, render: money },
    { title: '毛利率', dataIndex: 'gross_profit_rate', width: 100, render: percent },
    { title: '活动状态', dataIndex: 'status', width: 110, render: (value) => <Tag color={statusColor(value)}>{text(value)}</Tag> }
  ];

  const financeColumns: ColumnsType<FinanceOverviewRecord> = [
    { title: '财务记录号', dataIndex: 'record_no', width: 150, render: text },
    { title: '订单编号', dataIndex: 'order_no', width: 150, render: text },
    { title: '门店', dataIndex: 'store_name', width: 160, render: text },
    { title: '订单金额', dataIndex: 'order_amount', width: 120, render: money },
    { title: '支付金额', dataIndex: 'payment_amount', width: 120, render: money },
    { title: '差异金额', dataIndex: 'difference_amount', width: 120, render: (value) => <span className={safeNumber(value) ? 'danger-text' : ''}>{money(value)}</span> },
    { title: '对账状态', dataIndex: 'status', width: 120, render: (value) => <Tag color={statusColor(value)}>{text(value)}</Tag> },
    { title: '对账时间', dataIndex: 'reconciliation_time', width: 130, render: text }
  ];

  return (
    <div className="reports-page">
      {contextHolder}
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>报表中心</Typography.Title>
          <Typography.Text type="secondary">销售、库存、商品、促销与财务经营数据综合分析</Typography.Text>
        </div>
        <Tag color="blue">第八阶段功能</Tag>
      </div>

      <Card className="report-filter-card">
        <Space wrap size={12}>
          <RangePicker value={dateRange} onChange={(value) => value && setDateRange(value as [dayjs.Dayjs, dayjs.Dayjs])} />
          <Select
            value={storeId ?? 0}
            onChange={(value) => setStoreId(value || undefined)}
            style={{ width: 190 }}
            options={[{ value: 0, label: '全部门店' }, ...stores.map((store) => ({ value: store.id, label: store.name || '-' }))]}
          />
          <Select
            value={categoryId ?? ALL}
            onChange={(value) => setCategoryId(value === ALL ? undefined : value)}
            style={{ width: 170 }}
            options={[{ value: ALL, label: '全部分类' }, ...categories.map((category) => ({ value: category, label: category }))]}
          />
          <Select
            value={period}
            onChange={setPeriod}
            style={{ width: 120 }}
            options={[
              { value: 'day', label: '日报' },
              { value: 'week', label: '周报' },
              { value: 'month', label: '月报' }
            ]}
          />
          <Button type="primary" onClick={handleSearch}>查询</Button>
          <Button onClick={handleReset}>重置</Button>
          <Button onClick={handleExport}>导出</Button>
        </Space>
      </Card>

      <Row gutter={[16, 16]} className="inventory-section">
        <Col xs={24} sm={12} lg={6}><MetricCard title="销售总额" value={safeNumber(summary.sales_total)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="订单总数" value={safeNumber(summary.order_count)} suffix="单" /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="客单价" value={safeNumber(summary.average_order_value)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="毛利额" value={safeNumber(summary.gross_profit)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="毛利率" value={safeNumber(summary.gross_profit_rate)} suffix="%" precision={1} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="支付总额" value={safeNumber(summary.payment_total)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="对账差异金额" value={safeNumber(summary.difference_amount)} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="缺货 SKU 数" value={safeNumber(summary.out_of_stock_sku_count)} suffix="个" /></Col>
      </Row>

      <Card className="inventory-section">
        <Tabs
          items={[
            {
              key: 'overview',
              label: '综合总览',
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={14}>
                    <Card title="最近销售额与订单量趋势">
                      <LineChart id="reports-sales-trend-overview" data={trend} />
                    </Card>
                  </Col>
                  <Col xs={24} lg={10}>
                    <Card title="门店销售额与毛利额对比">
                      <BarChart
                        id="reports-store-overview"
                        names={storePerformance.map((item) => item.store_name || '-')}
                        series={[
                          { name: '销售额', data: storePerformance.map((item) => safeNumber(item.sales_amount)) },
                          { name: '毛利额', data: storePerformance.map((item) => safeNumber(item.gross_profit)) }
                        ]}
                      />
                    </Card>
                  </Col>
                </Row>
              )
            },
            {
              key: 'trend',
              label: '销售趋势',
              children: <Card title="销售额与订单量趋势"><LineChart id="reports-sales-trend" data={trend} /></Card>
            },
            {
              key: 'store',
              label: '门店排行',
              children: (
                <>
                  <Card title="门店销售额与毛利额对比">
                    <BarChart
                      id="reports-store-rank-chart"
                      names={storePerformance.map((item) => item.store_name || '-')}
                      series={[
                        { name: '销售额', data: storePerformance.map((item) => safeNumber(item.sales_amount)) },
                        { name: '毛利额', data: storePerformance.map((item) => safeNumber(item.gross_profit)) }
                      ]}
                    />
                  </Card>
                  <Card title="门店经营表现" className="inventory-section">
                    <Table rowKey="store_id" loading={loading} columns={storeColumns} dataSource={storePerformance} scroll={{ x: 1060 }} pagination={{ pageSize: 8 }} />
                  </Card>
                </>
              )
            },
            {
              key: 'product',
              label: '商品 / 品类分析',
              children: (
                <>
                  <Row gutter={[16, 16]}>
                    <Col xs={24} lg={12}>
                      <Card title="品类销售额">
                        <BarChart id="reports-category-sales" names={categoryAnalysis.map((item) => item.category || '-')} series={[{ name: '销售额', data: categoryAnalysis.map((item) => safeNumber(item.sales_amount)) }]} />
                      </Card>
                    </Col>
                    <Col xs={24} lg={12}>
                      <Card title="品类毛利率">
                        <BarChart id="reports-category-profit" names={categoryAnalysis.map((item) => item.category || '-')} series={[{ name: '毛利率', data: categoryAnalysis.map((item) => safeNumber(item.gross_profit_rate)) }]} />
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={[16, 16]} className="inventory-section">
                    <Col xs={24} lg={9}><Card title="品类分析表"><Table rowKey="category" loading={loading} columns={categoryColumns} dataSource={categoryAnalysis} pagination={false} /></Card></Col>
                    <Col xs={24} lg={15}><Card title="商品销售排行表"><Table rowKey="sku_code" loading={loading} columns={productColumns} dataSource={productRanking} scroll={{ x: 1100 }} pagination={{ pageSize: 8 }} /></Card></Col>
                  </Row>
                </>
              )
            },
            {
              key: 'inventory',
              label: '库存健康分析',
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={8}>
                    <Card title="库存状态分布"><PieChart id="reports-inventory-pie" data={inventoryHealth.distribution} /></Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card title="缺货 / 低库存 SKU">
                      <Table rowKey="id" loading={loading} columns={inventoryColumns} dataSource={inventoryHealth.alerts} scroll={{ x: 1070 }} pagination={{ pageSize: 8 }} />
                    </Card>
                  </Col>
                </Row>
              )
            },
            {
              key: 'promotion',
              label: '促销效果分析',
              children: (
                <>
                  <Row gutter={[16, 16]}>
                    <Col xs={24} lg={12}>
                      <Card title="优惠金额对比">
                        <BarChart id="reports-promotion-discount" names={promotionEffect.map((item) => item.promotion_name || '-')} series={[{ name: '优惠金额', data: promotionEffect.map((item) => safeNumber(item.discount_amount)) }]} />
                      </Card>
                    </Col>
                    <Col xs={24} lg={12}>
                      <Card title="促销带动销售额">
                        <BarChart id="reports-promotion-sales" names={promotionEffect.map((item) => item.promotion_name || '-')} series={[{ name: '实收金额', data: promotionEffect.map((item) => safeNumber(item.paid_amount)) }]} />
                      </Card>
                    </Col>
                  </Row>
                  <Card title="促销活动效果表" className="inventory-section">
                    <Table rowKey="promotion_id" loading={loading} columns={promotionColumns} dataSource={promotionEffect} scroll={{ x: 1200 }} pagination={{ pageSize: 8 }} />
                  </Card>
                </>
              )
            },
            {
              key: 'finance',
              label: '财务对账概览',
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={8}>
                    <Card title="对账状态分布"><PieChart id="reports-finance-pie" data={financeOverview.distribution} /></Card>
                  </Col>
                  <Col xs={24} lg={16}>
                    <Card title="财务概览表">
                      <Table rowKey="id" loading={loading} columns={financeColumns} dataSource={financeOverview.records} scroll={{ x: 1070 }} pagination={{ pageSize: 8 }} />
                    </Card>
                  </Col>
                </Row>
              )
            }
          ]}
        />
      </Card>
    </div>
  );
}
