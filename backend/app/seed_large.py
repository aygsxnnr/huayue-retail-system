from __future__ import annotations

import argparse
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta
from typing import Any

from sqlalchemy import func, text

from .database import Base, SessionLocal, engine
from .models import (
    Coupon,
    FinanceRecord,
    Inventory,
    MarketingTouch,
    Member,
    MemberTag,
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


SCALE_ORDERS = {
    "small": 1_000,
    "demo": 10_000,
    "large": 50_000,
    "enterprise": 200_000,
}

CATEGORY_PREFIX = {
    "上衣": "TO",
    "连衣裙": "DR",
    "裤装": "PA",
    "半裙": "SK",
    "外套": "CO",
    "鞋类": "SH",
    "配饰": "AC",
}

CATEGORY_BASE_PRICE = {
    "上衣": (99, 299),
    "连衣裙": (169, 499),
    "裤装": (139, 399),
    "半裙": (129, 329),
    "外套": (299, 899),
    "鞋类": (199, 699),
    "配饰": (39, 259),
}

SEASON_CATEGORIES = {
    1: ["外套", "上衣", "鞋类"],
    2: ["外套", "上衣", "鞋类"],
    3: ["上衣", "半裙", "外套"],
    4: ["上衣", "半裙", "外套"],
    5: ["连衣裙", "上衣", "配饰"],
    6: ["连衣裙", "上衣", "配饰"],
    7: ["连衣裙", "上衣", "配饰"],
    8: ["连衣裙", "上衣", "配饰"],
    9: ["外套", "裤装", "上衣"],
    10: ["外套", "裤装", "上衣"],
    11: ["外套", "上衣", "鞋类"],
    12: ["外套", "上衣", "鞋类"],
}


@dataclass
class RuntimeData:
    stores: list[dict[str, Any]]
    active_store_ids: list[int]
    products: list[dict[str, Any]]
    skus: list[dict[str, Any]]
    members: list[dict[str, Any]]
    promotions: list[dict[str, Any]]
    coupons: list[dict[str, Any]]
    inventory_by_key: dict[tuple[int, int], dict[str, Any]]
    sku_by_id: dict[int, dict[str, Any]]
    sku_ids_by_category: dict[str, list[int]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成华悦零售系统大规模模拟运营数据")
    parser.add_argument("--scale", choices=["small", "demo", "large", "enterprise"], default="demo")
    parser.add_argument("--target-orders", type=int, default=None)
    parser.add_argument("--start-date", type=str, default=None)
    parser.add_argument("--end-date", type=str, default=None)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--reset", type=str, default="false")
    return parser.parse_args()


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是"}


def parse_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    return datetime.strptime(value, "%Y-%m-%d").date()


def max_id(db, model) -> int:
    return int(db.query(func.coalesce(func.max(model.id), 0)).scalar() or 0)


def weighted_choice(items: list[Any], weights: list[float]) -> Any:
    return random.choices(items, weights=weights, k=1)[0]


def round_money(value: float) -> float:
    return round(float(value or 0), 2)


def random_order_time(start: date, end: date) -> datetime:
    days = (end - start).days + 1
    while True:
        current = start + timedelta(days=random.randrange(days))
        weight = day_weight(current)
        if random.random() <= min(weight / 4.5, 1):
            hour = weighted_choice(
                list(range(10, 22)),
                [1.0, 1.1, 2.1, 2.0, 1.2, 1.0, 1.1, 1.4, 3.0, 3.4, 3.0, 1.8],
            )
            return datetime.combine(
                current,
                dtime(hour=hour, minute=random.randrange(60), second=random.randrange(60)),
            )


def day_weight(current: date) -> float:
    weight = 1.0
    if current.weekday() >= 5:
        weight *= random.uniform(1.5, 2.0)
    promo_ranges = [
        ((5, 1), (5, 5), 2.4),
        ((6, 1), (6, 20), 3.2),
        ((7, 1), (8, 20), 1.8),
        ((9, 20), (10, 10), 2.3),
        ((11, 1), (11, 12), 4.0),
        ((12, 1), (12, 12), 3.2),
        ((1, 1), (1, 3), 2.0),
        ((1, 15), (2, 10), 2.5),
        ((3, 15), (4, 10), 1.7),
        ((8, 20), (9, 10), 1.6),
    ]
    for (sm, sd), (em, ed), factor in promo_ranges:
        start = date(current.year, sm, sd)
        end = date(current.year, em, ed)
        if start <= current <= end:
            weight *= factor
            break
    return weight


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_indexes(db) -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_sales_orders_store_time ON sales_orders(store_id, order_time)",
        "CREATE INDEX IF NOT EXISTS ix_sales_orders_member_time ON sales_orders(member_id, order_time)",
        "CREATE INDEX IF NOT EXISTS ix_sales_orders_status ON sales_orders(status)",
        "CREATE INDEX IF NOT EXISTS ix_sales_order_items_order_sku ON sales_order_items(order_id, sku_id)",
        "CREATE INDEX IF NOT EXISTS ix_payment_records_time_method ON payment_records(paid_at, method)",
        "CREATE INDEX IF NOT EXISTS ix_payment_records_status ON payment_records(status)",
        "CREATE INDEX IF NOT EXISTS ix_finance_records_store_status ON finance_records(store_id, reconcile_status)",
        "CREATE INDEX IF NOT EXISTS ix_finance_records_business_date ON finance_records(business_date)",
        "CREATE INDEX IF NOT EXISTS ix_inventories_store_sku ON inventories(store_id, sku_id)",
        "CREATE INDEX IF NOT EXISTS ix_marketing_touches_member_time ON marketing_touches(member_id, touch_time)",
        "CREATE INDEX IF NOT EXISTS ix_marketing_touches_coupon_channel ON marketing_touches(coupon_id, channel)",
        "CREATE INDEX IF NOT EXISTS ix_members_level_status ON members(level, status)",
        "CREATE INDEX IF NOT EXISTS ix_members_joined_at ON members(joined_at)",
    ]
    for statement in statements:
        db.execute(text(statement))
    db.commit()


def generate_stores(start_id: int) -> list[dict[str, Any]]:
    cities = ["上海", "杭州", "广州", "深圳", "北京", "南京", "成都", "武汉", "苏州", "重庆", "宁波", "西安"]
    statuses = ["正常营业"] * 12 + ["临时歇业", "闭店升级", "已关闭", "停用"]
    stores = []
    for index, city in enumerate(cities[:16]):
        status = statuses[index]
        stores.append(
            {
                "id": start_id + index,
                "code": f"{city[:1].upper() if city else 'S'}Y{index + 1:03d}",
                "name": f"{city}核心商圈店",
                "city": city,
                "address": f"{city}核心商圈{88 + index}号",
                "manager": f"店长{index + 1:02d}",
                "status": status,
            }
        )
    return stores


def generate_products(start_id: int, target_orders: int, start: date, end: date) -> list[dict[str, Any]]:
    target_count = 120 if target_orders <= 10_000 else 180 if target_orders <= 50_000 else 240
    categories = list(CATEGORY_PREFIX)
    seasons = ["春季", "夏季", "秋季", "冬季", "四季"]
    names = {
        "上衣": ["针织开衫", "雪纺衬衫", "圆领T恤", "连帽卫衣", "速干上衣"],
        "连衣裙": ["法式碎花连衣裙", "通勤衬衫裙", "吊带连衣裙", "针织连衣裙"],
        "裤装": ["直筒西装裤", "休闲长裤", "牛仔阔腿裤", "束脚运动裤"],
        "半裙": ["高腰A字裙", "百褶半裙", "牛仔半裙", "伞摆半裙"],
        "外套": ["短款外套", "羊毛大衣", "轻薄夹克", "风衣外套"],
        "鞋类": ["方头乐福鞋", "通勤短靴", "休闲运动鞋", "细带凉鞋"],
        "配饰": ["托特包", "银色项链", "针织围巾", "棒球帽"],
    }
    counters = defaultdict(int)
    products = []
    for index in range(target_count):
        category = categories[index % len(categories)]
        counters[category] += 1
        prefix = CATEGORY_PREFIX[category]
        code = f"{prefix}{counters[category]:05d}"
        low, high = CATEGORY_BASE_PRICE[category]
        sale_price = random.randrange(low, high + 1, 10) - 1
        margin = random.uniform(0.32, 0.62)
        if random.random() < 0.08:
            margin = random.uniform(0.18, 0.28)
        cost_price = round_money(sale_price * (1 - margin))
        launch_days = random.randrange(max((end - start).days, 1))
        status = weighted_choice(["在售", "停售", "下架"], [0.82, 0.12, 0.06])
        lifecycle = weighted_choice(["新品", "成长期", "成熟期", "清货期", "下架"], [0.18, 0.28, 0.34, 0.14, 0.06])
        products.append(
            {
                "id": start_id + index,
                "code": code,
                "name": f"华悦{random.choice(names[category])}{counters[category]:03d}",
                "category": category,
                "season": random.choice(seasons),
                "brand": "华悦",
                "status": status,
                "launch_date": start + timedelta(days=launch_days),
                "lifecycle_status": lifecycle,
                "sale_price": sale_price,
                "cost_price": cost_price,
            }
        )
    return products


def generate_skus(start_id: int, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    colors = ["米白", "黑色", "雾霾蓝", "卡其", "灰色", "棕色", "浅粉", "墨绿", "多色拼接", "设计师定制色", "藏蓝", "牛仔蓝"]
    sizes_by_category = {
        "鞋类": ["35", "36", "37", "38", "39", "40", "41", "42"],
        "裤装": ["24", "25", "26", "27", "28", "29", "30", "31", "32"],
        "配饰": ["均码"],
    }
    default_sizes = ["XS", "S", "M", "L", "XL", "XXL"]
    skus: list[dict[str, Any]] = []
    sku_id = start_id
    barcode_serial = 10_000
    seen_codes: set[str] = set()
    for product in products:
        variant_count = random.randint(4, 15)
        sizes = sizes_by_category.get(product["category"], default_sizes)
        combos = [(color, size) for color in random.sample(colors, min(len(colors), 5)) for size in sizes]
        random.shuffle(combos)
        for color, size in combos[:variant_count]:
            color_match = match_color(color)
            size_match = match_size(product["category"], size)
            sku_code = build_sku_code(product["code"], color_match, size_match)
            if sku_code in seen_codes:
                continue
            seen_codes.add(sku_code)
            price_delta = random.choice([-20, -10, 0, 0, 0, 10, 20, 30])
            sale_price = max(product["sale_price"] + price_delta, product["cost_price"] + 5)
            cost_price = max(round_money(product["cost_price"] * random.uniform(0.95, 1.08)), 1)
            if cost_price >= sale_price:
                cost_price = round_money(sale_price * 0.65)
            barcode_serial += 1
            skus.append(
                {
                    "id": sku_id,
                    "sku_code": sku_code,
                    "product_id": product["id"],
                    "color": color,
                    "size": size,
                    "list_price": round_money(sale_price),
                    "cost_price": round_money(cost_price),
                    "barcode": make_ean13(barcode_serial),
                    "status": "在售" if product["status"] == "在售" else product["status"],
                }
            )
            sku_id += 1
    return skus


def generate_inventory(start_id: int, stores: list[dict[str, Any]], skus: list[dict[str, Any]]) -> dict[tuple[int, int], dict[str, Any]]:
    inventory: dict[tuple[int, int], dict[str, Any]] = {}
    inv_id = start_id
    for store in stores:
        if store["status"] not in {"正常营业", "临时歇业", "闭店升级"}:
            continue
        for sku in skus:
            safety = random.randint(5, 20)
            roll = random.random()
            if roll < 0.04:
                quantity = 0
            elif roll < 0.16:
                quantity = random.randint(1, max(safety - 1, 1))
            else:
                quantity = random.randint(safety, safety * random.randint(3, 8))
            item = {
                "id": inv_id,
                "store_id": store["id"],
                "sku_id": sku["id"],
                "quantity": quantity,
                "safety_stock": safety,
                "in_transit": random.choice([0, 0, 0, 5, 10, 15]),
                "updated_at": datetime.utcnow(),
            }
            inventory[(store["id"], sku["id"])] = item
            inv_id += 1
    return inventory


def generate_members(start_id: int, target_orders: int, start: date, end: date, stores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    member_count = 2_000 if target_orders <= 1_000 else 12_000 if target_orders <= 10_000 else 28_000 if target_orders <= 50_000 else 50_000
    levels = ["普通会员", "银卡会员", "金卡会员", "黑金会员"]
    tags = ["新品敏感", "促销敏感", "高客单价", "高频购买", "低频购买", "女装偏好", "配饰偏好", "清仓偏好"]
    active_store_ids = [str(store["id"]) for store in stores if store["status"] in {"正常营业", "临时歇业", "闭店升级"}]
    members = []
    total_days = max((end - start).days, 1)
    for index in range(member_count):
        joined_at = datetime.combine(start + timedelta(days=random.randrange(total_days)), dtime(hour=random.randrange(9, 22)))
        members.append(
            {
                "id": start_id + index,
                "member_no": f"HY{start.year}{start_id + index:08d}",
                "name": f"会员{start_id + index:06d}",
                "phone": f"13{random.randrange(100000000, 999999999)}",
                "level": weighted_choice(levels, [0.68, 0.2, 0.1, 0.02]),
                "tags": ",".join(random.sample(tags, random.randint(1, 3))),
                "points": 0,
                "total_spent": 0,
                "total_orders": 0,
                "last_purchase_at": None,
                "status": weighted_choice(["正常", "停用", "黑名单", "注销"], [0.96, 0.025, 0.01, 0.005]),
                "registered_store": random.choice(active_store_ids) if active_store_ids else "华悦线上会员中心",
                "joined_at": joined_at,
            }
        )
    return members


def generate_member_tags(start_id: int, members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = ["高价值会员", "价格敏感会员", "促销敏感会员", "新品偏好会员", "清仓偏好会员", "高频购买会员", "低频购买会员", "女装偏好会员", "配饰偏好会员", "普通会员"]
    tags = []
    for index, member in enumerate(members):
        tags.append(
            {
                "id": start_id + index,
                "member_id": member["id"],
                "r_score": random.randint(1, 5),
                "f_score": random.randint(1, 5),
                "m_score": random.randint(1, 5),
                "member_group": random.choice(groups),
                "preference_tag": random.choice(["新品敏感", "女装偏好", "配饰偏好", "鞋类偏好"]),
                "price_sensitive_tag": random.choice(["价格敏感", "价格适中", "高客单价"]),
                "activity_tag": random.choice(["高频购买", "低频购买", "普通活跃"]),
                "risk_tag": random.choice(["稳定", "流失风险", "沉睡风险"]),
                "updated_at": datetime.utcnow(),
            }
        )
    return tags


def generate_promotions(start_id: int, start: date, end: date) -> list[dict[str, Any]]:
    periods = [
        ("春装上新", date(start.year, 3, 1), date(start.year, 4, 15), 0.90),
        ("五一门店焕新", date(start.year, 4, 25), date(start.year, 5, 5), 0.88),
        ("618年中大促", date(start.year, 6, 1), date(start.year, 6, 20), 0.82),
        ("暑期清凉节", date(start.year, 7, 1), date(start.year, 8, 20), 0.86),
        ("国庆黄金周", date(start.year, 9, 25), date(start.year, 10, 10), 0.85),
        ("双11会员狂欢", date(start.year, 11, 1), date(start.year, 11, 12), 0.78),
        ("双12暖冬购", date(start.year, 12, 1), date(start.year, 12, 12), 0.80),
    ]
    promotions = []
    promotion_id = start_id
    for year in range(start.year, end.year + 1):
        for name, s, e, rate in periods:
            ps = date(year, s.month, s.day)
            pe = date(year, e.month, e.day)
            if pe < start or ps > end:
                continue
            promotions.append(
                {
                    "id": promotion_id,
                    "name": f"{year}{name}",
                    "promotion_type": "折扣",
                    "discount_rate": rate,
                    "start_date": ps,
                    "end_date": pe,
                    "status": "进行中" if ps <= date.today() <= pe else ("已结束" if pe < date.today() else "未开始"),
                    "description": "大规模运营数据促销活动",
                    "applicable_scope": "全场或指定品类",
                    "approval_status": "已审批",
                }
            )
            promotion_id += 1
    return promotions


def generate_coupons(start_id: int, promotions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    coupon_types = ["满减券", "折扣券", "会员券", "积分券"]
    coupons = []
    for index, promotion in enumerate(promotions[:40]):
        coupon_type = coupon_types[index % len(coupon_types)]
        coupons.append(
            {
                "id": start_id + index,
                "code": f"CP{promotion['start_date']:%Y%m%d}{index + 1:04d}",
                "name": f"{promotion['name']}{coupon_type}",
                "coupon_type": coupon_type,
                "promotion_id": promotion["id"],
                "discount_amount": random.choice([10, 20, 30, 50, 80]) if coupon_type != "折扣券" else 0,
                "discount_rate": random.choice([0.85, 0.88, 0.9, 0.95]) if coupon_type == "折扣券" else 1,
                "threshold_amount": random.choice([99, 199, 299, 499]),
                "valid_start": promotion["start_date"],
                "valid_end": promotion["end_date"],
                "target_group": random.choice(["全部会员", "金卡会员", "银卡及以上", "新会员"]),
                "issued_count": 0,
                "used_count": 0,
                "status": "可用" if promotion["end_date"] >= date.today() else "已过期",
                "created_at": datetime.combine(promotion["start_date"], dtime(hour=9)),
                "per_member_limit": random.choice([1, 1, 2, None]),
                "per_order_use_limit": 1,
                "stackable": random.choice([False, False, True]),
                "total_issue_limit": random.choice([5000, 10000, 20000, None]),
                "total_redeem_limit": random.choice([3000, 8000, None]),
                "applicable_category_ids": "",
                "applicable_product_ids": "",
                "applicable_seasons": "",
                "applicable_member_levels": "",
                "applicable_member_groups": "",
                "applicable_store_ids": "",
                "target_tags": "",
                "issue_mode": random.choice(["手动发放", "智能发放", "新会员自动发放", "系统触达"]),
                "auto_issue_enabled": random.choice([False, True]),
            }
        )
    return coupons


def promotion_for_time(order_time: datetime, promotions: list[dict[str, Any]]) -> dict[str, Any] | None:
    active = [promo for promo in promotions if promo["start_date"] <= order_time.date() <= promo["end_date"]]
    if active and random.random() < 0.45:
        return random.choice(active)
    return None


def choose_store(stores: list[dict[str, Any]], order_time: datetime) -> int:
    candidates = []
    weights = []
    for store in stores:
        status = store["status"]
        if status == "停用":
            continue
        if status == "已关闭" and order_time.date() >= date(2026, 1, 1):
            continue
        weight = 1.0
        if status == "正常营业":
            weight = random.uniform(0.8, 1.8)
        elif status in {"临时歇业", "闭店升级"}:
            weight = 0.08
        elif status == "已关闭":
            weight = 0.25
        candidates.append(store["id"])
        weights.append(weight)
    return weighted_choice(candidates, weights)


def choose_sku_id(order_time: datetime, sku_ids_by_category: dict[str, list[int]]) -> int:
    preferred = SEASON_CATEGORIES.get(order_time.month, ["上衣"])
    category = weighted_choice(preferred + list(sku_ids_by_category), [3.0] * len(preferred) + [0.4] * len(sku_ids_by_category))
    if not sku_ids_by_category.get(category):
        category = random.choice([key for key, values in sku_ids_by_category.items() if values])
    return random.choice(sku_ids_by_category[category])


def insert_base_data(db, args: argparse.Namespace, start: date, end: date, target_orders: int) -> RuntimeData:
    ids = {
        "store": max_id(db, Store) + 1,
        "product": max_id(db, Product) + 1,
        "sku": max_id(db, SKU) + 1,
        "inventory": max_id(db, Inventory) + 1,
        "member": max_id(db, Member) + 1,
        "member_tag": max_id(db, MemberTag) + 1,
        "promotion": max_id(db, Promotion) + 1,
        "coupon": max_id(db, Coupon) + 1,
    }
    stores = generate_stores(ids["store"])
    products = generate_products(ids["product"], target_orders, start, end)
    skus = generate_skus(ids["sku"], products)
    inventory = generate_inventory(ids["inventory"], stores, skus)
    members = generate_members(ids["member"], target_orders, start, end, stores)
    member_tags = generate_member_tags(ids["member_tag"], members)
    promotions = generate_promotions(ids["promotion"], start, end)
    coupons = generate_coupons(ids["coupon"], promotions)

    db.bulk_insert_mappings(Store, stores)
    db.bulk_insert_mappings(Product, products)
    db.bulk_insert_mappings(SKU, skus)
    db.bulk_insert_mappings(Inventory, list(inventory.values()))
    db.bulk_insert_mappings(Member, members)
    db.bulk_insert_mappings(MemberTag, member_tags)
    db.bulk_insert_mappings(Promotion, promotions)
    db.bulk_insert_mappings(Coupon, coupons)
    db.commit()

    sku_by_id = {sku["id"]: sku for sku in skus}
    sku_ids_by_category: dict[str, list[int]] = defaultdict(list)
    product_category = {product["id"]: product["category"] for product in products}
    for sku in skus:
        sku_ids_by_category[product_category[sku["product_id"]]].append(sku["id"])
    active_store_ids = [store["id"] for store in stores if store["status"] in {"正常营业", "临时歇业", "闭店升级"}]

    return RuntimeData(stores, active_store_ids, products, skus, members, promotions, coupons, inventory, sku_by_id, dict(sku_ids_by_category))


def generate_orders(db, args: argparse.Namespace, start: date, end: date, target_orders: int, data: RuntimeData) -> dict[str, int]:
    order_id = max_id(db, SalesOrder) + 1
    item_id = max_id(db, SalesOrderItem) + 1
    payment_id = max_id(db, PaymentRecord) + 1
    finance_id = max_id(db, FinanceRecord) + 1
    member_stats: dict[int, dict[str, Any]] = defaultdict(lambda: {"total_spent": 0.0, "total_orders": 0, "points": 0, "last_purchase_at": None})
    counts = {"orders": 0, "items": 0, "payments": 0, "finance": 0}
    member_ids = [member["id"] for member in data.members]
    batch_size = max(args.batch_size, 100)
    started = time.perf_counter()

    for offset in range(0, target_orders, batch_size):
        batch_count = min(batch_size, target_orders - offset)
        orders = []
        items = []
        payments = []
        finances = []
        for index in range(batch_count):
            current_order_id = order_id + offset + index
            order_time = random_order_time(start, end)
            store_id = choose_store(data.stores, order_time)
            member_id = random.choice(member_ids) if random.random() < random.uniform(0.70, 0.85) else None
            promotion = promotion_for_time(order_time, data.promotions)
            discount_rate = promotion["discount_rate"] if promotion else 1.0
            line_count = weighted_choice([1, 2, 3, 4, 5], [0.55, 0.28, 0.1, 0.05, 0.02])
            total_amount = 0.0
            discount_amount = 0.0
            paid_amount = 0.0
            cost_amount = 0.0
            for _ in range(line_count):
                sku_id = choose_sku_id(order_time, data.sku_ids_by_category)
                sku = data.sku_by_id[sku_id]
                inventory = data.inventory_by_key.get((store_id, sku_id))
                if inventory and inventory["quantity"] <= 0:
                    inventory["quantity"] = random.randint(1, max(inventory["safety_stock"], 2))
                quantity = weighted_choice([1, 2, 3], [0.82, 0.15, 0.03])
                unit_price = float(sku["list_price"])
                unit_cost = float(sku["cost_price"])
                original = unit_price * quantity
                paid = round_money(original * discount_rate)
                discount = round_money(original - paid)
                cost = round_money(unit_cost * quantity)
                items.append(
                    {
                        "id": item_id,
                        "order_id": current_order_id,
                        "sku_id": sku_id,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "unit_cost": unit_cost,
                        "discount_amount": discount,
                        "subtotal": paid,
                        "cost_amount": cost,
                    }
                )
                item_id += 1
                total_amount += original
                discount_amount += discount
                paid_amount += paid
                cost_amount += cost
                if inventory:
                    inventory["quantity"] = max(0, inventory["quantity"] - quantity)
                    inventory["updated_at"] = order_time
            payment_method = weighted_choice(["微信", "支付宝", "银联卡", "现金"], [0.42, 0.34, 0.16, 0.08])
            payment_status = weighted_choice(["成功", "失败", "待确认", "已退款"], [0.95, 0.01, 0.02, 0.02])
            paid_at = order_time + timedelta(minutes=random.randint(0, 5), seconds=random.randint(0, 59))
            reconcile_status = weighted_choice(["已平账", "待对账", "存在差异", "待处理", "已处理", "已关闭"], [0.80, 0.08, 0.05, 0.03, 0.03, 0.01])
            difference = 0.0
            if reconcile_status in {"存在差异", "待处理", "已处理"}:
                difference = random.choice([-5, -1, -0.05, -0.01, 0.01, 0.05, 1, 5])
            payment_amount = round_money(paid_amount + difference)
            orders.append(
                {
                    "id": current_order_id,
                    "order_no": f"SO{order_time:%Y%m%d}{current_order_id:08d}",
                    "store_id": store_id,
                    "member_id": member_id,
                    "promotion_id": promotion["id"] if promotion else None,
                    "order_time": order_time,
                    "total_amount": round_money(total_amount),
                    "discount_amount": round_money(discount_amount),
                    "paid_amount": round_money(paid_amount),
                    "payment_method": payment_method,
                    "status": "已完成" if payment_status in {"成功", "已退款"} else "待支付",
                }
            )
            payments.append(
                {
                    "id": payment_id,
                    "payment_no": f"PAY{paid_at:%Y%m%d}{payment_id:08d}",
                    "order_id": current_order_id,
                    "amount": payment_amount,
                    "method": payment_method,
                    "paid_at": paid_at,
                    "status": payment_status,
                }
            )
            payment_id += 1
            finances.append(
                {
                    "id": finance_id,
                    "record_no": f"FIN{order_time:%Y%m%d}{finance_id:08d}",
                    "order_id": current_order_id,
                    "store_id": store_id,
                    "sales_amount": round_money(paid_amount),
                    "cost_amount": round_money(cost_amount),
                    "gross_profit": round_money(paid_amount - cost_amount),
                    "promotion_loss": round_money(discount_amount),
                    "reconcile_status": reconcile_status,
                    "business_date": order_time.date(),
                }
            )
            finance_id += 1
            if member_id:
                stat = member_stats[member_id]
                stat["total_spent"] += paid_amount
                stat["total_orders"] += 1
                stat["points"] += int(paid_amount)
                if not stat["last_purchase_at"] or order_time > stat["last_purchase_at"]:
                    stat["last_purchase_at"] = order_time
        db.bulk_insert_mappings(SalesOrder, orders)
        db.bulk_insert_mappings(SalesOrderItem, items)
        db.bulk_insert_mappings(PaymentRecord, payments)
        db.bulk_insert_mappings(FinanceRecord, finances)
        db.commit()
        counts["orders"] += len(orders)
        counts["items"] += len(items)
        counts["payments"] += len(payments)
        counts["finance"] += len(finances)
        elapsed = time.perf_counter() - started
        print(f"订单批次完成：{counts['orders']}/{target_orders}，明细 {counts['items']}，耗时 {elapsed:.1f}s")

    if member_stats:
        updates = [
            {
                "id": member_id,
                "total_spent": round_money(stat["total_spent"]),
                "total_orders": stat["total_orders"],
                "points": stat["points"],
                "last_purchase_at": stat["last_purchase_at"],
            }
            for member_id, stat in member_stats.items()
        ]
        db.bulk_update_mappings(Member, updates)
        db.commit()

    return counts


def generate_replenishment_and_transfers(db, data: RuntimeData) -> tuple[int, int]:
    request_id = max_id(db, ReplenishmentRequest) + 1
    transfer_id = max_id(db, TransferRecord) + 1
    low_items = [item for item in data.inventory_by_key.values() if item["quantity"] <= item["safety_stock"]]
    random.shuffle(low_items)
    request_rows = []
    transfer_rows = []
    for item in low_items[: min(len(low_items), 3000)]:
        suggested = max(item["safety_stock"] * 2 - item["quantity"] - item["in_transit"], 0)
        if suggested <= 0:
            continue
        status = weighted_choice(["待审核", "已审核", "已驳回", "在途", "已完成"], [0.35, 0.18, 0.07, 0.25, 0.15])
        request_rows.append(
            {
                "id": request_id,
                "inventory_id": item["id"],
                "store_id": item["store_id"],
                "sku_id": item["sku_id"],
                "current_quantity": item["quantity"],
                "safety_stock": item["safety_stock"],
                "in_transit": item["in_transit"],
                "recent_7d_sales": random.randint(0, 18),
                "suggested_qty": suggested,
                "request_qty": suggested,
                "reason": "系统根据低库存自动生成模拟补货申请",
                "applicant": "系统模拟",
                "status": status,
                "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 45)),
                "updated_at": datetime.utcnow(),
            }
        )
        if status in {"在途", "已完成"}:
            transfer_status = "已到货" if status == "已完成" else "在途"
            shipped_at = datetime.utcnow() - timedelta(days=random.randint(1, 10))
            arrived_at = shipped_at + timedelta(days=random.randint(2, 5)) if transfer_status == "已到货" else None
            transfer_rows.append(
                {
                    "id": transfer_id,
                    "request_id": request_id,
                    "inventory_id": item["id"],
                    "store_id": item["store_id"],
                    "sku_id": item["sku_id"],
                    "source_location": "华悦中央仓",
                    "transfer_qty": suggested,
                    "in_transit_qty": 0 if transfer_status == "已到货" else suggested,
                    "status": transfer_status,
                    "shipped_at": shipped_at,
                    "expected_arrival_at": shipped_at + timedelta(days=4),
                    "arrived_at": arrived_at,
                }
            )
            transfer_id += 1
            if transfer_status == "在途":
                item["in_transit"] += suggested
            else:
                item["quantity"] += suggested
        request_id += 1
    if request_rows:
        db.bulk_insert_mappings(ReplenishmentRequest, request_rows)
    if transfer_rows:
        db.bulk_insert_mappings(TransferRecord, transfer_rows)
    db.bulk_update_mappings(Inventory, list(data.inventory_by_key.values()))
    db.commit()
    return len(request_rows), len(transfer_rows)


def generate_marketing_touches(db, target_orders: int, data: RuntimeData, start: date, end: date) -> int:
    target = 5_000 if target_orders <= 1_000 else 50_000 if target_orders <= 10_000 else 100_000 if target_orders <= 50_000 else 160_000
    touch_id = max_id(db, MarketingTouch) + 1
    member_ids = [member["id"] for member in data.members]
    coupon_ids = [coupon["id"] for coupon in data.coupons]
    promotion_ids = [promo["id"] for promo in data.promotions]
    channels = ["短信", "微信", "APP推送", "小程序", "人工电话"]
    remarks = ["手动发放", "智能发放", "新会员自动发放", "系统触达"]
    statuses = ["未参与", "已参与", "已转化"]
    writeoff = ["未核销", "已核销", "已过期"]
    batch_size = 5000
    inserted = 0
    total_days = max((end - start).days, 1)
    while inserted < target:
        rows = []
        for _ in range(min(batch_size, target - inserted)):
            touch_time = datetime.combine(start + timedelta(days=random.randrange(total_days)), dtime(hour=random.randrange(9, 22), minute=random.randrange(60)))
            rows.append(
                {
                    "id": touch_id,
                    "member_id": random.choice(member_ids),
                    "coupon_id": random.choice(coupon_ids) if coupon_ids and random.random() < 0.8 else None,
                    "promotion_id": random.choice(promotion_ids) if promotion_ids and random.random() < 0.7 else None,
                    "channel": random.choice(channels),
                    "touch_time": touch_time,
                    "participation_status": weighted_choice(statuses, [0.65, 0.25, 0.10]),
                    "writeoff_status": weighted_choice(writeoff, [0.72, 0.18, 0.10]),
                    "remark": random.choice(remarks),
                }
            )
            touch_id += 1
        db.bulk_insert_mappings(MarketingTouch, rows)
        db.commit()
        inserted += len(rows)
        print(f"营销触达批次完成：{inserted}/{target}")
    return inserted


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    target_orders = args.target_orders or SCALE_ORDERS[args.scale]
    end = parse_date(args.end_date, datetime.utcnow().date())
    start = parse_date(args.start_date, end - timedelta(days=548))
    if args.scale == "enterprise":
        print("企业级数据生成耗时较长，SQLite 查询可能变慢，建议仅用于演示压力数据。")
    started = time.perf_counter()
    if parse_bool(args.reset):
        reset_database()
    else:
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print(f"开始生成大规模模拟数据：scale={args.scale}, target_orders={target_orders}, {start} 至 {end}")
        create_indexes(db)
        data = insert_base_data(db, args, start, end, target_orders)
        order_counts = generate_orders(db, args, start, end, target_orders, data)
        replenish_count, transfer_count = generate_replenishment_and_transfers(db, data)
        touch_count = generate_marketing_touches(db, target_orders, data, start, end)
        create_indexes(db)
        elapsed = time.perf_counter() - started
        summary = {
            "门店数": len(data.stores),
            "商品数": len(data.products),
            "SKU 数": len(data.skus),
            "库存记录数": len(data.inventory_by_key),
            "会员数": len(data.members),
            "订单数": order_counts["orders"],
            "订单明细数": order_counts["items"],
            "支付流水数": order_counts["payments"],
            "财务记录数": order_counts["finance"],
            "促销活动数": len(data.promotions),
            "优惠券数": len(data.coupons),
            "营销触达数": touch_count,
            "补货申请数": replenish_count,
            "调拨记录数": transfer_count,
            "操作日志数": 0,
            "生成耗时": f"{elapsed:.1f}s",
        }
        print("\n数据生成完成：")
        for key, value in summary.items():
            print(f"- {key}: {value}")
        print("\n提示：20 万订单下，订单、支付流水、财务记录等全量接口可能明显变慢，后续建议改分页和后端聚合。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
