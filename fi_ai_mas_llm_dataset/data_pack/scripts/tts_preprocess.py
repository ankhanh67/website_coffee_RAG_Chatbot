# -*- coding: utf-8 -*-
"""Tien xu ly van ban truoc khi dua vao TTS (C3) - cai dat tham chieu.

Quy tac:
  * Gia tien: 49.000đ -> 49k ; 49.500đ -> 49k ruoi ; 1.250.000đ -> 1 trieu 250 ; 2.000.000đ -> 2 trieu
  * Size: size M -> size mo ; (S) -> (so) ; S/M/L -> so, mo hoac lo
  * VAT -> thue ; 10% -> 10 phan tram
  * Don vi: 470ml -> 470 mi li lit ; 22:30 -> 22 gio 30
  * "&" -> "va" ; bo ky hieu markdown (** # gach dau dong)
"""
import re

SIZE_SAY = {"S": "sờ", "M": "mờ", "L": "lờ"}
_NUM = r"(\d{1,3}(?:[.,]\d{3})+|\d+)"
_PRICE = re.compile(_NUM + r"\s?(?:đ|₫|VNĐ|VND|vnđ|vnd)(?!\w)")


def _price(m):
    n = int(re.sub(r"[.,]", "", m.group(1)))
    if n >= 1_000_000:
        mil, rem = divmod(n, 1_000_000)
        if rem == 0:
            return "%d triệu" % mil
        if rem % 1000 == 0:
            return "%d triệu %d" % (mil, rem // 1000)
    elif n % 1000 == 0:
        return "%dk" % (n // 1000)
    elif n % 1000 == 500:
        return "%dk rưỡi" % (n // 1000)
    return "{:,}".format(n).replace(",", ".") + " đồng"


def tts_normalize(text):
    s = text
    s = re.sub(r"\*\*|__|`", "", s)                       # markdown
    s = re.sub(r"(?m)^\s*(?:[-*•]|#+)\s+", "", s)           # gach dau dong, heading
    s = re.sub(r"\s*\n+\s*", ". ", s.strip())              # xuong dong -> ngat cau
    s = _PRICE.sub(_price, s)
    s = re.sub(r"\b((?:[Ss]ize|[Cc]ỡ)\s)?S/M/L\b", lambda m: (m.group(1) or "") + "sờ, mờ hoặc lờ", s)
    s = re.sub(r"\b([Ss]ize|[Cc]ỡ)\s([SML])\b", lambda m: "%s %s" % (m.group(1), SIZE_SAY[m.group(2)]), s)
    s = re.sub(r"\(([SML])\)", lambda m: "(%s)" % SIZE_SAY[m.group(1)], s)
    s = re.sub(r"\bVAT\b", "thuế", s)
    s = re.sub(r"(\d+(?:[.,]\d+)?)\s?%", r"\1 phần trăm", s)
    s = re.sub(r"(\d+)\s?ml\b", r"\1 mi li lít", s)
    s = re.sub(r"(\d+)\s?kcal\b", r"\1 ki lô ca", s)
    s = re.sub(r"\b(\d{1,2}):(\d{2})\b", lambda m: "%d giờ" % int(m.group(1)) if m.group(2) == "00" else "%d giờ %d" % (int(m.group(1)), int(m.group(2))), s)
    s = s.replace("&", " và ")
    return re.sub(r"\s+", " ", s).strip()
