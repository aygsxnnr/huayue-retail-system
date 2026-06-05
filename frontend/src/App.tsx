import { Navigate, Route, Routes } from 'react-router-dom';
import { BrowserRouter } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import InventoryReplenishment from './pages/InventoryReplenishment';
import MemberMarketing from './pages/MemberMarketing';
import POSOrder from './pages/POSOrder';
import ProductPromotion from './pages/ProductPromotion';

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="placeholder-page">
      <h2>{title}</h2>
      <p>该模块将在后续阶段实现，当前阶段先完成首页经营看板。</p>
    </div>
  );
}

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
          <Route path="finance" element={<PlaceholderPage title="财务对账" />} />
          <Route path="reports" element={<PlaceholderPage title="报表中心" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
