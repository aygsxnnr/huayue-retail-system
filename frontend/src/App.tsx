import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
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

function ProtectedRoute() {
  const token = localStorage.getItem('huayue_token');

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

function LoginRoute() {
  const token = localStorage.getItem('huayue_token');

  if (token) {
    return <Navigate to="/dashboard" replace />;
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
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="pos" element={<POSOrder />} />
            <Route path="products" element={<ProductPromotion />} />
            <Route path="inventory" element={<InventoryReplenishment />} />
            <Route path="members" element={<MemberMarketing />} />
            <Route path="finance" element={<FinanceReconciliation />} />
            <Route path="reports" element={<ReportsCenter />} />
            <Route path="users" element={<UserPermission />} />
            <Route path="operation-logs" element={<OperationLog />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
