#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pipeline sinh du lieu Router bang LLM API (module A1.2).

Dap ung yeu cau de: async API calls, deduplication, checkpoint/resume, progress tracking.
Chi dung thu vien chuan (urllib + asyncio.to_thread), khong can pip install.

API la bat ky endpoint OpenAI-compatible (OpenAI, Gemini OpenAI-compat, vLLM, SGLang, Ollama...):
    export LLM_BASE_URL=https://api.openai.com/v1      # hoac http://localhost:8000/v1
    export LLM_API_KEY=sk-...
    export LLM_MODEL=gpt-4o-mini
    python gen_router_data.py --per-intent 1100 --concurrency 8

Chay lai cung lenh sau khi bi ngat -> tu dong resume tu checkpoint (data/router/_checkpoint.jsonl).
Thu nghiem khong can API:  python gen_router_data.py --mock --per-intent 60
Xuat file cuoi:             python gen_router_data.py --finalize
"""
import argparse
import asyncio
import csv
import json
import os
import random
import re
import sys
import time
import urllib.request
import zlib
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from common import norm_text  # noqa

ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
INTENTS = ["order", "consultant", "faq", "ignore"]
LANG_SPLIT = {"vi": 0.55, "en": 0.40, "vi-en": 0.05}
HARD_RATIO = 0.12
BATCH = 20

INTENT_DEF = {
    "order": "đặt món / thêm / bớt / đổi / hủy món, hoặc tính tiền, thanh toán. Khách nói rõ muốn mua hoặc trả tiền.",
    "consultant": "xin tư vấn, gợi ý món, hỏi về vị / giá / thành phần / so sánh các món cụ thể, chưa quyết định mua.",
    "faq": "hỏi thông tin chung về quán và chính sách: wifi, giờ mở cửa, đặt bàn, giao hàng, thanh toán, hóa đơn VAT, thành viên, đỗ xe...",
    "ignore": "chào hỏi suông, cảm ơn, tiếng ồn, ậm ừ, cười, nói chuyện không liên quan quán, câu bỏ dở không có yêu cầu.",
}
HARD_DEF = {
    "order": "câu có yêu cầu mua rõ ràng NHƯNG kèm câu hỏi phụ (ví dụ vừa hỏi giá vừa lấy món, hoặc chào + gọi món).",
    "consultant": "câu mơ hồ giữa order và consultant: nhờ quán chọn hộ (\"có gì ngon rẻ không\", \"cho anh món nào ngon nhất\").",
    "faq": "câu nhắc tới món nhưng thực chất hỏi chính sách/thông tin quán (giao hàng, đổi điểm, VAT, mang đi), hoặc chào + hỏi thông tin.",
    "ignore": "câu bỏ dở hoặc lưỡng lự chưa thành yêu cầu (\"cho anh... à thôi\", \"để anh xem menu đã\").",
}
STYLES = ["thân mật, ngắn gọn", "lịch sự", "giọng nói bị nhận dạng sai (ASR), không dấu, không dấu câu",
          "có lỗi chính tả nhẹ", "câu dài có từ đệm (ừm, à, ờ)", "viết hoa/viết thường lộn xộn", "người lớn tuổi nói chậm",
          "thanh niên dùng từ lóng"]
LANG_NAME = {"vi": "tiếng Việt", "en": "tiếng Anh", "vi-en": "tiếng Việt pha lẫn tên món tiếng Anh (code-switch)"}


def menu_names(n=12):
    p = os.path.join(ROOT, "kb", "menu.csv")
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    return [r["name_vi"] for r in random.sample(rows, min(n, len(rows)))]


def build_prompt(intent, lang, hard, rnd):
    names = ", ".join(menu_names())
    return (
        "Bạn là chuyên gia tạo dữ liệu huấn luyện cho robot phục vụ quán cà phê (F&B) tại Việt Nam.\n"
        f"Sinh đúng {BATCH} câu nói NGẮN của khách hàng (tối đa 25 từ) bằng {LANG_NAME[lang]}, "
        f"thuộc intent \"{intent}\": {INTENT_DEF[intent]}\n"
        + (f"Yêu cầu bổ sung (câu KHÓ): {HARD_DEF[intent]}\n" if hard else "")
        + f"Phong cách: {rnd.choice(STYLES)}. Có thể dùng các món sau (và tên món khác): {names}.\n"
        "Các câu phải khác nhau rõ rệt về cấu trúc, không lặp ý, không đánh số.\n"
        'Chỉ trả về MỘT mảng JSON các chuỗi, ví dụ: ["câu 1", "câu 2"]. Không giải thích.'
    )


# ----------------------------------------------------------------- LLM call
def _http_chat(base, key, model, prompt, timeout):
    body = json.dumps({"model": model, "temperature": 1.0, "top_p": 0.95,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def _mock_chat(prompt, fail_rate, rnd):
    """Gia lap LLM de test pipeline offline (khong goi mang)."""
    if rnd.random() < fail_rate:
        raise RuntimeError("mock transient error")
    intent = re.search(r'intent "(\w+)"', prompt).group(1)
    stems = {"order": ["cho anh {n} ly cà phê sữa", "lấy thêm {n} bánh", "tính tiền bàn {n}"],
             "consultant": ["món nào ngon số {n}", "gợi ý đồ uống mát {n}", "trà nào ít ngọt {n}"],
             "faq": ["wifi tên gì chi nhánh {n}", "mấy giờ đóng cửa hôm {n}", "có giao hàng quận {n} không"],
             "ignore": ["ừm {n}", "haha {n}", "hello {n}"]}[intent]
    out = [rnd.choice(stems).format(n=rnd.randint(1, 400)) for _ in range(BATCH)]
    return "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"


def parse_list(txt):
    m = re.search(r"\[.*\]", txt, re.S)
    if not m:
        raise ValueError("no json array")
    arr = json.loads(m.group(0))
    return [s.strip() for s in arr if isinstance(s, str) and 1 <= len(s.strip()) <= 200]


async def call_llm(args, prompt, rnd):
    """Retry exponential backoff + jitter."""
    delay = 1.0
    for attempt in range(1, args.retries + 1):
        try:
            if args.mock:
                txt = await asyncio.to_thread(_mock_chat, prompt, args.mock_fail_rate, rnd)
            else:
                txt = await asyncio.to_thread(_http_chat, args.base_url, args.api_key, args.model, prompt, args.timeout)
            return parse_list(txt)
        except Exception as e:  # noqa
            if attempt == args.retries:
                raise
            await asyncio.sleep(delay + rnd.random() * 0.3)
            delay *= 2


# ------------------------------------------------------------ state / resume
class State:
    def __init__(self, path):
        self.path = path
        self.seen = set()
        self.count = Counter()          # (intent, lang, hard) -> n
        self.lock = asyncio.Lock()
        self.fail = 0
        self.t0 = time.time()
        self.loaded = 0
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    try:
                        x = json.loads(line)
                    except json.JSONDecodeError:
                        continue            # dong cuoi co the bi cat khi crash
                    self.seen.add(norm_text(x["text"]))
                    self.count[(x["intent"], x["language"], bool(x["is_hard"]))] += 1
                    self.loaded += 1
        # Neu lan chay truoc bi crash giua chung dong, file co the khong ket thuc bang newline:
        # them newline de ban ghi moi khong dinh vao dong bi cat.
        need_nl = os.path.exists(path) and os.path.getsize(path) > 0 and not open(path, "rb").read()[-1:] == b"\n"
        self.f = open(path, "a", encoding="utf-8")
        if need_nl:
            self.f.write("\n")

    async def add(self, intent, lang, hard, texts, limit):
        added = 0
        async with self.lock:
            for t in texts:
                if added >= limit:
                    break
                k = norm_text(t)
                if not k or k in self.seen:
                    continue
                self.seen.add(k)
                self.f.write(json.dumps(dict(text=t, intent=intent, language=lang, is_hard=hard), ensure_ascii=False) + "\n")
                self.count[(intent, lang, hard)] += 1
                added += 1
            self.f.flush()
            os.fsync(self.f.fileno())          # checkpoint ben vung
        return added

    def total(self):
        return sum(self.count.values())


def plan(per_intent):
    cells = {}
    for it in INTENTS:
        for lg, w in LANG_SPLIT.items():
            n_hard = round(per_intent * w * HARD_RATIO)
            cells[(it, lg, True)] = n_hard
            cells[(it, lg, False)] = round(per_intent * w) - n_hard
    return cells


async def worker(name, args, st, cells, queue, rnd, goal):
    while True:
        try:
            cell = queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        intent, lang, hard = cell
        if st.count[cell] >= cells[cell]:
            continue
        try:
            texts = await call_llm(args, build_prompt(intent, lang, hard, rnd), rnd)
            await st.add(intent, lang, hard, texts, cells[cell] - st.count[cell])
        except Exception as e:  # noqa
            st.fail += 1
            print("\n[warn] %s %s: %s" % (name, cell, e), file=sys.stderr)
        if st.count[cell] < cells[cell]:
            queue.put_nowait(cell)         # chua du -> xep hang lai
        progress(st, goal)


def progress(st, goal):
    done = st.total()
    el = max(time.time() - st.t0, 1e-6)
    rate = (done - st.loaded) / el
    eta = max(goal - done, 0) / rate if rate > 0 else float("inf")
    bar = "#" * int(30 * min(done / goal, 1))
    print("\r[%-30s] %d/%d  %.1f mau/s  ETA %s  loi=%d" % (bar, done, goal, rate,
          "%ds" % eta if eta != float("inf") else "?", st.fail), end="", file=sys.stderr, flush=True)


async def run(args):
    random.seed(args.seed)
    rnd = random.Random(args.seed)
    os.makedirs(os.path.dirname(args.checkpoint), exist_ok=True)
    st = State(args.checkpoint)
    cells = plan(args.per_intent)
    goal = sum(cells.values())
    print("Resume: %d mau da co trong checkpoint. Muc tieu %d." % (st.loaded, goal), file=sys.stderr)
    queue = asyncio.Queue()
    for c, n in cells.items():
        if st.count[c] < n:
            queue.put_nowait(c)
    if queue.empty():
        print("Da du du lieu.", file=sys.stderr)
    else:
        await asyncio.gather(*[worker("w%d" % i, args, st, cells, queue, rnd, goal) for i in range(args.concurrency)])
    print(file=sys.stderr)
    st.f.close()
    finalize(args)


def finalize(args):
    """Can bang 4 intent, chia train/test (hash theo text), ghi router_train.json / router_test.json."""
    rows = []
    for l in open(args.checkpoint, encoding="utf-8"):
        try:
            rows.append(json.loads(l))
        except json.JSONDecodeError:
            pass            # bo qua dong bi cat do crash
    by = {it: [r for r in rows if r["intent"] == it] for it in INTENTS}
    n = min(len(v) for v in by.values())
    test_n = max(int(n * args.test_ratio), 1)
    out = {"train": [], "test": []}
    rnd = random.Random(args.seed)
    for it in INTENTS:
        v = by[it][:]
        rnd.shuffle(v)
        v = v[:n]
        hard = [x for x in v if x["is_hard"]]
        easy = [x for x in v if not x["is_hard"]]
        t_hard = hard[:max(round(test_n * 0.2), 1)]
        t_easy = easy[:test_n - len(t_hard)]
        test = t_hard + t_easy
        ids = {id(x) for x in test}
        out["test"] += test
        out["train"] += [x for x in v if id(x) not in ids]
    for split, lst in out.items():
        rnd.shuffle(lst)
        recs = [dict(id="R-%s-%05d" % (split.upper(), i), text=x["text"], label=INTENTS.index(x["intent"]),
                     intent=x["intent"], is_noise=(x["intent"] == "ignore"), language=x["language"],
                     is_hard=x["is_hard"]) for i, x in enumerate(lst, 1)]
        p = os.path.join(os.path.dirname(args.checkpoint), "llm_router_%s.json" % split)
        json.dump(recs, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("%s: %d mau -> %s  %s" % (split, len(recs), p, dict(Counter(r["intent"] for r in recs))), file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-intent", type=int, default=1100, help="so mau moi intent (1100 x 4 = 4400)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--test-ratio", type=float, default=0.0909, help="ti le test moi intent")
    ap.add_argument("--checkpoint", default=os.path.join(ROOT, "router", "_checkpoint.jsonl"))
    ap.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
    ap.add_argument("--api-key", default=os.getenv("LLM_API_KEY", ""))
    ap.add_argument("--model", default=os.getenv("LLM_MODEL", "gpt-4o-mini"))
    ap.add_argument("--mock", action="store_true", help="khong goi API, dung LLM gia lap de test pipeline")
    ap.add_argument("--mock-fail-rate", type=float, default=0.15)
    ap.add_argument("--finalize", action="store_true", help="chi can bang + chia train/test tu checkpoint")
    args = ap.parse_args()
    if args.finalize:
        return finalize(args)
    if not args.mock and not args.api_key:
        sys.exit("Thieu LLM_API_KEY (hoac dung --mock de thu pipeline).")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
