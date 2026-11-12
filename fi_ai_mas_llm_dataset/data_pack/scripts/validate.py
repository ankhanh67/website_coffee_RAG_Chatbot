# -*- coding: utf-8 -*-
"""Kiem tra toan bo bo du lieu: dem, can bang, trung lap, ro ri train/test, nhat quan cheo giua cac file."""
import csv
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from tts_preprocess import tts_normalize

D = os.path.join(os.path.dirname(__file__), "..", "data")
ok, fail = [], []


def check(name, cond, detail=""):
    (ok if cond else fail).append(name)
    print("%s  %s %s" % ("PASS" if cond else "FAIL", name, ("- " + str(detail)) if detail else ""))


def J(*p):
    return json.load(open(os.path.join(D, *p), encoding="utf-8"))


# ---------------- Router
tr, te = J("router", "router_train.json"), J("router", "router_test.json")
check("router: train 4000 mau", len(tr) == 4000, len(tr))
check("router: test 400 mau", len(te) == 400, len(te))
for nm, ds in (("train", tr), ("test", te)):
    c = Counter(x["intent"] for x in ds)
    check("router %s: can bang 4 intent" % nm, len(set(c.values())) == 1 and len(c) == 4, dict(c))
    check("router %s: label khop intent" % nm, all(["order", "consultant", "faq", "ignore"][x["label"]] == x["intent"] for x in ds))
    check("router %s: is_noise <=> ignore" % nm, all(x["is_noise"] == (x["intent"] == "ignore") for x in ds))
    check("router %s: co du truong" % nm, all({"text", "label", "intent", "is_noise", "language"} <= set(x) for x in ds))
hr = sum(x["is_hard"] for x in tr) / len(tr)
check("router train: hard samples 5-20%", .05 <= hr <= .20, "%.1f%%" % (hr * 100))
allnorm = [norm_text(x["text"]) for x in tr + te]
check("router: khong trung lap (train+test)", len(set(allnorm)) == len(allnorm), "%d trung" % (len(allnorm) - len(set(allnorm))))
langs = Counter(x["language"] for x in tr + te)
check("router: >= 2 ngon ngu (vi, en)", langs["vi"] > 0 and langs["en"] > 0, dict(langs))
sft = [json.loads(l) for l in open(os.path.join(D, "router", "router_train_sft.jsonl"), encoding="utf-8")]
check("router sft: assistant la JSON {action}", all(set(json.loads(s["messages"][2]["content"])) == {"action"} for s in sft), len(sft))
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    v = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)
    X = v.fit_transform([x["text"] for x in tr])
    m = LogisticRegression(max_iter=2000, C=10).fit(X, [x["label"] for x in tr])
    pred = m.predict(v.transform([x["text"] for x in te]))
    acc = sum(int(p == x["label"]) for p, x in zip(pred, te)) / len(te)
    hard = [(p, x) for p, x in zip(pred, te) if x["is_hard"]]
    hacc = sum(int(p == x["label"]) for p, x in hard) / len(hard)
    check("router: baseline TF-IDF hoc duoc (acc>=80%, khong qua de >99%)", .80 <= acc <= .99, "acc=%.1f%% hard=%.1f%%" % (acc * 100, hacc * 100))
except ImportError:
    print("SKIP  baseline (khong co sklearn)")

# ---------------- KB
menu = list(csv.DictReader(open(os.path.join(D, "kb", "menu.csv"), encoding="utf-8-sig")))
faq = list(csv.DictReader(open(os.path.join(D, "kb", "faq.csv"), encoding="utf-8-sig")))
man = J("kb", "docs", "doc_sections_manifest.json")
check("kb: menu >= 100 MenuItem", len(menu) >= 100, len(menu))
check("kb: faq >= 150 chunk", len(faq) >= 150, len(faq))
check("kb: tai lieu >= 50 chunk", len(man) >= 50, len(man))
check("kb: item_id/faq_id/section_id duy nhat", len({m["item_id"] for m in menu}) == len(menu) and len({f["faq_id"] for f in faq}) == len(faq)
      and len({m["section_id"] for m in man}) == len(man))
check("kb: gia hop le (S<M<L)", all(int(m["price_m"]) > 0 and (not m["price_s"] or int(m["price_s"]) < int(m["price_m"]) < int(m["price_l"])) for m in menu))
def _combo_ok():
    by = {m["name_vi"]: int(m["price_m"]) for m in menu}
    bad = []
    for m in menu:
        if m["category"] != "Combo":
            continue
        tot = 0
        for part in m["ingredients"].split(", "):
            mm = re.match(r"(\d+) (.+)", part)
            q, name = (int(mm.group(1)), mm.group(2)) if mm else (1, part)
            tot += q * by[name]
        if not int(m["price_m"]) < tot:
            bad.append((m["name_vi"], m["price_m"], tot))
    return bad
