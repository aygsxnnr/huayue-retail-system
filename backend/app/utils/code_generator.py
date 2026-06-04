from __future__ import annotations

from dataclasses import dataclass
import re


CATEGORY_PREFIXES = {
    "上衣": "TO",
    "top": "TO",
    "t恤": "TO",
    "衬衫": "TO",
    "针织": "TO",
    "卫衣": "TO",
    "连衣裙": "DR",
    "dress": "DR",
    "裤": "PA",
    "pants": "PA",
    "半裙": "SK",
    "裙": "SK",
    "外套": "CO",
    "coat": "CO",
    "夹克": "CO",
    "鞋": "SH",
    "shoes": "SH",
    "靴": "SH",
    "配饰": "AC",
    "饰": "AC",
    "包": "AC",
}

LETTER_SIZE_CODES = {
    "XXXXS": "01",
    "XXXS": "02",
    "XXS": "03",
    "XS": "04",
    "S": "05",
    "M": "06",
    "L": "07",
    "XL": "08",
    "XXL": "09",
    "XXXL": "10",
    "XXXXL": "11",
}


@dataclass(frozen=True)
class ColorMatch:
    main_color_code: str
    sub_color_code: str
    note: str


@dataclass(frozen=True)
class SizeMatch:
    size_code: str
    note: str


@dataclass(frozen=True)
class SKUCodeParts:
    product_code: str
    main_color_code: str
    sub_color_code: str
    size_code: str
    is_valid: bool


SKU_CODE_PATTERN = re.compile(r"^[A-Z]{2}\d{5}[A-Z]{2}[0-9A-Z]{2}[0-9A-Z]{2}$")
PRODUCT_CODE_PATTERN = re.compile(r"^[A-Z]{2}\d{5}$")


def normalize_text(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "")


def category_prefix(category: str | None, name: str | None = None) -> str:
    name_text = normalize_text(name)
    if any(word in name_text for word in ["鞋", "靴", "乐福"]):
        return "SH"
    if any(word in name_text for word in ["包", "项链", "围巾", "饰"]):
        return "AC"
    text = normalize_text(f"{category or ''}{name or ''}")
    for keyword, prefix in CATEGORY_PREFIXES.items():
        if keyword.lower() in text:
            return prefix
    return "TO"


def next_product_code(category: str | None, name: str | None, existing_codes: list[str]) -> str:
    prefix = category_prefix(category, name)
    max_no = 10000
    for code in existing_codes:
        if code.startswith(prefix) and len(code) >= 7 and code[2:7].isdigit():
            max_no = max(max_no, int(code[2:7]))
    return f"{prefix}{max_no + 1:05d}"


def is_valid_product_code(code: str | None) -> bool:
    return PRODUCT_CODE_PATTERN.fullmatch((code or "").strip().upper()) is not None


def match_color(color_text: str | None) -> ColorMatch:
    text = normalize_text(color_text)
    if not text:
        return ColorMatch("CU", "C1", "未输入颜色，已按定制色处理")

    if any(word in text for word in ["多色", "彩虹", "拼接"]):
        sub = "10" if "撞色" in text else "09"
        return ColorMatch("MC", sub, f"{color_text}已匹配为多色/拼接色{sub}")
    if any(word in text for word in ["撞色", "撞款"]):
        return ColorMatch("MC", "10", f"{color_text}已匹配为多色-撞色")

    main_rules: list[tuple[str, list[str]]] = [
        ("BK", ["黑", "雅黑", "炭黑"]),
        ("WH", ["白", "米白", "象牙白", "奶油白", "珍珠白"]),
        ("GY", ["灰", "银灰", "炭灰"]),
        ("BE", ["米", "卡其", "奶茶", "燕麦", "杏"]),
        ("RD", ["红", "酒红", "砖红"]),
        ("PK", ["粉", "桃", "玫"]),
        ("OR", ["橙", "橘"]),
        ("YE", ["黄", "柠檬"]),
        ("GN", ["绿", "墨绿", "牛油果", "橄榄"]),
        ("BL", ["蓝", "藏蓝", "雾霾蓝", "牛仔蓝"]),
        ("PU", ["紫", "鸢尾", "薰衣草"]),
        ("BN", ["棕", "咖", "驼", "褐"]),
        ("GD", ["金"]),
        ("SV", ["银"]),
    ]
    main = "CU"
    for code, words in main_rules:
        if any(word in text for word in words):
            main = code
            break

    if main == "CU" or any(word in text for word in ["定制", "设计师", "小众", "特殊"]):
        return ColorMatch("CU", "C2" if "设计师" in text else "C1", f"{color_text}无法标准归类，已按定制色处理")

    sub = "00"
    if any(word in text for word in ["浅", "米白", "象牙", "奶油", "雾霾", "低饱和", "莫兰迪"]):
        sub = "01" if "低饱和" not in text and "莫兰迪" not in text else "12"
    if any(word in text for word in ["深", "藏", "炭", "墨"]):
        sub = "02"
    if "条纹" in text:
        sub = "03"
    if "格纹" in text:
        sub = "04"
    if "印花" in text:
        sub = "05"
    if "渐变" in text:
        sub = "06"
    if "牛仔" in text:
        sub = "07"
    if any(word in text for word in ["金属", "光泽"]):
        sub = "08"
    if "拼接" in text:
        sub = "09"
    if "撞色" in text:
        sub = "10"
    if any(word in text for word in ["花色", "碎花"]):
        sub = "11"

    return ColorMatch(main, sub, f"{color_text}已匹配为{main}-{sub}")


