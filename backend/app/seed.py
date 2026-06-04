from datetime import date, datetime, timedelta

from .database import Base, SessionLocal, engine
from .models import (
    Coupon,
    FinanceRecord,
    Inventory,
    Member,
    PaymentRecord,
    Product,
    Promotion,
    ReplenishmentRequest,
    SKU,
    SalesOrder,
    SalesOrderItem,
    Store,
    TransferRecord,
)
from .utils.code_generator import build_sku_code, make_ean13, match_color, match_size


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

        product_specs = [
            ("TO10001", "法式短款针织开衫", "上衣", "春季", "新品", "在售", 20),
            ("PA10001", "通勤直筒西装裤", "裤装", "四季", "成长期", "在售", 55),
            ("TO10002", "轻盈雪纺衬衫", "上衣", "夏季", "新品", "在售", 12),
            ("SK10001", "高腰A字半身裙", "半裙", "春季", "成熟期", "在售", 80),
            ("CO10001", "羊毛混纺短外套", "外套", "秋冬", "清货期", "停售", 180),
            ("CO10002", "都市轻薄夹克", "外套", "春季", "成长期", "在售", 45),
            ("TO10003", "基础圆领T恤", "上衣", "夏季", "成熟期", "在售", 95),
            ("PA10002", "弹力休闲长裤", "裤装", "四季", "成长期", "在售", 65),
            ("TO10004", "简约连帽卫衣", "上衣", "秋季", "清货期", "下架", 220),
            ("SH30008", "复古方头乐福鞋", "鞋类", "四季", "成熟期", "在售", 120),
            ("AC03002", "轻便通勤托特包", "配饰", "四季", "新品", "在售", 18),
            ("TO10005", "运动速干上衣", "上衣", "夏季", "成长期", "在售", 38),
            ("PA10003", "束脚运动长裤", "裤装", "四季", "成熟期", "停售", 150),
            ("AC03003", "极简银色项链", "配饰", "四季", "新品", "在售", 8),
            ("AC03004", "复古针织围巾", "配饰", "秋冬", "下架", "下架", 260),
        ]
        products = [
            Product(
                code=code,
                name=name,
                category=category,
                season=season,
                lifecycle_status=lifecycle,
                status=status,
                launch_date=date.today() - timedelta(days=days_ago),
            )
            for code, name, category, season, lifecycle, status, days_ago in product_specs
        ]
        db.add_all(products)
        db.flush()

        base_prices = [199, 259, 229, 189, 499, 329, 99, 239, 279, 299, 359, 169, 219, 129, 159]
        colors = ["米白", "黑色", "雾霾蓝", "卡其", "灰色", "棕色", "浅粉", "墨绿", "多色拼接", "设计师定制色"]
        sizes = ["S", "M", "L", "均码", "38", "40", "26", "30", "42", "XXXL"]
        skus = []
        barcode_serial = 1000
        for index, product in enumerate(products):
            for variant in range(2):
                price = base_prices[index] + variant * 20
                color = colors[(index + variant) % len(colors)]
                size = sizes[(index + variant) % len(sizes)]
                if product.code == "AC03002" and variant == 0:
                    color = "蓝色"
                    size = "38"
                color_match = match_color(color)
                size_match = match_size(product.category, size)
                barcode_serial += 1
                skus.append(
                    SKU(
                        sku_code=build_sku_code(product.code, color_match, size_match),
                        product_id=product.id,
                        color=color,
                        size=size,
                        list_price=price,
                        cost_price=round(price * 0.45, 2),
                        barcode=make_ean13(barcode_serial),
                        status="在售" if product.status == "在售" else product.status,
                    )
                )
        db.add_all(skus)

        promotions = [
            Promotion(
                name="春装上新9折",
                promotion_type="折扣",
                discount_rate=0.9,
                start_date=date.today() - timedelta(days=7),
                end_date=date.today() + timedelta(days=14),
                status="进行中",
                applicable_scope="春季女装",
                approval_status="已审批",
                description="春季新品限时九折，用于演示促销匹配。",
            ),
            Promotion(
                name="会员专享95折",
                promotion_type="会员折扣",
                discount_rate=0.95,
                start_date=date.today() - timedelta(days=30),
                end_date=date.today() + timedelta(days=30),
                status="进行中",
                applicable_scope="全场商品",
                approval_status="已审批",
                description="会员消费模拟优惠。",
            ),
            Promotion(
                name="夏季清爽满减",
                promotion_type="满减",
                discount_rate=1.0,
                start_date=date.today() + timedelta(days=3),
                end_date=date.today() + timedelta(days=20),
                status="未开始",
                applicable_scope="夏季商品",
                approval_status="已审批",
                description="满399减60，适用于夏季上新商品。",
            ),
            Promotion(
                name="旧款清仓7折",
                promotion_type="折扣",
                discount_rate=0.7,
                start_date=date.today() - timedelta(days=45),
                end_date=date.today() - timedelta(days=5),
                status="已结束",
                applicable_scope="清货期商品",
                approval_status="已审批",
                description="清货期商品阶段性折扣。",
            ),
            Promotion(
                name="鞋包配饰组合购",
                promotion_type="组合优惠",
                discount_rate=0.85,
                start_date=date.today() - timedelta(days=2),
                end_date=date.today() + timedelta(days=5),
                status="已停用",
                applicable_scope="鞋包配饰",
                approval_status="已审批",
                description="鞋包配饰组合购活动，当前已停用。",
            ),
        ]
        db.add_all(promotions)
        db.flush()

        coupons = [
            Coupon(code="CP20260001", name="满299减40券", coupon_type="满减券", promotion_id=promotions[0].id, discount_amount=40, threshold_amount=299, valid_start=date.today() - timedelta(days=7), valid_end=date.today() + timedelta(days=14), target_group="全部会员", issued_count=1200, used_count=386, status="可用"),
            Coupon(code="CP20260002", name="会员专享9折券", coupon_type="折扣券", promotion_id=promotions[1].id, discount_rate=0.9, threshold_amount=0, valid_start=date.today() - timedelta(days=30), valid_end=date.today() + timedelta(days=30), target_group="银卡/金卡会员", issued_count=820, used_count=216, status="可用"),
            Coupon(code="CP20260003", name="夏季满399减60券", coupon_type="满减券", promotion_id=promotions[2].id, discount_amount=60, threshold_amount=399, valid_start=date.today() + timedelta(days=3), valid_end=date.today() + timedelta(days=20), target_group="全部会员", issued_count=0, used_count=0, status="未开始"),
            Coupon(code="CP20260004", name="清仓专享7折券", coupon_type="折扣券", promotion_id=promotions[3].id, discount_rate=0.7, threshold_amount=0, valid_start=date.today() - timedelta(days=45), valid_end=date.today() - timedelta(days=5), target_group="价格敏感会员", issued_count=600, used_count=188, status="已过期"),
            Coupon(code="CP20260005", name="积分兑换20元券", coupon_type="积分券", promotion_id=None, discount_amount=20, threshold_amount=99, valid_start=date.today() - timedelta(days=10), valid_end=date.today() + timedelta(days=40), target_group="积分800以上会员", issued_count=300, used_count=74, status="可用"),
            Coupon(code="CP20260006", name="生日会员满199减30", coupon_type="会员券", promotion_id=None, discount_amount=30, threshold_amount=199, valid_start=date.today() - timedelta(days=1), valid_end=date.today() + timedelta(days=29), target_group="生日月会员", issued_count=180, used_count=42, status="可用"),
            Coupon(code="CP20260007", name="配饰组合85折券", coupon_type="折扣券", promotion_id=promotions[4].id, discount_rate=0.85, threshold_amount=0, valid_start=date.today() - timedelta(days=2), valid_end=date.today() + timedelta(days=5), target_group="配饰偏好会员", issued_count=260, used_count=19, status="已停用"),
            Coupon(code="CP20260008", name="新客首单满199减50", coupon_type="会员券", promotion_id=None, discount_amount=50, threshold_amount=199, valid_start=date.today() - timedelta(days=3), valid_end=date.today() + timedelta(days=25), target_group="新注册会员", issued_count=500, used_count=96, status="可用"),
        ]
        db.add_all(coupons)

        members = [
            Member(member_no="HY20260001", name="王佳怡", phone="13800000001", level="金卡会员", tags="活跃会员,新品敏感", points=1280, total_spent=3680),
            Member(member_no="HY20260002", name="李明轩", phone="13800000002", level="普通会员", tags="基础款偏好,价格敏感", points=460, total_spent=980),
            Member(member_no="HY20260003", name="赵雨晴", phone="13800000003", level="银卡会员", tags="价格敏感,活跃会员", points=820, total_spent=2100),
        ]
        db.add_all(members)
        db.flush()

        inventory_pattern = [18, 4, 0, 12, 3, 9, 1, 16, 5, 2, 11, 0, 7, 20, 4, 13, 6, 0, 8, 3, 17, 10, 2, 14, 5, 1, 19, 4, 12, 6]
        for store_index, store in enumerate(stores):
            for index, sku in enumerate(skus):
                db.add(
                    Inventory(
                        store_id=store.id,
                        sku_id=sku.id,
                        quantity=max(inventory_pattern[index % len(inventory_pattern)] - store_index, 0),
                        safety_stock=5,
                        in_transit=0,
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

        db.flush()

        replenishment_targets = (
            db.query(Inventory)
            .filter(Inventory.quantity < Inventory.safety_stock)
            .order_by(Inventory.quantity, Inventory.id)
            .limit(8)
            .all()
        )
        pending_targets = replenishment_targets[:5]
        transfer_targets = replenishment_targets[5:8]

        for index, inventory in enumerate(pending_targets, start=1):
            recent_sales = 3 + index
            suggested_qty = max(
                inventory.safety_stock * 2 + recent_sales - inventory.quantity - inventory.in_transit,
                0,
            )
            db.add(
                ReplenishmentRequest(
                    inventory_id=inventory.id,
                    store_id=inventory.store_id,
                    sku_id=inventory.sku_id,
                    current_quantity=inventory.quantity,
                    safety_stock=inventory.safety_stock,
                    in_transit=inventory.in_transit,
                    recent_7d_sales=recent_sales,
                    suggested_qty=suggested_qty,
                    request_qty=max(suggested_qty, 6),
                    reason="畅销款低于安全库存，申请补货。",
                    applicant="门店店长",
                    status="待审核",
                    created_at=datetime.utcnow() - timedelta(hours=index),
                    updated_at=datetime.utcnow() - timedelta(hours=index),
                )
            )

        db.flush()

        for index, inventory in enumerate(transfer_targets, start=1):
            recent_sales = 5 + index
            suggested_qty = max(
                inventory.safety_stock * 2 + recent_sales - inventory.quantity - inventory.in_transit,
                0,
            )
            transfer_qty = max(suggested_qty, 8)
            request = ReplenishmentRequest(
                inventory_id=inventory.id,
                store_id=inventory.store_id,
                sku_id=inventory.sku_id,
                current_quantity=inventory.quantity,
                safety_stock=inventory.safety_stock,
                in_transit=inventory.in_transit,
                recent_7d_sales=recent_sales,
                suggested_qty=suggested_qty,
                request_qty=transfer_qty,
                reason="库存预警已审核，进入调拨在途。",
                applicant="区域督导",
                status="在途",
                created_at=datetime.utcnow() - timedelta(days=index),
                updated_at=datetime.utcnow() - timedelta(hours=index),
            )
            db.add(request)
            db.flush()
            inventory.in_transit += transfer_qty
            inventory.updated_at = datetime.utcnow()
            db.add(
                TransferRecord(
                    request_id=request.id,
                    inventory_id=inventory.id,
                    store_id=inventory.store_id,
                    sku_id=inventory.sku_id,
                    source_location="华悦中央仓",
                    transfer_qty=transfer_qty,
                    in_transit_qty=transfer_qty,
                    status="在途",
                    shipped_at=datetime.utcnow() - timedelta(days=index),
                    expected_arrival_at=datetime.utcnow() + timedelta(days=3 - index),
                )
            )

        db.commit()
        print("数据库初始化完成：已生成门店、商品、SKU、会员、订单、库存、财务和看板测试数据。")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