check("kb: moi combo re hon tong gia mua le", not _combo_ok(), _combo_ok())
files = glob.glob(os.path.join(D, "kb", "docs", "*.docx")) + glob.glob(os.path.join(D, "kb", "docs", "*.pdf"))
check("kb: 4 file docx/pdf", len(files) == 4, [os.path.basename(f) for f in files])
from docx import Document
for f in files:
    if f.endswith(".docx"):
        paras = [p.text for p in Document(f).paragraphs if p.text.strip()]
        check("docx doc duoc: " + os.path.basename(f), len(paras) > 15, len(paras))
    else:
        txt = subprocess.run(["pdftotext", f, "-"], capture_output=True, text=True).stdout
        check("pdf doc duoc + co tieng Viet: " + os.path.basename(f), "chi nhánh" in txt.lower() or "quy trình" in txt.lower() or "pha chế" in txt.lower(), len(txt))
# nhat quan su that giua FAQ / docs
alltxt = " ".join(m["text"] for m in man) + " ".join(f["answer"] for f in faq)
for k in ("hotline", "email", "wifi_pw"):
    check("nhat quan: %s xuat hien trong KB" % k, F[k] in alltxt)
# menu price tokens xuat hien trong cache_seed phai khop menu
prices = set()
for m in menu:
    for k in ("price_s", "price_m", "price_l"):
        if m[k]:
            prices.add(fmt_vnd(m[k]))
facts = {fmt_vnd(v) for v in (F["topping_low"], F["topping_high"], F["free_ship_min"], F["ship_fee"], F["cake_from"], 8000, 6000, 10000, 15000)}
facts |= {"%d.000đ" % n for n in (100, 200, 500)}
seed = J("cache", "cache_seed.json")["groups"]
bad = []
for g in seed:
    for r in (g["response_template_vi"],):
        for tok in re.findall(r"\d{1,3}(?:\.\d{3})+đ", r):
            if tok not in prices and tok not in facts:
                bad.append((g["group_id"], tok))
check("nhat quan: moi gia trong cache_seed khop menu/FACTS", not bad, bad)

# ---------------- Cache
ie = J("cache", "intent_extraction.json")
cnt = Counter(x["split"] for x in ie)
check("intent_extraction: 1500 mau (1200/150/150)", len(ie) == 1500 and cnt == {"train": 1200, "val": 150, "test": 150}, dict(cnt))
check("intent_extraction: subject/action/context la chuoi con cua text",
      all(x["action"] in x["text"] and (not x["context"] or x["context"] in x["text"]) and (not x["subject"] or x["subject"] in x["text"]) for x in ie))
check("intent_extraction: action khong chua thoi gian/so nguoi",
      not any(re.search(r"\d+ người|tối nay|ngày mai|tomorrow|tonight", x["action"].lower()) for x in ie))
ev = J("cache", "cache_eval_500.json")
check("cache_eval: 500 cau", len(ev) == 500, len(ev))
check("cache_eval: 425 hit / 75 miss", sum(e["expected_hit"] for e in ev) == 425)
check("cache_eval: khong trung voi intent_extraction", not ({norm_text(e["text"]) for e in ev} & {norm_text(x["text"]) for x in ie}))
check("cache_eval: tat ca 30 group co mat", len({e["expected_group"] for e in ev if e["expected_hit"]}) == 30)
check("cache_eval: co bien the context", sum(e["has_context"] for e in ev) >= 400, sum(e["has_context"] for e in ev))
inv = J("cache", "cache_invalidation_map.json")["map"]
check("cache: invalidation map co menu:*", "menu:*" in inv and len(inv["menu:*"]) >= 10)

# ---------------- Eval
rag = J("eval", "rag_eval_20.json")
check("rag_eval: 20 cau", len(rag) == 20)
mid = {m["item_id"] for m in menu}
fid = {f["faq_id"] for f in faq}
sid = {m["section_id"] for m in man}
check("rag_eval: gold id ton tai trong KB", all(set(q["gold_menu_ids"]) <= mid and set(q["gold_faq_ids"]) <= fid and set(q["gold_doc_sections"]) <= sid for q in rag))
check("rag_eval: co >=2 cau graph expansion, >=2 cau khong tra loi duoc",
      sum(q["needs_graph_expansion"] for q in rag) >= 2 and sum(not q["answerable"] for q in rag) >= 2)
exp_ok = True
for q in rag:
    if q["needs_graph_expansion"]:
        order = [next(m["order"] for m in man if m["section_id"] == s) for s in q["gold_doc_sections"]]
        exp_ok &= max(order) - min(order) == len(order) - 1
check("rag_eval: gold cua cau graph-expansion la cac chunk ke nhau", exp_ok)
tts = J("eval", "tts_cases.json")
check("tts: >= 40 case, ham tham chieu dat 100%", len(tts) >= 40 and all(tts_normalize(t["input"]) == t["expected"] for t in tts), len(tts))

print("\n==> %d PASS, %d FAIL" % (len(ok), len(fail)))
sys.exit(1 if fail else 0)
