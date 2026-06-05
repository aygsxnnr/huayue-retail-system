import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import MetricCard from '../components/MetricCard';
import {
  approveReplenishment,
  createReplenishment,
  createTransfer,
  fetchInventory,
  fetchLowStockInventory,
  fetchReplenishments,
  fetchTransfers,
  markTransferArrival,
  rejectReplenishment,
  updateInventorySafetyStock,
  type InventoryItem,
  type ReplenishmentRequest,
  type TransferRecord
} from '../api/inventory';

type InventoryStatus = InventoryItem['inventory_status'] | '全部';

function getInventoryStatus(record: InventoryItem): InventoryItem['inventory_status'] {
  if (record.inventory_status) return record.inventory_status;
  if (record.quantity <= 0) return '缺货预警';
  if (record.quantity < record.safety_stock) return '低库存';
  return '正常';
}

function statusColor(status: string) {
  if (status === '正常' || status === '已完成' || status === '已到货') return 'green';
  if (status === '低库存' || status === '待审核') return 'orange';
  if (status === '缺货预警' || status === '已驳回' || status === '异常') return 'red';
  if (status === '在途' || status === '待补货' || status === '已审核') return 'blue';
  return 'default';
}

function formatDate(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('zh-CN');
}

function productName(record: { sku?: InventoryItem['sku'] }) {
  return record.sku?.product?.name ?? '-';
}

function skuCode(record: { sku?: InventoryItem['sku'] }) {
  return record.sku?.sku_code ?? '-';
}

function colorSize(record: { sku?: InventoryItem['sku'] }) {
  return `${record.sku?.color ?? '-'} / ${record.sku?.size ?? '-'}`;
}

