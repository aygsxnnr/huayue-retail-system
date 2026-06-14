# 华悦快时尚服饰有限公司 —— 零售门店数字化管理系统

## 1. 项目概述

本项目是“华悦快时尚服饰有限公司”的课程设计系统开发项目，系统名称为：

**零售门店数字化管理系统**

系统面向快时尚服装企业的门店经营场景，目标是构建一套覆盖门店销售、商品促销、库存补货、会员营销、财务对账和经营看板的一体化管理系统。

本项目是信息系统分析与设计课程中的系统实现部分，前期已经完成或正在完成：

- 企业案例描述
- 访谈问题设计与需求分析
- 用例图
- DFD 上下文图、0 层图、子图
- 数据字典
- 数据库实体设计
- 初步 UI 原型设计

本 README 用于指导 Codex 根据现有需求完成系统开发和实现。

---

## 2. 业务背景

华悦快时尚服饰有限公司是一家面向年轻消费群体的快时尚服装企业，主要销售女装、男装、鞋包配饰等产品。企业采用“小批量上新、快速补货、快速清货”的经营模式。

随着门店规模扩大，企业原有门店经营方式暴露出以下问题：

1. POS 销售、库存、会员、促销、财务数据分散，难以统一分析。
2. 门店库存更新不及时，畅销款容易断码断货。
3. 补货主要依赖人工经验，缺少基于销售数据的自动预警和建议。
4. 促销活动下发和执行结果难以统一跟踪。
5. 会员数据没有充分用于精准营销和复购分析。
6. 财务对账依赖人工核对，差异处理效率较低。
7. 管理层缺少实时经营看板，难以及时掌握销售、库存、会员和利润情况。

因此，本系统需要将门店销售、商品、库存、会员、财务和看板数据打通，形成一个可演示、可操作、可扩展的数字化门店运营系统。

---

## 3. 系统目标

本系统目标不是开发真实商用系统，而是完成课程设计所需的可演示原型系统。

系统应达到以下目标：

1. 支持门店 POS 销售订单录入、会员识别、促销匹配和支付模拟。
2. 支持商品、SKU、价格、促销活动和优惠券管理。
3. 支持库存查询、库存预警、补货申请、补货审核和在途库存跟踪。
4. 支持会员档案、会员标签、RFM 分群和营销触达记录。
5. 支持支付流水、财务对账、毛利分析和促销损益展示。
6. 支持首页经营看板，展示销售额、成交笔数、客单价、会员销售占比、缺货 SKU 数、库存周转天数、毛利额等指标。
7. 使用清晰的数据库结构支撑 DFD 和数据字典中的核心数据存储。
8. 提供可运行的前后端项目，便于课堂展示和后续报告撰写。

---

## 4. 技术栈建议

为了便于 Codex 快速实现，本项目采用前后端分离结构。

### 4.1 前端

建议使用：

- React
- Vite
- TypeScript
- Ant Design
- ECharts
- Axios
- React Router

前端主要负责：

- 页面布局
- 表格展示
- 表单录入
- 图表可视化
- 调用后端 API
- 本地演示交互

### 4.2 后端

建议使用：

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- SQLite

后端主要负责：

- 数据模型定义
- REST API
- 模拟业务逻辑
- 数据初始化
- 财务、库存、会员、看板等基础计算

### 4.3 数据库

开发阶段使用：

- SQLite

原因：

- 便于本地运行
- 不依赖复杂数据库环境
- 适合课程展示
- 方便 Codex 自动生成和调试

后续如需扩展，可迁移到 MySQL 或 PostgreSQL。

---

## 5. 推荐项目结构

Codex 请按照下面结构创建项目：

```text
huayue-retail-system/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── seed.py
│   │   ├── routers/
│   │   │   ├── dashboard.py
│   │   │   ├── products.py
│   │   │   ├── sales.py
│   │   │   ├── inventory.py
│   │   │   ├── members.py
│   │   │   ├── finance.py
│   │   │   └── promotions.py
│   │   └── services/
│   │       ├── inventory_service.py
│   │       ├── finance_service.py
│   │       ├── member_service.py
│   │       └── dashboard_service.py
│   ├── requirements.txt
│   └── run_backend.md
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   └── request.ts
│   │   ├── layouts/
│   │   │   └── MainLayout.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── POSOrder.tsx
│   │   │   ├── ProductPromotion.tsx
│   │   │   ├── InventoryReplenishment.tsx
│   │   │   ├── MemberMarketing.tsx
│   │   │   └── FinanceReconciliation.tsx
│   │   ├── components/
│   │   │   ├── MetricCard.tsx
│   │   │   ├── StatusTag.tsx
│   │   │   └── PageHeader.tsx
│   │   └── styles/
│   │       └── global.css
└── docs/
    ├── dfd-summary.md
    ├── data-dictionary.md
    ├── database-design.md
    └── ui-design.md

## 认证测试账号初始化

如果是全新数据库，或执行过大规模数据重建命令，例如：

```bash
python -m app.seed_large --reset true
```

请在后端目录下重新生成认证测试账号：

```bash
cd backend
python -m app.seed_auth
```

默认测试账号：

| 用户名       | 密码     | 角色    |
| --------- | ------ | ----- |
| admin     | 123456 | 系统管理员 |
| manager   | 123456 | 总经理   |
| cashier   | 123456 | 收银员   |
| stock     | 123456 | 库存管理员 |
| marketing | 123456 | 营销专员  |
| finance   | 123456 | 财务人员  |

说明：`seed_auth` 用于幂等创建或修复默认登录账号，不负责生成业务运营数据。如果当前数据库中已经存在这些账号，可以不重复执行；如果执行过数据库 reset 或大规模 seed 重建，建议重新执行一次。

