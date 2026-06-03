from datetime import date, datetime, timedelta

from .database import Base, SessionLocal, engine
from .models import (
    FinanceRecord,
    Inventory,
    Member,
    PaymentRecord,
    Product,
    Promotion,
    SKU,
    SalesOrder,
    SalesOrderItem,
    Store,
)


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed() -> None:
    reset_database()
    db = SessionLocal()
    try:
        stores = [
            Store(code="SH001", name="上海南京东路店", city="上海", address="南京东路步行街88号", manager="周敏"),
            Store(code="HZ001", name="杭州湖滨银泰店", city="杭州", address="湖滨商圈18号", manager="林悦"),
            Store(code="SZ001", name="深圳万象天地店", city="深圳", address="深南大道9668号", manager="陈可"),
        ]
        db.add_all(stores)

        products = [
            Product(code="P1001", name="法式短款针织开衫", category="女装", season="春季"),
            Product(code="P1002", name="通勤直筒西装裤", category="女装", season="四季"),
            Product(code="P2001", name="都市轻薄夹克", category="男装", season="春季"),
            Product(code="P3001", name="复古方头乐福鞋", category="鞋包配饰", season="四季"),
        ]
        db.add_all(products)
        db.flush()

        skus = [
            SKU(sku_code="P1001-BE-S", product_id=products[0].id, color="米白", size="S", list_price=199, cost_price=82, barcode="690000100101"),
            SKU(sku_code="P1001-BE-M", product_id=products[0].id, color="米白", size="M", list_price=199, cost_price=82, barcode="690000100102"),
            SKU(sku_code="P1002-BK-M", product_id=products[1].id, color="黑色", size="M", list_price=259, cost_price=116, barcode="690000100201"),
            SKU(sku_code="P1002-BK-L", product_id=products[1].id, color="黑色", size="L", list_price=259, cost_price=116, barcode="690000100202"),
            SKU(sku_code="P2001-GY-L", product_id=products[2].id, color="灰色", size="L", list_price=329, cost_price=158, barcode="690000200101"),
            SKU(sku_code="P3001-BR-38", product_id=products[3].id, color="棕色", size="38", list_price=299, cost_price=132, barcode="690000300101"),
        ]
        db.add_all(skus)

        promotions = [
            Promotion(
                name="春装上新9折",
                promotion_type="折扣",
                discount_rate=0.9,
                start_date=date.today() - timedelta(days=7),
                end_date=date.today() + timedelta(days=14),
                description="春季新品限时九折，用于演示促销匹配。",
            ),
            Promotion(
                name="会员专享95折",
                promotion_type="会员折扣",
                discount_rate=0.95,
                start_date=date.today() - timedelta(days=30),
                end_date=date.today() + timedelta(days=30),
                description="会员消费模拟优惠。",
            ),
        ]
        db.add_all(promotions)

        members = [
            Member(member_no="HY20260001", name="王佳怡", phone="13800000001", level="金卡会员", tags="高复购,女装", points=1280, total_spent=3680),
            Member(member_no="HY20260002", name="李明轩", phone="13800000002", level="普通会员", tags="男装,新品偏好", points=460, total_spent=980),
            Member(member_no="HY20260003", name="赵雨晴", phone="13800000003", level="银卡会员", tags="促销敏感,鞋包", points=820, total_spent=2100),
        ]
        db.add_all(members)
        db.flush()

        quantities = [18, 4, 12, 3, 9, 2]
        for store in stores:
            for index, sku in enumerate(skus):
                db.add(
                    Inventory(
                        store_id=store.id,
                        sku_id=sku.id,
                        quantity=max(0, quantities[index] - (store.id - 1) * 2),
                        safety_stock=5,
                        in_transit=8 if quantities[index] <= 4 else 0,
                    )
                )
        db.flush()

        order_specs = [
            (stores[0], members[0], promotions[0], [(skus[0], 1), (skus[2], 1)], "微信"),
            (stores[0], members[2], promotions[1], [(skus[5], 1)], "支付宝"),
            (stores[1], members[1], None, [(skus[4], 1), (skus[1], 1)], "银行卡"),
            (stores[2], None, promotions[0], [(skus[3], 1)], "现金"),
        ]

        for idx, (store, member, promotion, items, method) in enumerate(order_specs, start=1):
            order = SalesOrder(
                order_no=f"SO20260603{idx:04d}",
                store_id=store.id,
                member_id=member.id if member else None,
                promotion_id=promotion.id if promotion else None,
                order_time=datetime.utcnow() - timedelta(hours=idx * 3),
                payment_method=method,
            )
            db.add(order)
            db.flush()

            total_amount = 0.0
            discount_amount = 0.0
            cost_amount = 0.0
            discount_rate = promotion.discount_rate if promotion else 1.0

            for sku, quantity in items:
                line_total = sku.list_price * quantity
                line_paid = round(line_total * discount_rate, 2)
                line_discount = round(line_total - line_paid, 2)
                db.add(
                    SalesOrderItem(
                        order_id=order.id,
                        sku_id=sku.id,
                        quantity=quantity,
                        unit_price=sku.list_price,
                        discount_amount=line_discount,
                        subtotal=line_paid,
                    )
                )
                inventory = (
                    db.query(Inventory)
                    .filter(Inventory.store_id == store.id, Inventory.sku_id == sku.id)
                    .first()
                )
                if inventory:
                    inventory.quantity -= quantity
                total_amount += line_total
                discount_amount += line_discount
                cost_amount += sku.cost_price * quantity

            paid_amount = round(total_amount - discount_amount, 2)
            order.total_amount = round(total_amount, 2)
            order.discount_amount = round(discount_amount, 2)
            order.paid_amount = paid_amount

            db.add(
                PaymentRecord(
                    payment_no=f"PAY20260603{idx:04d}",
                    order_id=order.id,
                    amount=paid_amount,
                    method=method,
                    paid_at=order.order_time,
                    status="支付成功",
                )
            )
            db.add(
                FinanceRecord(
                    record_no=f"FIN20260603{idx:04d}",
                    order_id=order.id,
                    store_id=store.id,
                    sales_amount=paid_amount,
                    cost_amount=round(cost_amount, 2),
                    gross_profit=round(paid_amount - cost_amount, 2),
                    promotion_loss=round(discount_amount, 2),
                    business_date=order.order_time.date(),
                    reconcile_status="已对账" if idx != 4 else "存在差异",
                )
            )

        db.commit()
        print("数据库初始化完成：已生成门店、商品、SKU、会员、订单、库存、财务和看板测试数据。")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
