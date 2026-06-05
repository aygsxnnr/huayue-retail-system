import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
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
import dayjs from 'dayjs';
import * as echarts from 'echarts';
import MetricCard from '../components/MetricCard';
import ResizableTable from '../components/ResizableTable';
import { fetchInventory, type InventoryItem } from '../api/inventory';
import {
  createCoupon,
  createProduct,
  createPromotion,
  createSku,
  fetchCoupons,
  fetchProducts,
  fetchPromotions,
  fetchSalesOrders,
  fetchSkus,
  generateSkuCode,
  updateCoupon,
  updateCouponStatus,
  updateProduct,
  updateProductStatus,
  updatePromotion,
  updatePromotionStatus,
  updateSku,
  updateSkuStatus,
  type Coupon,
  type CouponPayload,
  type Product,
  type ProductPayload,
  type Promotion,
  type PromotionPayload,
  type SKU,
  type SKUCodePreview,
  type SKUPayload,
  type SalesOrder
} from '../api/products';

function money(value?: number) {
  return `¥${Number(value ?? 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`;
}

function percent(value?: number) {
  return `${Number(value ?? 0).toFixed(1)}%`;
}

function dateText(value?: string) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('zh-CN');
}

function tagColor(value: string) {
  if (['在售', '启用', '进行中', '可用', '已审批', '新品', '成长期'].includes(value)) return 'green';
  if (['未开始', '成熟期'].includes(value)) return 'blue';
  if (['清货期', '即将结束'].includes(value)) return 'orange';
  if (['停售', '停用', '下架', '已结束', '已过期', '已停用'].includes(value)) return 'red';
  return 'default';
}

function promotionDisplayStatus(record: Promotion) {
  if (record.status === '已停用') return '已停用';
  const today = new Date();
  const start = new Date(record.start_date);
  const end = new Date(record.end_date);
  if (today < start) return '未开始';
  if (today > end) return '已结束';
  return '进行中';
}

function isEndingSoon(record: Promotion) {
  const end = new Date(record.end_date).getTime();
  const now = Date.now();
  const diffDays = (end - now) / 86400000;
  return promotionDisplayStatus(record) === '进行中' && diffDays >= 0 && diffDays <= 7;
}

function couponRate(record: Coupon) {
  return record.issued_count > 0 ? (record.used_count / record.issued_count) * 100 : 0;
}

function discountText(record: Promotion | Coupon) {
  if ('coupon_type' in record) {
    if (record.discount_amount > 0) return money(record.discount_amount);
    if (record.discount_rate > 0 && record.discount_rate < 1) return `${Math.round(record.discount_rate * 100)}折`;
    return '-';
  }
  return record.discount_rate < 1 ? `${Math.round(record.discount_rate * 100)}折` : record.description || '-';
}

function productName(record?: Product | null) {
  return record?.name || record?.product_name || '-';
}

function productCode(record?: Product | null) {
  return record?.code || record?.product_code || '';
}

function displayProductCode(record?: Product | null) {
  return productCode(record) || '编码缺失';
}

function isStandardProductCode(code?: string) {
  return /^[A-Z]{2}\d{5}$/.test((code || '').trim());
}

function compareCodeValue(a: string, b: string, standard: (value?: string) => boolean) {
  const aCode = a || '';
  const bCode = b || '';
  const aValid = standard(aCode);
  const bValid = standard(bCode);
  if (aValid !== bValid) return aValid ? -1 : 1;
  if (!aCode && bCode) return 1;
  if (aCode && !bCode) return -1;
  return aCode.localeCompare(bCode, 'zh-CN', { numeric: true, sensitivity: 'base' });
}

function skuCode(record: SKU) {
  return record.sku_code || record.code || '-';
}

function skuPrice(record: SKU) {
  return record.list_price ?? record.sale_price ?? record.price ?? 0;
}

function compareSkuCode(a: SKU, b: SKU) {
  return compareCodeValue(skuCode(a), skuCode(b), isStandardSkuCode);
}

function compareProductCode(a: Product, b: Product) {
  return compareCodeValue(productCode(a), productCode(b), isStandardProductCode);
}

function productForSku(record: SKU, products: Product[]) {
  return record.product ?? products.find((product) => product.id === record.product_id) ?? null;
}

function sortProducts(items: Product[]) {
  return [...items].sort(compareProductCode);
}

function compareSkuByProductThenCode(a: SKU, b: SKU, products: Product[]) {
  const aProduct = productForSku(a, products);
  const bProduct = productForSku(b, products);
  const productResult = compareCodeValue(
    a.product_code || productCode(aProduct),
    b.product_code || productCode(bProduct),
    isStandardProductCode
  );
  return productResult || compareSkuCode(a, b);
}

function skuSegment(code: string, start: number, end: number) {
  if (!code) return '-';
  return isStandardSkuCode(code) ? code.slice(start, end) : '旧格式';
}

function isStandardSkuCode(code?: string) {
  return /^[A-Z]{2}\d{5}[A-Z]{2}[0-9A-Z]{2}[0-9A-Z]{2}$/.test((code || '').trim());
}

function mainColorCode(record: SKU) {
  return record.main_color_code || skuSegment(skuCode(record), 7, 9);
}

