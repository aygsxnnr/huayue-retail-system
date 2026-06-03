import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Input,
  InputNumber,
  message,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  createSalesOrder,
  fetchPromotions,
  fetchRecentOrders,
  fetchStores,
  searchMembers,
  searchPosSkus,
  type Member,
  type POSSku,
  type Promotion,
  type SalesOrder,
  type Store
} from '../api/pos';

interface CartItem extends POSSku {
  quantity: number;
}

interface HeldOrder {
  id: number;
  hold_no: string;
  store_id?: number;
  member: Member | null;
  items: CartItem[];
  original_amount: number;
  discount_amount: number;
  paid_amount: number;
  created_at: string;
}

const HELD_ORDERS_STORAGE_KEY = 'huayue_pos_held_orders';
const defaultPaymentMethod = '微信支付';

function money(value: number) {
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function POSOrder() {
  const [messageApi, contextHolder] = message.useMessage();
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState<number>();
  const [keyword, setKeyword] = useState('');
  const [skuResults, setSkuResults] = useState<POSSku[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [memberKeyword, setMemberKeyword] = useState('');
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [promotionId, setPromotionId] = useState<number>();
  const [paymentMethod, setPaymentMethod] = useState(defaultPaymentMethod);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [heldOrders, setHeldOrders] = useState<HeldOrder[]>(() => {
    const stored = window.localStorage.getItem(HELD_ORDERS_STORAGE_KEY);
    if (!stored) return [];
    try {
      return JSON.parse(stored) as HeldOrder[];
    } catch {
      return [];
    }
  });
  const [recentOrders, setRecentOrders] = useState<SalesOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([fetchStores(), fetchPromotions(), fetchRecentOrders()])
      .then(([storeData, promotionData, orderData]) => {
        setStores(storeData);
        setStoreId(storeData[0]?.id);
        setPromotions(promotionData);
        setPromotionId(promotionData.find((item) => item.status === '进行中')?.id);
        setRecentOrders(orderData);
      })
      .catch(() => messageApi.error('POS 基础数据读取失败，请确认后端已启动。'));
  }, [messageApi]);

  useEffect(() => {
    if (!storeId) return;
    setLoading(true);
    searchPosSkus(storeId, keyword)
      .then(setSkuResults)
      .catch(() => messageApi.error('商品 SKU 查询失败。'))
      .finally(() => setLoading(false));
  }, [storeId, keyword, messageApi]);

  useEffect(() => {
    window.localStorage.setItem(HELD_ORDERS_STORAGE_KEY, JSON.stringify(heldOrders));
  }, [heldOrders]);

  const selectedPromotion = promotions.find((item) => item.id === promotionId);
  const discountRate = selectedPromotion?.discount_rate ?? 1;
  const originalAmount = cart.reduce((sum, item) => sum + item.list_price * item.quantity, 0);
  const discountAmount = Number((originalAmount * (1 - discountRate)).toFixed(2));
  const paidAmount = Number((originalAmount - discountAmount).toFixed(2));

  const addToCart = (sku: POSSku) => {
    if (sku.inventory_quantity <= 0) {
      messageApi.warning('该 SKU 当前无可售库存。');
      return;
    }
    setCart((items) => {
      const existing = items.find((item) => item.sku_id === sku.sku_id);
      if (existing) {
        if (existing.quantity + 1 > sku.inventory_quantity) {
          messageApi.warning('购物车数量不能超过当前库存。');
          return items;
        }
        return items.map((item) =>
          item.sku_id === sku.sku_id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...items, { ...sku, quantity: 1 }];
    });
  };

  const updateCartQuantity = (skuId: number, quantity: number | null) => {
    if (!quantity) {
      setCart((items) => items.filter((item) => item.sku_id !== skuId));
      return;
    }
    setCart((items) =>
      items.map((item) =>
        item.sku_id === skuId ? { ...item, quantity: Math.min(quantity, item.inventory_quantity) } : item
      )
    );
  };

  const removeCartItem = (skuId: number) => {
    setCart((items) => items.filter((item) => item.sku_id !== skuId));
  };

  const resetCurrentOrder = () => {
    setCart([]);
    setSelectedMember(null);
    setMemberKeyword('');
    setMembers([]);
    setPaymentMethod(defaultPaymentMethod);
    setPromotionId(promotions.find((item) => item.status === '进行中')?.id);
  };

  const handleMemberSearch = async () => {
    if (!memberKeyword.trim()) {
      messageApi.warning('请输入会员手机号、姓名或会员编号。');
      return;
    }
    const result = await searchMembers(memberKeyword);
    setMembers(result);
    if (result.length === 1) {
      setSelectedMember(result[0]);
      messageApi.success(`已识别会员：${result[0].name}`);
    } else if (!result.length) {
      setSelectedMember(null);
      messageApi.info('未查询到会员。');
    }
  };

  const submitOrder = async () => {
    if (!storeId) {
      messageApi.warning('请选择收银门店。');
      return;
    }
    if (!cart.length) {
      messageApi.warning('请先加入商品到购物车。');
      return;
    }
    setSubmitting(true);
    try {
      const order = await createSalesOrder({
        store_id: storeId,
        member_id: selectedMember?.id,
        promotion_id: promotionId,
        payment_method: paymentMethod,
        items: cart.map((item) => ({ sku_id: item.sku_id, quantity: item.quantity }))
      });
      messageApi.success(`收银成功，订单已生成：${order.order_no}`);
      resetCurrentOrder();
      if (storeId) {
        setSkuResults(await searchPosSkus(storeId, keyword));
      }
      setRecentOrders(await fetchRecentOrders());
    } catch (error) {
      messageApi.error('订单生成失败，请检查库存或后端服务。');
    } finally {
      setSubmitting(false);
    }
  };

  const holdOrder = () => {
    if (!cart.length) {
      messageApi.warning('请先选择商品');
      return;
    }
    const now = new Date();
    const nextOrder: HeldOrder = {
      id: now.getTime(),
      hold_no: `HD${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(
        now.getDate()
      ).padStart(2, '0')}${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(
        2,
        '0'
      )}${String(now.getSeconds()).padStart(2, '0')}`,
      store_id: storeId,
      member: selectedMember,
      items: cart,
      original_amount: originalAmount,
      discount_amount: discountAmount,
      paid_amount: paidAmount,
      created_at: now.toLocaleString('zh-CN')
    };
    setHeldOrders((orders) => [nextOrder, ...orders]);
    resetCurrentOrder();
    messageApi.success('挂单成功');
  };

  const cancelOrder = () => {
    resetCurrentOrder();
    messageApi.info('当前订单已取消。');
  };

  const restoreHeldOrder = (order: HeldOrder) => {
    setStoreId(order.store_id);
    setSelectedMember(order.member);
    setMemberKeyword(order.member?.phone ?? '');
    setMembers(order.member ? [order.member] : []);
    setCart(order.items);
    setHeldOrders((orders) => orders.filter((item) => item.id !== order.id));
    messageApi.success('挂单已恢复');
  };

  const cancelHeldOrder = (orderId: number) => {
    setHeldOrders((orders) => orders.filter((item) => item.id !== orderId));
    messageApi.info('挂单已取消');
  };

  const skuColumns = useMemo<ColumnsType<POSSku>>(
    () => [
      { title: '商品', dataIndex: 'product_name' },
      { title: 'SKU', dataIndex: 'sku_code' },
      { title: '颜色/尺码', render: (_, record) => `${record.color} / ${record.size}` },
      { title: '售价', dataIndex: 'list_price', render: (value: number) => money(value) },
      {
        title: '库存',
        dataIndex: 'inventory_quantity',
        render: (value: number, record) => (
          <Tag color={value <= 0 ? 'red' : value <= record.safety_stock ? 'orange' : 'green'}>
            {value <= 0 ? '缺货' : `${value}件`}
          </Tag>
        )
      },
      {
        title: '操作',
        render: (_, record) => (
          <Button type="link" disabled={record.inventory_quantity <= 0} onClick={() => addToCart(record)}>
            加入购物车
          </Button>
        )
      }
    ],
    []
  );

  const cartColumns = useMemo<ColumnsType<CartItem>>(
    () => [
      { title: '商品', dataIndex: 'product_name' },
      { title: 'SKU', dataIndex: 'sku_code' },
      { title: '单价', dataIndex: 'list_price', render: (value: number) => money(value) },
      {
        title: '数量',
        render: (_, record) => (
          <InputNumber
            min={0}
            max={record.inventory_quantity}
            value={record.quantity}
            onChange={(value) => updateCartQuantity(record.sku_id, value === null ? null : Number(value))}
          />
        )
      },
      { title: '小计', render: (_, record) => money(record.list_price * record.quantity) },
      {
        title: '操作',
        render: (_, record) => (
          <Button type="link" danger onClick={() => removeCartItem(record.sku_id)}>
            移除
          </Button>
        )
      }
    ],
    []
  );

  const orderColumns = useMemo<ColumnsType<SalesOrder>>(
    () => [
      { title: '订单号', dataIndex: 'order_no' },
      { title: '时间', dataIndex: 'order_time', render: (value: string) => new Date(value).toLocaleString('zh-CN') },
      { title: '实收', dataIndex: 'paid_amount', render: (value: number) => money(value) },
      { title: '支付方式', dataIndex: 'payment_method' },
      { title: '状态', dataIndex: 'status', render: (value: string) => <Tag color="green">{value}</Tag> }
    ],
    []
  );

  const heldOrderColumns = useMemo<ColumnsType<HeldOrder>>(
    () => [
      { title: '挂单编号', dataIndex: 'hold_no' },
      { title: '会员', render: (_, record) => record.member?.name ?? '散客' },
      {
        title: '商品件数',
        render: (_, record) => `${record.items.reduce((sum, item) => sum + item.quantity, 0)}件`
      },
      { title: '实收金额', dataIndex: 'paid_amount', render: (value: number) => money(value) },
      { title: '挂单时间', dataIndex: 'created_at' },
      {
        title: '操作',
        render: (_, record) => (
          <Space>
            <Button type="link" onClick={() => restoreHeldOrder(record)}>
              恢复
            </Button>
            <Button type="link" danger onClick={() => cancelHeldOrder(record.id)}>
              取消
            </Button>
          </Space>
        )
      }
    ],
    []
  );

  return (
    <div className="pos-page">
      {contextHolder}
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>POS销售订单</Typography.Title>
          <Typography.Text type="secondary">商品扫码/搜索、会员识别、模拟支付和销售订单生成</Typography.Text>
        </div>
        <Tag color="blue">收银演示</Tag>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={15}>
          <Card title="商品搜索与SKU选择">
            <Space className="pos-toolbar" wrap>
              <Select
                className="store-select"
                placeholder="选择门店"
                value={storeId}
                options={stores.map((store) => ({ value: store.id, label: store.name }))}
                onChange={(value) => {
                  setStoreId(value);
                  setCart([]);
                }}
              />
              <Input.Search
                className="sku-search"
                placeholder="输入商品名称、SKU、条码、颜色或尺码"
                allowClear
                enterButton="搜索"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                onSearch={setKeyword}
              />
            </Space>
            <Table
              rowKey="sku_id"
              className="pos-table"
              size="middle"
              loading={loading}
              columns={skuColumns}
              dataSource={skuResults}
              pagination={{ pageSize: 6 }}
            />
          </Card>
        </Col>

        <Col xs={24} xl={9}>
          <Card title="会员查询">
            <Space.Compact className="member-search">
              <Input
                placeholder="手机号 / 会员编号 / 姓名"
                value={memberKeyword}
                onChange={(event) => setMemberKeyword(event.target.value)}
                onPressEnter={handleMemberSearch}
              />
              <Button type="primary" onClick={handleMemberSearch}>
                查询
              </Button>
            </Space.Compact>
            {selectedMember ? (
              <div className="member-detail-card">
                <div className="member-detail-header">
                  <div>
                    <div className="member-name">{selectedMember.name}</div>
                    <div className="member-level">{selectedMember.level}</div>
                  </div>
                  <Button size="small" onClick={() => setSelectedMember(null)}>
                    清除
                  </Button>
                </div>
                <div className="member-info-grid">
                  <span>会员号</span>
                  <strong>{selectedMember.member_no}</strong>
                  <span>手机号</span>
                  <strong>{selectedMember.phone}</strong>
                  <span>当前积分</span>
                  <strong>{selectedMember.points}</strong>
                  <span>累计消费</span>
                  <strong>{money(selectedMember.total_spent)}</strong>
                </div>
                <div className="member-tag-section">
                  <span>可用优惠券</span>
                  <Space wrap>
                    {(selectedMember.available_coupons.length ? selectedMember.available_coupons : ['满299减40券']).map(
                      (coupon) => (
                        <Tag color="blue" key={coupon}>
                          {coupon}
                        </Tag>
                      )
                    )}
                  </Space>
                </div>
                <div className="member-tag-section">
                  <span>会员标签</span>
                  <Space wrap>
                    {(selectedMember.member_tags.length
                      ? selectedMember.member_tags
                      : selectedMember.tags.split(',').filter(Boolean)
                    ).map((tag) => (
                      <Tag color="geekblue" key={tag}>
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                </div>
              </div>
            ) : members.length ? (
              <Select
                className="member-select"
                placeholder="选择查询到的会员"
                options={members.map((member) => ({
                  value: member.id,
                  label: `${member.name} / ${member.phone} / ${member.level}`
                }))}
                onChange={(id) => setSelectedMember(members.find((member) => member.id === id) ?? null)}
              />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未选择会员" />
            )}
          </Card>

          <Card title="结算信息" className="pos-section">
            <Space direction="vertical" className="settlement-panel" size={12}>
              <Select
                placeholder="选择促销活动"
                allowClear
                value={promotionId}
                options={promotions.map((item) => ({
                  value: item.id,
                  label: `${item.name}（${Math.round(item.discount_rate * 100)}折）`
                }))}
                onChange={setPromotionId}
              />
              <Select
                value={paymentMethod}
                className="payment-select"
                popupMatchSelectWidth={false}
                options={['微信支付', '支付宝', '银联卡', '现金'].map((method) => ({
                  value: method,
                  label: method
                }))}
                onChange={setPaymentMethod}
              />
              <Divider />
              <div className="settlement-row">
                <span>原价金额</span>
                <strong>{money(originalAmount)}</strong>
              </div>
              <div className="settlement-row">
                <span>折扣金额</span>
                <strong className="discount-text">-{money(discountAmount)}</strong>
              </div>
              <div className="settlement-row settlement-total">
                <span>实收金额</span>
                <strong>{money(paidAmount)}</strong>
              </div>
              <Space className="pos-action-buttons" wrap>
                <Button
                  type="primary"
                  size="large"
                  loading={submitting}
                  disabled={!cart.length}
                  onClick={submitOrder}
                >
                  确认收银
                </Button>
                <Button size="large" disabled={!cart.length} onClick={holdOrder}>
                  挂单
                </Button>
                <Button danger size="large" disabled={!cart.length && !selectedMember} onClick={cancelOrder}>
                  取消订单
                </Button>
              </Space>
              <div className="hold-order-note">当前本地挂单：{heldOrders.length} 单</div>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title="购物车" className="pos-section">
        <Table
          rowKey="sku_id"
          size="middle"
          columns={cartColumns}
          dataSource={cart}
          pagination={false}
          locale={{ emptyText: '请从商品列表加入购物车' }}
        />
      </Card>

      <Card title="挂起订单列表" className="pos-section">
        <Table
          rowKey="id"
          size="middle"
          columns={heldOrderColumns}
          dataSource={heldOrders}
          pagination={false}
          locale={{ emptyText: '暂无挂起订单' }}
        />
      </Card>

      <Card title="最近订单" className="pos-section">
        <Table
          rowKey="id"
          size="middle"
          columns={orderColumns}
          dataSource={recentOrders}
          pagination={false}
        />
      </Card>
    </div>
  );
}