export default function InventoryReplenishment() {
  const [messageApi, contextHolder] = message.useMessage();
  const [form] = Form.useForm();
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [lowStockInventory, setLowStockInventory] = useState<InventoryItem[]>([]);
  const [replenishments, setReplenishments] = useState<ReplenishmentRequest[]>([]);
  const [transfers, setTransfers] = useState<TransferRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [storeFilter, setStoreFilter] = useState<number | '全部'>('全部');
  const [categoryFilter, setCategoryFilter] = useState<string>('全部');
  const [statusFilter, setStatusFilter] = useState<InventoryStatus>('全部');
  const [selectedInventory, setSelectedInventory] = useState<InventoryItem | null>(null);
  const [detailInventory, setDetailInventory] = useState<InventoryItem | null>(null);
  const [safetyStockInventory, setSafetyStockInventory] = useState<InventoryItem | null>(null);
  const [safetyStockValue, setSafetyStockValue] = useState<number>(0);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [inventoryData, lowStockData, replenishmentData, transferData] = await Promise.all([
        fetchInventory(),
        fetchLowStockInventory(),
        fetchReplenishments(),
        fetchTransfers()
      ]);
      setInventory(inventoryData);
      setLowStockInventory(lowStockData);
      setReplenishments(replenishmentData);
      setTransfers(transferData);
    } catch {
      setError('库存与补货数据读取失败，请确认后端服务已启动。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!selectedInventory) return;
    form.setFieldsValue({
      request_qty: Math.max(selectedInventory.suggested_qty, 1),
      reason: getInventoryStatus(selectedInventory) === '缺货预警'
        ? '当前 SKU 已缺货，需尽快补货。'
        : '当前 SKU 低于安全库存，申请补货。'
    });
  }, [form, selectedInventory]);

  const stores = useMemo(() => {
    const map = new Map<number, string>();
    inventory.forEach((item) => {
      if (item.store) map.set(item.store_id, item.store.name);
    });
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }));
  }, [inventory]);

  const categories = useMemo(() => {
    const values = new Set<string>();
    inventory.forEach((item) => {
      if (item.sku?.product?.category) values.add(item.sku.product.category);
    });
    return Array.from(values).map((value) => ({ value, label: value }));
  }, [inventory]);

  const filteredInventory = useMemo(
    () =>
      inventory.filter((item) => {
        const status = getInventoryStatus(item);
        const category = item.sku?.product?.category ?? '';
        return (
          (storeFilter === '全部' || item.store_id === storeFilter) &&
          (categoryFilter === '全部' || category === categoryFilter) &&
          (statusFilter === '全部' || status === statusFilter)
        );
      }),
    [categoryFilter, inventory, statusFilter, storeFilter]
  );

  const metrics = useMemo(() => {
    const outOfStockCount = inventory.filter((item) => item.quantity <= 0).length;
    const lowStockCount = inventory.filter((item) => item.quantity > 0 && item.quantity < item.safety_stock).length;
    const pendingCount = replenishments.filter((item) => item.status === '待审核').length;
    const inTransitQty = inventory.reduce((sum, item) => sum + item.in_transit, 0);
    const completedCount = replenishments.filter((item) => item.status === '已完成').length;
    const completionRate = replenishments.length ? (completedCount / replenishments.length) * 100 : 0;
    const totalQuantity = inventory.reduce((sum, item) => sum + item.quantity, 0);
    const totalRecentSales = inventory.reduce((sum, item) => sum + item.recent_7d_sales, 0);
    const turnoverDays = totalRecentSales ? (totalQuantity / totalRecentSales) * 7 : 0;
    return {
      outOfStockCount,
      lowStockCount,
      pendingCount,
      inTransitQty,
      completionRate,
      turnoverDays
    };
  }, [inventory, replenishments]);

  const submitReplenishment = async () => {
    if (!selectedInventory) return;
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      await createReplenishment({
        inventory_id: selectedInventory.id,
        request_qty: Number(values.request_qty),
        reason: values.reason,
        applicant: values.applicant || '门店店长'
      });
      messageApi.success('补货申请已提交');
      setSelectedInventory(null);
      form.resetFields();
      await loadData();
    } catch {
      messageApi.error('补货申请提交失败，请检查申请数量或后端服务。');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await approveReplenishment(id);
      messageApi.success('补货申请已审核通过');
      await loadData();
    } catch {
      messageApi.error('审核通过失败，请确认申请状态。');
    }
  };

  const handleReject = async (id: number) => {
    try {
      await rejectReplenishment(id);
      messageApi.success('补货申请已驳回');
      await loadData();
    } catch {
      messageApi.error('驳回失败，请确认申请状态。');
    }
  };

  const handleCreateTransfer = async (record: ReplenishmentRequest) => {
    try {
      await createTransfer({
        request_id: record.id,
        source_location: '华悦中央仓',
        transfer_qty: record.request_qty
      });
      messageApi.success('调拨单已生成，库存已进入在途');
      await loadData();
    } catch {
      messageApi.error('生成调拨单失败，只能对已审核申请生成调拨单。');
    }
  };

  const handleArrival = async (id: number) => {
    try {
      await markTransferArrival(id);
      messageApi.success('已标记到货，库存数量已更新');
      await loadData();
    } catch {
      messageApi.error('标记到货失败，请确认调拨单状态。');
    }
  };

  const openSafetyStockModal = (record: InventoryItem) => {
    setSafetyStockInventory(record);
    setSafetyStockValue(Math.max(Number(record.safety_stock) || 0, 0));
  };

  const submitSafetyStock = async () => {
    if (!safetyStockInventory) return;
    if (safetyStockValue < 0) {
      messageApi.error('安全库存不能小于 0');
      return;
    }
    setSubmitting(true);
    try {
      await updateInventorySafetyStock(safetyStockInventory.id, safetyStockValue);
      messageApi.success('安全库存已更新');
      setSafetyStockInventory(null);
      await loadData();
    } catch {
      messageApi.error('安全库存更新失败，请确认库存记录是否存在。');
    } finally {
      setSubmitting(false);
    }
  };

  const resetFilters = () => {
    setStoreFilter('全部');
    setCategoryFilter('全部');
    setStatusFilter('全部');
  };

  const exportInventory = () => {
    const header = ['门店', '商品名称', 'SKU', '当前库存', '安全库存', '在途库存', '近7天销量', '建议补货量', '库存状态'];
    const rows = filteredInventory.map((item) => [
      item.store?.name ?? '',
      productName(item),
      skuCode(item),
      item.quantity,
      item.safety_stock,
      item.in_transit,
      item.recent_7d_sales,
      item.suggested_qty,
      getInventoryStatus(item)
    ]);
    const csv = [header, ...rows].map((row) => row.join(',')).join('\n');
    const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = '库存与补货列表.csv';
    link.click();
    URL.revokeObjectURL(url);
    messageApi.success('库存列表已导出');
  };

  const inventoryColumns: ColumnsType<InventoryItem> = [
    { title: '门店', render: (_, record) => record.store?.name ?? '-' },
    { title: '商品名称', render: (_, record) => productName(record) },
    { title: 'SKU', render: (_, record) => skuCode(record) },
    { title: '颜色/尺码', render: (_, record) => colorSize(record) },
    {
      title: '当前库存',
      dataIndex: 'quantity',
      render: (value: number) => <span className={value <= 0 ? 'danger-text' : ''}>{value}</span>
    },
    { title: '安全库存', dataIndex: 'safety_stock' },
    { title: '在途库存', dataIndex: 'in_transit' },
    { title: '近7天销量', dataIndex: 'recent_7d_sales' },
    { title: '建议补货量', dataIndex: 'suggested_qty' },
    {
      title: '库存状态',
      render: (_, record) => {
        const status = getInventoryStatus(record);
        return <Tag color={statusColor(status)}>{status}</Tag>;
      }
    },
    {
      title: '操作',
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => setDetailInventory(record)}>
            查看详情
          </Button>
          <Button type="link" onClick={() => setSelectedInventory(record)}>
            提交补货
          </Button>
          <Button type="link" onClick={() => openSafetyStockModal(record)}>
            编辑安全库存
          </Button>
        </Space>
      )
    }
  ];

  const replenishmentColumns: ColumnsType<ReplenishmentRequest> = [
    { title: '申请单号', render: (_, record) => `RQ${String(record.id).padStart(5, '0')}` },
    { title: '门店', render: (_, record) => record.store?.name ?? '-' },
    { title: '商品名称', render: (_, record) => productName(record) },
    { title: 'SKU', render: (_, record) => skuCode(record) },
    { title: '申请数量', dataIndex: 'request_qty' },
    { title: '建议补货量', dataIndex: 'suggested_qty' },
    { title: '申请人', dataIndex: 'applicant' },
    { title: '申请时间', dataIndex: 'created_at', render: formatDate },
    { title: '审核状态', dataIndex: 'status', render: (status: string) => <Tag color={statusColor(status)}>{status}</Tag> },
    {
      title: '操作',
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" disabled={record.status !== '待审核'} onClick={() => handleApprove(record.id)}>
            审核通过
          </Button>
          <Button type="link" danger disabled={!['待审核', '已审核'].includes(record.status)} onClick={() => handleReject(record.id)}>
            驳回
          </Button>
          <Button type="link" disabled={record.status !== '已审核'} onClick={() => handleCreateTransfer(record)}>
            生成调拨单
          </Button>
        </Space>
      )
    }
  ];

  const transferColumns: ColumnsType<TransferRecord> = [
    { title: '调拨单号', render: (_, record) => `TR${String(record.id).padStart(5, '0')}` },
    { title: '来源仓库/门店', dataIndex: 'source_location' },
    { title: '目标门店', render: (_, record) => record.store?.name ?? '-' },
    { title: '商品名称', render: (_, record) => productName(record) },
    { title: 'SKU', render: (_, record) => skuCode(record) },
    { title: '调拨数量', dataIndex: 'transfer_qty' },
    { title: '在途数量', dataIndex: 'in_transit_qty' },
    { title: '发货时间', dataIndex: 'shipped_at', render: formatDate },
    { title: '预计到货时间', dataIndex: 'expected_arrival_at', render: formatDate },
    { title: '到货状态', dataIndex: 'status', render: (status: string) => <Tag color={statusColor(status)}>{status}</Tag> },
    {
      title: '操作',
      fixed: 'right',
      render: (_, record) => (
        <Button type="link" disabled={record.status === '已到货'} onClick={() => handleArrival(record.id)}>
          标记到货
        </Button>
      )
    }
  ];

  if (error) {
    return <Alert type="error" message={error} showIcon />;
  }

  return (
    <div className="inventory-page">
      {contextHolder}
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>库存与补货管理</Typography.Title>
          <Typography.Text type="secondary">库存预警、补货申请、调拨处理与在途库存跟踪</Typography.Text>
        </div>
        <Tag color="blue">第四阶段功能</Tag>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={4}>
          <MetricCard title="缺货SKU数" value={metrics.outOfStockCount} suffix="个" />
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <MetricCard title="低库存SKU数" value={metrics.lowStockCount} suffix="个" />
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <MetricCard title="待审核补货" value={metrics.pendingCount} suffix="单" />
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <MetricCard title="在途库存数量" value={metrics.inTransitQty} suffix="件" />
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <MetricCard title="补货完成率" value={metrics.completionRate} suffix="%" precision={1} />
        </Col>
        <Col xs={24} sm={12} lg={4}>
          <MetricCard title="库存周转天数" value={metrics.turnoverDays} suffix="天" precision={1} />
        </Col>
      </Row>

      <Card className="inventory-section">
        <Space className="inventory-toolbar" wrap>
          <Select
            className="inventory-filter"
            value={storeFilter}
            options={[{ value: '全部', label: '全部门店' }, ...stores]}
            onChange={setStoreFilter}
          />
          <Select
            className="inventory-filter"
            value={categoryFilter}
            options={[{ value: '全部', label: '全部品类' }, ...categories]}
            onChange={setCategoryFilter}
          />
          <Select
            className="inventory-filter"
            value={statusFilter}
            options={['全部', '正常', '低库存', '缺货预警', '待补货'].map((value) => ({ value, label: value }))}
            onChange={setStatusFilter}
          />
          <Button type="primary" onClick={loadData}>
            查询
          </Button>
          <Button onClick={resetFilters}>重置</Button>
          <Button onClick={exportInventory}>导出</Button>
        </Space>
      </Card>

      <Card title="库存预警列表" className="inventory-section">
        <Table
          rowKey="id"
          loading={loading}
          columns={inventoryColumns}
          dataSource={filteredInventory}
          scroll={{ x: 1280 }}
          pagination={{ pageSize: 8 }}
        />
      </Card>

      <Card title="补货申请审核区" className="inventory-section">
        <Table
          rowKey="id"
          loading={loading}
          columns={replenishmentColumns}
          dataSource={replenishments}
          scroll={{ x: 1280 }}
          pagination={{ pageSize: 6 }}
        />
      </Card>

      <Card title="在途库存跟踪区" className="inventory-section">
        <Table
          rowKey="id"
          loading={loading}
          columns={transferColumns}
          dataSource={transfers}
          scroll={{ x: 1280 }}
          pagination={{ pageSize: 6 }}
        />
      </Card>

      <Modal
        title="提交补货申请"
        open={Boolean(selectedInventory)}
        onCancel={() => {
          setSelectedInventory(null);
          form.resetFields();
        }}
        onOk={submitReplenishment}
        confirmLoading={submitting}
        okText="提交申请"
        cancelText="取消"
      >
        {selectedInventory && (
          <>
            <Descriptions bordered size="small" column={1} className="inventory-descriptions">
              <Descriptions.Item label="申请门店">{selectedInventory.store?.name ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="商品名称">{productName(selectedInventory)}</Descriptions.Item>
              <Descriptions.Item label="SKU">{skuCode(selectedInventory)}</Descriptions.Item>
              <Descriptions.Item label="当前库存">{selectedInventory.quantity}</Descriptions.Item>
              <Descriptions.Item label="近7天销量">{selectedInventory.recent_7d_sales}</Descriptions.Item>
              <Descriptions.Item label="建议补货量">{selectedInventory.suggested_qty}</Descriptions.Item>
            </Descriptions>
            <Form form={form} layout="vertical" initialValues={{ applicant: '门店店长' }}>
              <Form.Item label="申请数量" name="request_qty" rules={[{ required: true, message: '请输入申请数量' }]}>
                <InputNumber min={1} className="full-width-control" />
              </Form.Item>
              <Form.Item label="申请理由" name="reason" rules={[{ required: true, message: '请输入申请理由' }]}>
                <Input.TextArea rows={3} />
              </Form.Item>
              <Form.Item label="申请人" name="applicant">
                <Input />
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      <Modal
        title="库存详情"
        open={Boolean(detailInventory)}
        onCancel={() => setDetailInventory(null)}
        footer={<Button onClick={() => setDetailInventory(null)}>关闭</Button>}
      >
        {detailInventory && (
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="门店">{detailInventory.store?.name ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="商品名称">{productName(detailInventory)}</Descriptions.Item>
            <Descriptions.Item label="SKU">{skuCode(detailInventory)}</Descriptions.Item>
            <Descriptions.Item label="颜色/尺码">{colorSize(detailInventory)}</Descriptions.Item>
            <Descriptions.Item label="当前库存">{detailInventory.quantity}</Descriptions.Item>
            <Descriptions.Item label="安全库存">{detailInventory.safety_stock}</Descriptions.Item>
            <Descriptions.Item label="在途库存">{detailInventory.in_transit}</Descriptions.Item>
            <Descriptions.Item label="近7天销量">{detailInventory.recent_7d_sales}</Descriptions.Item>
            <Descriptions.Item label="建议补货量">{detailInventory.suggested_qty}</Descriptions.Item>
            <Descriptions.Item label="库存状态">
              <Tag color={statusColor(getInventoryStatus(detailInventory))}>{getInventoryStatus(detailInventory)}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatDate(detailInventory.updated_at)}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      <Modal
        title="编辑安全库存"
        open={Boolean(safetyStockInventory)}
        onCancel={() => setSafetyStockInventory(null)}
        onOk={submitSafetyStock}
        confirmLoading={submitting}
        okText="保存"
        cancelText="取消"
      >
        {safetyStockInventory && (
          <>
            <Descriptions bordered size="small" column={1} className="inventory-descriptions">
              <Descriptions.Item label="门店">{safetyStockInventory.store?.name ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="商品名称">{productName(safetyStockInventory)}</Descriptions.Item>
              <Descriptions.Item label="SKU">{skuCode(safetyStockInventory)}</Descriptions.Item>
              <Descriptions.Item label="当前库存">{safetyStockInventory.quantity ?? 0}</Descriptions.Item>
              <Descriptions.Item label="原安全库存">{safetyStockInventory.safety_stock ?? 0}</Descriptions.Item>
            </Descriptions>
            <Form layout="vertical">
              <Form.Item label="新安全库存" required>
                <InputNumber
                  min={0}
                  value={safetyStockValue}
                  onChange={(value) => setSafetyStockValue(Math.max(Number(value) || 0, 0))}
                  className="full-width-control"
                />
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>
    </div>
  );
}
