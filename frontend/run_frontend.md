# 前端运行说明

## 安装依赖

```bash
cd frontend
npm install
```

## 启动前端

```bash
npm run dev
```

启动后访问：

- 前端页面：http://localhost:5173

## 联调说明

首页经营看板会通过 Vite 代理请求后端接口：

- `/api/dashboard/summary`

请先启动后端：

```bash
cd backend
uvicorn app.main:app --reload
```
