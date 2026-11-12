# -*- coding: utf-8 -*-
"""Sinh data/eval/tts_cases.json. Expected viet TAY (doc lap voi code), roi kiem tra ham tham chieu khop het."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tts_preprocess import tts_normalize

CASES = [
    ("price", "Phin Sữa Đá giá 39.000đ", "Phin Sữa Đá giá 39k"),
    ("price+size", "Trà Đào Cam Sả size M giá 55.000đ ạ", "Trà Đào Cam Sả size mờ giá 55k ạ"),
    ("price+size", "Size S 49.000₫, size L 65.000₫", "Size sờ 49k, size lờ 65k"),
    ("vat", "Giá đã bao gồm VAT", "Giá đã bao gồm thuế"),
    ("vat+percent", "Giá chưa gồm VAT 8%", "Giá chưa gồm thuế 8 phần trăm"),
    ("price", "Combo Nhóm 4 Người 199.000 VNĐ", "Combo Nhóm 4 Người 199k"),
    ("price", "Bánh Brownie 35.000đ", "Bánh Brownie 35k"),
    ("price", "Nước Suối 15.000đ", "Nước Suối 15k"),
    ("size_paren", "Phin Đen Đá (S) 29.000đ", "Phin Đen Đá (sờ) 29k"),
    ("size_paren", "Latte (M) 55.000đ, (L) 65.000đ", "Latte (mờ) 55k, (lờ) 65k"),
    ("unit_ml", "Size M 470ml", "Size mờ 470 mi li lít"),
    ("unit_ml", "Ly 360ml, 470ml và 700ml", "Ly 360 mi li lít, 470 mi li lít và 700 mi li lít"),
    ("time", "Quán mở cửa 07:00 đến 22:00", "Quán mở cửa 7 giờ đến 22 giờ"),
    ("time", "Đóng cửa lúc 22:30", "Đóng cửa lúc 22 giờ 30"),
    ("untouched", "Hotline 1900 1234", "Hotline 1900 1234"),
    ("price", "Đơn từ 100.000đ được miễn phí giao hàng", "Đơn từ 100k được miễn phí giao hàng"),
    ("price", "Phí giao hàng 15.000đ", "Phí giao hàng 15k"),
    ("price", "Giá từ 250.000đ", "Giá từ 250k"),
    ("price_million", "Tổng cộng 1.250.000đ", "Tổng cộng 1 triệu 250"),
    ("price_million", "Hóa đơn 2.000.000đ", "Hóa đơn 2 triệu"),
    ("price_half", "Giá 49.500đ", "Giá 49k rưỡi"),
    ("price_odd", "Tổng 12.345đ", "Tổng 12.345 đồng"),
    ("percent", "Giảm 10% đồ uống", "Giảm 10 phần trăm đồ uống"),
    ("percent", "Giảm 20% bánh ngọt", "Giảm 20 phần trăm bánh ngọt"),
    ("markdown", "**Phin Sữa Đá** - 39.000đ", "Phin Sữa Đá - 39k"),
    ("markdown_list", "- Trà Vải 49.000đ\n- Trà Dâu 49.000đ", "Trà Vải 49k. Trà Dâu 49k"),
    ("ampersand", "Cookies & Cream Freeze 59.000đ", "Cookies và Cream Freeze 59k"),
    ("size_all", "Size S/M/L", "Size sờ, mờ hoặc lờ"),
    ("size", "Cho anh 2 ly size L nhé", "Cho anh 2 ly size lờ nhé"),
    ("mixed", "Combo Sáng 69.000đ, giảm 10% từ 07:00 đến 09:00", "Combo Sáng 69k, giảm 10 phần trăm từ 7 giờ đến 9 giờ"),
    ("vat+time", "Xuất hóa đơn VAT trước 22:00", "Xuất hóa đơn thuế trước 22 giờ"),
    ("price", "Cà phê 1 shot 12.000đ", "Cà phê 1 shot 12k"),
    ("size_paren", "Latte (S) 49.000đ", "Latte (sờ) 49k"),
    ("price_space", "Tiramisu 45.000 đ", "Tiramisu 45k"),
    ("price_nodot", "Giá 45000đ", "Giá 45k"),
    ("price_comma", "Giá 45,000 VND", "Giá 45k"),
    ("price+size_en", "Price: 59.000 VND (size M)", "Price: 59k (size mờ)"),
    ("untouched", "Mua 2 tặng 1, size M", "Mua 2 tặng 1, size mờ"),
    ("untouched", "Wifi: Highlands_Free", "Wifi: Highlands_Free"),
    ("untouched", "Hạn dùng 12 tháng", "Hạn dùng 12 tháng"),
    ("untouched_size", "Size XL không có trong menu", "Size XL không có trong menu"),
    ("false_positive", "Bánh Mì Thịt Nướng 39.000đ", "Bánh Mì Thịt Nướng 39k"),
    ("false_positive", "Matcha Latte M tặng kèm", "Matcha Latte M tặng kèm"),
    ("kcal", "Món này khoảng 250kcal", "Món này khoảng 250 ki lô ca"),
]

out = []
bad = 0
for i, (tag, inp, exp) in enumerate(CASES, 1):
    got = tts_normalize(inp)
    if got != exp:
        bad += 1
        print("MISMATCH #%d [%s]\n  in : %r\n  exp: %r\n  got: %r" % (i, tag, inp, exp, got))
    out.append(dict(id="T%02d" % i, tag=tag, input=inp, expected=exp))
p = os.path.join(os.path.dirname(__file__), "..", "data", "eval", "tts_cases.json")
json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("tts cases=%d mismatches=%d" % (len(out), bad))
sys.exit(1 if bad else 0)
