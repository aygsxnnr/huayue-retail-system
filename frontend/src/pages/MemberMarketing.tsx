import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
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
import MetricCard from '../components/MetricCard';
import { fetchCoupons, type Coupon } from '../api/products';
import { createStore, fetchStores, updateStore, updateStoreStatus, type Store } from '../api/stores';
import {
  createMarketingTouchesBatch,
  createMember,
  fetchMarketingTouches,
  fetchMemberProfile,
  fetchMembers,
  fetchRepurchaseAnalysis,
  fetchRfm,
  recalculateRfm,
  updateMember,
  updateMemberStatus,
  type MarketingEffect,
  type MarketingTouch,
  type Member,
  type MemberProfile,
  type RepurchaseAnalysis,
  type RepurchaseRank,
  type RFMRecord
} from '../api/members';

const memberLevels = ['普通会员', '银卡会员', '金卡会员', '黑金会员'];
const memberStatuses = ['正常', '活跃', '沉睡', '流失风险', '已停用'];
const touchChannels = ['短信', '微信', 'APP推送', '小程序', '人工电话'];
const storeStatuses = ['正常营业', '临时歇业', '闭店升级', '已关闭', '停用'];
const normalStoreStatuses = ['正常营业', '营业中'];
const closedStoreStatuses = ['已关闭', '停用'];

interface RegisteredStoreItem {
  id?: number;
  code?: string;
  name: string;
}

function parseRegisteredStores(value?: string | null, stores: Store[] = []): RegisteredStoreItem[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) {
      return parsed
        .map((item) => {
          if (typeof item === 'string' || typeof item === 'number') {
            const store = stores.find((option) => String(option.id) === String(item) || option.name === String(item));
            return store ? { id: store.id, code: store.code, name: store.name } : { name: String(item) };
          }
          if (item && typeof item === 'object') {
            const id = Number((item as RegisteredStoreItem).id);
            const store = stores.find((option) => option.id === id || option.name === (item as RegisteredStoreItem).name);
            return store
              ? { id: store.id, code: store.code, name: store.name }
              : { id: Number.isFinite(id) ? id : undefined, code: (item as RegisteredStoreItem).code, name: (item as RegisteredStoreItem).name || '-' };
          }
          return null;
        })
        .filter(Boolean) as RegisteredStoreItem[];
    }
  } catch {
    // Legacy plain text is handled below.
  }
  return value
    .split(/[、,，]/)
    .map((name) => name.trim())
    .filter(Boolean)
    .map((name) => {
      const store = stores.find((option) => option.name === name || option.code === name);
      return store ? { id: store.id, code: store.code, name: store.name } : { name };
    });
}

function registeredStoreValues(value?: string | null, stores: Store[] = []) {
  return parseRegisteredStores(value, stores)
    .map((item) => (Number.isFinite(item.id) ? item.id : item.name))
    .filter(Boolean) as Array<number | string>;
}

function serializeRegisteredStores(values: Array<number | string> = [], stores: Store[] = []) {
  const selectedStores = values
    .map((value) => {
      const store = stores.find((item) => item.id === value || item.name === value);
      return store ? { id: store.id, code: store.code, name: store.name } : { name: String(value) };
    })
    .filter((item) => item.name && item.name !== 'undefined');
  return selectedStores.length
    ? JSON.stringify(selectedStores)
    : '';
}

function RegisteredStoreTags({ value, stores }: { value?: string | null; stores: Store[] }) {
  const items = parseRegisteredStores(value, stores);
  if (!items.length) return <span>-</span>;
  return (
    <Space wrap size={[0, 4]}>
      {items.map((item, index) => (
        <Tag key={`${item.id ?? item.name}-${index}`} color="blue">
          {item.code ? `${item.code} - ${item.name}` : item.name}
        </Tag>
      ))}
    </Space>
  );
}

