"""Text-To-Speech (TTS) normalizer for Vietnamese coffee shop domain.

Normalizes prices, sizes, units, times, VAT, percentages, and markdown
for natural voice synthesis. Verified against `data/evaluation/tts_cases.json`.
"""

import re


def normalize_for_tts(text: str) -> str:
    """Normalize raw Vietnamese assistant text into clean, natural TTS speakable text."""
    if not text:
        return ""

    res = text

    # 1. Markdown bold: **text** -> text
    res = re.sub(r"\*\*([^*]+)\*\*", r"\1", res)

    # 2. Markdown list: - Item 1\n- Item 2 -> Item 1. Item 2
    lines = res.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = re.sub(r"^\s*-\s+", "", line)
        if stripped:
            cleaned_lines.append(stripped)
    res = ". ".join(cleaned_lines)

    # 3. Ampersand: & -> và
    res = re.sub(r"\s+&\s+", " và ", res)

    # 4. Units: ml -> mi li lít
    res = re.sub(r"(\d+)\s*ml\b", r"\1 mi li lít", res)

    # 5. Kcal -> ki lô ca
    res = re.sub(r"(\d+)\s*kcal\b", r"\1 ki lô ca", res)

    # 6. Percent: % -> phần trăm
    res = re.sub(r"(\d+)%", r"\1 phần trăm", res)

    # 7. VAT -> thuế
    res = re.sub(r"\bVAT\b", "thuế", res)

    # 8. Time: 07:00 -> 7 giờ, 22:30 -> 22 giờ 30
    def _replace_time(m: re.Match) -> str:
        h = int(m.group(1))
        minute = m.group(2)
        if minute == "00":
            return f"{h} giờ"
        return f"{h} giờ {minute}"

    res = re.sub(r"\b(\d{1,2}):(\d{2})\b", _replace_time, res)

    # 9. Sizes:
    # Size all: Size S/M/L -> Size sờ, mờ hoặc lờ
    res = re.sub(r"\b([Ss]ize)\s+S/M/L\b", r"\1 sờ, mờ hoặc lờ", res)

    # Parenthesized size: (S) -> (sờ), (M) -> (mờ), (L) -> (lờ)
    res = re.sub(r"\([Ss]\)", "(sờ)", res)
    res = re.sub(r"\([Mm]\)", "(mờ)", res)
    res = re.sub(r"\([Ll]\)", "(lờ)", res)

    # Explicit size prefix: size S/M/L
    res = re.sub(r"\b([Ss]ize)\s+S\b", r"\1 sờ", res)
    res = re.sub(r"\b([Ss]ize)\s+M\b", r"\1 mờ", res)
    res = re.sub(r"\b([Ss]ize)\s+L\b", r"\1 lờ", res)

    # 10. Prices:
    # Match patterns with currency: đ, ₫, VNĐ, VND (case-insensitive)
    currency_pattern = r"(?:\s*(?:đ|₫|[Vv][Nn][Đđ]|[Vv][Nn][Dd]))(?![a-zA-Z0-9])"

    # Millions: X.000.000đ -> X triệu, X.Y00.000đ -> X triệu Y
    res = re.sub(
        rf"\b(\d+)\.(\d{{3}})\.000{currency_pattern}",
        lambda m: f"{m.group(1)} triệu" if m.group(2) == "000" else f"{m.group(1)} triệu {int(m.group(2))}",
        res,
    )

    # Half thousands: e.g. 49.500đ -> 49k rưỡi
    res = re.sub(rf"\b(\d+)\.500{currency_pattern}", r"\1k rưỡi", res)

    # Odd thousands: e.g. 12.345đ -> 12.345 đồng
    def _replace_odd(m: re.Match) -> str:
        val = m.group(1)
        last3 = m.group(2)
        if last3 != "000" and last3 != "500":
            return f"{val}.{last3} đồng"
        return m.group(0)

    res = re.sub(rf"\b(\d+)\.(\d{{3}}){currency_pattern}", _replace_odd, res)

    # Standard thousands with dot/comma/none:
    # 39.000đ, 45,000 VND, 45000đ -> 39k, 45k
    res = re.sub(rf"\b(\d+)[.,]000{currency_pattern}", r"\1k", res)
    res = re.sub(rf"\b(\d+)000{currency_pattern}", r"\1k", res)

    return res
