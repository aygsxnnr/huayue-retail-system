# 后端运行说明

## 安装依赖

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 初始化数据库

```bash
python -m app.seed
```

初始化后会在 `backend/huayue.db` 生成 SQLite 数据库，并写入门店、商品、SKU、会员、订单、库存、财务和看板测试数据。

## 启动后端

```bash
uvicorn app.main:app --reload
```

启动后访问：

- API 首页：http://localhost:8000/
- Swagger 文档：http://localhost:8000/docs