function safeNumber(value: unknown) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function money(value: unknown) {
  return `¥${safeNumber(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function percent(value: unknown) {
  return `${safeNumber(value).toFixed(1)}%`;
}

function formatDate(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('zh-CN');
}

function maskPhone(phone?: string) {
  const value = phone || '';
  if (value.length < 7) return value || '-';
  return `${value.slice(0, 3)}****${value.slice(-4)}`;
}

function memberPoints(member?: Member | null) {
  return safeNumber(member?.current_points ?? member?.points);
}

function memberAmount(member?: Member | null) {
  return safeNumber(member?.total_amount ?? member?.total_spent);
}

function memberOrders(member?: Member | null) {
  return safeNumber(member?.total_orders ?? member?.total_times ?? member?.total_count ?? member?.cumulative_orders);
}

function memberLastPurchase(member?: Member | null) {
  return member?.last_purchase_date ?? member?.last_purchase_at ?? null;
}

function tagColor(value: string) {
  if (['活跃', '正常', '已核销', '高价值会员'].includes(value)) return 'green';
  if (['银卡会员', '金卡会员', '已点击', '已参与', '潜力会员'].includes(value)) return 'blue';
  if (['沉睡', '未参与', '未核销', '价格敏感会员'].includes(value)) return 'orange';
  if (['流失风险', '已停用', '已过期', '流失风险会员'].includes(value)) return 'red';
  if (value === '黑金会员') return 'purple';
  return 'default';
}

function storeStatusColor(value?: string) {
  if (!value || normalStoreStatuses.includes(value)) return 'green';
  if (value === '临时歇业') return 'orange';
  if (value === '闭店升级') return 'blue';
  if (closedStoreStatuses.includes(value)) return 'red';
  return 'default';
}

function storeOptionLabel(store: Store) {
  const base = `${store.code || '-'} - ${store.name || '-'}`;
  return normalStoreStatuses.includes(store.status) ? base : `${base}（${store.status || '状态未设置'}）`;
}

function LevelChart({ data }: { data: RepurchaseAnalysis['level_distribution'] }) {
  useEffect(() => {
    const node = document.getElementById('member-level-chart');
    if (!node) return;
    const chart = echarts.init(node);
    chart.setOption({
      color: ['#1677ff', '#13c2c2', '#faad14', '#722ed1'],
      tooltip: { trigger: 'item' },
      series: [
        {
          name: '会员等级',
          type: 'pie',
          radius: ['48%', '72%'],
          data: data.map((item) => ({ name: item.level, value: item.count })),
          label: { formatter: '{b}\n{d}%' }
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

  return <div id="member-level-chart" className="chart-box chart-box-small" />;
}

export default function MemberMarketing() {
  const [messageApi, contextHolder] = message.useMessage();
  const [memberForm] = Form.useForm();
  const [touchForm] = Form.useForm();
  const [storeForm] = Form.useForm();
  const [members, setMembers] = useState<Member[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [coupons, setCoupons] = useState<Coupon[]>([]);
  const [rfm, setRfm] = useState<RFMRecord[]>([]);
  const [touches, setTouches] = useState<MarketingTouch[]>([]);
  const [analysis, setAnalysis] = useState<RepurchaseAnalysis | null>(null);
  const [profile, setProfile] = useState<MemberProfile | null>(null);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [touchModalOpen, setTouchModalOpen] = useState(false);
  const [storeModalOpen, setStoreModalOpen] = useState(false);
  const [storeManageOpen, setStoreManageOpen] = useState(false);
  const [editingStore, setEditingStore] = useState<Store | null>(null);
  const [editingMember, setEditingMember] = useState<Member | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [keyword, setKeyword] = useState('');
  const [levelFilter, setLevelFilter] = useState('全部');
  const [statusFilter, setStatusFilter] = useState('全部');
  const [activeKey, setActiveKey] = useState('members');
  const selectedRegisteredStores = Form.useWatch('registered_store', memberForm) || [];

  const loadStores = async () => {
    try {
      const storeData = await fetchStores();
      setStores(storeData || []);
      return storeData || [];
    } catch {
      messageApi.warning('门店列表读取失败，注册门店下拉暂为空。');
      setStores([]);
      return [];
    }
  };

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [memberData, couponData, rfmData, touchData, analysisData] = await Promise.all([
        fetchMembers(),
        fetchCoupons(),
        fetchRfm(),
        fetchMarketingTouches(),
        fetchRepurchaseAnalysis()
      ]);
      setMembers(memberData);
      setCoupons(couponData);
      setRfm(rfmData);
      setTouches(touchData);
      setAnalysis(analysisData);
      if (!selectedMember && memberData.length) {
        setSelectedMember(memberData[0]);
      }
    } catch {
      setError('会员与营销数据读取失败，请确认后端服务已启动并重新初始化数据库。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStores();
    loadData();
  }, []);

  useEffect(() => {
    if (!selectedMember) return;
    fetchMemberProfile(selectedMember.id)
      .then(setProfile)
      .catch(() => setProfile(null));
  }, [selectedMember]);

  const filteredMembers = useMemo(
    () =>
      members.filter((member) => {
        const text = `${member.member_no}${member.name}${member.phone}`.toLowerCase();
        return (
          (!keyword || text.includes(keyword.toLowerCase())) &&
          (levelFilter === '全部' || member.level === levelFilter) &&
          (statusFilter === '全部' || member.status === statusFilter)
        );
      }),
    [keyword, levelFilter, members, statusFilter]
  );

  const metrics = useMemo(() => {
    const memberCount = members.length;
    const newCount = members.filter((item) => {
      const joined = new Date(item.joined_at);
      return !Number.isNaN(joined.getTime()) && Date.now() - joined.getTime() <= 30 * 24 * 60 * 60 * 1000;
    }).length;
    const activeCount = members.filter((item) => item.status === '活跃').length;
    const sleepingCount = members.filter((item) => item.status === '沉睡' || item.status === '流失风险').length;
    const totalSpent = members.reduce((sum, item) => sum + memberAmount(item), 0);
    const totalOrders = members.reduce((sum, item) => sum + memberOrders(item), 0);
    const repeatedMembers = members.filter((item) => memberOrders(item) >= 2).length;
    const issued = coupons.reduce((sum, item) => sum + safeNumber(item.issued_count), 0);
    const used = coupons.reduce((sum, item) => sum + safeNumber(item.used_count), 0);
    return {
      memberCount,
      newCount,
      activeCount,
      sleepingCount,
      memberSalesRatio: 76.8,
      averageOrderValue: totalOrders ? totalSpent / totalOrders : 0,
      repurchaseRate: memberCount ? (repeatedMembers / memberCount) * 100 : 0,
      couponWriteoffRate: issued ? (used / issued) * 100 : 0
    };
  }, [coupons, members]);

  const storeOptions = useMemo(() => {
    const selectedValues = selectedRegisteredStores as Array<number | string>;
    const options = stores.map((store) => ({
      value: store.id as number | string,
      label: storeOptionLabel(store),
      disabled: closedStoreStatuses.includes(store.status) && !selectedValues.includes(store.id)
    }));
    parseRegisteredStores(editingMember?.registered_store, stores).forEach((item) => {
      const value = Number.isFinite(item.id) ? item.id as number : item.name;
      if (!options.some((option) => option.value === value)) {
        options.push({
          value,
          label: item.code ? `${item.code} - ${item.name}` : item.name,
          disabled: false
        });
      }
    });
    return options;
  }, [editingMember?.registered_store, selectedRegisteredStores, stores]);

  const openCreateMember = () => {
    setEditingMember(null);
    memberForm.resetFields();
    memberForm.setFieldsValue({ level: '普通会员', status: '正常', points: 0, total_spent: 0, total_orders: 0, registered_store: [] });
    setMemberModalOpen(true);
  };

  const openEditMember = (member: Member) => {
    setEditingMember(member);
    memberForm.setFieldsValue({
      ...member,
      registered_store: registeredStoreValues(member.registered_store, stores)
    });
    setMemberModalOpen(true);
  };

  const submitMember = async () => {
    const values = await memberForm.validateFields();
    const payload = {
      ...values,
      registered_store: serializeRegisteredStores(values.registered_store, stores)
    };
    setSubmitting(true);
    try {
      if (editingMember) {
        await updateMember(editingMember.id, payload);
        messageApi.success('会员信息已更新');
      } else {
        await createMember(payload);
        messageApi.success('会员新增成功');
      }
      setMemberModalOpen(false);
      await loadData();
    } catch {
      messageApi.error('会员保存失败，请检查手机号是否重复。');
    } finally {
      setSubmitting(false);
    }
  };

  const changeStatus = async (member: Member) => {
    try {
      await updateMemberStatus(member.id, member.status === '已停用' ? '正常' : '已停用');
      messageApi.success(member.status === '已停用' ? '会员已启用' : '会员已停用');
      await loadData();
    } catch {
      messageApi.error('会员状态修改失败');
    }
  };

  const openStoreModal = (store?: Store) => {
    setEditingStore(store || null);
    storeForm.resetFields();
    storeForm.setFieldsValue(store || { status: '正常营业' });
    setStoreModalOpen(true);
  };

  const submitStore = async () => {
    const values = await storeForm.validateFields();
    setSubmitting(true);
    try {
      const store = editingStore
        ? await updateStore(editingStore.id, values)
        : await createStore(values);
      messageApi.success(editingStore ? '门店信息已更新' : '门店新增成功');
      const nextStores = await loadStores();
      const currentIds = memberForm.getFieldValue('registered_store') || [];
      if (store?.id && !editingStore) {
        const exists = nextStores.some((item) => item.id === store.id);
        memberForm.setFieldsValue({
          registered_store: Array.from(new Set([...(currentIds || []), exists ? store.id : store.id]))
        });
      }
      setStoreModalOpen(false);
      setEditingStore(null);
    } catch {
      messageApi.error(editingStore ? '门店信息更新失败，请检查门店编码是否重复。' : '门店新增失败，请检查门店编码是否重复。');
    } finally {
      setSubmitting(false);
    }
  };

  const changeStoreStatus = (store: Store, status: string) => {
    Modal.confirm({
      title: '确认修改门店状态',
      content: `确认将该门店状态修改为 ${status} 吗？历史数据将保留。`,
      okText: '确认修改',
      cancelText: '取消',
      onOk: async () => {
        try {
          await updateStoreStatus(store.id, status);
          messageApi.success('门店状态已更新');
          await loadStores();
        } catch {
          messageApi.error('门店状态修改失败');
        }
      }
    });
  };

  const openTouchModal = (member?: Member) => {
    const target = member || selectedMember;
    if (!target) {
      messageApi.error('请先选择会员');
      return;
    }
    setSelectedMember(target);
    touchForm.resetFields();
    touchForm.setFieldsValue({ member_id: target.id, coupon_ids: [], channels: ['微信'], remark: '手动发放' });
    setTouchModalOpen(true);
  };

  const submitTouch = async () => {
    const values = await touchForm.validateFields();
    const couponIds = values.coupon_ids || [];
    const channels = values.channels || [];
    Modal.confirm({
      title: '确认发放优惠券',
      content: `将向 1 位会员发放 ${couponIds.length} 张优惠券，并通过 ${channels.length} 个渠道触达。`,
      okText: '确认发放',
      cancelText: '取消',
      onOk: async () => {
        setSubmitting(true);
        try {
          const result = await createMarketingTouchesBatch({
            member_ids: [values.member_id],
            coupon_ids: couponIds,
            channels,
            remark: values.remark || '手动发放'
          });
          messageApi.success(`优惠券发放完成，新增 ${result.created_count} 条触达记录，跳过 ${result.skipped_count} 条重复记录。`);
          setTouchModalOpen(false);
          const [touchData, analysisData, couponData] = await Promise.all([
            fetchMarketingTouches(),
            fetchRepurchaseAnalysis(),
            fetchCoupons()
          ]);
          setTouches(touchData);
          setAnalysis(analysisData);
          setCoupons(couponData);
          if (selectedMember) {
            fetchMemberProfile(selectedMember.id).then(setProfile).catch(() => setProfile(null));
          }
        } catch {
          messageApi.error('发放优惠券失败，请检查会员或优惠券状态。');
        } finally {
          setSubmitting(false);
        }
      }
    });
  };

  const handleRecalculate = async () => {
    setSubmitting(true);
    try {
      const data = await recalculateRfm();
      setRfm(data);
      messageApi.success('RFM 已重新计算');
    } catch {
      messageApi.error('RFM 重新计算失败');
    } finally {
      setSubmitting(false);
    }
  };

  const memberColumns: ColumnsType<Member> = [
    { title: '会员号', dataIndex: 'member_no', width: 140 },
    { title: '姓名', dataIndex: 'name', width: 100 },
    { title: '手机号', dataIndex: 'phone', width: 130, render: maskPhone },
    { title: '注册门店', dataIndex: 'registered_store', width: 220, render: (value: string) => <RegisteredStoreTags value={value} stores={stores} /> },
    { title: '会员等级', dataIndex: 'level', width: 110, render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    { title: '当前积分', width: 100, render: (_, record) => memberPoints(record) },
    { title: '累计消费金额', width: 130, render: (_, record) => money(memberAmount(record)) },
    { title: '累计消费次数', width: 120, render: (_, record) => memberOrders(record) },
    { title: '最近消费日期', width: 160, render: (_, record) => formatDate(memberLastPurchase(record)) },
    { title: '会员状态', dataIndex: 'status', width: 110, render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    {
      title: '操作',
      width: 260,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => { setSelectedMember(record); setActiveKey('profile'); }}>
            查看画像
          </Button>
          <Button type="link" onClick={() => openEditMember(record)}>
            编辑会员
          </Button>
          <Button type="link" onClick={() => openTouchModal(record)}>
            发放优惠券
          </Button>
          <Popconfirm title={record.status === '已停用' ? '确认启用该会员？' : '确认停用该会员？'} onConfirm={() => changeStatus(record)}>
            <Button type="link" danger={record.status !== '已停用'}>
              {record.status === '已停用' ? '启用' : '停用'}
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  const rfmColumns: ColumnsType<RFMRecord> = [
    { title: '会员号', dataIndex: 'member_no' },
    { title: '姓名', dataIndex: 'name' },
    { title: 'R值', dataIndex: 'r_score' },
    { title: 'F值', dataIndex: 'f_score' },
    { title: 'M值', dataIndex: 'm_score' },
    { title: '会员分群', dataIndex: 'member_group', render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    { title: '主要标签', dataIndex: 'main_tags', render: (tags: string[]) => <Space wrap>{(tags || []).map((tag) => <Tag key={tag}>{tag}</Tag>)}</Space> },
    { title: '推荐运营策略', dataIndex: 'strategy' }
  ];

  const touchColumns: ColumnsType<MarketingTouch> = [
    { title: '触达编号', render: (_, record) => `MT${String(record.id).padStart(5, '0')}` },
    { title: '会员号', render: (_, record) => record.member?.member_no ?? '-' },
    { title: '会员姓名', render: (_, record) => record.member?.name ?? '-' },
    { title: '触达渠道', dataIndex: 'channel' },
    { title: '营销活动 / 优惠券', render: (_, record) => record.coupon?.name ?? record.remark ?? '-' },
    { title: '触达时间', dataIndex: 'touch_time', render: formatDate },
    { title: '参与状态', dataIndex: 'participation_status', render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    { title: '核销状态', dataIndex: 'writeoff_status', render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    {
      title: '操作',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => openTouchModal(record.member || undefined)}>
            发放优惠券
          </Button>
          <Button type="link" onClick={() => messageApi.info(`触达效果：${record.participation_status} / ${record.writeoff_status}`)}>
            查看效果
          </Button>
        </Space>
      )
    }
  ];

  const rankColumns: ColumnsType<RepurchaseRank> = [
    { title: '排名', dataIndex: 'rank', width: 80, render: (value: number) => <Tag color="blue">第{value}名</Tag> },
    { title: '会员号', dataIndex: 'member_no' },
    { title: '姓名', dataIndex: 'name' },
    { title: '累计消费次数', dataIndex: 'total_orders' },
    { title: '累计消费金额', dataIndex: 'total_spent', render: money },
    { title: '最近消费日期', dataIndex: 'last_purchase_at', render: formatDate },
    { title: '会员等级', dataIndex: 'level', render: (value: string) => <Tag color={tagColor(value)}>{value}</Tag> },
    { title: '复购标签', dataIndex: 'repurchase_tag', render: (value: string) => <Tag color="green">{value}</Tag> }
  ];

  const effectColumns: ColumnsType<MarketingEffect> = [
    { title: '活动 / 优惠券名称', dataIndex: 'name' },
    { title: '触达人数', dataIndex: 'touched_count' },
    { title: '点击人数', dataIndex: 'clicked_count' },
    { title: '参与人数', dataIndex: 'participated_count' },
    { title: '核销人数', dataIndex: 'writeoff_count' },
    { title: '核销率', dataIndex: 'writeoff_rate', render: percent },
    { title: '带动销售额', dataIndex: 'driven_sales_amount', render: money }
  ];

  const storeColumns: ColumnsType<Store> = [
    { title: '门店编码', dataIndex: 'code', width: 120, render: (value: string) => value || '-' },
    { title: '门店名称', dataIndex: 'name', width: 180, render: (value: string) => value || '-' },
    { title: '城市', dataIndex: 'city', width: 100, render: (value: string) => value || '-' },
    { title: '地址', dataIndex: 'address', width: 220, render: (value: string) => value || '-' },
    { title: '负责人', dataIndex: 'manager', width: 110, render: (value: string) => value || '-' },
    {
      title: '门店状态',
      dataIndex: 'status',
      width: 130,
      render: (value: string) => <Tag color={storeStatusColor(value)}>{value || '-'}</Tag>
    },
    {
      title: '操作',
      width: 260,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button type="link" onClick={() => openStoreModal(record)}>
            编辑
          </Button>
          <Select
            size="small"
            value={record.status || '正常营业'}
            style={{ width: 120 }}
            options={storeStatuses.map((status) => ({ value: status, label: status }))}
            onChange={(status) => changeStoreStatus(record, status)}
          />
        </Space>
      )
    }
  ];

  if (error) return <Alert type="error" message={error} showIcon />;

  return (
    <div className="member-page">
      {contextHolder}
      <div className="page-heading">
        <div>
          <Typography.Title level={3}>会员与营销管理</Typography.Title>
          <Typography.Text type="secondary">会员档案、标签分群、优惠券触达与复购分析</Typography.Text>
        </div>
        <Tag color="blue">第六阶段功能</Tag>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}><MetricCard title="会员总数" value={metrics.memberCount} suffix="人" /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="新增会员数" value={metrics.newCount} suffix="人" /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="活跃会员数" value={metrics.activeCount} suffix="人" /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="沉睡会员数" value={metrics.sleepingCount} suffix="人" /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="会员销售占比" value={metrics.memberSalesRatio} suffix="%" precision={1} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="平均客单价" value={metrics.averageOrderValue} prefix="¥" precision={2} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="复购率" value={metrics.repurchaseRate} suffix="%" precision={1} /></Col>
        <Col xs={24} sm={12} lg={6}><MetricCard title="优惠券核销率" value={metrics.couponWriteoffRate} suffix="%" precision={1} /></Col>
      </Row>

      <Card className="inventory-section">
        <Tabs
          activeKey={activeKey}
          onChange={setActiveKey}
          items={[
            {
              key: 'members',
              label: '会员列表',
              children: (
                <>
                  <Space className="inventory-toolbar" wrap>
                    <Input.Search placeholder="搜索手机号、姓名、会员号" allowClear value={keyword} onChange={(event) => setKeyword(event.target.value)} style={{ width: 260 }} />
                    <Select value={levelFilter} onChange={setLevelFilter} options={['全部', ...memberLevels].map((value) => ({ value, label: value }))} style={{ width: 140 }} />
                    <Select value={statusFilter} onChange={setStatusFilter} options={['全部', ...memberStatuses].map((value) => ({ value, label: value }))} style={{ width: 140 }} />
                    <Button type="primary" onClick={openCreateMember}>新增会员</Button>
                    <Button onClick={() => setStoreManageOpen(true)}>门店管理</Button>
                  </Space>
                  <Table rowKey="id" loading={loading} columns={memberColumns} dataSource={filteredMembers} scroll={{ x: 1500 }} pagination={{ pageSize: 8 }} />
                </>
              )
            },
            {
              key: 'profile',
              label: '会员画像',
              children: selectedMember && profile ? (
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Card title="基础信息">
                      <Descriptions bordered size="small" column={1}>
                        <Descriptions.Item label="会员号">{profile.member.member_no}</Descriptions.Item>
                        <Descriptions.Item label="姓名">{profile.member.name}</Descriptions.Item>
                        <Descriptions.Item label="手机号">{maskPhone(profile.member.phone)}</Descriptions.Item>
                        <Descriptions.Item label="注册时间">{formatDate(profile.member.joined_at)}</Descriptions.Item>
                        <Descriptions.Item label="注册门店"><RegisteredStoreTags value={profile.member.registered_store} stores={stores} /></Descriptions.Item>
                        <Descriptions.Item label="会员等级"><Tag color={tagColor(profile.member.level)}>{profile.member.level}</Tag></Descriptions.Item>
                        <Descriptions.Item label="当前积分">{memberPoints(profile.member)}</Descriptions.Item>
                        <Descriptions.Item label="会员状态"><Tag color={tagColor(profile.member.status)}>{profile.member.status}</Tag></Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="消费信息">
                      <Descriptions bordered size="small" column={1}>
                        <Descriptions.Item label="累计消费金额">{money(memberAmount(profile.member))}</Descriptions.Item>
                        <Descriptions.Item label="累计消费次数">{memberOrders(profile.member)}</Descriptions.Item>
                        <Descriptions.Item label="平均客单价">{money(memberOrders(profile.member) ? memberAmount(profile.member) / memberOrders(profile.member) : 0)}</Descriptions.Item>
                        <Descriptions.Item label="最近消费日期">{formatDate(memberLastPurchase(profile.member))}</Descriptions.Item>
                        <Descriptions.Item label="最近购买商品">{profile.recent_products.join('、')}</Descriptions.Item>
                        <Descriptions.Item label="偏好品类">{profile.preferred_categories.join('、')}</Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="标签信息">
                      <Space wrap>
                        {[
                          profile.tag_profile?.preference_tag,
                          profile.tag_profile?.price_sensitive_tag,
                          profile.tag_profile?.activity_tag,
                          profile.tag_profile?.risk_tag,
                          ...(profile.member.member_tags || [])
                        ].filter(Boolean).map((tag) => <Tag key={String(tag)} color={tagColor(String(tag))}>{tag}</Tag>)}
                      </Space>
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="推荐营销动作">
                      <List dataSource={profile.recommended_actions} renderItem={(item) => <List.Item>{item}</List.Item>} />
                    </Card>
                  </Col>
                </Row>
              ) : (
                <Empty description="请先选择会员查看画像" />
              )
            },
            {
              key: 'rfm',
              label: 'RFM分群',
              children: (
                <>
                  <Space className="inventory-toolbar"><Button type="primary" loading={submitting} onClick={handleRecalculate}>重新计算RFM</Button></Space>
                  <Table rowKey="member_id" loading={loading} columns={rfmColumns} dataSource={rfm} pagination={{ pageSize: 8 }} />
                </>
              )
            },
            {
              key: 'touches',
              label: '营销触达',
              children: (
                <>
                  <Space className="inventory-toolbar"><Button type="primary" onClick={() => openTouchModal()}>发放优惠券</Button></Space>
                  <Table rowKey="id" loading={loading} columns={touchColumns} dataSource={touches} scroll={{ x: 1200 }} pagination={{ pageSize: 8 }} />
                </>
              )
            },
            {
              key: 'analysis',
              label: '复购分析',
              children: analysis ? (
                <>
                  <Row gutter={[16, 16]}>
                    <Col xs={24} lg={14}>
                      <Card title="会员复购排行表">
                        <Table rowKey="member_id" columns={rankColumns} dataSource={analysis.repurchase_ranking} pagination={false} />
                      </Card>
                    </Col>
                    <Col xs={24} lg={10}>
                      <Card title="会员等级分布图">
                        <LevelChart data={analysis.level_distribution} />
                      </Card>
                    </Col>
                  </Row>
                  <Card title="营销效果分析表" className="inventory-section">
                    <Table rowKey="name" columns={effectColumns} dataSource={analysis.marketing_effects} pagination={false} />
                  </Card>
                </>
              ) : (
                <Empty description="暂无复购分析数据" />
              )
            }
          ]}
        />
      </Card>

      <Modal title={editingMember ? '编辑会员' : '新增会员'} open={memberModalOpen} onCancel={() => setMemberModalOpen(false)} onOk={submitMember} confirmLoading={submitting} okText="保存" cancelText="取消">
        <Form form={memberForm} layout="vertical">
          <Form.Item label="姓名" name="name" rules={[{ required: true, message: '请输入姓名' }]}><Input /></Form.Item>
          <Form.Item label="手机号" name="phone" rules={[{ required: true, message: '请输入手机号' }]}><Input /></Form.Item>
          <Form.Item label="会员等级" name="level"><Select options={memberLevels.map((value) => ({ value, label: value }))} /></Form.Item>
          <Form.Item label="会员状态" name="status"><Select options={memberStatuses.map((value) => ({ value, label: value }))} /></Form.Item>
          <Form.Item label="注册门店" name="registered_store">
            <Select
              mode="multiple"
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="可选择多个注册门店，非必填"
              options={storeOptions}
              dropdownRender={(menu) => (
                <>
                  {menu}
                  <Button type="link" block onClick={() => openStoreModal()}>
                    新增门店
                  </Button>
                  <Button type="link" block onClick={() => setStoreManageOpen(true)}>
                    门店管理
                  </Button>
                </>
              )}
            />
          </Form.Item>
          <Form.Item label="会员标签" name="tags"><Input placeholder="多个标签用逗号分隔" /></Form.Item>
          <Row gutter={12}>
            <Col span={8}><Form.Item label="积分" name="points"><InputNumber min={0} className="full-width-control" /></Form.Item></Col>
            <Col span={8}><Form.Item label="累计消费" name="total_spent"><InputNumber min={0} className="full-width-control" /></Form.Item></Col>
            <Col span={8}><Form.Item label="消费次数" name="total_orders"><InputNumber min={0} className="full-width-control" /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title="门店管理"
        open={storeManageOpen}
        onCancel={() => setStoreManageOpen(false)}
        footer={<Button onClick={() => setStoreManageOpen(false)}>关闭</Button>}
        width={960}
      >
        <Typography.Text type="secondary">
          门店新增、编辑和状态变更后续将接入登录、角色与权限管理模块进行控制。
        </Typography.Text>
        <Space className="inventory-toolbar" style={{ marginTop: 12, marginBottom: 12 }}>
          <Button type="primary" onClick={() => openStoreModal()}>
            新增门店
          </Button>
        </Space>
        <Table
          rowKey="id"
          columns={storeColumns}
          dataSource={stores}
          scroll={{ x: 1120 }}
          pagination={{ pageSize: 6 }}
        />
      </Modal>

      <Modal
        title={editingStore ? '编辑门店' : '新增门店'}
        open={storeModalOpen}
        onCancel={() => {
          setStoreModalOpen(false);
          setEditingStore(null);
        }}
        onOk={submitStore}
        confirmLoading={submitting}
        okText={editingStore ? '保存修改' : '保存门店'}
        cancelText="取消"
      >
        <Form form={storeForm} layout="vertical">
          <Form.Item label="门店编码" name="code" rules={[{ required: true, message: '请输入门店编码' }]}>
            <Input placeholder="例如：GZ001" />
          </Form.Item>
          <Form.Item label="门店名称" name="name" rules={[{ required: true, message: '请输入门店名称' }]}>
            <Input placeholder="例如：广州天河城店" />
          </Form.Item>
          <Form.Item label="城市" name="city">
            <Input placeholder="例如：广州" />
          </Form.Item>
          <Form.Item label="地址" name="address">
            <Input placeholder="请输入门店地址" />
          </Form.Item>
          <Form.Item label="店长/负责人" name="manager">
            <Input placeholder="请输入负责人姓名" />
          </Form.Item>
          <Form.Item label="状态" name="status">
            <Select options={storeStatuses.map((value) => ({ value, label: value }))} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="发放优惠券 / 记录触达" open={touchModalOpen} onCancel={() => setTouchModalOpen(false)} onOk={submitTouch} confirmLoading={submitting} okText="确认发放" cancelText="取消">
        <Form form={touchForm} layout="vertical">
          <Form.Item label="选择会员" name="member_id" rules={[{ required: true, message: '请选择会员' }]}>
            <Select showSearch optionFilterProp="label" options={members.map((member) => ({ value: member.id, label: `${member.member_no} - ${member.name}` }))} />
          </Form.Item>
          <Form.Item label="选择优惠券" name="coupon_ids" rules={[{ required: true, message: '请至少选择 1 张优惠券' }]}>
            <Select
              mode="multiple"
              allowClear
              optionFilterProp="label"
              placeholder="可多选优惠券"
              options={coupons.map((coupon) => ({ value: coupon.id, label: `${coupon.code || '-'} - ${coupon.name || '-'}` }))}
            />
          </Form.Item>
          <Form.Item label="触达渠道" name="channels" rules={[{ required: true, message: '请至少选择 1 个触达渠道' }]}>
            <Select
              mode="multiple"
              allowClear
              options={touchChannels.map((value) => ({ value, label: value }))}
            />
          </Form.Item>
          <Form.Item label="备注" name="remark"><Input.TextArea rows={3} placeholder="例如：针对沉睡会员发放回流券" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