def match_size(category: str | None, size_text: str | None) -> SizeMatch:
    raw = (size_text or "").strip()
    text = normalize_text(raw).upper().replace("码", "")
    if text in ["均码", "ONESIZE", "ONE-SIZE", "OS", "F", "FREE"]:
        return SizeMatch("OS", f"{raw}已匹配为均码OS")
    if text in LETTER_SIZE_CODES:
        return SizeMatch(LETTER_SIZE_CODES[text], f"{raw}已匹配为服装标准尺码{LETTER_SIZE_CODES[text]}")

    category_text = normalize_text(category)
    if re.fullmatch(r"\d{2}", text):
        number = int(text)
        if ("裤" in category_text and 24 <= number <= 36) or ("鞋" in category_text and 35 <= number <= 45):
            return SizeMatch(text, f"{raw}已匹配为{'鞋类' if '鞋' in category_text else '裤装'}数字尺码{text}")
        if 24 <= number <= 45:
            return SizeMatch(text, f"{raw}已匹配为数字尺码{text}")

    half_match = re.fullmatch(r"(\d{2})\.5", text)
    if half_match and "鞋" in category_text:
        number = int(half_match.group(1))
        if 35 <= number <= 45:
            return SizeMatch(f"{number % 10}H", f"{raw}已匹配为鞋类半码{number % 10}H")

    return SizeMatch("OT", f"{raw or '空尺码'}无法识别，尺码已按特殊尺码处理")


def ean13_check_digit(first_12_digits: str) -> str:
    digits = [int(char) for char in first_12_digits]
    odd_sum = sum(digits[0::2])
    even_sum = sum(digits[1::2])
    return str((10 - ((odd_sum + even_sum * 3) % 10)) % 10)


def make_ean13(serial: int) -> str:
    first_12 = f"69{serial:010d}"[-12:]
    if not first_12.startswith("69"):
        first_12 = f"69{serial % 10_000_000_000:010d}"
    return first_12 + ean13_check_digit(first_12)


def next_barcode(existing_barcodes: list[str]) -> str:
    serial = 1000
    for barcode in existing_barcodes:
        if re.fullmatch(r"69\d{11}", barcode or ""):
            serial = max(serial, int(barcode[2:12]))
    return make_ean13(serial + 1)


def build_sku_code(product_code: str, color: ColorMatch, size: SizeMatch) -> str:
    return f"{product_code}{color.main_color_code}{color.sub_color_code}{size.size_code}"


def parse_sku_code(sku_code: str | None) -> SKUCodeParts:
    code = (sku_code or "").strip().upper()
    if not SKU_CODE_PATTERN.fullmatch(code):
        return SKUCodeParts("", "", "", "", False)
    return SKUCodeParts(
        product_code=code[:7],
        main_color_code=code[7:9],
        sub_color_code=code[9:11],
        size_code=code[11:13],
        is_valid=True,
    )
