import {
  AuditOutlined,
  BarChartOutlined,
  BellOutlined,
  DashboardOutlined,
  DollarOutlined,
  GiftOutlined,
  LogoutOutlined,
  ShoppingCartOutlined,
  ShopOutlined,
  TeamOutlined,
  UserOutlined
} from '@ant-design/icons';
import { Avatar, Badge, Breadcrumb, Button, Layout, Menu, Space, Typography, message } from 'antd';
import type { MenuProps } from 'antd';
import type { ReactNode } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { logout } from '../api/auth';
import type { CurrentUser } from '../api/auth';

const { Header, Sider, Content } = Layout;

type RoleName =
  | '系统管理员'
  | '总经理'
  | '店长'
  | '收银员'
  | '库存管理员'
  | '营销专员'
  | '财务人员';

type MenuEntry = {
  key: string;
  icon: ReactNode;
  label: string;
  roles: RoleName[];
};

const allRoles: RoleName[] = [
  '系统管理员',
  '总经理',
  '店长',
  '收银员',
  '库存管理员',
  '营销专员',
  '财务人员'
];

const menuEntries: MenuEntry[] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '首页看板',
    roles: ['系统管理员', '总经理']
  },
  {
    key: '/pos',
    icon: <ShoppingCartOutlined />,
    label: 'POS销售订单',
    roles: ['系统管理员', '店长', '收银员']
  },
  {
    key: '/products',
    icon: <GiftOutlined />,
    label: '商品与促销',
    roles: ['系统管理员', '店长']
  },
  {
    key: '/inventory',
    icon: <ShopOutlined />,
    label: '库存与补货',
    roles: ['系统管理员', '店长', '库存管理员']
  },
  {
    key: '/members',
    icon: <TeamOutlined />,
    label: '会员与营销',
    roles: ['系统管理员', '店长', '营销专员']
  },
  {
    key: '/finance',
    icon: <DollarOutlined />,
    label: '财务对账',
    roles: ['系统管理员', '总经理', '财务人员']
  },
  {
    key: '/reports',
    icon: <BarChartOutlined />,
    label: '报表中心',
    roles: ['系统管理员', '总经理']
  },
  {
    key: '/users',
    icon: <UserOutlined />,
    label: '用户管理',
    roles: ['系统管理员']
  },
  {
    key: '/operation-logs',
    icon: <AuditOutlined />,
    label: '操作日志',
    roles: ['系统管理员']
  }
];

function readLocalUser(): CurrentUser | null {
  const userText = localStorage.getItem('huayue_user');
  if (!userText) {
    return null;
  }

  try {
    return JSON.parse(userText) as CurrentUser;
  } catch {
    localStorage.removeItem('huayue_user');
    return null;
  }
}

function getMenuItemsByRole(role: string): MenuProps['items'] {
  const safeRole = allRoles.includes(role as RoleName) ? (role as RoleName) : '收银员';

  return menuEntries
    .filter((item) => item.roles.includes(safeRole))
    .map((item) => ({
      key: item.key,
      icon: item.icon,
      label: item.label
    }));
}

function getCurrentMenuLabel(pathname: string) {
  return menuEntries.find((item) => item.key === pathname)?.label || '经营看板';
}

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const currentUser = readLocalUser();
  const role = currentUser?.role || '未登录';
  const menuItems = getMenuItemsByRole(role);

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // 后端退出接口失败也允许清理本地登录状态
    }

    localStorage.removeItem('huayue_token');
    localStorage.removeItem('huayue_user');
    message.success('已退出登录');
    navigate('/login', { replace: true });
  };

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
                { title: getCurrentMenuLabel(location.pathname) }
              ]}
            />
          </div>

          <Space size={18} className="header-actions">
            <span className="role-text">当前角色：{role}</span>

            <Badge dot offset={[-2, 4]}>
              <BellOutlined className="header-bell" />
            </Badge>

            <Space size={8}>
              <Avatar className="user-avatar">
                {(currentUser?.real_name || currentUser?.username || '用').slice(0, 1)}
              </Avatar>
              <span className="user-name">{currentUser?.real_name || currentUser?.username || '用户'}</span>
            </Space>

            <Button type="link" icon={<LogoutOutlined />} onClick={handleLogout}>
              退出
            </Button>
          </Space>
        </Header>

        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
