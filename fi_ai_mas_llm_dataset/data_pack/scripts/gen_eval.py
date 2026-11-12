# -*- coding: utf-8 -*-
"""Sinh data/eval/rag_eval_20.json: 20 cau hoi test co ground truth, dap an tinh tu du lieu that."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa

D = os.path.join(os.path.dirname(__file__), "..", "data")
faq = list(csv.DictReader(open(os.path.join(D, "kb", "faq.csv"), encoding="utf-8-sig")))
manifest = json.load(open(os.path.join(D, "kb", "docs", "doc_sections_manifest.json"), encoding="utf-8"))
SEC = {m["section_id"]: m for m in manifest}


def faq_ids(topic):
    return [r["faq_id"] for r in faq if r["topic_id"] == topic]


def sec(prefix, heading_part):
    hits = [m["section_id"] for m in manifest if m["doc_id"] == prefix and heading_part in m["heading"]]
    assert len(hits) == 1, (prefix, heading_part, hits)
    return hits[0]


M = MENU_BY_VI
items = []


def add(qid, lang, q, typ, ans, kws, menu=(), topics=(), docs=(), expand=False, forbid=(), note=""):
    items.append(dict(
        id=qid, language=lang, question=q, type=typ, expected_answer=ans, answer_keywords=list(kws),
        gold_menu_ids=list(menu), gold_faq_topics=list(topics),
        gold_faq_ids=[i for t in topics for i in faq_ids(t)], gold_doc_sections=list(docs),
        needs_graph_expansion=expand, forbidden_keywords=list(forbid), answerable=True, note=note))


# ---- MENU (6)
m = M["Phin Đen Đá"]
add("Q01", "vi", "Phin Đen Đá giá bao nhiêu và có caffeine không?", "menu",
    "Phin Đen Đá size M giá %s, có caffeine." % fmt_vnd(m["price_m"]), [fmt_vnd(m["price_m"]), "caffeine"], menu=[m["item_id"]])
nv = [x for x in MENU if x["kind"] == "drink" and x["caffeine"] == "không" and x["vegan"] == "có"]
add("Q02", "vi", "Quán có đồ uống nào không có caffeine và thuần chay?", "menu",
    "Các đồ uống không caffeine và thuần chay: " + ", ".join(x["name_vi"] for x in nv) + ".",
    [x["name_vi"] for x in nv[:3]], menu=[x["item_id"] for x in nv], note="Nhieu dap an dung; precision@5 tinh theo gold_menu_ids.")
m = M["Trà Đào Cam Sả"]
add("Q03", "en", "How much is the Peach Orange Lemongrass Tea in size L?", "menu",
    "The Peach Orange Lemongrass Tea in size L costs %s VND." % "{:,}".format(m["price_l"]), ["{:,}".format(m["price_l"]), "65"], menu=[m["item_id"]])
m = M["Combo Nhóm 4 Người"]
add("Q04", "vi", "Combo nào dành cho nhóm 4 người và giá bao nhiêu?", "menu",
    "Combo Nhóm 4 Người gồm %s, giá %s." % (m["ingredients"], fmt_vnd(m["price_m"])), ["Combo Nhóm 4 Người", fmt_vnd(m["price_m"])], menu=[m["item_id"]])
nuts = [x for x in MENU if x["category"] == "Bánh ngọt" and "hạt" in x["allergens"]]
add("Q05", "en", "Which cakes and pastries contain nuts?", "menu",
    "Items containing nuts: " + ", ".join(x["name_en"] for x in nuts) + ".", [x["name_en"] for x in nuts], menu=[x["item_id"] for x in nuts])
m = M["Bạc Xỉu"]
add("Q06", "vi", "Bạc Xỉu có sữa không và uống nóng được không?", "menu",
    "Bạc Xỉu có sữa (sữa tươi, sữa đặc) và có thể uống nóng hoặc lạnh.", ["sữa", "nóng"], menu=[m["item_id"]])
# ---- FAQ (5)
add("Q07", "vi", "Mật khẩu wifi của quán là gì?", "faq", "Mật khẩu wifi là %s (mạng %s)." % (F["wifi_pw"], F["wifi_ssid"]),
    [F["wifi_pw"]], topics=["wifi"])
add("Q08", "en", "How many people do I need for a birthday party and how early should I book?", "faq",
    "Birthday parties need at least %d people and should be booked %d day ahead." % (F["birthday_min_people"], F["birthday_days_ahead"]),
    [str(F["birthday_min_people"]), "1 day"], topics=["birthday_party"])
pts = 250000 // F["point_per"]
add("Q09", "vi", "Nếu tôi chi 250.000đ thì được bao nhiêu điểm thành viên?", "faq_calc",
    "Mỗi %s được 1 điểm nên 250.000đ được %d điểm." % (fmt_vnd(F["point_per"]), pts), [str(pts)], topics=["loyalty_earn"],
    note="Can suy luan so hoc tu cau tra loi FAQ.")
add("Q10", "en", "Is delivery free for a 120,000 VND order within 2 km?", "faq_calc",
    "Yes. Orders of 100,000 VND or more within 3 km get free delivery.", ["free"], topics=["delivery_fee"],
    note="120k >= 100k va 2km <= 3km.")
hn = [b for b in BRANCHES if b["city"] == "Hà Nội" and "workspace" in b["features"]]
add("Q11", "vi", "Chi nhánh nào ở Hà Nội có khu làm việc yên tĩnh?", "faq_branch",
    "Tại Hà Nội, khu làm việc yên tĩnh có ở chi nhánh " + ", ".join(b["short"] for b in hn) + ".", [b["short"] for b in hn],
    topics=["quiet_space"], docs=[sec("branch", "Chi nhánh Cầu Giấy")])
# ---- DOC (5)
add("Q12", "vi", "Nếu nước pha sai thì quán làm lại trong bao lâu?", "doc",
    "Quán làm lại món mới trong vòng %d phút kể từ khi khách nhận món." % F["remake_minutes"], [str(F["remake_minutes"]), "phút"],
    topics=["refund"], docs=[sec("policy", "làm lại món")])
add("Q13", "vi", "Điểm thưởng HL Rewards hết hạn sau bao lâu?", "doc", "Điểm có hạn sử dụng 12 tháng kể từ ngày phát sinh.", ["12 tháng"],
    docs=[sec("policy", "đổi điểm")], note="Chi co trong tai lieu, KHONG co trong FAQ.")
add("Q14", "en", "How long should a hot drink take to prepare?", "doc", "Hot drinks must be ready within 4 minutes of taking the order.", ["4 minutes"],
    docs=[sec("sop", "Thời gian chuẩn bị")], note="Tai lieu tieng Viet, cau hoi tieng Anh (cross-lingual).")
add("Q15", "vi", "Chương trình Thứ Tư có ưu đãi gì?", "doc", "Thứ Tư Nhân Đôi Điểm: thành viên HL Rewards nhận gấp đôi điểm thưởng cho mọi đơn hàng.",
    ["gấp đôi", "điểm"], docs=[sec("promo", "Thứ Tư Nhân Đôi Điểm")], topics=["promotions"])
add("Q16", "vi", "Khiếu nại về an toàn thực phẩm được liên hệ lại trong bao lâu?", "doc",
    "Quản lý phải liên hệ lại với khách trong vòng 2 giờ.", ["2 giờ"], docs=[sec("policy", "góp ý và khiếu nại")], note="Chi co trong tai lieu.")
# ---- Graph expansion (2): dap an nam o chunk ke nhau
add("Q17", "vi", "Hạng Vàng cần bao nhiêu điểm và điểm thưởng đổi được gì?", "multi_chunk",
    "Hạng Vàng cần từ 500 điểm tích lũy trong năm. 100 điểm đổi được 1 đồ uống size M bất kỳ.", ["500", "100 điểm"],
    docs=[sec("policy", "Chương trình thành viên"), sec("policy", "đổi điểm")], expand=True,
    note="Hai section ke nhau (NEXT) - vector search thuan thuong chi lay duoc 1.")
hn_car = [b for b in BRANCHES if b["city"] == "Hà Nội" and "car_park" in b["features"]]
add("Q18", "en", "Which Hanoi branches have car parking and when do they open?", "multi_chunk",
    "Hanoi branches with car parking: " + "; ".join("%s opens %s to %s" % (b["short"], b["open"], b["close"]) for b in hn_car) + ".",
    [b["short"] for b in hn_car] + [b["open"] for b in hn_car],
    docs=[sec("branch", "Chi nhánh " + b["short"]) for b in hn_car], topics=["parking"], expand=True,
    note="Hai chunk chi nhanh ke nhau.")
# ---- Unanswerable (2) - kiem tra zero hallucination
items.append(dict(id="Q19", language="vi", question="Quán có bán phở bò không và giá bao nhiêu?", type="unanswerable",
                  expected_answer="Menu không có phở. Mình chỉ có đồ uống, bánh và một số món mặn như bánh mì, mì Ý, salad, cơm gà.",
                  answer_keywords=["không có"], gold_menu_ids=[], gold_faq_topics=[], gold_faq_ids=[], gold_doc_sections=[],
                  needs_graph_expansion=False, forbidden_keywords=["phở bò giá", "50.000đ", "60.000đ", "70.000đ"], answerable=False,
                  note="Phai tu choi / noi khong co thong tin, khong duoc bia gia."))
items.append(dict(id="Q20", language="en", question="How many calories are in a Latte?", type="unanswerable",
                  expected_answer="The menu does not include calorie information for the Latte.",
                  answer_keywords=["not"], gold_menu_ids=[], gold_faq_topics=[], gold_faq_ids=[], gold_doc_sections=[],
                  needs_graph_expansion=False, forbidden_keywords=["kcal", "calories per", "150 calories", "190 calories"], answerable=False,
                  note="Menu/FAQ khong co du lieu calo. Khong duoc bia con so."))

assert len(items) == 20
json.dump(items, open(os.path.join(D, "eval", "rag_eval_20.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("rag_eval_20 =", len(items), "| types:", {t: sum(i["type"] == t for i in items) for t in sorted({i["type"] for i in items})})
for i in items[:2] + items[10:11] + items[16:18]:
    print(i["id"], i["question"], "->", i["expected_answer"][:110], i["gold_doc_sections"])
