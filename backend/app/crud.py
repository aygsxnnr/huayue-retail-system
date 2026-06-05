from datetime import datetime, timedelta
from uuid import uuid4
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
    list_price = payload.list_price or payload.sale_price or payload.price
    if not list_price:
        raise HTTPException(status_code=400, detail="销售价不能为空")
    sku = models.SKU(
        sku_code=sku_code,
        product_id=payload.product_id,
        color=payload.color,
        size=payload.size,
        barcode=barcode,
        list_price=list_price,
        cost_price=round(list_price * 0.55, 2),
        status=payload.status,
    )
    db.add(sku)
    db.commit()
    db.refresh(sku)
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
            "cost_price": item.sku.cost_price,
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


def create_coupon(db: Session, payload: schemas.CouponCreate) -> models.Coupon:
    existing = db.query(models.Coupon).filter(models.Coupon.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="优惠券编号已存在")
    coupon = models.Coupon(**payload.model_dump())
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
    _recalculate_member_tags(db, commit=True)
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
    levels = ["普通会员", "银卡会员", "金卡会员", "黑金会员"]
    level_distribution = [
        {
            "level": level,
            "count": db.query(models.Member).filter(models.Member.level == level).count(),
        }
        for level in levels
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
        "marketing_effects": marketing_effects,
    }


def _sync_member_metrics(db: Session) -> None:
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

        line_total = sku.list_price * item.quantity
        line_paid = round(line_total * discount_rate, 2)
        line_discount = round(line_total - line_paid, 2)
        db.add(
            models.SalesOrderItem(
                order_id=order.id,
                sku_id=item.sku_id,
                quantity=item.quantity,
                unit_price=sku.list_price,
                discount_amount=line_discount,
                subtotal=line_paid,
            )
        )
        inventory.quantity -= item.quantity
        inventory.updated_at = datetime.utcnow()
        total_amount += line_total
        discount_amount += line_discount
        cost_amount += sku.cost_price * item.quantity

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


def list_finance_records(db: Session) -> list[models.FinanceRecord]:
    return db.query(models.FinanceRecord).order_by(models.FinanceRecord.business_date.desc()).all()


def finance_summary(db: Session) -> dict:
    row = db.query(
        func.coalesce(func.sum(models.FinanceRecord.sales_amount), 0),
        func.coalesce(func.sum(models.FinanceRecord.cost_amount), 0),
        func.coalesce(func.sum(models.FinanceRecord.gross_profit), 0),
        func.coalesce(func.sum(models.FinanceRecord.promotion_loss), 0),
    ).one()
    return {
        "销售额": round(row[0], 2),
        "成本": round(row[1], 2),
        "毛利": round(row[2], 2),
        "促销让利": round(row[3], 2),
    }