function subColorCode(record: SKU) {
  return record.sub_color_code || skuSegment(skuCode(record), 9, 11);
}

function sizeCode(record: SKU) {
  return record.size_code || skuSegment(skuCode(record), 11, 13);
}

function productCodeFromSku(record: SKU) {
  return record.product_code || (isStandardSkuCode(skuCode(record)) ? skuCode(record).slice(0, 7) : '');
}

function isStandardRecord(record: SKU) {
  return record.is_standard_code ?? isStandardSkuCode(skuCode(record));
}

type ProductFormValues = Omit<ProductPayload, 'launch_date'> & { launch_date: dayjs.Dayjs };
type PromotionFormValues = Omit<PromotionPayload, 'start_date' | 'end_date'> & {
  start_date: dayjs.Dayjs;
  end_date: dayjs.Dayjs;
};
type CouponFormValues = Omit<CouponPayload, 'valid_start' | 'valid_end'> & {
  valid_start: dayjs.Dayjs;
  valid_end: dayjs.Dayjs;
};
type SKUFormValues = Required<Pick<SKUPayload, 'product_id' | 'sku_code' | 'color' | 'size' | 'barcode' | 'list_price' | 'status'>>;

const productStatuses = ['在售', '停售', '下架'];
const skuStatuses = ['启用', '停用'];
const promotionStatuses = ['未开始', '进行中', '已结束', '已停用'];
const couponStatuses = ['未开始', '可用', '已过期', '已停用'];
const lifecycleStatuses = ['新品', '成长期', '成熟期', '清货期', '下架'];

