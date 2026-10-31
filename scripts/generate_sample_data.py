"""Regenerate public, entirely fictional sample transactions."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sample_transactions.csv"

MERCHANTS = {
    "餐饮": ["橙树食堂", "禾风小馆", "青柠咖啡", "日光面馆"],
    "交通": ["城市交通", "蓝线地铁", "晴空巴士", "绿道单车"],
    "购物": ["简集商店", "拾光杂货", "云朵文具", "方圆超市"],
    "学习": ["向上书屋", "纸飞机书店", "星河课程", "新知文具"],
    "娱乐": ["周末影院", "山谷展览", "悠游桌游", "乐声剧场"],
    "礼物": ["小礼物店", "花与纸", "春天手作", "暖心礼盒"],
}
AMOUNTS = {
    "2026-08": {
        "餐饮": ["42.00", "58.00", "73.00", "61.00"],
        "交通": ["18.00", "26.00", "31.00", "24.00"],
        "购物": ["109.00", "75.00", "95.00", "160.00"],
        "学习": ["39.00", "89.00", "40.00", "99.00"],
        "娱乐": ["65.00", "48.00", "76.00", "90.00"],
        "礼物": ["120.00", "80.00", "55.00", "99.00"],
    },
    "2026-09": {
        "餐饮": ["49.00", "72.00", "65.00", "56.00"],
        "交通": ["22.00", "34.00", "28.00", "45.00"],
        "购物": ["88.00", "139.00", "79.00", "159.00"],
        "学习": ["66.00", "99.00", "25.00", "68.00"],
        "娱乐": ["70.00", "110.00", "65.00", "85.00"],
        "礼物": ["150.00", "79.00", "45.00", "140.00"],
    },
    "2026-10": {
        "餐饮": ["45.50", "68.00", "87.50", "79.00"],
        "交通": ["15.00", "29.00", "42.00", "38.00"],
        "购物": ["119.00", "88.00", "235.00", "56.00"],
        "学习": ["79.00", "128.00", "45.00", "28.00"],
        "娱乐": ["88.00", "45.00", "60.00", "120.00"],
        "礼物": ["149.00", "59.00", "89.00", "260.00"],
    },
}

OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["transaction_id", "date", "merchant", "amount", "category"])
    number = 1
    for month, categories in AMOUNTS.items():
        for category_index, (category, amounts) in enumerate(categories.items()):
            for item_index, amount in enumerate(amounts):
                day = [2, 8, 16, 25][item_index] + category_index
                writer.writerow([
                    f"T{number:03d}",
                    f"{month}-{day:02d}",
                    MERCHANTS[category][item_index],
                    amount,
                    category,
                ])
                number += 1
print(f"Wrote {number - 1} fictional transactions to {OUT}")
