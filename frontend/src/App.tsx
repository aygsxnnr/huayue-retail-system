import { Navigate, Route, Routes } from 'react-router-dom';
import { BrowserRouter } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import POSOrder from './pages/POSOrder';

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
          <Route path="products" element={<PlaceholderPage title="商品与促销" />} />
          <Route path="inventory" element={<PlaceholderPage title="库存与补货" />} />
          <Route path="members" element={<PlaceholderPage title="会员与营销" />} />
          <Route path="finance" element={<PlaceholderPage title="财务对账" />} />
          <Route path="reports" element={<PlaceholderPage title="报表中心" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
