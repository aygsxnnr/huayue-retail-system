from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, ensure_coupon_schema, ensure_member_schema, ensure_product_schema, ensure_sales_order_item_schema
from .routers import coupons, dashboard, finance, inventory, members, products, promotions, reports, sales, stores

Base.metadata.create_all(bind=engine)
ensure_member_schema()
ensure_coupon_schema()
ensure_product_schema()
ensure_sales_order_item_schema()

app = FastAPI(
    title="华悦零售门店数字化管理系统 API",
    description="第一阶段后端基础：门店、商品、SKU、会员、订单、库存、财务和经营看板数据接口。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix="/api")
app.include_router(promotions.router, prefix="/api")
app.include_router(coupons.router, prefix="/api")
app.include_router(members.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(stores.router, prefix="/api")
app.include_router(finance.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/", tags=["系统"])
def health_check():
    return {"message": "华悦零售门店数字化管理系统后端已启动"}