function CategorySalesChart({ data }: { data: Array<{ category: string; sales_amount: number }> }) {
  useEffect(() => {
    const node = document.getElementById('product-category-sales-chart');
    if (!node) return;
    const chart = echarts.init(node);
    chart.setOption({
      color: ['#1677ff'],
      tooltip: { trigger: 'axis' },
      grid: { left: 64, right: 24, top: 28, bottom: 48 },
      xAxis: { type: 'category', data: data.map((item) => item.category), axisTick: { show: false } },
      yAxis: {
        type: 'value',
        axisLabel: { formatter: (value: number) => `${value / 1000}k` },
        splitLine: { lineStyle: { color: '#edf2f7' } }
      },
      series: [
        {
          name: '品类销售额',
          type: 'bar',
          barWidth: 28,
          data: data.map((item) => item.sales_amount),
          itemStyle: { borderRadius: [4, 4, 0, 0] }
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

  return <div id="product-category-sales-chart" className="chart-box chart-box-rank" />;
}

export default function ProductPromotion() {
  const [messageApi, contextHolder] = message.useMessage();
  const [modal, modalContextHolder] = Modal.useModal();
  const [productForm] = Form.useForm<ProductFormValues>();
  const [skuForm] = Form.useForm<SKUFormValues>();
  const [promotionForm] = Form.useForm<PromotionFormValues>();
  const [couponForm] = Form.useForm<CouponFormValues>();
  const [products, setProducts] = useState<Product[]>([]);
  const [skus, setSkus] = useState<SKU[]>([]);
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [productKeyword, setProductKeyword] = useState('');
  const [productStatus, setProductStatus] = useState('全部');
  const [skuKeyword, setSkuKeyword] = useState('');
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [productModalOpen, setProductModalOpen] = useState(false);
  const [editingSku, setEditingSku] = useState<SKU | null>(null);
  const [skuModalOpen, setSkuModalOpen] = useState(false);
  const [skuPreview, setSkuPreview] = useState<SKUCodePreview | null>(null);
  const [skuPreviewLoading, setSkuPreviewLoading] = useState(false);
  const [editingPromotion, setEditingPromotion] = useState<Promotion | null>(null);
  const [promotionModalOpen, setPromotionModalOpen] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState<Coupon | null>(null);
  const [couponModalOpen, setCouponModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const watchedSkuProductId = Form.useWatch('product_id', skuForm);
  const watchedSkuColor = Form.useWatch('color', skuForm);
  const watchedSkuSize = Form.useWatch('size', skuForm);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [productData, skuData, promotionData, couponData, inventoryData, orderData] = await Promise.all([
      fetchProducts(),
      fetchSkus(),
      fetchPromotions(),
      fetchCoupons(),
      fetchInventory(),
      fetchSalesOrders()
      ]);
      setProducts(sortProducts(productData));
      setSkus([...skuData].sort((a, b) => compareSkuByProductThenCode(a, b, productData)));
      setPromotions(promotionData);
      setCoupons(couponData);
      setInventory(inventoryData);
      setOrders(orderData);
    } catch {
      setError('商品与促销数据读取失败，请确认后端服务已启动。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!skuModalOpen || !watchedSkuProductId || !watchedSkuColor || !watchedSkuSize) {
      setSkuPreview(null);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setSkuPreviewLoading(true);
      try {
        const preview = await generateSkuCode({
          product_id: watchedSkuProductId,
          color: watchedSkuColor,
          size: watchedSkuSize
        });
        if (cancelled) return;
        setSkuPreview(preview);
        skuForm.setFieldsValue({
          sku_code: preview.sku_code,
          barcode: editingSku && preview.sku_code === skuCode(editingSku) ? editingSku.barcode : preview.barcode
        });
      } catch {
        if (!cancelled) {
          setSkuPreview(null);
          messageApi.error('SKU编码预览生成失败，请检查商品、颜色和尺码。');
        }
      } finally {
        if (!cancelled) setSkuPreviewLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [editingSku, messageApi, skuForm, skuModalOpen, watchedSkuColor, watchedSkuProductId, watchedSkuSize]);

  const openProductModal = (record?: Product) => {
    setEditingProduct(record ?? null);
    productForm.setFieldsValue(
      record
        ? { ...record, launch_date: dayjs(record.launch_date) }
        : {
            code: '',
            name: '',
            category: '',
            season: '四季',
            brand: '华悦',
            status: '在售',
            lifecycle_status: '新品',
            launch_date: dayjs()
          }
    );
    setProductModalOpen(true);
  };

  const saveProduct = async () => {
    const values = await productForm.validateFields();
    setSubmitting(true);
    try {
      const payload: ProductPayload = {
        ...values,
        code: values.code?.trim() || undefined,
        launch_date: values.launch_date.format('YYYY-MM-DD')
      };
      if (editingProduct) {
        await updateProduct(editingProduct.id, payload);
        messageApi.success('商品信息已更新');
      } else {
        await createProduct(payload);
        messageApi.success('商品新增成功，可继续创建 SKU');
      }
      setProductModalOpen(false);
      await loadData();
    } catch {
      messageApi.error('商品保存失败，请检查商品编码是否重复。');
    } finally {
      setSubmitting(false);
    }
  };

  const openSkuModal = (record?: SKU, product?: Product) => {
    setEditingSku(record ?? null);
    setSkuPreview(null);
    skuForm.setFieldsValue(
      record
        ? {
            product_id: record.product_id,
            sku_code: skuCode(record),
            color: record.color || '',
            size: record.size || '',
            barcode: record.barcode || '',
            list_price: skuPrice(record),
            status: record.status || '启用'
          }
        : {
            product_id: product?.id ?? products[0]?.id,
            sku_code: '',
            color: '',
            size: '',
            barcode: '',
            list_price: 0,
            status: '启用'
          }
    );
    setSkuModalOpen(true);
  };

  const saveSku = async () => {
    const values = await skuForm.validateFields();
    const duplicateCurrentSku = skuPreview?.duplicate_sku && (!editingSku || skuPreview.sku_code !== skuCode(editingSku));
    if (duplicateCurrentSku) {
      messageApi.error('该颜色尺码组合已存在');
      return;
    }
    setSubmitting(true);
    try {
      const payload: SKUPayload = {
        ...values,
        barcode: values.barcode,
        code: values.sku_code,
        sale_price: values.list_price
      };
      if (editingSku) {
        await updateSku(editingSku.id, payload);
        messageApi.success('SKU信息已更新');
      } else {
        const sku = await createSku(payload);
        if (Number.isFinite(sku.created_inventory_count)) {
          messageApi.success(`SKU 创建成功，已同步生成 ${sku.created_inventory_count || 0} 条门店库存记录。`);
        } else {
          messageApi.success('SKU 创建成功，已同步生成门店库存记录，可在库存与补货页面进行补货管理。');
        }
      }
      setSkuModalOpen(false);
      setEditingSku(null);
      await loadData();
    } catch {
      messageApi.error('SKU保存失败，请稍后重试。');
    } finally {
      setSubmitting(false);
    }
  };

  const openPromotionModal = (record?: Promotion) => {
    setEditingPromotion(record ?? null);
    promotionForm.setFieldsValue(
      record
        ? { ...record, start_date: dayjs(record.start_date), end_date: dayjs(record.end_date) }
        : {
            name: '',
            promotion_type: '折扣',
            discount_rate: 0.9,
            start_date: dayjs(),
            end_date: dayjs().add(14, 'day'),
            status: '未开始',
            description: '',
            applicable_scope: '全部商品',
            approval_status: '已审批'
          }
    );
    setPromotionModalOpen(true);
  };

  const savePromotion = async () => {
    const values = await promotionForm.validateFields();
    setSubmitting(true);
    try {
      const payload: PromotionPayload = {
        ...values,
        start_date: values.start_date.format('YYYY-MM-DD'),
        end_date: values.end_date.format('YYYY-MM-DD')
      };
      if (editingPromotion) {
        await updatePromotion(editingPromotion.id, payload);
        messageApi.success('促销活动已更新');
      } else {
        await createPromotion(payload);
        messageApi.success('促销活动已新增');
      }
      setPromotionModalOpen(false);
      await loadData();
    } catch {
      messageApi.error('促销活动保存失败，请检查日期和折扣率。');
    } finally {
      setSubmitting(false);
    }
  };

  const openCouponModal = (record?: Coupon) => {
    setEditingCoupon(record ?? null);
    couponForm.setFieldsValue(
      record
        ? { ...record, valid_start: dayjs(record.valid_start), valid_end: dayjs(record.valid_end) }
        : {
            code: '',
            name: '',
            coupon_type: '满减券',
            promotion_id: null,
            discount_amount: 0,
            discount_rate: 1,
            threshold_amount: 0,
            valid_start: dayjs(),
            valid_end: dayjs().add(30, 'day'),
            target_group: '全部会员',
            issued_count: 0,
            used_count: 0,
            status: '可用'
          }
    );
    setCouponModalOpen(true);
  };

  const saveCoupon = async () => {
    const values = await couponForm.validateFields();
    setSubmitting(true);
    try {
      const payload: CouponPayload = {
        ...values,
        promotion_id: values.promotion_id ?? null,
        valid_start: values.valid_start.format('YYYY-MM-DD'),
        valid_end: values.valid_end.format('YYYY-MM-DD')
      };
      if (editingCoupon) {
        await updateCoupon(editingCoupon.id, payload);
        messageApi.success('优惠券已更新');
      } else {
        await createCoupon(payload);
        messageApi.success('优惠券已新增');
      }
      setCouponModalOpen(false);
      await loadData();
    } catch {
      messageApi.error('优惠券保存失败，请检查编号是否重复。');
    } finally {
      setSubmitting(false);
    }
  };

  const confirmStatusChange = (
    title: string,
    status: string,
    action: () => Promise<unknown>,
  ) => {
    modal.confirm({
      title,
      content: `确认将状态修改为“${status}”？`,
      okText: '确认修改',
      cancelText: '取消',
      onOk: async () => {
        try {
          await action();
          messageApi.success('状态已更新');
          await loadData();
        } catch {
          messageApi.error('状态更新失败，请稍后重试。');
        }
      }
    });
  };

  const inventoryBySku = useMemo(() => {
    const map = new Map<number, number>();
    inventory.forEach((item) => map.set(item.sku_id, (map.get(item.sku_id) ?? 0) + item.quantity));
    return map;
  }, [inventory]);

  const metrics = useMemo(() => {
    const activePromotions = promotions.filter((item) => promotionDisplayStatus(item) === '进行中').length;
    const lowStockSkus = skus.filter((sku) => (inventoryBySku.get(sku.id) ?? 0) < 5).length;
    const averageDiscount = promotions.length
      ? promotions.reduce((sum, item) => sum + (item.discount_rate || 1), 0) / promotions.length
      : 1;
    const issued = coupons.reduce((sum, item) => sum + item.issued_count, 0);
    const used = coupons.reduce((sum, item) => sum + item.used_count, 0);
    return {
      productCount: products.length,
      skuCount: skus.length,
      onSaleProductCount: products.filter((item) => item.status === '在售').length,
      lowStockSkus,
      activePromotions,
      couponCount: coupons.length,
      averageDiscount: averageDiscount * 10,
      couponUseRate: issued > 0 ? (used / issued) * 100 : 0
    };
  }, [coupons, inventoryBySku, products, promotions, skus]);

  const filteredProducts = useMemo(
    () =>
      products
        .filter((item) => {
          const keywordMatched = !productKeyword.trim() || productName(item).includes(productKeyword.trim());
          const statusMatched = productStatus === '全部' || item.status === productStatus;
          return keywordMatched && statusMatched;
        })
        .sort(compareProductCode),
    [productKeyword, productStatus, products]
  );

  const filteredSkus = useMemo(
    () =>
      skus
        .filter((item) => {
          const keyword = skuKeyword.trim();
          const mappedProduct = item.product ?? products.find((product) => product.id === item.product_id);
          return !keyword || skuCode(item).includes(keyword) || productName(mappedProduct).includes(keyword);
        })
        .sort((a, b) => compareSkuByProductThenCode(a, b, products)),
    [products, skuKeyword, skus]
  );

  const salesAnalysis = useMemo(() => {
    const productMap = new Map<number, { product_name: string; category: string; quantity: number; sales_amount: number }>();
    const promotionMap = new Map<number, { promotion_name: string; order_count: number; sales_amount: number; discount_amount: number }>();
    orders.forEach((order) => {
      if (order.promotion_id) {
        const promotion = promotions.find((item) => item.id === order.promotion_id);
        const current = promotionMap.get(order.promotion_id) ?? {
          promotion_name: promotion?.name ?? `活动${order.promotion_id}`,
          order_count: 0,
          sales_amount: 0,
          discount_amount: 0
        };
        current.order_count += 1;
        current.sales_amount += order.paid_amount;
        current.discount_amount += order.discount_amount;
        promotionMap.set(order.promotion_id, current);
      }
      order.items.forEach((item) => {
        const product = item.sku?.product;
        if (!product) return;
        const current = productMap.get(product.id) ?? {
          product_name: product.name,
          category: product.category,
          quantity: 0,
          sales_amount: 0
        };
        current.quantity += item.quantity;
        current.sales_amount += item.subtotal;
        productMap.set(product.id, current);
      });
    });
    const productRanks = Array.from(productMap.values()).sort((a, b) => b.sales_amount - a.sales_amount);
    const categoryMap = new Map<string, number>();
    productRanks.forEach((item) => categoryMap.set(item.category, (categoryMap.get(item.category) ?? 0) + item.sales_amount));
    return {
      productRanks,
      categorySales: Array.from(categoryMap.entries()).map(([category, sales_amount]) => ({ category, sales_amount })),
      promotionEffect: Array.from(promotionMap.values()).sort((a, b) => b.sales_amount - a.sales_amount)
    };
  }, [orders, promotions]);

  const productColumns: ColumnsType<Product> = [
    {
      title: '商品编码',
      render: (_, record) => displayProductCode(record),
      sorter: compareProductCode,
      defaultSortOrder: 'ascend',
      width: 120
    },
    { title: '商品名称', render: (_, record) => productName(record), width: 180 },
    { title: '商品分类', dataIndex: 'category', width: 120 },
    { title: '季节', dataIndex: 'season', width: 100 },
    { title: '吊牌价', dataIndex: 'list_price', render: money, width: 100 },
    { title: '成本价', dataIndex: 'cost_price', render: money, width: 100 },
    { title: '上市日期', dataIndex: 'launch_date', render: dateText, width: 130 },
    { title: '生命周期状态', dataIndex: 'lifecycle_status', width: 120, render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    { title: '商品状态', dataIndex: 'status', width: 100, render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    {
      title: '操作',
      fixed: 'right',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button type="link">查看</Button>
          <Button type="link" onClick={() => openProductModal(record)}>编辑</Button>
          <Button type="link" onClick={() => openSkuModal(undefined, record)}>新增 SKU</Button>
          <Button
            type="link"
            onClick={() => {
              const firstSku = skus.find((sku) => sku.product_id === record.id);
              if (firstSku) {
                openSkuModal(firstSku);
              } else {
                messageApi.info('该商品暂无 SKU，请先新增 SKU 后再调价');
                openSkuModal(undefined, record);
              }
            }}
          >
            调价
          </Button>
          <Button
            type="link"
            danger
            onClick={() => confirmStatusChange('下架商品', '下架', () => updateProductStatus(record.id, '下架'))}
          >
            下架
          </Button>
          <Select
            size="small"
            value={record.status}
            popupMatchSelectWidth={false}
            options={productStatuses.map((status) => ({ value: status, label: status }))}
            onChange={(status) =>
              confirmStatusChange('修改商品状态', status, () => updateProductStatus(record.id, status))
            }
          />
        </Space>
      )
    }
  ];

  const skuColumns: ColumnsType<SKU> = [
    {
      title: 'SKU编码',
      render: (_, record) => (
        <Space>
          <span>{skuCode(record)}</span>
          {!isStandardRecord(record) ? <Tag color="orange">旧格式</Tag> : null}
        </Space>
      ),
      width: 180,
      sorter: compareSkuCode
    },
    {
      title: '所属商品',
      width: 180,
      render: (_, record) => productName(productForSku(record, products))
    },
    { title: '颜色', dataIndex: 'color', width: 120, render: (value: string) => value || '-' },
    { title: '尺码', dataIndex: 'size', width: 100, render: (value: string) => value || '-' },
    {
      title: '商品编码',
      width: 120,
      render: (_, record) => productCodeFromSku(record) || displayProductCode(productForSku(record, products)),
      sorter: (a, b) =>
        compareCodeValue(
          a.product_code || productCode(productForSku(a, products)),
          b.product_code || productCode(productForSku(b, products)),
          isStandardProductCode
        )
    },
    { title: '主色编码', width: 100, render: (_, record) => mainColorCode(record) },
    { title: '细分色编码', width: 110, render: (_, record) => subColorCode(record) },
    { title: '尺码编码', width: 100, render: (_, record) => sizeCode(record) },
    { title: '条码', width: 160, render: (_, record) => record.barcode || '-' },
    { title: '销售价', width: 100, render: (_, record) => money(skuPrice(record)) },
    { title: 'SKU状态', dataIndex: 'status', width: 100, render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    { title: '当前库存', width: 100, render: (_, record) => inventoryBySku.get(record.id) ?? 0 },
    {
      title: '操作',
      fixed: 'right',
      width: 180,
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => openSkuModal(record)}>编辑</Button>
          <Select
            size="small"
            value={skuStatuses.includes(record.status) ? record.status : '启用'}
            popupMatchSelectWidth={false}
            options={skuStatuses.map((status) => ({ value: status, label: status }))}
            onChange={(status) => confirmStatusChange('修改SKU状态', status, () => updateSkuStatus(record.id, status))}
          />
        </Space>
      )
    }
  ];

  const promotionColumns: ColumnsType<Promotion> = [
    { title: '活动编号', render: (_, record) => `PM${String(record.id).padStart(5, '0')}` },
    { title: '活动名称', dataIndex: 'name' },
    { title: '活动类型', dataIndex: 'promotion_type' },
    { title: '适用范围', dataIndex: 'applicable_scope' },
    { title: '开始时间', dataIndex: 'start_date', render: dateText },
    { title: '结束时间', dataIndex: 'end_date', render: dateText },
    { title: '折扣率/优惠规则', render: (_, record) => discountText(record) },
    { title: '审批状态', dataIndex: 'approval_status', render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    {
      title: '活动状态',
      render: (_, record) => (
        <Space>
          <Tag color={tagColor(promotionDisplayStatus(record))}>{promotionDisplayStatus(record)}</Tag>
          {isEndingSoon(record) ? <Tag color="orange">即将结束</Tag> : null}
        </Space>
      )
    },
    {
      title: '操作',
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => openPromotionModal(record)}>编辑</Button>
          <Select
            size="small"
            value={record.status}
            popupMatchSelectWidth={false}
            options={promotionStatuses.map((status) => ({ value: status, label: status }))}
            onChange={(status) =>
              confirmStatusChange('修改促销状态', status, () => updatePromotionStatus(record.id, status))
            }
          />
        </Space>
      )
    }
  ];

  const couponColumns: ColumnsType<Coupon> = [
    { title: '优惠券编号', dataIndex: 'code' },
    { title: '优惠券名称', dataIndex: 'name' },
    { title: '所属活动', render: (_, record) => record.promotion?.name ?? '独立发券' },
    { title: '优惠类型', dataIndex: 'coupon_type' },
    { title: '优惠金额/折扣率', render: (_, record) => discountText(record) },
    { title: '使用门槛', dataIndex: 'threshold_amount', render: (value: number) => (value > 0 ? money(value) : '无门槛') },
    { title: '有效期', render: (_, record) => `${dateText(record.valid_start)} 至 ${dateText(record.valid_end)}` },
    { title: '目标会员群体', dataIndex: 'target_group' },
    { title: '发放数量', dataIndex: 'issued_count' },
    { title: '已核销数量', dataIndex: 'used_count' },
    { title: '核销率', render: (_, record) => percent(couponRate(record)) },
    { title: '状态', dataIndex: 'status', render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    {
      title: '操作',
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => openCouponModal(record)}>编辑</Button>
          <Select
            size="small"
            value={record.status}
            popupMatchSelectWidth={false}
            options={couponStatuses.map((status) => ({ value: status, label: status }))}
            onChange={(status) =>
              confirmStatusChange('修改优惠券状态', status, () => updateCouponStatus(record.id, status))
            }
          />
        </Space>
      )
    }
  ];

  if (error) {
    return <Alert type="error" message={error} showIcon />;
  }

  return (
    <div className="product-page">
      {contextHolder}
      {modalContextHolder}
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>商品与促销管理</Typography.Title>
          <Typography.Text type="secondary">商品资料、SKU价格、促销活动与优惠券统一管理</Typography.Text>
        </div>
        <Tag color="blue">第五阶段A</Tag>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6} xl={3}>
          <MetricCard title="商品总数" value={metrics.productCount} suffix="个" />
        </Col>
        <Col xs={24} sm={12} lg={6} xl={3}>
          <MetricCard title="SKU总数" value={metrics.skuCount} suffix="个" />
        </Col>
        <Col xs={24} sm={12} lg={6} xl={3}>
          <MetricCard title="在售商品数" value={metrics.onSaleProductCount} suffix="个" />
        </Col>
        <Col xs={24} sm={12} lg={6} xl={3}>
          <MetricCard title="低库存SKU数" value={metrics.lowStockSkus} suffix="个" />
        </Col>
        <Col xs={24} sm={12} lg={6} xl={3}>
          <MetricCard title="进行中促销数" value={metrics.activePromotions} suffix="个" />
        </Col>
        <Col xs={24} sm={12} lg={6} xl={3}>
          <MetricCard title="优惠券数量" value={metrics.couponCount} suffix="张" />
        </Col>
        <Col xs={24} sm={12} lg={6} xl={3}>
          <MetricCard title="平均折扣" value={metrics.averageDiscount} suffix="折" precision={1} />
        </Col>
        <Col xs={24} sm={12} lg={6} xl={3}>
          <MetricCard title="优惠券核销率" value={metrics.couponUseRate} suffix="%" precision={1} />
        </Col>
      </Row>

      <Card className="product-section">
        <Tabs
          items={[
            {
              key: 'products',
              label: '商品列表',
              children: (
                <>
                  <Space className="product-toolbar" wrap>
                    <Button type="primary" onClick={() => openProductModal()}>新增商品</Button>
                    <Input.Search
                      className="product-search"
                      placeholder="输入商品名称"
                      allowClear
                      value={productKeyword}
                      onChange={(event) => setProductKeyword(event.target.value)}
                      onSearch={setProductKeyword}
                    />
                    <Select
                      className="inventory-filter"
                      value={productStatus}
                      options={['全部', '在售', '停售', '下架'].map((value) => ({ value, label: value }))}
                      onChange={setProductStatus}
                    />
                  </Space>
                  <ResizableTable rowKey="id" loading={loading} columns={productColumns} dataSource={filteredProducts} scroll={{ x: 1360 }} />
                </>
              )
            },
            {
              key: 'skus',
              label: 'SKU管理',
              children: (
                <>
                  <Space className="product-toolbar" wrap>
                    <Button type="primary" onClick={() => openSkuModal()}>新增 SKU</Button>
                    <Input.Search
                      className="product-search"
                      placeholder="输入商品名或SKU"
                      allowClear
                      value={skuKeyword}
                      onChange={(event) => setSkuKeyword(event.target.value)}
                      onSearch={setSkuKeyword}
                    />
                  </Space>
                  <ResizableTable rowKey="id" loading={loading} columns={skuColumns} dataSource={filteredSkus} scroll={{ x: 1560 }} />
                </>
              )
            },
            {
              key: 'promotions',
              label: '促销活动',
              children: (
                <>
                  <Space className="product-toolbar" wrap>
                    <Button type="primary" onClick={() => openPromotionModal()}>新增促销活动</Button>
                  </Space>
                  <Table rowKey="id" loading={loading} columns={promotionColumns} dataSource={promotions} scroll={{ x: 1360 }} />
                </>
              )
            },
            {
              key: 'coupons',
              label: '优惠券管理',
              children: (
                <>
                  <Space className="product-toolbar" wrap>
                    <Button type="primary" onClick={() => openCouponModal()}>新增优惠券</Button>
                  </Space>
                  <Table rowKey="id" loading={loading} columns={couponColumns} dataSource={coupons} scroll={{ x: 1660 }} />
                </>
              )
            },
            {
              key: 'analysis',
              label: '商品分析',
              children: (
                <Row gutter={[16, 16]}>
                  <Col xs={24} xl={12}>
                    <Card title="商品销售排行">
                      <Table
                        rowKey="product_name"
                        size="small"
                        pagination={false}
                        dataSource={salesAnalysis.productRanks}
                        locale={{ emptyText: <Empty description="暂无销售数据" /> }}
                        columns={[
                          { title: '商品名称', dataIndex: 'product_name' },
                          { title: '品类', dataIndex: 'category' },
                          { title: '销量', dataIndex: 'quantity', render: (value: number) => `${value}件` },
                          { title: '销售额', dataIndex: 'sales_amount', render: money }
                        ]}
                      />
                    </Card>
                  </Col>
                  <Col xs={24} xl={12}>
                    <Card title="品类销售额图表">
                      <CategorySalesChart data={salesAnalysis.categorySales} />
                    </Card>
                  </Col>
                  <Col xs={24}>
                    <Card title="促销效果分析">
                      <Table
                        rowKey="promotion_name"
                        pagination={false}
                        dataSource={salesAnalysis.promotionEffect}
                        locale={{ emptyText: <Empty description="暂无促销销售数据" /> }}
                        columns={[
                          { title: '活动名称', dataIndex: 'promotion_name' },
                          { title: '订单数', dataIndex: 'order_count', render: (value: number) => `${value}单` },
                          { title: '活动销售额', dataIndex: 'sales_amount', render: money },
                          { title: '促销让利', dataIndex: 'discount_amount', render: money }
                        ]}
                      />
                    </Card>
                  </Col>
                </Row>
              )
            }
          ]}
        />
      </Card>

      <Modal
        title={editingProduct ? '编辑商品' : '新增商品'}
        open={productModalOpen}
        onOk={saveProduct}
        onCancel={() => setProductModalOpen(false)}
        confirmLoading={submitting}
        okText="保存"
        cancelText="取消"
        width={720}
      >
        <Form form={productForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="商品编码" name="code">
                <Input placeholder="可留空，系统按品类自动生成" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="商品名称" name="name" rules={[{ required: true, message: '请输入商品名称' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="商品分类" name="category" rules={[{ required: true, message: '请输入商品分类' }]}>
                <Input placeholder="如：女装、男装、配饰" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="季节" name="season" rules={[{ required: true, message: '请输入季节' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="品牌" name="brand" rules={[{ required: true, message: '请输入品牌' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="上市日期" name="launch_date" rules={[{ required: true, message: '请选择上市日期' }]}>
                <DatePicker className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="生命周期状态" name="lifecycle_status" rules={[{ required: true, message: '请选择生命周期' }]}>
                <Select options={lifecycleStatuses.map((value) => ({ value, label: value }))} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="商品状态" name="status" rules={[{ required: true, message: '请选择商品状态' }]}>
                <Select options={productStatuses.map((value) => ({ value, label: value }))} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title={editingSku ? '编辑SKU' : '新增SKU'}
        open={skuModalOpen}
        onOk={saveSku}
        onCancel={() => {
          setSkuModalOpen(false);
          setEditingSku(null);
        }}
        confirmLoading={submitting}
        okText="保存"
        cancelText="取消"
        width={720}
      >
        <Form form={skuForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="所属商品" name="product_id" rules={[{ required: true, message: '请选择所属商品' }]}>
                <Select
                  showSearch
                  disabled={Boolean(editingSku)}
                  optionFilterProp="label"
                  options={sortProducts(products).map((item) => ({
                    value: item.id,
                    label: `${displayProductCode(item)} - ${productName(item)}`
                  }))}
                  placeholder="请选择商品"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="SKU编码" name="sku_code" rules={[{ required: true, message: '请输入SKU编码' }]}>
                <Input readOnly placeholder="选择商品并填写颜色、尺码后自动生成" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="颜色" name="color" rules={[{ required: true, message: '请输入颜色' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="尺码" name="size" rules={[{ required: true, message: '请输入尺码' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="条码" name="barcode" rules={[{ required: true, message: '请输入条码' }]}>
                <Input readOnly placeholder="系统自动生成13位数字条码" />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Space wrap>
                <Tag color="geekblue">
                  商品编码：{skuPreview?.product_code ?? editingSku?.product_code ?? skuSegment(skuForm.getFieldValue('sku_code') || '', 0, 7)}
                </Tag>
                <Tag color="blue">
                  主色编码：{skuPreview?.main_color_code ?? editingSku?.main_color_code ?? skuSegment(skuForm.getFieldValue('sku_code') || '', 7, 9)}
                </Tag>
                <Tag color="cyan">
                  细分色编码：{skuPreview?.sub_color_code ?? editingSku?.sub_color_code ?? skuSegment(skuForm.getFieldValue('sku_code') || '', 9, 11)}
                </Tag>
                <Tag color="purple">
                  尺码编码：{skuPreview?.size_code ?? editingSku?.size_code ?? skuSegment(skuForm.getFieldValue('sku_code') || '', 11, 13)}
                </Tag>
                {skuPreviewLoading ? <Tag color="processing">编码生成中</Tag> : null}
              </Space>
            </Col>
            <Col span={24}>
              <Alert
                type={
                  skuPreview?.duplicate_sku && (!editingSku || skuPreview.sku_code !== skuCode(editingSku))
                    ? 'error'
                    : editingSku && !isStandardRecord(editingSku) && !skuPreview
                      ? 'warning'
                      : 'info'
                }
                showIcon
                message={
                  skuPreview
                    ? `${skuPreview.color_match_note}；${skuPreview.size_match_note}${skuPreview.duplicate_sku && (!editingSku || skuPreview.sku_code !== skuCode(editingSku)) ? '；该颜色尺码组合已存在' : ''}`
                    : editingSku && !isStandardRecord(editingSku)
                      ? '旧编码格式，请重新生成编码。修改颜色或尺码后系统会重新调用编码接口。'
                    : '选择商品并填写颜色、尺码后，系统将自动生成 SKU 编码和 13 位数字条码。'
                }
              />
            </Col>
            <Col span={12}>
              <Form.Item label="销售价" name="list_price" rules={[{ required: true, message: '请输入销售价' }]}>
                <InputNumber min={0.01} precision={2} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="SKU状态" name="status" rules={[{ required: true, message: '请选择SKU状态' }]}>
                <Select options={skuStatuses.map((value) => ({ value, label: value }))} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title={editingPromotion ? '编辑促销活动' : '新增促销活动'}
        open={promotionModalOpen}
        onOk={savePromotion}
        onCancel={() => setPromotionModalOpen(false)}
        confirmLoading={submitting}
        okText="保存"
        cancelText="取消"
        width={760}
      >
        <Form form={promotionForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="活动名称" name="name" rules={[{ required: true, message: '请输入活动名称' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="活动类型" name="promotion_type" rules={[{ required: true, message: '请输入活动类型' }]}>
                <Input placeholder="折扣 / 满减 / 会员折扣" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="适用范围" name="applicable_scope" rules={[{ required: true, message: '请输入适用范围' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="折扣率" name="discount_rate" rules={[{ required: true, message: '请输入折扣率' }]}>
                <InputNumber min={0} max={1} step={0.01} precision={2} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="开始时间" name="start_date" rules={[{ required: true, message: '请选择开始时间' }]}>
                <DatePicker className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="结束时间" name="end_date" rules={[{ required: true, message: '请选择结束时间' }]}>
                <DatePicker className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="审批状态" name="approval_status" rules={[{ required: true, message: '请输入审批状态' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="活动状态" name="status" rules={[{ required: true, message: '请选择活动状态' }]}>
                <Select options={promotionStatuses.map((value) => ({ value, label: value }))} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item label="优惠规则说明" name="description">
                <Input.TextArea rows={3} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title={editingCoupon ? '编辑优惠券' : '新增优惠券'}
        open={couponModalOpen}
        onOk={saveCoupon}
        onCancel={() => setCouponModalOpen(false)}
        confirmLoading={submitting}
        okText="保存"
        cancelText="取消"
        width={820}
      >
        <Form form={couponForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="优惠券编号" name="code" rules={[{ required: true, message: '请输入优惠券编号' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="优惠券名称" name="name" rules={[{ required: true, message: '请输入优惠券名称' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="优惠类型" name="coupon_type" rules={[{ required: true, message: '请输入优惠类型' }]}>
                <Input placeholder="满减券 / 折扣券 / 会员券 / 积分券" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="所属活动" name="promotion_id">
                <Select
                  allowClear
                  options={promotions.map((item) => ({ value: item.id, label: item.name }))}
                  placeholder="可选择独立发券"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="优惠金额" name="discount_amount" rules={[{ required: true, message: '请输入优惠金额' }]}>
                <InputNumber min={0} precision={2} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="折扣率" name="discount_rate" rules={[{ required: true, message: '请输入折扣率' }]}>
                <InputNumber min={0} max={1} step={0.01} precision={2} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="使用门槛" name="threshold_amount" rules={[{ required: true, message: '请输入使用门槛' }]}>
                <InputNumber min={0} precision={2} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="目标会员群体" name="target_group" rules={[{ required: true, message: '请输入目标会员群体' }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="有效开始" name="valid_start" rules={[{ required: true, message: '请选择有效开始日期' }]}>
                <DatePicker className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="有效结束" name="valid_end" rules={[{ required: true, message: '请选择有效结束日期' }]}>
                <DatePicker className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="发放数量" name="issued_count" rules={[{ required: true, message: '请输入发放数量' }]}>
                <InputNumber min={0} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="已核销数量" name="used_count" rules={[{ required: true, message: '请输入已核销数量' }]}>
                <InputNumber min={0} className="full-width-control" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
                <Select options={couponStatuses.map((value) => ({ value, label: value }))} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
}
