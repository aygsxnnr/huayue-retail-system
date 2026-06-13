from datetime import datetime, timedelta
from uuid import uuid4
import json
import re

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .utils.code_generator import (
    build_sku_code,
    is_valid_product_code,
    match_color,
    match_size,
    next_barcode,
    next_product_code,
)


def list_stores(db: Session) -> list[models.Store]:
    return db.query(models.Store).order_by(models.Store.id).all()


def create_store(db: Session, payload: schemas.StoreCreate) -> models.Store:
    existing = db.query(models.Store).filter(models.Store.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="门店编码已存在")
    store = models.Store(**payload.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


def update_store(db: Session, store_id: int, payload: schemas.StoreUpdate) -> models.Store:
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "code" in updates and updates["code"] != store.code:
        existing = db.query(models.Store).filter(models.Store.code == updates["code"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="门店编码已存在")
    for key, value in updates.items():
        setattr(store, key, value)
    db.commit()
    db.refresh(store)
    return store


def update_store_status(db: Session, store_id: int, status: str) -> models.Store:
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    store.status = status
    db.commit()
    db.refresh(store)
    return store


def list_products(db: Session) -> list[models.Product]:
    return db.query(models.Product).options(joinedload(models.Product.skus)).order_by(models.Product.code.asc()).all()


def standard_product_code(db: Session, product: models.Product) -> str:
    if is_valid_product_code(product.code):
        return product.code
    return next_product_code(
        product.category,
        product.name,
        [item[0] for item in db.query(models.Product.code).filter(models.Product.id != product.id).all()],
    )


def create_product(db: Session, payload: schemas.ProductCreate) -> models.Product:
    product_code = payload.code or next_product_code(
        payload.category,
        payload.name,
        [item[0] for item in db.query(models.Product.code).all()],
    )
    existing = db.query(models.Product).filter(models.Product.code == product_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="商品编码已存在")
    product = models.Product(
        code=product_code,
        name=payload.name,
        category=payload.category,
        season=payload.season,
        brand=payload.brand,
        status=payload.status,
        launch_date=payload.launch_date or datetime.utcnow().date(),
        lifecycle_status=payload.lifecycle_status,
        sale_price=round(float(payload.sale_price or 0), 2),
        cost_price=round(float(payload.cost_price or 0), 2),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, payload: schemas.ProductUpdate) -> models.Product:
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "code" in updates and updates["code"] != product.code:
        existing = db.query(models.Product).filter(models.Product.code == updates["code"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="商品编码已存在")
    for key, value in updates.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def update_product_status(db: Session, product_id: int, status: str) -> models.Product:
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.status = status
    db.commit()
    db.refresh(product)
    return product


def list_skus(db: Session) -> list[models.SKU]:
    return (
        db.query(models.SKU)
        .join(models.Product, models.SKU.product_id == models.Product.id)
        .options(joinedload(models.SKU.product).joinedload(models.Product.skus))
        .order_by(models.Product.code.asc(), models.SKU.sku_code.asc())
        .all()
    )


def generate_sku_code_preview(db: Session, payload: schemas.SKUCodePreviewRequest) -> schemas.SKUCodePreviewOut:
    product = db.get(models.Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    color_match = match_color(payload.color)
    size_match = match_size(product.category, payload.size)
    product_code = standard_product_code(db, product)
    sku_code = build_sku_code(product_code, color_match, size_match)
    barcode = next_barcode([item[0] for item in db.query(models.SKU.barcode).all()])
    duplicate_sku = db.query(models.SKU).filter(models.SKU.sku_code == sku_code).first() is not None
    return schemas.SKUCodePreviewOut(
        product_code=product_code,
        main_color_code=color_match.main_color_code,
        sub_color_code=color_match.sub_color_code,
        size_code=size_match.size_code,
        sku_code=sku_code,
        barcode=barcode,
        color_match_note=color_match.note,
        size_match_note=size_match.note,
        duplicate_sku=duplicate_sku,
    )


def create_sku(db: Session, payload: schemas.SKUCreate) -> models.SKU:
    product = db.get(models.Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    color_match = match_color(payload.color)
    size_match = match_size(product.category, payload.size)
    product_code = standard_product_code(db, product)
    if product.code != product_code:
        product.code = product_code
    sku_code = build_sku_code(product_code, color_match, size_match)
    existing_code = db.query(models.SKU).filter(models.SKU.sku_code == sku_code).first()
    if existing_code:
        raise HTTPException(status_code=400, detail="该颜色尺码组合已存在")
    barcode = next_barcode([item[0] for item in db.query(models.SKU.barcode).all()])
    existing_barcode = db.query(models.SKU).filter(models.SKU.barcode == barcode).first()
    if existing_barcode:
        raise HTTPException(status_code=400, detail="条码已存在")
    list_price = payload.list_price or payload.sale_price or payload.price or product.sale_price
    if not list_price:
        raise HTTPException(status_code=400, detail="销售价不能为空")
    cost_price = payload.cost_price
    if cost_price is None:
        cost_price = product.cost_price if product.cost_price > 0 else round(list_price * 0.55, 2)
    sku = models.SKU(
        sku_code=sku_code,
        product_id=payload.product_id,
        color=payload.color,
        size=payload.size,
        barcode=barcode,
        list_price=list_price,
        cost_price=round(float(cost_price), 2),
        status=payload.status,
    )
    db.add(sku)
    db.flush()
    created_inventory_count = _create_default_inventory_for_sku(db, sku)
    db.commit()
    db.refresh(sku)
    sku.created_inventory_count = created_inventory_count
    return sku


def update_sku(db: Session, sku_id: int, payload: schemas.SKUUpdate) -> models.SKU:
    sku = db.get(models.SKU, sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU不存在")
    updates = payload.model_dump(exclude_unset=True)
    updates.pop("sku_code", None)
    updates.pop("code", None)
    list_price = updates.pop("sale_price", None) or updates.pop("price", None)
    if list_price is not None and "list_price" not in updates:
        updates["list_price"] = list_price
    if updates.get("cost_price") is None:
        updates.pop("cost_price", None)
    updates.pop("barcode", None)
    for key, value in updates.items():
        setattr(sku, key, value)
    color_match = match_color(sku.color)
    size_match = match_size(sku.product.category if sku.product else "", sku.size)
    product_code = standard_product_code(db, sku.product) if sku.product else ""
    if sku.product and sku.product.code != product_code:
        sku.product.code = product_code
    target_sku_code = build_sku_code(product_code, color_match, size_match) if sku.product else sku.sku_code
    if target_sku_code != sku.sku_code:
        existing = db.query(models.SKU).filter(models.SKU.sku_code == target_sku_code, models.SKU.id != sku.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="该颜色尺码组合已存在")
        sku.sku_code = target_sku_code
        sku.barcode = next_barcode([item[0] for item in db.query(models.SKU.barcode).filter(models.SKU.id != sku.id).all()])
    elif not re.fullmatch(r"69\d{11}", sku.barcode or ""):
        sku.barcode = next_barcode([item[0] for item in db.query(models.SKU.barcode).filter(models.SKU.id != sku.id).all()])
    db.commit()
    db.refresh(sku)
    return sku


def update_sku_status(db: Session, sku_id: int, status: str) -> models.SKU:
    sku = db.get(models.SKU, sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU不存在")
    sku.status = status
    db.commit()
    db.refresh(sku)
    return sku


def _is_available_store_for_inventory(store: models.Store) -> bool:
    return (store.status or "") in {"正常", "正常营业", "营业中"}


def _create_default_inventory_for_sku(db: Session, sku: models.SKU) -> int:
    stores = db.query(models.Store).order_by(models.Store.id).all()
    created_count = 0
    for store in stores:
        if not _is_available_store_for_inventory(store):
            continue
        existing = (
            db.query(models.Inventory)
            .filter(models.Inventory.store_id == store.id, models.Inventory.sku_id == sku.id)
            .first()
        )
        if existing:
            continue
        db.add(
            models.Inventory(
                store_id=store.id,
                sku_id=sku.id,
                quantity=0,
                safety_stock=5,
                in_transit=0,
                updated_at=datetime.utcnow(),
            )
        )
        created_count += 1
    return created_count


def search_pos_skus(db: Session, store_id: int, keyword: str = "") -> list[dict]:
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")

    query = (
        db.query(models.Inventory)
        .join(models.SKU, models.Inventory.sku_id == models.SKU.id)
        .join(models.Product, models.SKU.product_id == models.Product.id)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .filter(models.Inventory.store_id == store_id)
        .filter(~models.SKU.status.in_(["停用", "下架"]))
    )
    if keyword:
        like_keyword = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                models.Product.name.like(like_keyword),
                models.Product.category.like(like_keyword),
                models.SKU.sku_code.like(like_keyword),
                models.SKU.barcode.like(like_keyword),
                models.SKU.color.like(like_keyword),
                models.SKU.size.like(like_keyword),
            )
        )

    inventories = query.order_by(models.Product.category, models.SKU.sku_code).limit(30).all()
    return [
        {
            "sku_id": item.sku_id,
            "sku_code": item.sku.sku_code,
            "barcode": item.sku.barcode,
            "product_name": item.sku.product.name,
            "category": item.sku.product.category,
            "color": item.sku.color,
            "size": item.sku.size,
            "list_price": item.sku.list_price,
            "cost_price": _sku_cost_price(item.sku),
            "store_id": item.store_id,
            "store_name": item.store.name,
            "inventory_quantity": item.quantity,
            "safety_stock": item.safety_stock,
        }
        for item in inventories
    ]


def list_promotions(db: Session) -> list[models.Promotion]:
    return db.query(models.Promotion).order_by(models.Promotion.id).all()


def create_promotion(db: Session, payload: schemas.PromotionCreate) -> models.Promotion:
    promotion = models.Promotion(**payload.model_dump())
    db.add(promotion)
    db.commit()
    db.refresh(promotion)
    return promotion


def update_promotion(db: Session, promotion_id: int, payload: schemas.PromotionUpdate) -> models.Promotion:
    promotion = db.get(models.Promotion, promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="促销活动不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(promotion, key, value)
    db.commit()
    db.refresh(promotion)
    return promotion


def update_promotion_status(db: Session, promotion_id: int, status: str) -> models.Promotion:
    promotion = db.get(models.Promotion, promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="促销活动不存在")
    promotion.status = status
    db.commit()
    db.refresh(promotion)
    return promotion


def list_coupons(db: Session) -> list[models.Coupon]:
    return (
        db.query(models.Coupon)
        .options(joinedload(models.Coupon.promotion))
        .order_by(models.Coupon.id)
        .all()
    )


def generate_coupon_code(db: Session) -> str:
    prefix = f"CP{datetime.utcnow():%Y%m%d}"
    existing_codes = [
        code
        for (code,) in db.query(models.Coupon.code)
        .filter(models.Coupon.code.like(f"{prefix}%"))
        .all()
    ]
    max_seq = 0
    for code in existing_codes:
        suffix = (code or "").replace(prefix, "", 1)
        if suffix.isdigit():
            max_seq = max(max_seq, int(suffix))
    while True:
        max_seq += 1
        candidate = f"{prefix}{max_seq:04d}"
        if not db.query(models.Coupon).filter(models.Coupon.code == candidate).first():
            return candidate


def create_coupon(db: Session, payload: schemas.CouponCreate) -> models.Coupon:
    data = payload.model_dump()
    data["code"] = (data.get("code") or "").strip() or generate_coupon_code(db)
    existing = db.query(models.Coupon).filter(models.Coupon.code == data["code"]).first()
    if existing:
        raise HTTPException(status_code=400, detail="优惠券编号已存在")
    coupon = models.Coupon(**data)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


def update_coupon(db: Session, coupon_id: int, payload: schemas.CouponUpdate) -> models.Coupon:
    coupon = db.get(models.Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "code" in updates and updates["code"] != coupon.code:
        existing = db.query(models.Coupon).filter(models.Coupon.code == updates["code"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="优惠券编号已存在")
    for key, value in updates.items():
        setattr(coupon, key, value)
    db.commit()
    db.refresh(coupon)
    return coupon


def update_coupon_status(db: Session, coupon_id: int, status: str) -> models.Coupon:
    coupon = db.get(models.Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    coupon.status = status
    db.commit()
    db.refresh(coupon)
    return coupon


def _json_values(value: str | None) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = [item.strip() for item in text.split(",") if item.strip()]
    else:
        parsed = value
    if not isinstance(parsed, list):
        parsed = [parsed]
    values: list[str] = []
    for item in parsed:
        if isinstance(item, dict):
            for key in ("id", "name", "code", "value", "label"):
                if item.get(key) is not None:
                    values.append(str(item[key]))
                    break
        elif item is not None:
            values.append(str(item))
    return [item for item in values if item]


def _member_group(member: models.Member) -> str:
    return member.tag_profile.member_group if member.tag_profile else ""


MEMBER_LIFECYCLE_STATUS_SET = {"新会员", "活跃会员", "流失风险会员", "沉睡会员", "未消费会员"}
MEMBER_GROUP_SET = {
    "高价值会员",
    "价格敏感会员",
    "促销敏感会员",
    "新品偏好会员",
    "清仓偏好会员",
    "高频购买会员",
    "低频购买会员",
    "女装偏好会员",
    "配饰偏好会员",
    "普通会员",
}


def _normalize_member_groups(values: list[str]) -> set[str]:
    return {value for value in values if value in MEMBER_GROUP_SET and value not in MEMBER_LIFECYCLE_STATUS_SET}


def _member_all_tags(member: models.Member) -> set[str]:
    tags = set(member.member_tags)
    if member.tag_profile:
        tags.update(
            tag
            for tag in [
                member.tag_profile.member_group,
                member.tag_profile.preference_tag,
                member.tag_profile.price_sensitive_tag,
                member.tag_profile.activity_tag,
                member.tag_profile.risk_tag,
            ]
            if tag
        )
    return tags


def _member_store_values(member: models.Member) -> set[str]:
    return set(_json_values(member.registered_store))


def compute_member_lifecycle_status(member: models.Member, today=None) -> str:
    today = today or datetime.utcnow().date()
    joined_at = getattr(member, "joined_at", None)
    if joined_at and (today - joined_at.date()).days <= 30:
        return "新会员"
    total_orders = int(getattr(member, "total_orders", 0) or 0)
    last_purchase_at = getattr(member, "last_purchase_at", None)
    if total_orders <= 0 or not last_purchase_at:
        return "未消费会员"
    days_since_purchase = (today - last_purchase_at.date()).days
    if days_since_purchase <= 45:
        return "活跃会员"
    if 45 <= days_since_purchase < 90:
        return "流失风险会员"
    if days_since_purchase >= 90:
        return "沉睡会员"
    return "普通会员"


def _member_registered_store_names(db: Session, member: models.Member) -> list[str]:
    raw_values: list[str] = []
    raw_text = (member.registered_store or "").strip()
    if raw_text:
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict):
                        raw_values.append(str(item.get("id") or item.get("name") or item.get("code") or ""))
                        if item.get("name"):
                            raw_values.append(str(item["name"]))
                    elif item is not None:
                        raw_values.append(str(item))
            else:
                raw_values = _json_values(raw_text)
        except json.JSONDecodeError:
            raw_values = _json_values(raw_text)
    names: list[str] = []
    for value in raw_values:
        store = None
        if str(value).isdigit():
            store = db.get(models.Store, int(value))
        if not store:
            store = (
                db.query(models.Store)
                .filter(or_(models.Store.name == str(value), models.Store.code == str(value)))
                .first()
            )
        names.append(store.name if store else str(value))
    return [name for name in dict.fromkeys(names) if name]


def _coupon_rule_values(coupon: models.Coupon, field: str) -> list[str]:
    values = _json_values(getattr(coupon, field, ""))
    if field == "applicable_member_groups":
        return sorted(_normalize_member_groups(values))
    return values


def _coupon_is_issueable(coupon: models.Coupon) -> tuple[bool, str]:
    today = datetime.utcnow().date()
    status = coupon.status or ""
    if "停" in status or "仠" in status:
        return False, "优惠券已停用"
    if coupon.valid_start and today < coupon.valid_start:
        return False, "优惠券未开始"
    if coupon.valid_end and today > coupon.valid_end:
        return False, "优惠券已过期"
    if coupon.total_issue_limit is not None and coupon.issued_count >= coupon.total_issue_limit:
        return False, "优惠券总发放数量已达上限"
    return True, ""


def _member_matches_coupon(coupon: models.Coupon, member: models.Member) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    levels = set(_coupon_rule_values(coupon, "applicable_member_levels"))
    if levels:
        if member.level not in levels:
            return False, []
        reasons.append("会员等级匹配")
    groups = set(_coupon_rule_values(coupon, "applicable_member_groups"))
    member_group = _member_group(member)
    if groups:
        if member_group not in groups:
            return False, []
        reasons.append("会员分群匹配")
    tags = set(_coupon_rule_values(coupon, "target_tags"))
    member_tags = _member_all_tags(member)
    if tags:
        matched_tags = sorted(tags & member_tags)
        if not matched_tags:
            return False, []
        reasons.append("标签匹配：" + "、".join(matched_tags[:3]))
    store_ids = set(_coupon_rule_values(coupon, "applicable_store_ids"))
    if store_ids:
        member_stores = _member_store_values(member)
        if not (store_ids & member_stores):
            return False, []
        reasons.append("注册门店匹配")
    return True, reasons or ["不限制会员条件"]


def _normalized_lifecycle_statuses(conditions: schemas.CouponMatchConditions) -> set[str]:
    statuses = set(conditions.lifecycle_statuses or [])
    if conditions.is_new_member is True:
        statuses.add("新会员")
    if conditions.is_sleeping_member is True:
        statuses.add("沉睡会员")
    if conditions.is_churn_risk is True:
        statuses.add("流失风险会员")
    return statuses


def _member_matches_conditions(db: Session, member: models.Member, conditions: schemas.CouponMatchConditions) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if conditions.member_levels:
        if member.level not in set(conditions.member_levels):
            return False, []
        reasons.append("人工等级条件匹配")
    condition_groups = _normalize_member_groups(conditions.member_groups or [])
    if condition_groups:
        if _member_group(member) not in condition_groups:
            return False, []
        reasons.append("人工分群条件匹配")
    if conditions.tags:
        matched_tags = sorted(set(conditions.tags) & _member_all_tags(member))
        if not matched_tags:
            return False, []
        reasons.append("人工标签条件匹配")
    if conditions.store_ids:
        store_values = {str(item) for item in conditions.store_ids}
        selected_store_names = {
            store.name
            for store in db.query(models.Store).filter(models.Store.id.in_(conditions.store_ids)).all()
        }
        member_store_names = set(_member_registered_store_names(db, member))
        if not (store_values & _member_store_values(member)) and not (selected_store_names & member_store_names):
            return False, []
        reasons.append("人工门店条件匹配")
    account_statuses = set((conditions.account_statuses or []) + (conditions.member_statuses or []))
    if account_statuses:
        if member.status not in account_statuses:
            return False, []
        reasons.append(f"账户状态匹配：{member.status}")
    lifecycle_statuses = _normalized_lifecycle_statuses(conditions)
    lifecycle_status = compute_member_lifecycle_status(member)
    if lifecycle_statuses:
        if lifecycle_status not in lifecycle_statuses:
            return False, []
        reasons.append(f"生命周期状态匹配：{lifecycle_status}")
    if conditions.recent_purchase_start:
        if not member.last_purchase_at or member.last_purchase_at.date() < conditions.recent_purchase_start:
            return False, []
        reasons.append("最近消费时间匹配")
    if conditions.recent_purchase_end:
        if not member.last_purchase_at or member.last_purchase_at.date() > conditions.recent_purchase_end:
            return False, []
        reasons.append("最近消费时间匹配")
    if conditions.min_total_spent is not None:
        if member.total_spent < conditions.min_total_spent:
            return False, []
        reasons.append("累计消费金额匹配")
    if conditions.max_total_spent is not None:
        if member.total_spent > conditions.max_total_spent:
            return False, []
        reasons.append("累计消费金额匹配")
    if conditions.min_points is not None:
        if member.points < conditions.min_points:
            return False, []
        reasons.append("积分范围匹配")
    if conditions.max_points is not None:
        if member.points > conditions.max_points:
            return False, []
        reasons.append("积分范围匹配")
    return True, reasons


def match_coupon_members(db: Session, coupon_id: int, payload: schemas.CouponMatchRequest) -> dict:
    coupon = db.get(models.Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    members = (
        db.query(models.Member)
        .options(joinedload(models.Member.tag_profile))
        .order_by(models.Member.id)
        .all()
    )
    exclude_ids = set(payload.exclude_member_ids or [])
    extra_ids = set(payload.extra_member_ids or [])
    matched: dict[int, dict] = {}
    for member in members:
        if member.id in exclude_ids:
            continue
        coupon_match, coupon_reasons = _member_matches_coupon(coupon, member)
        condition_match, condition_reasons = _member_matches_conditions(db, member, payload.conditions)
        if coupon_match and condition_match:
            store_names = _member_registered_store_names(db, member)
            matched[member.id] = {
                "id": member.id,
                "name": member.name,
                "phone": member.phone,
                "level": member.level,
                "member_group": _member_group(member) or "-",
                "registered_store": "、".join(store_names) or "-",
                "registered_store_text": "、".join(store_names) or "-",
                "registered_store_names": store_names,
                "account_status": member.status or "-",
                "lifecycle_status": compute_member_lifecycle_status(member),
                "last_purchase_at": member.last_purchase_at,
                "match_reason": "；".join(coupon_reasons + condition_reasons),
            }
    for member_id in extra_ids - exclude_ids:
        member = db.get(models.Member, member_id)
        if member:
            store_names = _member_registered_store_names(db, member)
            matched[member.id] = {
                "id": member.id,
                "name": member.name,
                "phone": member.phone,
                "level": member.level,
                "member_group": _member_group(member) or "-",
                "registered_store": "、".join(store_names) or "-",
                "registered_store_text": "、".join(store_names) or "-",
                "registered_store_names": store_names,
                "account_status": member.status or "-",
                "lifecycle_status": compute_member_lifecycle_status(member),
                "last_purchase_at": member.last_purchase_at,
                "match_reason": "人工添加",
            }
    rows = list(matched.values())
    return {"matched_count": len(rows), "matched_members": rows}


def _member_coupon_touch_count(db: Session, member_id: int, coupon_id: int) -> int:
    return (
        db.query(models.MarketingTouch)
        .filter(
            models.MarketingTouch.member_id == member_id,
            models.MarketingTouch.coupon_id == coupon_id,
        )
        .count()
    )


def _issue_coupon_to_member_channels(
    db: Session,
    coupon: models.Coupon,
    member: models.Member,
    channels: list[str],
    remark: str,
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    issueable, reason = _coupon_is_issueable(coupon)
    if not issueable:
        return 0, [reason]
    matches, _ = _member_matches_coupon(coupon, member)
    if not matches:
        return 0, ["会员不符合优惠券适用范围"]
    current_count = _member_coupon_touch_count(db, member.id, coupon.id)
    created = 0
    for channel in channels:
        if coupon.total_issue_limit is not None and coupon.issued_count >= coupon.total_issue_limit:
            reasons.append("优惠券总发放数量已达上限")
            break
        if coupon.per_member_limit is not None and current_count >= coupon.per_member_limit:
            reasons.append("该会员已达到领取上限")
            break
        existing = (
            db.query(models.MarketingTouch)
            .filter(
                models.MarketingTouch.member_id == member.id,
                models.MarketingTouch.coupon_id == coupon.id,
                models.MarketingTouch.channel == channel,
                models.MarketingTouch.writeoff_status == "未核销",
            )
            .first()
        )
        if existing:
            reasons.append(f"{channel} 渠道已发放")
            continue
        db.add(
            models.MarketingTouch(
                member_id=member.id,
                coupon_id=coupon.id,
                promotion_id=coupon.promotion_id,
                channel=channel,
                participation_status="未参与",
                writeoff_status="未核销",
                remark=remark,
            )
        )
        coupon.issued_count += 1
        current_count += 1
        created += 1
    return created, reasons


def issue_coupon_to_members(db: Session, coupon_id: int, payload: schemas.CouponIssueRequest) -> dict:
    coupon = db.get(models.Coupon, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    created_count = 0
    failed_items: list[dict] = []
    channels = [channel for channel in dict.fromkeys(payload.channels) if channel]
    for member_id in dict.fromkeys(payload.member_ids):
        member = db.get(models.Member, member_id)
        if not member:
            failed_items.append({"member_id": member_id, "reason": "会员不存在"})
            continue
        created, reasons = _issue_coupon_to_member_channels(db, coupon, member, channels, payload.remark)
        created_count += created
        if reasons:
            failed_items.append({"member_id": member_id, "reason": "；".join(dict.fromkeys(reasons))})
    db.commit()
    return {
        "created_count": created_count,
        "skipped_count": len(failed_items),
        "failed_items": failed_items,
    }


def _auto_issue_new_member_coupons(db: Session, member: models.Member) -> None:
    coupons = (
        db.query(models.Coupon)
        .filter(models.Coupon.auto_issue_enabled.is_(True))
        .order_by(models.Coupon.id)
        .all()
    )
    for coupon in coupons:
        issue_mode = coupon.issue_mode or ""
        if issue_mode and "新会员" not in issue_mode and "new" not in issue_mode.lower() and set(issue_mode) != {"?"}:
            continue
        try:
            _issue_coupon_to_member_channels(db, coupon, member, ["APP推送"], "新会员自动发放")
        except Exception:
            continue


def list_members(db: Session) -> list[models.Member]:
    _sync_member_metrics(db)
    return (
        db.query(models.Member)
        .options(joinedload(models.Member.tag_profile))
        .order_by(models.Member.id)
        .all()
    )


def search_members(db: Session, keyword: str) -> list[models.Member]:
    if not keyword.strip():
        return []
    like_keyword = f"%{keyword.strip()}%"
    return (
        db.query(models.Member)
        .filter(
            or_(
                models.Member.name.like(like_keyword),
                models.Member.phone.like(like_keyword),
                models.Member.member_no.like(like_keyword),
            )
        )
        .order_by(models.Member.id)
        .limit(10)
        .all()
    )


def create_member(db: Session, payload: schemas.MemberCreate) -> models.Member:
    existing = db.query(models.Member).filter(models.Member.phone == payload.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="手机号已存在")

    member = models.Member(
        member_no=f"HY{datetime.utcnow():%Y%m%d}{uuid4().hex[:6].upper()}",
        name=payload.name,
        phone=payload.phone,
        level=payload.level,
        tags=payload.tags,
        points=payload.points,
        total_spent=payload.total_spent,
        total_orders=payload.total_orders,
        status=payload.status,
        registered_store=payload.registered_store,
    )
    db.add(member)
    db.flush()
    try:
        _auto_issue_new_member_coupons(db, member)
    except Exception:
        pass
    db.commit()
    db.refresh(member)
    return member


def update_member(db: Session, member_id: int, payload: schemas.MemberUpdate) -> models.Member:
    member = db.get(models.Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "phone" in updates and updates["phone"] != member.phone:
        existing = db.query(models.Member).filter(models.Member.phone == updates["phone"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="手机号已存在")
    for key, value in updates.items():
        setattr(member, key, value)
    db.commit()
    db.refresh(member)
    return member


def update_member_status(db: Session, member_id: int, status: str) -> models.Member:
    member = db.get(models.Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    member.status = status
    db.commit()
    db.refresh(member)
    return member


def get_member_profile(db: Session, member_id: int) -> dict:
    _sync_member_metrics(db)
    member = (
        db.query(models.Member)
        .options(joinedload(models.Member.tag_profile))
        .filter(models.Member.id == member_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    recent_items = (
        db.query(models.SalesOrderItem)
        .join(models.SalesOrder, models.SalesOrderItem.order_id == models.SalesOrder.id)
        .join(models.SKU, models.SalesOrderItem.sku_id == models.SKU.id)
        .join(models.Product, models.SKU.product_id == models.Product.id)
        .filter(models.SalesOrder.member_id == member.id)
        .order_by(models.SalesOrder.order_time.desc())
        .limit(6)
        .all()
    )
    recent_products = []
    preferred_categories: dict[str, int] = {}
    for item in recent_items:
        product = item.sku.product if item.sku else None
        if product:
            recent_products.append(product.name)
            preferred_categories[product.category] = preferred_categories.get(product.category, 0) + item.quantity
    tags = member.tag_profile
    actions = ["发放满减券", "推送新品活动"]
    if tags and "沉睡" in tags.member_group:
        actions = ["唤醒沉睡会员", "发放限时回流券", "推荐相似品类商品"]
    elif tags and "高价值" in tags.member_group:
        actions = ["邀请参加会员专享活动", "推送高价值新品", "发放专属折扣券"]
    return {
        "member": member,
        "tag_profile": tags,
        "recent_products": recent_products or ["暂无最近购买商品"],
        "preferred_categories": [
            item[0] for item in sorted(preferred_categories.items(), key=lambda entry: entry[1], reverse=True)
        ] or ["暂无偏好品类"],
        "recommended_actions": actions,
    }


def list_member_rfm(db: Session) -> list[dict]:
    _sync_member_metrics(db)
    #_recalculate_member_tags(db, commit=True)
    members = (
        db.query(models.Member)
        .options(joinedload(models.Member.tag_profile))
        .order_by(models.Member.total_spent.desc(), models.Member.id)
        .all()
    )
    return [_rfm_row(member) for member in members]


def recalculate_member_rfm(db: Session) -> list[dict]:
    _sync_member_metrics(db)
    _recalculate_member_tags(db, commit=True)
    return list_member_rfm(db)


def list_marketing_touches(db: Session) -> list[models.MarketingTouch]:
    return (
        db.query(models.MarketingTouch)
        .options(
            joinedload(models.MarketingTouch.member),
            joinedload(models.MarketingTouch.coupon).joinedload(models.Coupon.promotion),
            joinedload(models.MarketingTouch.promotion),
        )
        .order_by(models.MarketingTouch.touch_time.desc(), models.MarketingTouch.id.desc())
        .all()
    )


def create_marketing_touch(db: Session, payload: schemas.MarketingTouchCreate) -> models.MarketingTouch:
    member = db.get(models.Member, payload.member_id)
    if not member:
        raise HTTPException(status_code=404, detail="会员不存在")
    coupon = db.get(models.Coupon, payload.coupon_id) if payload.coupon_id else None
    if payload.coupon_id and not coupon:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    promotion_id = payload.promotion_id or (coupon.promotion_id if coupon else None)
    touch = models.MarketingTouch(
        member_id=payload.member_id,
        coupon_id=payload.coupon_id,
        promotion_id=promotion_id,
        channel=payload.channel,
        participation_status=payload.participation_status,
        writeoff_status=payload.writeoff_status,
        remark=payload.remark,
    )
    if coupon:
        coupon.issued_count += 1
    db.add(touch)
    db.commit()
    db.refresh(touch)
    return touch


def batch_create_marketing_touches(db: Session, payload: schemas.MarketingTouchBatchCreate) -> dict:
    created_count = 0
    skipped_count = 0
    member_ids = list(dict.fromkeys(payload.member_ids))
    coupon_ids = list(dict.fromkeys(payload.coupon_ids))
    channels = [channel for channel in dict.fromkeys(payload.channels) if channel]
    for member_id in member_ids:
        member = db.get(models.Member, member_id)
        if not member:
            skipped_count += len(coupon_ids) * len(channels)
            continue
        for coupon_id in coupon_ids:
            coupon = db.get(models.Coupon, coupon_id)
            if not coupon:
                skipped_count += len(channels)
                continue
            for channel in channels:
                existing = (
                    db.query(models.MarketingTouch)
                    .filter(
                        models.MarketingTouch.member_id == member_id,
                        models.MarketingTouch.coupon_id == coupon_id,
                        models.MarketingTouch.channel == channel,
                        models.MarketingTouch.writeoff_status == "未核销",
                    )
                    .first()
                )
                if existing:
                    skipped_count += 1
                    continue
                db.add(
                    models.MarketingTouch(
                        member_id=member_id,
                        coupon_id=coupon_id,
                        promotion_id=coupon.promotion_id,
                        channel=channel,
                        participation_status="未参与",
                        writeoff_status="未核销",
                        remark=payload.remark,
                    )
                )
                coupon.issued_count += 1
                created_count += 1
    db.commit()
    return {"created_count": created_count, "skipped_count": skipped_count}


def repurchase_analysis(db: Session) -> dict:
    _sync_member_metrics(db)
    members = (
        db.query(models.Member)
        .order_by(models.Member.total_orders.desc(), models.Member.total_spent.desc())
        .limit(10)
        .all()
    )
    ranking = [
        {
            "rank": index,
            "member_id": member.id,
            "member_no": member.member_no,
            "name": member.name,
            "total_orders": member.total_orders,
            "total_spent": member.total_spent,
            "last_purchase_at": member.last_purchase_at,
            "level": member.level,
            "repurchase_tag": "高频复购" if member.total_orders >= 5 else "待培育复购",
        }
        for index, member in enumerate(members, start=1)
    ]
    all_members = db.query(models.Member).all()
    member_levels = ["普通会员", "银卡会员", "金卡会员", "黑金会员"]
    level_counts = {level: 0 for level in member_levels}
    for member in all_members:
        level = member.level or "普通会员"
        level_counts[level] = level_counts.get(level, 0) + 1
    level_distribution = [
        {
            "level": level,
            "count": level_counts.get(level, 0),
        }
        for level in member_levels
    ]
    lifecycle_levels = ["新会员", "活跃会员", "流失风险会员", "沉睡会员", "未消费会员", "普通会员"]
    lifecycle_counts = {level: 0 for level in lifecycle_levels}
    for member in all_members:
        status = compute_member_lifecycle_status(member)
        lifecycle_counts[status] = lifecycle_counts.get(status, 0) + 1
    lifecycle_distribution = [
        {
            "level": level,
            "count": lifecycle_counts.get(level, 0),
        }
        for level in lifecycle_levels
    ]
    touches = list_marketing_touches(db)
    effect_map: dict[str, dict] = {}
    for touch in touches:
        name = touch.coupon.name if touch.coupon else (touch.promotion.name if touch.promotion else "门店营销触达")
        row = effect_map.setdefault(
            name,
            {
                "name": name,
                "touched_count": 0,
                "clicked_count": 0,
                "participated_count": 0,
                "writeoff_count": 0,
                "driven_sales_amount": 0.0,
            },
        )
        row["touched_count"] += 1
        if touch.participation_status in {"已点击", "已参与", "已购买"}:
            row["clicked_count"] += 1
        if touch.participation_status in {"已参与", "已购买"}:
            row["participated_count"] += 1
        if touch.writeoff_status == "已核销":
            row["writeoff_count"] += 1
            row["driven_sales_amount"] += 268.0
    marketing_effects = []
    for row in effect_map.values():
        touched = row["touched_count"]
        writeoff = row["writeoff_count"]
        marketing_effects.append(
            {
                **row,
                "writeoff_rate": round((writeoff / touched * 100) if touched else 0, 2),
                "driven_sales_amount": round(row["driven_sales_amount"], 2),
            }
        )
    return {
        "repurchase_ranking": ranking,
        "level_distribution": level_distribution,
        "lifecycle_distribution": lifecycle_distribution,
        "marketing_effects": marketing_effects,
    }


def _sync_member_metrics(db: Session) -> None:
    return
    members = db.query(models.Member).all()
    for member in members:
        metrics = (
            db.query(
                func.count(models.SalesOrder.id),
                func.coalesce(func.sum(models.SalesOrder.paid_amount), 0),
                func.max(models.SalesOrder.order_time),
            )
            .filter(models.SalesOrder.member_id == member.id)
            .one()
        )
        order_count = int(metrics[0] or 0)
        order_amount = float(metrics[1] or 0)
        if order_count:
            member.total_orders = max(member.total_orders, order_count)
            member.total_spent = max(member.total_spent, round(order_amount, 2))
            member.last_purchase_at = metrics[2]
        member.level = _member_level(member.total_spent)
        if member.status != "已停用":
            member.status = _member_status(member.last_purchase_at)
    db.flush()


def _member_level(total_spent: float) -> str:
    if total_spent >= 8000:
        return "黑金会员"
    if total_spent >= 3000:
        return "金卡会员"
    if total_spent >= 1000:
        return "银卡会员"
    return "普通会员"


def _member_status(last_purchase_at: datetime | None) -> str:
    if not last_purchase_at:
        return "沉睡"
    days = (datetime.utcnow() - last_purchase_at).days
    if days <= 30:
        return "活跃"
    if days <= 90:
        return "正常"
    if days <= 180:
        return "沉睡"
    return "流失风险"


def _score_recency(last_purchase_at: datetime | None) -> int:
    if not last_purchase_at:
        return 1
    days = (datetime.utcnow() - last_purchase_at).days
    if days <= 15:
        return 5
    if days <= 30:
        return 4
    if days <= 90:
        return 3
    if days <= 180:
        return 2
    return 1


def _score_frequency(total_orders: int) -> int:
    if total_orders >= 8:
        return 5
    if total_orders >= 5:
        return 4
    if total_orders >= 3:
        return 3
    if total_orders >= 1:
        return 2
    return 1


def _score_monetary(total_spent: float) -> int:
    if total_spent >= 8000:
        return 5
    if total_spent >= 3000:
        return 4
    if total_spent >= 1000:
        return 3
    if total_spent > 0:
        return 2
    return 1


def _rfm_group(r_score: int, f_score: int, m_score: int) -> str:
    if r_score >= 4 and f_score >= 4 and m_score >= 4:
        return "高价值会员"
    if r_score >= 4 and f_score >= 3:
        return "重点保持会员"
    if r_score >= 4 and f_score <= 2:
        return "新会员"
    if r_score <= 2 and m_score >= 4:
        return "流失风险会员"
    if r_score <= 2:
        return "沉睡会员"
    if m_score <= 2:
        return "价格敏感会员"
    return "潜力会员"


def _strategy_for_group(group: str) -> str:
    strategies = {
        "高价值会员": "维护专属权益，推送新品预览和高客单搭配推荐",
        "重点保持会员": "保持稳定触达，发放会员专享折扣券",
        "潜力会员": "引导二次购买，推荐相似品类商品",
        "新会员": "发送新客欢迎券，促进首轮复购",
        "沉睡会员": "使用限时满减券唤醒，降低回流门槛",
        "流失风险会员": "人工关怀并发放回流优惠券",
        "价格敏感会员": "优先推送清货和满减活动",
    }
    return strategies.get(group, "保持常规会员运营触达")


def _recalculate_member_tags(db: Session, commit: bool = False) -> None:
    for member in db.query(models.Member).all():
        r_score = _score_recency(member.last_purchase_at)
        f_score = _score_frequency(member.total_orders)
        m_score = _score_monetary(member.total_spent)
        group = _rfm_group(r_score, f_score, m_score)
        tag = member.tag_profile or models.MemberTag(member_id=member.id)
        tag.r_score = r_score
        tag.f_score = f_score
        tag.m_score = m_score
        tag.member_group = group
        tag.preference_tag = "新品敏感" if r_score >= 4 else "基础款偏好"
        tag.price_sensitive_tag = "价格敏感" if m_score <= 2 else "高价值会员"
        tag.activity_tag = "高活跃" if f_score >= 4 else ("沉睡会员" if r_score <= 2 else "普通活跃")
        tag.risk_tag = "流失风险" if r_score <= 2 else "稳定"
        tag.updated_at = datetime.utcnow()
        db.add(tag)
    if commit:
        db.commit()


def _rfm_row(member: models.Member) -> dict:
    tag = member.tag_profile
    if not tag:
        return {
            "member_id": member.id,
            "member_no": member.member_no,
            "name": member.name,
            "r_score": 1,
            "f_score": 1,
            "m_score": 1,
            "member_group": "潜力会员",
            "main_tags": ["待补充标签"],
            "strategy": "完善会员基础数据后进行常规触达",
        }
    tags = [tag.preference_tag, tag.price_sensitive_tag, tag.activity_tag, tag.risk_tag]
    return {
        "member_id": member.id,
        "member_no": member.member_no,
        "name": member.name,
        "r_score": tag.r_score,
        "f_score": tag.f_score,
        "m_score": tag.m_score,
        "member_group": tag.member_group,
        "main_tags": [item for item in tags if item],
        "strategy": _strategy_for_group(tag.member_group),
    }


def list_inventory(db: Session) -> list[models.Inventory]:
    inventories = (
        db.query(models.Inventory)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .order_by(models.Inventory.store_id, models.Inventory.sku_id)
        .all()
    )
    return [_inventory_with_replenishment_metrics(db, item) for item in inventories]


def list_low_stock(db: Session) -> list[models.Inventory]:
    inventories = (
        db.query(models.Inventory)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .filter(models.Inventory.quantity <= models.Inventory.safety_stock)
        .order_by(models.Inventory.quantity)
        .all()
    )
    return [_inventory_with_replenishment_metrics(db, item) for item in inventories]


def update_inventory_safety_stock(
    db: Session,
    inventory_id: int,
    payload: schemas.InventorySafetyStockUpdate,
) -> dict:
    inventory = (
        db.query(models.Inventory)
        .options(
            joinedload(models.Inventory.store),
            joinedload(models.Inventory.sku).joinedload(models.SKU.product),
        )
        .filter(models.Inventory.id == inventory_id)
        .first()
    )
    if not inventory:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    inventory.safety_stock = payload.safety_stock
    inventory.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(inventory)
    return _inventory_with_replenishment_metrics(db, inventory)


def _recent_7d_sales(db: Session, store_id: int, sku_id: int) -> int:
    since = datetime.utcnow() - timedelta(days=7)
    return (
        db.query(func.coalesce(func.sum(models.SalesOrderItem.quantity), 0))
        .join(models.SalesOrder, models.SalesOrderItem.order_id == models.SalesOrder.id)
        .filter(
            models.SalesOrder.store_id == store_id,
            models.SalesOrderItem.sku_id == sku_id,
            models.SalesOrder.order_time >= since,
        )
        .scalar()
        or 0
    )


def _inventory_status(quantity: int, safety_stock: int, has_pending_replenishment: bool = False) -> str:
    if has_pending_replenishment:
        return "待补货"
    if quantity <= 0:
        return "缺货预警"
    if quantity < safety_stock:
        return "低库存"
    return "正常"


def _suggested_qty(safety_stock: int, recent_7d_sales: int, quantity: int, in_transit: int) -> int:
    return max(safety_stock * 2 + recent_7d_sales - quantity - in_transit, 0)


def _inventory_with_replenishment_metrics(db: Session, inventory: models.Inventory) -> dict:
    recent_7d_sales = _recent_7d_sales(db, inventory.store_id, inventory.sku_id)
    has_pending_replenishment = (
        db.query(models.ReplenishmentRequest)
        .filter(
            models.ReplenishmentRequest.inventory_id == inventory.id,
            models.ReplenishmentRequest.status.in_(["待审核", "已审核", "待调拨", "在途"]),
        )
        .first()
        is not None
    )
    return {
        "id": inventory.id,
        "store_id": inventory.store_id,
        "sku_id": inventory.sku_id,
        "quantity": inventory.quantity,
        "safety_stock": inventory.safety_stock,
        "in_transit": inventory.in_transit,
        "updated_at": inventory.updated_at,
        "store": inventory.store,
        "sku": inventory.sku,
        "recent_7d_sales": recent_7d_sales,
        "suggested_qty": _suggested_qty(
            inventory.safety_stock,
            recent_7d_sales,
            inventory.quantity,
            inventory.in_transit,
        ),
        "inventory_status": _inventory_status(
            inventory.quantity,
            inventory.safety_stock,
            has_pending_replenishment,
        ),
    }


def list_replenishments(db: Session) -> list[models.ReplenishmentRequest]:
    return (
        db.query(models.ReplenishmentRequest)
        .options(
            joinedload(models.ReplenishmentRequest.store),
            joinedload(models.ReplenishmentRequest.sku).joinedload(models.SKU.product),
        )
        .order_by(models.ReplenishmentRequest.created_at.desc())
        .all()
    )


def create_replenishment(
    db: Session,
    payload: schemas.ReplenishmentCreate,
) -> models.ReplenishmentRequest:
    inventory = (
        db.query(models.Inventory)
        .options(joinedload(models.Inventory.sku).joinedload(models.SKU.product))
        .filter(models.Inventory.id == payload.inventory_id)
        .first()
    )
    if not inventory:
        raise HTTPException(status_code=404, detail="库存记录不存在")

    recent_7d_sales = _recent_7d_sales(db, inventory.store_id, inventory.sku_id)
    request = models.ReplenishmentRequest(
        inventory_id=inventory.id,
        store_id=inventory.store_id,
        sku_id=inventory.sku_id,
        current_quantity=inventory.quantity,
        safety_stock=inventory.safety_stock,
        in_transit=inventory.in_transit,
        recent_7d_sales=recent_7d_sales,
        suggested_qty=_suggested_qty(
            inventory.safety_stock,
            recent_7d_sales,
            inventory.quantity,
            inventory.in_transit,
        ),
        request_qty=payload.request_qty,
        reason=payload.reason,
        applicant=payload.applicant,
        status="待审核",
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def approve_replenishment(db: Session, request_id: int) -> models.ReplenishmentRequest:
    request = db.get(models.ReplenishmentRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="补货申请不存在")
    if request.status not in {"待审核", "已驳回"}:
        raise HTTPException(status_code=400, detail="当前状态不能审核通过")
    request.status = "已审核"
    request.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return request


def reject_replenishment(db: Session, request_id: int) -> models.ReplenishmentRequest:
    request = db.get(models.ReplenishmentRequest, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="补货申请不存在")
    if request.status not in {"待审核", "已审核"}:
        raise HTTPException(status_code=400, detail="当前状态不能驳回")
    request.status = "已驳回"
    request.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(request)
    return request


def list_transfers(db: Session) -> list[models.TransferRecord]:
    return (
        db.query(models.TransferRecord)
        .options(
            joinedload(models.TransferRecord.request),
            joinedload(models.TransferRecord.store),
            joinedload(models.TransferRecord.sku).joinedload(models.SKU.product),
        )
        .order_by(models.TransferRecord.shipped_at.desc(), models.TransferRecord.id.desc())
        .all()
    )


def create_transfer(db: Session, payload: schemas.TransferCreate) -> models.TransferRecord:
    request = db.get(models.ReplenishmentRequest, payload.request_id)
    if not request:
        raise HTTPException(status_code=404, detail="补货申请不存在")
    if request.status != "已审核":
        raise HTTPException(status_code=400, detail="只能对已审核补货申请生成调拨单")

    inventory = db.get(models.Inventory, request.inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="库存记录不存在")

    transfer_qty = payload.transfer_qty or request.request_qty
    transfer = models.TransferRecord(
        request_id=request.id,
        inventory_id=request.inventory_id,
        store_id=request.store_id,
        sku_id=request.sku_id,
        source_location=payload.source_location,
        transfer_qty=transfer_qty,
        in_transit_qty=transfer_qty,
        status="在途",
        shipped_at=datetime.utcnow(),
        expected_arrival_at=datetime.utcnow() + timedelta(days=3),
    )
    request.status = "在途"
    request.updated_at = datetime.utcnow()
    inventory.in_transit += transfer_qty
    inventory.updated_at = datetime.utcnow()

    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return transfer


def mark_transfer_arrival(db: Session, transfer_id: int) -> models.TransferRecord:
    transfer = db.get(models.TransferRecord, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="调拨记录不存在")
    if transfer.status == "已到货":
        return transfer

    inventory = db.get(models.Inventory, transfer.inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="库存记录不存在")
    request = db.get(models.ReplenishmentRequest, transfer.request_id)

    arrived_qty = transfer.in_transit_qty
    inventory.quantity += arrived_qty
    inventory.in_transit = max(inventory.in_transit - arrived_qty, 0)
    inventory.updated_at = datetime.utcnow()
    transfer.status = "已到货"
    transfer.in_transit_qty = 0
    transfer.arrived_at = datetime.utcnow()
    if request:
        request.status = "已完成"
        request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(transfer)
    return transfer


def list_orders(db: Session, limit: int | None = None) -> list[models.SalesOrder]:
    query = (
        db.query(models.SalesOrder)
        .options(
            joinedload(models.SalesOrder.items)
            .joinedload(models.SalesOrderItem.sku)
            .joinedload(models.SKU.product)
        )
        .order_by(models.SalesOrder.order_time.desc())
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def list_recent_orders(db: Session, limit: int = 8) -> list[models.SalesOrder]:
    return (
        db.query(models.SalesOrder)
        .options(
            joinedload(models.SalesOrder.items)
            .joinedload(models.SalesOrderItem.sku)
            .joinedload(models.SKU.product)
        )
        .order_by(models.SalesOrder.order_time.desc())
        .limit(limit)
        .all()
    )


def create_order(db: Session, payload: schemas.OrderCreate) -> models.SalesOrder:
    if not payload.items:
        raise HTTPException(status_code=400, detail="订单明细不能为空")

    store = db.get(models.Store, payload.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")

    member = db.get(models.Member, payload.member_id) if payload.member_id else None
    if payload.member_id and not member:
        raise HTTPException(status_code=404, detail="会员不存在")

    promotion = db.get(models.Promotion, payload.promotion_id) if payload.promotion_id else None
    if payload.promotion_id and not promotion:
        raise HTTPException(status_code=404, detail="促销活动不存在")

    discount_rate = promotion.discount_rate if promotion else 1.0
    order = models.SalesOrder(
        order_no=f"SO{datetime.utcnow():%Y%m%d%H%M%S}{uuid4().hex[:4].upper()}",
        store_id=payload.store_id,
        member_id=payload.member_id,
        promotion_id=payload.promotion_id,
        payment_method=payload.payment_method,
    )
    db.add(order)
    db.flush()

    total_amount = 0.0
    discount_amount = 0.0
    cost_amount = 0.0

    for item in payload.items:
        sku = db.get(models.SKU, item.sku_id)
        if not sku:
            raise HTTPException(status_code=404, detail=f"SKU {item.sku_id} 不存在")

        inventory = (
            db.query(models.Inventory)
            .filter(
                models.Inventory.store_id == payload.store_id,
                models.Inventory.sku_id == item.sku_id,
            )
            .first()
        )
        if not inventory or inventory.quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"SKU {sku.sku_code} 库存不足")

        unit_price = _sku_sale_price(sku)
        unit_cost = _sku_cost_price(sku)
        line_total = unit_price * item.quantity
        line_paid = round(line_total * discount_rate, 2)
        line_discount = round(line_total - line_paid, 2)
        line_cost = round(unit_cost * item.quantity, 2)
        db.add(
            models.SalesOrderItem(
                order_id=order.id,
                sku_id=item.sku_id,
                quantity=item.quantity,
                unit_price=unit_price,
                unit_cost=unit_cost,
                discount_amount=line_discount,
                subtotal=line_paid,
                cost_amount=line_cost,
            )
        )
        inventory.quantity -= item.quantity
        inventory.updated_at = datetime.utcnow()
        total_amount += line_total
        discount_amount += line_discount
        cost_amount += line_cost

    paid_amount = round(total_amount - discount_amount, 2)
    order.total_amount = round(total_amount, 2)
    order.discount_amount = round(discount_amount, 2)
    order.paid_amount = paid_amount

    db.add(
        models.PaymentRecord(
            payment_no=f"PAY{datetime.utcnow():%Y%m%d%H%M%S}{uuid4().hex[:4].upper()}",
            order_id=order.id,
            amount=paid_amount,
            method=payload.payment_method,
        )
    )
    db.add(
        models.FinanceRecord(
            record_no=f"FIN{datetime.utcnow():%Y%m%d%H%M%S}{uuid4().hex[:4].upper()}",
            order_id=order.id,
            store_id=payload.store_id,
            sales_amount=paid_amount,
            cost_amount=round(cost_amount, 2),
            gross_profit=round(paid_amount - cost_amount, 2),
            promotion_loss=round(discount_amount, 2),
        )
    )

    if member:
        member.total_spent = round(member.total_spent + paid_amount, 2)
        member.total_orders += 1
        member.last_purchase_at = order.order_time
        member.points += int(paid_amount)

    db.commit()
    return (
        db.query(models.SalesOrder)
        .options(joinedload(models.SalesOrder.items).joinedload(models.SalesOrderItem.sku))
        .filter(models.SalesOrder.id == order.id)
        .one()
    )


def list_finance_records(db: Session) -> list[dict]:
    records = _finance_record_query(db).all()
    return sorted(
        [_finance_record_view(record) for record in records],
        key=_finance_record_sort_key,
    )


def resolve_finance_record(db: Session, record_id: int) -> dict:
    record = (
        _finance_record_query(db)
        .filter(models.FinanceRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="财务记录不存在")
    can_resolve, reason = _can_resolve_finance_record(record)
    if not can_resolve:
        raise HTTPException(status_code=400, detail=reason)
    record.reconcile_status = "已处理"
    db.commit()
    db.refresh(record)
    return _finance_record_view(record)


def reconcile_finance_record(db: Session, record_id: int) -> dict:
    record = (
        _finance_record_query(db)
        .filter(models.FinanceRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="财务记录不存在")
    can_reconcile, reason = _can_reconcile_finance_record(record)
    if not can_reconcile:
        raise HTTPException(status_code=400, detail=reason)
    _apply_reconciliation(record)
    db.commit()
    db.refresh(record)
    return _finance_record_view(record)


def batch_reconcile_finance_records(db: Session, record_ids: list[int]) -> dict:
    success_count = 0
    failed_items = []
    for record_id in record_ids:
        record = (
            _finance_record_query(db)
            .filter(models.FinanceRecord.id == record_id)
            .first()
        )
        if not record:
            failed_items.append({"id": record_id, "reason": "财务记录不存在"})
            continue
        can_reconcile, reason = _can_reconcile_finance_record(record)
        if not can_reconcile:
            failed_items.append({"id": record_id, "reason": reason})
            continue
        _apply_reconciliation(record)
        success_count += 1
    db.commit()
    return {
        "success_count": success_count,
        "failed_count": len(failed_items),
        "failed_items": failed_items,
    }


def batch_resolve_finance_records(db: Session, record_ids: list[int]) -> dict:
    success_count = 0
    failed_items = []
    for record_id in record_ids:
        record = (
            _finance_record_query(db)
            .filter(models.FinanceRecord.id == record_id)
            .first()
        )
        if not record:
            failed_items.append({"id": record_id, "reason": "财务记录不存在"})
            continue
        can_resolve, reason = _can_resolve_finance_record(record)
        if not can_resolve:
            failed_items.append({"id": record_id, "reason": reason})
            continue
        record.reconcile_status = "已处理"
        success_count += 1
    db.commit()
    return {
        "success_count": success_count,
        "failed_count": len(failed_items),
        "failed_items": failed_items,
    }


def list_payment_records(db: Session) -> list[dict]:
    payments = (
        db.query(models.PaymentRecord)
        .options(
            joinedload(models.PaymentRecord.order).joinedload(models.SalesOrder.store),
        )
        .all()
    )
    return sorted(
        [_payment_view(payment) for payment in payments],
        key=_payment_record_sort_key,
    )


def finance_summary(db: Session) -> dict:
    today = datetime.utcnow().date()
    records = _finance_record_query(db).all()
    today_records = [record for record in records if record.business_date == today]
    gross_profit = sum(_record_gross_profit(record) for record in records)
    sales_amount = sum(record.sales_amount for record in records)
    return {
        "today_order_amount": _round(sum(_order_amount(record) for record in today_records)),
        "today_payment_amount": _round(sum(_payment_amount(record) for record in today_records)),
        "today_difference_amount": _round(sum(_difference_amount(record) for record in today_records)),
        "pending_difference_count": sum(1 for record in records if _can_resolve_finance_record(record)[0]),
        "settled_count": sum(1 for record in records if record.reconcile_status in {"已对账", "已处理", "已平账"}),
        "gross_profit": _round(gross_profit),
        "gross_profit_rate": _rate(gross_profit, sales_amount),
        "promotion_discount_amount": _round(sum(record.promotion_loss for record in records)),
    }


def finance_profit_trend(db: Session) -> dict:
    records = _finance_record_query(db).all()
    today = datetime.utcnow().date()
    trend = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_records = [record for record in records if record.business_date == day]
        trend.append(
            {
                "date": day.strftime("%m-%d"),
                "order_amount": _round(sum(_order_amount(record) for record in day_records)),
                "payment_amount": _round(sum(_payment_amount(record) for record in day_records)),
                "difference_amount": _round(sum(_difference_amount(record) for record in day_records)),
                "sales_amount": _round(sum(record.sales_amount for record in day_records)),
                "cost_amount": _round(sum(_record_cost_amount(record) for record in day_records)),
                "gross_profit": _round(sum(_record_gross_profit(record) for record in day_records)),
            }
        )
    product_rows, category_rows = _profit_breakdown(db)
    return {
        "trend": trend,
        "product_profit_rank": product_rows,
        "category_profit": category_rows,
    }


def finance_promotion_loss(db: Session) -> list[dict]:
    promotions = db.query(models.Promotion).order_by(models.Promotion.id).all()
    rows = []
    for promotion in promotions:
        orders = (
            db.query(models.SalesOrder)
            .options(joinedload(models.SalesOrder.items).joinedload(models.SalesOrderItem.sku))
            .filter(models.SalesOrder.promotion_id == promotion.id)
            .all()
        )
        original_amount = sum(order.total_amount for order in orders)
        discount_amount = sum(order.discount_amount for order in orders)
        paid_amount = sum(order.paid_amount for order in orders)
        cost_amount = sum(_order_cost(order) for order in orders)
        gross_profit = paid_amount - cost_amount
        rows.append(
            {
                "promotion_id": promotion.id,
                "promotion_code": f"PR{promotion.id:05d}",
                "promotion_name": promotion.name,
                "promotion_type": promotion.promotion_type,
                "order_count": len(orders),
                "original_amount": _round(original_amount),
                "discount_amount": _round(discount_amount),
                "paid_amount": _round(paid_amount),
                "cost_amount": _round(cost_amount),
                "gross_profit": _round(gross_profit),
                "gross_profit_rate": _rate(gross_profit, paid_amount),
                "status": promotion.status,
            }
        )
    return rows


def finance_store_settlement(db: Session) -> list[dict]:
    stores = db.query(models.Store).order_by(models.Store.id).all()
    rows = []
    for store in stores:
        records = _finance_record_query(db).filter(models.FinanceRecord.store_id == store.id).all()
        sales_amount = sum(record.sales_amount for record in records)
        cost_amount = sum(_record_cost_amount(record) for record in records)
        gross_profit = sum(_record_gross_profit(record) for record in records)
        order_count = len({record.order_id for record in records})
        difference_amount = sum(_difference_amount(record) for record in records)
        status = "良好"
        if difference_amount > 300:
            status = "异常"
        elif difference_amount > 100:
            status = "需关注"
        elif order_count == 0:
            status = "正常"
        rows.append(
            {
                "store_id": store.id,
                "store_name": store.name,
                "sales_amount": _round(sales_amount),
                "order_count": order_count,
                "average_order_value": _round(sales_amount / order_count if order_count else 0),
                "cost_amount": _round(cost_amount),
                "gross_profit": _round(gross_profit),
                "gross_profit_rate": _rate(gross_profit, sales_amount),
                "promotion_discount_amount": _round(sum(record.promotion_loss for record in records)),
                "difference_amount": _round(difference_amount),
                "settlement_status": status,
            }
        )
    return rows


def _finance_record_query(db: Session):
    return db.query(models.FinanceRecord).options(
        joinedload(models.FinanceRecord.order).joinedload(models.SalesOrder.payment),
        joinedload(models.FinanceRecord.order).joinedload(models.SalesOrder.store),
        joinedload(models.FinanceRecord.order)
        .joinedload(models.SalesOrder.items)
        .joinedload(models.SalesOrderItem.sku)
        .joinedload(models.SKU.product),
        joinedload(models.FinanceRecord.store),
    )


def _finance_record_view(record: models.FinanceRecord) -> dict:
    order = record.order
    payment = order.payment if order else None
    store = record.store or (order.store if order else None)
    return {
        "id": record.id,
        "record_no": record.record_no,
        "order_no": order.order_no if order else "-",
        "store_name": store.name if store else "-",
        "cashier_name": "门店收银员",
        "order_amount": _round(_order_amount(record)),
        "payment_amount": _round(_payment_amount(record)),
        "discount_amount": _round(order.discount_amount if order else record.promotion_loss),
        "difference_amount": _round(_difference_amount(record)),
        "payment_method": payment.method if payment else (order.payment_method if order else "-"),
        "status": record.reconcile_status,
        "reconciliation_time": record.business_date,
    }


def _payment_view(payment: models.PaymentRecord) -> dict:
    order = payment.order
    store = order.store if order else None
    finance_record = order.finance_record if order else None
    return {
        "id": payment.id,
        "payment_no": payment.payment_no,
        "order_no": order.order_no if order else "-",
        "store_name": store.name if store else "-",
        "payment_method": payment.method,
        "payable_amount": _round(order.paid_amount if order else payment.amount),
        "paid_amount": _round(payment.amount),
        "payment_status": payment.status,
        "payment_time": payment.paid_at,
        "third_party_no": f"TP{payment.payment_no}",
        "cashier_name": "门店收银员",
        "finance_record_no": finance_record.record_no if finance_record else "-",
        "difference_amount": _round(_difference_amount(finance_record)) if finance_record else 0,
        "remark": "支付流水与财务记录存在差异" if finance_record and _difference_amount(finance_record) else "支付流水正常",
    }


def _order_amount(record: models.FinanceRecord) -> float:
    return float(record.order.paid_amount if record.order else record.sales_amount)


def _payment_amount(record: models.FinanceRecord) -> float:
    payment = record.order.payment if record.order else None
    return float(payment.amount if payment else record.sales_amount)


def _difference_amount(record: models.FinanceRecord) -> float:
    if not record:
        return 0
    return abs(_order_amount(record) - _payment_amount(record))


def _can_resolve_finance_record(record: models.FinanceRecord) -> tuple[bool, str]:
    status = record.reconcile_status
    difference_amount = _difference_amount(record)
    if status in {"已处理"}:
        return False, "已处理记录不能重复处理"
    if status in {"已关闭"}:
        return False, "已关闭记录不能操作"
    if status in {"已对账", "已平账"}:
        return False, "已平账记录无需处理"
    if status == "待对账":
        return False, "该记录尚未执行对账，请先点击‘执行对账’。"
    if status in {"存在差异", "待处理"}:
        return True, ""
    if difference_amount != 0:
        return True, ""
    return False, "无差异金额，无需处理"


def _can_reconcile_finance_record(record: models.FinanceRecord) -> tuple[bool, str]:
    if record.reconcile_status != "待对账":
        if record.reconcile_status in {"已对账", "已平账"}:
            return False, "该记录已平账，无需重复对账"
        if record.reconcile_status == "已处理":
            return False, "已处理记录不能重复对账"
        if record.reconcile_status == "已关闭":
            return False, "已关闭记录不能操作"
        return False, "只有待对账记录可以执行对账"
    if not record.order or not record.order.payment:
        return False, "缺少支付流水，暂无法完成对账。"
    return True, ""


def _apply_reconciliation(record: models.FinanceRecord) -> None:
    difference_amount = _difference_amount(record)
    record.reconcile_status = "已平账" if difference_amount == 0 else "存在差异"


def _finance_status_priority(status: str) -> int:
    priority = {
        "存在差异": 1,
        "待处理": 2,
        "待对账": 3,
        "已处理": 4,
        "已对账": 5,
        "已平账": 5,
        "已关闭": 6,
    }
    return priority.get(status, 7)


def _finance_record_sort_key(record: dict) -> tuple:
    return (
        _finance_status_priority(record.get("status", "")),
        -_timestamp(record.get("reconciliation_time")),
        -_number_suffix(record.get("record_no", "")),
        -int(record.get("id", 0)),
    )


def _payment_status_priority(status: str) -> int:
    priority = {
        "失败": 1,
        "待确认": 2,
        "已退款": 3,
        "成功": 4,
    }
    return priority.get(status, 5)


def _payment_record_sort_key(payment: dict) -> tuple:
    return (
        _payment_status_priority(payment.get("payment_status", "")),
        -_timestamp(payment.get("payment_time")),
        -_number_suffix(payment.get("payment_no", "")),
        -int(payment.get("id", 0)),
    )


def _timestamp(value) -> float:
    if not value:
        return 0
    if isinstance(value, datetime):
        return value.timestamp()
    if hasattr(value, "isoformat"):
        return datetime.fromisoformat(value.isoformat()).timestamp()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def _number_suffix(value: str) -> int:
    digits = "".join(char for char in str(value) if char.isdigit())
    return int(digits or 0)


def _order_cost(order: models.SalesOrder) -> float:
    return sum(_order_item_cost(item) for item in order.items)


def _profit_breakdown(db: Session) -> tuple[list[dict], list[dict]]:
    items = (
        db.query(models.SalesOrderItem)
        .options(
            joinedload(models.SalesOrderItem.order),
            joinedload(models.SalesOrderItem.sku).joinedload(models.SKU.product),
        )
        .all()
    )
    product_map: dict[str, dict] = {}
    category_map: dict[str, dict] = {}
    for item in items:
        sku = item.sku
        product = sku.product if sku else None
        product_name = product.name if product else "未知商品"
        sku_code = sku.sku_code if sku else "-"
        category = product.category if product else "未分类"
        sales_amount = float(item.subtotal)
        cost_amount = float(_order_item_cost(item))
        product_key = f"{product_name}-{sku_code}"
        product_row = product_map.setdefault(
            product_key,
            {
                "product_name": product_name,
                "sku_code": sku_code,
                "sales_quantity": 0,
                "sales_amount": 0.0,
                "cost_amount": 0.0,
            },
        )
        product_row["sales_quantity"] += item.quantity
        product_row["sales_amount"] += sales_amount
        product_row["cost_amount"] += cost_amount
        category_row = category_map.setdefault(category, {"category": category, "sales_amount": 0.0, "cost_amount": 0.0})
        category_row["sales_amount"] += sales_amount
        category_row["cost_amount"] += cost_amount
    product_rows = []
    for index, row in enumerate(sorted(product_map.values(), key=lambda item: item["sales_amount"], reverse=True), start=1):
        gross_profit = row["sales_amount"] - row["cost_amount"]
        product_rows.append(
            {
                "rank": index,
                **row,
                "sales_amount": _round(row["sales_amount"]),
                "cost_amount": _round(row["cost_amount"]),
                "gross_profit": _round(gross_profit),
                "gross_profit_rate": _rate(gross_profit, row["sales_amount"]),
            }
        )
    category_rows = []
    for row in sorted(category_map.values(), key=lambda item: item["sales_amount"], reverse=True):
        gross_profit = row["sales_amount"] - row["cost_amount"]
        category_rows.append(
            {
                **row,
                "sales_amount": _round(row["sales_amount"]),
                "cost_amount": _round(row["cost_amount"]),
                "gross_profit": _round(gross_profit),
                "gross_profit_rate": _rate(gross_profit, row["sales_amount"]),
            }
        )
    return product_rows[:10], category_rows


def _round(value: float) -> float:
    return round(float(value or 0), 2)


def _rate(numerator: float, denominator: float) -> float:
    return round((float(numerator or 0) / float(denominator or 1)) * 100, 2) if denominator else 0


def _sku_sale_price(sku: models.SKU | None) -> float:
    if not sku:
        return 0
    if sku.list_price is not None and sku.list_price > 0:
        return float(sku.list_price)
    product = sku.product
    if product and product.sale_price is not None and product.sale_price > 0:
        return float(product.sale_price)
    return 0


def _sku_cost_price(sku: models.SKU | None) -> float:
    if not sku:
        return 0
    if sku.cost_price is not None and sku.cost_price > 0:
        return float(sku.cost_price)
    product = sku.product
    if product and product.cost_price is not None and product.cost_price > 0:
        return float(product.cost_price)
    return 0


def _order_item_cost(item: models.SalesOrderItem) -> float:
    if item.cost_amount is not None and item.cost_amount > 0:
        return float(item.cost_amount)
    if item.unit_cost is not None and item.unit_cost > 0:
        return float(item.unit_cost) * item.quantity
    return _sku_cost_price(item.sku) * item.quantity


def _record_cost_amount(record: models.FinanceRecord) -> float:
    if record.order and record.order.items:
        return _order_cost(record.order)
    return float(record.cost_amount or 0)


def _record_gross_profit(record: models.FinanceRecord) -> float:
    return _order_amount(record) - _record_cost_amount(record)
