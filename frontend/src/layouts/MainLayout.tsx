import {
  BarChartOutlined,
  BellOutlined,
  DashboardOutlined,
  DollarOutlined,
  GiftOutlined,
  ShoppingCartOutlined,
  ShopOutlined,
  TeamOutlined
} from '@ant-design/icons';
import { Avatar, Badge, Breadcrumb, Layout, Menu, Space, Typography } from 'antd';
import type { MenuProps } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

const menuItems: MenuProps['items'] = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '首页看板' },
  { key: '/pos', icon: <ShoppingCartOutlined />, label: 'POS销售订单' },
  { key: '/products', icon: <GiftOutlined />, label: '商品与促销' },
  { key: '/inventory', icon: <ShopOutlined />, label: '库存与补货' },
  { key: '/members', icon: <TeamOutlined />, label: '会员与营销' },
  { key: '/finance', icon: <DollarOutlined />, label: '财务对账' },
  { key: '/reports', icon: <BarChartOutlined />, label: '报表中心' }
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Layout className="app-shell">
      <Sider width={236} className="app-sider">
        <div className="brand-block">
          <div className="brand-mark">悦</div>
          <div>
            <div className="brand-title">华悦零售</div>
            <div className="brand-subtitle">门店数字化管理系统</div>
          </div>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div className="header-left">
            <Typography.Title level={4}>华悦快时尚服饰有限公司</Typography.Title>
            <Breadcrumb
              items={[
                { title: '首页' },
                { title: '经营看板' }
              ]}
            />
          </div>
          <Space size={18} className="header-actions">
            <span className="role-text">当前角色：总经理/管理层</span>
            <Badge dot offset={[-2, 4]}>
              <BellOutlined className="header-bell" />
            </Badge>
            <Space size={8}>
              <Avatar className="user-avatar">管</Avatar>
              <span className="user-name">管理员</span>
            </Space>
          </Space>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
