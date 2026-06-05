import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import FinanceReconciliation from './pages/FinanceReconciliation';
import InventoryReplenishment from './pages/InventoryReplenishment';
import MemberMarketing from './pages/MemberMarketing';
import POSOrder from './pages/POSOrder';
import ProductPromotion from './pages/ProductPromotion';
import ReportsCenter from './pages/ReportsCenter';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="pos" element={<POSOrder />} />
          <Route path="products" element={<ProductPromotion />} />
          <Route path="inventory" element={<InventoryReplenishment />} />
          <Route path="members" element={<MemberMarketing />} />
          <Route path="finance" element={<FinanceReconciliation />} />
          <Route path="reports" element={<ReportsCenter />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
