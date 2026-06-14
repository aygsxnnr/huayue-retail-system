import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { getDefaultPathByRole } from './api/auth';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import FinanceReconciliation from './pages/FinanceReconciliation';
import InventoryReplenishment from './pages/InventoryReplenishment';
import LoginPage from './pages/LoginPage';
import MemberMarketing from './pages/MemberMarketing';
import OperationLog from './pages/OperationLog';
import POSOrder from './pages/POSOrder';
import ProductPromotion from './pages/ProductPromotion';
import ReportsCenter from './pages/ReportsCenter';
import UserPermission from './pages/UserPermission';

type RoleName =
  | '系统管理员'
  | '总经理'
  | '店长'
  | '收银员'
  | '库存管理员'
  | '营销专员'
  | '财务人员';

function getLocalUserRole() {
  const userText = localStorage.getItem('huayue_user');

  if (!userText) {
    return '';
  }

  try {
    const user = JSON.parse(userText);
    return user.role || '';
  } catch {
    localStorage.removeItem('huayue_user');
    return '';
  }
}

function ProtectedRoute() {
  const token = localStorage.getItem('huayue_token');

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

function RoleRoute({
  roles,
  children
}: {
  roles: RoleName[];
  children: JSX.Element;
}) {
  const token = localStorage.getItem('huayue_token');
  const role = getLocalUserRole();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!roles.includes(role as RoleName)) {
    return <Navigate to={getDefaultPathByRole(role)} replace />;
  }

  return children;
}

function LoginRoute() {
  const token = localStorage.getItem('huayue_token');
  const role = getLocalUserRole();

  if (token) {
    return <Navigate to={getDefaultPathByRole(role)} replace />;
  }

  return <LoginPage />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />

            <Route
              path="dashboard"
              element={
                <RoleRoute roles={['系统管理员', '总经理']}>
                  <Dashboard />
                </RoleRoute>
              }
            />

            <Route
              path="pos"
              element={
                <RoleRoute roles={['系统管理员', '店长', '收银员']}>
                  <POSOrder />
                </RoleRoute>
              }
            />

            <Route
              path="products"
              element={
                <RoleRoute roles={['系统管理员', '店长']}>
                  <ProductPromotion />
                </RoleRoute>
              }
            />

            <Route
              path="inventory"
              element={
                <RoleRoute roles={['系统管理员', '店长', '库存管理员']}>
                  <InventoryReplenishment />
                </RoleRoute>
              }
            />

            <Route
              path="members"
              element={
                <RoleRoute roles={['系统管理员', '店长', '营销专员']}>
                  <MemberMarketing />
                </RoleRoute>
              }
            />

            <Route
              path="finance"
              element={
                <RoleRoute roles={['系统管理员', '总经理', '财务人员']}>
                  <FinanceReconciliation />
                </RoleRoute>
              }
            />

            <Route
              path="reports"
              element={
                <RoleRoute roles={['系统管理员', '总经理']}>
                  <ReportsCenter />
                </RoleRoute>
              }
            />

            <Route
              path="users"
              element={
                <RoleRoute roles={['系统管理员']}>
                  <UserPermission />
                </RoleRoute>
              }
            />

            <Route
              path="operation-logs"
              element={
                <RoleRoute roles={['系统管理员']}>
                  <OperationLog />
                </RoleRoute>
              }
            />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
