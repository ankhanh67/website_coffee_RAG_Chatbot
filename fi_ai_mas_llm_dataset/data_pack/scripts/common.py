# -*- coding: utf-8 -*-
"""Nguon su that dung chung cho moi bo du lieu (menu, chi nhanh, FACTS, khuyen mai).

Moi generator (menu/faq/docs/router/cache/rag_eval) deu import tu day,
nen du lieu giua cac file luon nhat quan (gia, gio mo cua, chinh sach...).
DU LIEU LA MO PHONG - khong phai menu/gia that cua Highlands Coffee.
"""
import random
import re
import unicodedata

SEED = 2026

# --------------------------------------------------------------------------
# MENU  (vi | en | gia size M (VND) | nguyen lieu | huong vi vi | huong vi en | flags)
# flags: h=co nong, i=co da/lanh, k=co caffeine, d=co sua, n=co hat, v=thuan chay, x=1 size duy nhat
# --------------------------------------------------------------------------
_MENU_BLOCKS = [
    ("Cà phê", "Coffee", "drink", """
Phin Sữa Đá|Iced Vietnamese Milk Coffee|39000|cà phê phin, sữa đặc, đá|đậm vị cà phê, ngọt béo|strong coffee with sweet creamy condensed milk|ikd
Phin Đen Đá|Iced Black Vietnamese Coffee|35000|cà phê phin, đá|đậm, đắng, không đường|bold and bitter with no sugar|ikv
Phin Sữa Nóng|Hot Vietnamese Milk Coffee|39000|cà phê phin, sữa đặc|ấm, ngọt béo|warm and sweetly creamy|hkd
Phin Đen Nóng|Hot Black Vietnamese Coffee|35000|cà phê phin|đậm đà, đắng nhẹ|rich with a mild bitterness|hkv
Bạc Xỉu|Bac Xiu (Milk Coffee)|39000|sữa tươi, sữa đặc, cà phê phin|nhiều sữa ít cà phê, ngọt dịu|more milk than coffee, gently sweet|hikd
Cà Phê Muối|Salted Cream Coffee|45000|cà phê phin, kem muối, sữa đặc|béo mặn nhẹ, đậm vị|creamy with a light salty finish|ikd
Cà Phê Cốt Dừa|Coconut Coffee|49000|cà phê, cốt dừa, sữa đặc|thơm béo vị dừa|fragrant coconut richness|ikd
Espresso|Espresso|39000|cà phê espresso|đậm đặc, một shot|a strong single shot|hkv
Americano|Americano|45000|espresso, nước|nhẹ hơn espresso, thanh|lighter and cleaner than espresso|hikv
Cappuccino|Cappuccino|55000|espresso, sữa tươi, bọt sữa|bọt sữa dày, cân bằng|thick foam and balanced|hkd
Latte|Latte|55000|espresso, sữa tươi|mềm mịn, nhiều sữa|smooth and milky|hikd
Mocha|Mocha|59000|espresso, socola, sữa tươi|cà phê hòa quyện socola|coffee blended with chocolate|hikd
Caramel Macchiato|Caramel Macchiato|59000|espresso, sữa tươi, sốt caramel|ngọt caramel, béo|sweet caramel and creamy|hikd
Cold Brew|Cold Brew|49000|cà phê ủ lạnh 18 giờ, đá|êm, ít đắng|smooth with low bitterness|ikv
Cold Brew Sữa Tươi|Cold Brew with Fresh Milk|55000|cà phê ủ lạnh, sữa tươi|êm, béo nhẹ|smooth and lightly creamy|ikd
Hazelnut Latte|Hazelnut Latte|59000|espresso, sữa tươi, siro hạt dẻ|thơm mùi hạt dẻ|nutty aroma|hiknd
"""),
    ("Freeze", "Freeze (Blended)", "drink", """
Freeze Trà Xanh|Green Tea Freeze|59000|matcha, sữa, đá xay, kem whipping|mát lạnh, trà xanh béo|icy and creamy matcha|ikd
Cookies & Cream Freeze|Cookies & Cream Freeze|59000|bánh oreo, sữa, đá xay, kem whipping|ngọt, giòn vị bánh|sweet with cookie crunch|id
Caramel Phin Freeze|Caramel Phin Freeze|59000|cà phê phin, caramel, đá xay|cà phê caramel mát lạnh|iced caramel coffee blend|ikd
Classic Phin Freeze|Classic Phin Freeze|55000|cà phê phin, sữa, đá xay|đậm vị cà phê|bold blended coffee|ikd
Chocolate Freeze|Chocolate Freeze|59000|socola, sữa, đá xay, kem whipping|ngọt đậm socola|rich chocolate|id
Matcha Đậu Đỏ Freeze|Matcha Red Bean Freeze|65000|matcha, đậu đỏ, sữa, đá xay|đậm matcha, bùi đậu đỏ|earthy matcha with sweet red beans|ikd
Dâu Freeze|Strawberry Freeze|59000|dâu tây, sữa chua, đá xay|chua ngọt mát lạnh|tart and sweet strawberry|id
Xoài Freeze|Mango Freeze|59000|xoài, sữa chua, đá xay|ngọt thơm xoài|sweet tropical mango|id
Chanh Dây Freeze|Passion Fruit Freeze|55000|chanh dây, đá xay|chua thanh, sảng khoái|tangy and refreshing|iv
Đào Freeze|Peach Freeze|59000|đào, sữa chua, đá xay|ngọt thanh mùi đào|sweet and peachy|id
Việt Quất Freeze|Blueberry Yogurt Freeze|65000|việt quất, sữa chua, đá xay|chua ngọt thanh|tart and sweet blueberry|id
Dừa Freeze|Coconut Freeze|59000|cốt dừa, sữa, đá xay, dừa sợi|béo thơm vị dừa|creamy coconut|id
"""),
    ("Trà", "Tea", "drink", """
Trà Sen Vàng|Golden Lotus Tea|49000|trà ô long, hạt sen, củ năng|thanh nhẹ, thơm sen, giòn củ năng|light lotus fragrance with crunchy water chestnut|hikv
Trà Thạch Đào|Peach Jelly Tea|49000|trà đen, đào miếng, thạch đào|thơm đào, giải khát|fruity peach, thirst quenching|hikv
Trà Thanh Đào|Peach Green Tea|49000|trà xanh, đào miếng|thanh mát|light and cooling|hikv
Trà Oolong Vải|Lychee Oolong Tea|49000|trà ô long, vải, siro vải|thơm vải, hậu ngọt|lychee aroma with a sweet finish|hikv
Trà Xanh Chanh Dây|Passion Fruit Green Tea|45000|trà xanh, chanh dây|chua nhẹ, sảng khoái|slightly tangy and refreshing|ikv
Trà Hoa Cúc Mật Ong|Chamomile Honey Tea|45000|hoa cúc, mật ong|dịu nhẹ, không caffeine|gentle and caffeine-free|h
Trà Gừng Mật Ong|Ginger Honey Tea|45000|gừng, mật ong|ấm bụng, cay nhẹ|warming with a mild spice|h
Trà Đào Cam Sả|Peach Orange Lemongrass Tea|55000|trà đen, đào, cam, sả|thơm sả, chua ngọt, bán chạy nhất|fragrant lemongrass, sweet and sour, a bestseller|hikv
Trà Vải|Lychee Tea|49000|trà đen, vải, siro vải|ngọt thơm vải|sweet lychee|ikv
Trà Ổi Hồng|Pink Guava Tea|49000|trà đen, ổi hồng|thơm ổi, hơi chua|guava aroma, slightly tart|ikv
Trà Dâu|Strawberry Tea|49000|trà đen, dâu tây|chua ngọt dịu|gently sweet and tart|ikv
Trà Chanh Dây|Passion Fruit Tea|45000|trà đen, chanh dây|chua thanh|bright and tangy|ikv
Trà Thạch Vải|Lychee Jelly Tea|49000|trà đen, vải, thạch vải|ngọt thơm, nhai vui miệng|sweet lychee with chewy jelly|ikv
Trà Xanh Espresso|Green Tea Espresso|55000|trà xanh, espresso|đậm, tỉnh táo|bold and energizing|hikv
Trà Đen Macchiato|Black Tea Macchiato|55000|trà đen, kem cheese|béo mặn nhẹ trên nền trà|creamy cheese foam over black tea|hikd
Trà Cam Quế|Orange Cinnamon Tea|49000|trà đen, cam, quế|thơm quế, ấm|cinnamon aroma and warming|hkv
Trà Atiso|Artichoke Tea|45000|atiso, đường phèn|thanh nhiệt, hậu ngọt|cooling with a sweet finish|hiv
Trà Bưởi Mật Ong|Pomelo Honey Tea|49000|bưởi, mật ong, trà xanh|chua nhẹ, thơm bưởi|mildly tart pomelo|hikv
Trà Táo Quế|Apple Cinnamon Tea|49000|trà đen, táo, quế|thơm táo, ấm|apple and cinnamon, warming|hkv
Trà Chanh Sả|Lemongrass Lemon Tea|45000|trà đen, chanh, sả|chua thanh, thơm sả|zesty and citrusy|hikv
"""),
    ("Trà sữa", "Milk Tea", "drink", """
Trà Sữa Truyền Thống|Classic Milk Tea|45000|trà đen, sữa, đường|vị truyền thống, béo vừa|classic and mildly creamy|hikd
Trà Sữa Trân Châu Đường Đen|Brown Sugar Boba Milk Tea|55000|trà đen, sữa, trân châu đường đen|ngọt đậm đường đen, dai dai|rich brown sugar with chewy boba|ikd
Trà Sữa Matcha|Matcha Milk Tea|55000|matcha, sữa, trà|vị matcha béo ngậy|rich and creamy matcha|ikd
Trà Sữa Ô Long|Oolong Milk Tea|52000|trà ô long, sữa|thơm trà, hậu thanh|fragrant tea with a clean finish|hikd
Trà Sữa Khoai Môn|Taro Milk Tea|55000|khoai môn, sữa, trà|béo bùi vị khoai môn|nutty and creamy taro|ikd
Trà Sữa Socola|Chocolate Milk Tea|52000|trà đen, socola, sữa|ngọt béo vị socola|sweet chocolate and creamy|ikd
Trà Sữa Hokkaido|Hokkaido Milk Tea|55000|trà đen, sữa Hokkaido, kem sữa|béo mịn|silky and creamy|ikd
Trà Sữa Thái|Thai Milk Tea|49000|trà Thái, sữa đặc|ngọt đậm kiểu Thái|bold Thai style sweetness|ikd
Trà Sữa Dâu|Strawberry Milk Tea|55000|trà đen, dâu tây, sữa|ngọt thơm dâu|sweet strawberry|ikd
Trà Sữa Hạt Dẻ|Hazelnut Milk Tea|55000|trà đen, siro hạt dẻ, sữa|thơm bùi hạt dẻ|nutty and fragrant|iknd
"""),
    ("Sinh tố & Nước ép", "Smoothies & Juices", "drink", """
Sinh Tố Xoài|Mango Smoothie|49000|xoài, sữa chua, đá|ngọt thơm xoài|sweet mango|id
Sinh Tố Bơ|Avocado Smoothie|55000|bơ, sữa đặc, đá|béo mịn|rich and smooth|id
Sinh Tố Dâu|Strawberry Smoothie|55000|dâu tây, sữa chua, đá|chua ngọt|sweet and tart|id
Sinh Tố Chuối Yến Mạch|Banana Oat Smoothie|55000|chuối, yến mạch, sữa|no lâu, ngọt dịu|filling and gently sweet|id
Sinh Tố Việt Quất|Blueberry Smoothie|59000|việt quất, sữa chua, đá|chua ngọt thanh|tart and sweet blueberry|id
Nước Ép Cam|Fresh Orange Juice|45000|cam tươi|chua ngọt, nhiều vitamin C|sweet and tangy, high in vitamin C|iv
Nước Ép Dưa Hấu|Watermelon Juice|45000|dưa hấu|ngọt mát|sweet and cooling|iv
Nước Ép Ổi|Guava Juice|45000|ổi hồng|thơm đậm vị ổi|bold guava flavor|iv
Nước Ép Cà Rốt|Carrot Juice|45000|cà rốt|ngọt tự nhiên|naturally sweet|iv
Nước Ép Dứa|Pineapple Juice|45000|dứa|chua ngọt|sweet and tart|iv
"""),
    ("Đồ uống khác", "Other Drinks", "drink", """
Chocolate Nóng|Hot Chocolate|49000|socola, sữa tươi|ngọt ấm, đậm socola|warm and chocolatey|hd
Matcha Latte|Matcha Latte|55000|matcha, sữa tươi|béo nhẹ, thơm trà xanh|lightly creamy green tea|hikd
Soda Chanh|Lemon Soda|39000|chanh, soda, đường|chua sảng khoái|sharp and refreshing|iv
Soda Dâu|Strawberry Soda|45000|siro dâu, soda|ngọt mát, có ga|sweet and fizzy|iv
Soda Việt Quất|Blueberry Soda|45000|siro việt quất, soda|ngọt mát, có ga|sweet and fizzy|iv
Nước Suối|Bottled Water|15000|nước tinh khiết|nước lọc đóng chai|plain bottled water|ixv
Sữa Tươi Trân Châu Đường Đen|Brown Sugar Boba Fresh Milk|55000|sữa tươi, trân châu đường đen|ngọt béo, không trà|sweet and creamy, no tea|ikd
Nước Dừa Tươi|Fresh Coconut Water|39000|dừa tươi|ngọt thanh tự nhiên|naturally sweet|ixv
"""),
    ("Bánh ngọt", "Cakes & Pastries", "food", """
Bánh Tiramisu|Tiramisu|45000|phô mai mascarpone, cà phê, bánh ladyfinger, ca cao|vị cà phê, béo mịn|coffee-soaked and creamy|dk
Bánh Mousse Chanh Dây|Passion Fruit Mousse Cake|39000|kem mousse, chanh dây|chua ngọt, mềm mịn|tangy and silky|d
Bánh Mousse Socola|Chocolate Mousse Cake|39000|socola, kem mousse|đậm socola, mềm|rich and soft|d
Bánh Phô Mai Chanh Dây|Passion Fruit Cheesecake|39000|phô mai, chanh dây, bánh quy|béo chua ngọt|creamy and tangy|d
Bánh Phô Mai Việt Quất|Blueberry Cheesecake|42000|phô mai, việt quất, bánh quy|béo, chua nhẹ|creamy with a light tartness|d
Bánh Phô Mai Trà Xanh|Matcha Cheesecake|42000|phô mai, matcha, bánh quy|béo, thơm trà xanh|creamy with green tea aroma|dk
Bánh Red Velvet|Red Velvet Cake|45000|bột mì, ca cao, kem phô mai|mềm ẩm, ngọt vừa|moist and mildly sweet|d
Bánh Su Kem|Cream Puff|25000|bột mì, kem sữa|vỏ mềm, nhân kem béo|soft shell with creamy filling|d
Bánh Croissant Bơ|Butter Croissant|29000|bột mì, bơ|giòn tan, thơm bơ|flaky and buttery|d
Bánh Croissant Socola|Chocolate Croissant|35000|bột mì, bơ, socola|giòn, nhân socola|flaky with chocolate filling|d
Bánh Muffin Việt Quất|Blueberry Muffin|29000|bột mì, việt quất, trứng|mềm xốp, thơm việt quất|fluffy with blueberries|d
Bánh Muffin Socola|Chocolate Muffin|29000|bột mì, socola chip, trứng|mềm xốp, ngọt|fluffy and sweet|d
Bánh Brownie|Brownie|35000|socola, bột mì, trứng, óc chó|đặc, dẻo, đậm socola|dense, fudgy and chocolatey|dn
Bánh Bông Lan Trứng Muối|Salted Egg Sponge Cake|39000|bột mì, trứng muối, ruốc|mặn ngọt, xốp mềm|savory-sweet and fluffy|d
Bánh Cookie Socola Chip|Chocolate Chip Cookie|25000|bột mì, bơ, socola chip|giòn ngoài mềm trong|crisp outside, soft inside|d
Bánh Sừng Bò Hạnh Nhân|Almond Croissant|39000|bột mì, bơ, hạnh nhân|giòn, thơm hạnh nhân|flaky with almond|dn
"""),
    ("Bánh mì & Món mặn", "Savory", "food", """
Bánh Mì Thịt Nướng|Grilled Pork Banh Mi|39000|bánh mì, thịt nướng, rau, dưa leo|đậm đà, thơm mùi nướng|savory and smoky|
Bánh Mì Gà Xé|Shredded Chicken Banh Mi|39000|bánh mì, gà xé, rau, sốt mayo|mềm, thanh vị|tender and light|d
Bánh Mì Trứng Ốp La|Fried Egg Banh Mi|35000|bánh mì, trứng, pate, rau|món sáng quen thuộc|a classic breakfast|d
Bánh Mì Pate Chả Lụa|Pate & Vietnamese Ham Banh Mi|35000|bánh mì, pate, chả lụa, rau|đậm vị truyền thống|traditional and savory|
Bánh Mì Phô Mai Gà|Chicken Cheese Banh Mi|45000|bánh mì, gà, phô mai|béo, nóng giòn|cheesy and crisp|d
Mì Ý Bò Bằm|Spaghetti Bolognese|59000|mì Ý, bò bằm, sốt cà chua|đậm đà|rich and hearty|
Mì Ý Sốt Kem Nấm|Mushroom Cream Pasta|59000|mì Ý, nấm, kem tươi|béo thơm nấm|creamy and earthy|d
Mì Ý Tôm Sốt Cà|Shrimp Tomato Pasta|65000|mì Ý, tôm, sốt cà chua|chua ngọt, thơm tôm|tangy and shrimpy|
Salad Gà|Chicken Salad|55000|rau xà lách, ức gà, sốt mè|nhẹ bụng, ít béo|light and low in fat|
Salad Rau Củ|Garden Salad|45000|xà lách, cà chua, dưa leo, bắp, sốt dầu giấm|thanh mát, ăn chay được|fresh and vegan-friendly|v
Sandwich Jambon Phô Mai|Ham & Cheese Sandwich|45000|bánh sandwich, jambon, phô mai|mặn béo|savory and cheesy|d
Sandwich Gà Nướng|Grilled Chicken Sandwich|49000|bánh sandwich, gà nướng, rau, sốt|no bụng, đậm đà|filling and savory|d
Khoai Tây Chiên|French Fries|35000|khoai tây, muối|giòn nóng|hot and crispy|v
Cơm Gà Teriyaki|Teriyaki Chicken Rice|65000|cơm, gà, sốt teriyaki, rau|ngọt mặn, đậm đà|sweet-savory and hearty|
"""),
    ("Combo", "Combos", "combo", """
Combo Sáng Bánh Mì|Banh Mi Breakfast Combo|69000|Bánh Mì Gà Xé, Phin Sữa Đá|bữa sáng gọn nhẹ|a quick breakfast|x
Combo Sáng Croissant|Croissant Breakfast Combo|79000|Bánh Croissant Bơ, Latte|bữa sáng kiểu Âu|a European style breakfast|x
Combo Trưa Cơm Gà|Teriyaki Lunch Combo|109000|Cơm Gà Teriyaki, Trà Đào Cam Sả|bữa trưa đầy đủ|a full lunch|x
Combo Mì Ý|Pasta Combo|89000|Mì Ý Bò Bằm, Soda Chanh|món chính kèm nước giải khát|a pasta main with a refresher|x
Combo Bạn Bè|Friends Combo (2 people)|109000|2 Phin Sữa Đá, 2 Bánh Muffin Việt Quất|dành cho 2 người|for two people|x
Combo Nhóm 4 Người|Group Combo (4 people)|199000|4 Trà Vải, 1 Khoai Tây Chiên|dành cho nhóm 4 người|for a group of four|x
Combo Ngọt Ngào|Sweet Combo|89000|Cookies & Cream Freeze, Bánh Tiramisu|dành cho người thích đồ ngọt|for the sweet tooth|x
Combo Healthy|Healthy Combo|79000|Salad Rau Củ, Nước Ép Cam|nhẹ bụng, tốt cho sức khỏe|light and healthy|xv
"""),
    ("Topping", "Toppings & Add-ons", "extra", """
Trân Châu Đường Đen|Brown Sugar Boba|10000|trân châu, đường đen|dai, ngọt|chewy and sweet|x
Thạch Đào|Peach Jelly|10000|thạch, đào|giòn mát|cool and chewy|x
Kem Cheese|Cream Cheese Foam|12000|phô mai kem, sữa|béo mặn nhẹ|creamy and lightly salty|xd
Shot Espresso Thêm|Extra Espresso Shot|12000|espresso|tăng độ đậm|stronger coffee|xk
Kem Whipping|Whipped Cream|8000|kem whipping|béo ngọt|sweet and rich|xd
Đổi Sữa Yến Mạch|Oat Milk Upgrade|15000|sữa yến mạch|thay sữa tươi, ăn chay|dairy-free swap|xv
"""),
]

SIZES_ML = {"S": 360, "M": 470, "L": 700}


def _build_menu():
    items = []
    n = 0
    for cat_vi, cat_en, kind, block in _MENU_BLOCKS:
        for line in block.strip().splitlines():
            vi, en, price, ingr, fl_vi, fl_en, flags = line.split("|")
            n += 1
            price = int(price)
            single = ("x" in flags) or kind in ("food", "combo", "extra")
            has_hot, has_ice = "h" in flags, "i" in flags
            if kind == "drink":
                temp = "both" if (has_hot and has_ice) else ("hot" if has_hot else "iced")
            else:
                temp = "n/a"
            allergens = []
            if "d" in flags:
                allergens.append("sữa")
            if "n" in flags:
                allergens.append("hạt")
            if cat_vi == "Bánh ngọt" or vi.startswith("Bánh Mì") or "Mì Ý" in vi or "Sandwich" in vi:
                allergens.append("gluten")
            if cat_vi == "Bánh ngọt":
                allergens.append("trứng")
            allergens = sorted(set(allergens))
            items.append(dict(
                item_id="M%03d" % n,
                name_vi=vi, name_en=en,
                category=cat_vi, category_en=cat_en, kind=kind,
                price_s="" if single else price - 6000,
                price_m=price,
                price_l="" if single else price + 10000,
                sizes="Một cỡ" if single else "S/M/L",
                temperature=temp,
                caffeine="có" if "k" in flags else "không",
                vegan="có" if "v" in flags else "không",
                allergens=", ".join(allergens) if allergens else "không",
                ingredients=ingr,
                description_vi="%s: %s. Thành phần: %s." % (vi, fl_vi, ingr),
                description_en="%s: %s." % (en, fl_en),
            ))
    # Combo: gop di ung nguyen tu cac mon thanh phan
    by_vi = {m["name_vi"]: m for m in items}
    for m in items:
        if m["kind"] != "combo":
            continue
        al = set()
        for comp, mm in by_vi.items():
            if mm["kind"] != "combo" and comp in m["ingredients"] and mm["allergens"] != "không":
                al.update(x.strip() for x in mm["allergens"].split(","))
        m["allergens"] = ", ".join(sorted(al)) if al else "không"
        comps = [mm for comp, mm in by_vi.items() if mm["kind"] != "combo" and comp in m["ingredients"]]
        m["caffeine"] = "có" if any(c["caffeine"] == "có" for c in comps) else "không"
    return items


MENU = _build_menu()
assert len(MENU) == 120, len(MENU)
MENU_BY_VI = {m["name_vi"]: m for m in MENU}
MENU_BY_ID = {m["item_id"]: m for m in MENU}


def fmt_vnd(n):
    return "{:,}".format(int(n)).replace(",", ".") + "đ"


def by_kind(*kinds):
    return [m for m in MENU if m["kind"] in kinds]


# --------------------------------------------------------------------------
# CHI NHANH
# --------------------------------------------------------------------------
# (id, ten, thanh pho, dia chi, mo, dong, features)
_BR = [
    ("B01", "Nguyễn Huệ", "TP. Hồ Chí Minh", "Số 12 Nguyễn Huệ, Quận 1", "07:00", "22:30", "workspace outdoor power car_park moto_park kids_chair"),
    ("B02", "Võ Văn Tần", "TP. Hồ Chí Minh", "Số 88 Võ Văn Tần, Quận 3", "07:00", "22:00", "power moto_park outdoor"),
    ("B03", "Phạm Văn Đồng", "TP. Hồ Chí Minh", "Số 245 Phạm Văn Đồng, TP. Thủ Đức", "06:30", "22:00", "workspace power car_park moto_park kids_chair outdoor"),
    ("B04", "Crescent Mall", "TP. Hồ Chí Minh", "Tầng 1 Crescent Mall, Quận 7", "09:30", "22:00", "power car_park kids_chair"),
    ("B05", "Tràng Tiền", "Hà Nội", "Số 5 Tràng Tiền, Quận Hoàn Kiếm", "07:00", "22:00", "outdoor power moto_park"),
    ("B06", "Cầu Giấy", "Hà Nội", "Số 101 Cầu Giấy, Quận Cầu Giấy", "06:30", "22:30", "workspace power moto_park car_park"),
    ("B07", "Royal City", "Hà Nội", "Tầng B1 Royal City, Quận Thanh Xuân", "09:00", "22:00", "power car_park kids_chair"),
    ("B08", "Bạch Đằng", "Đà Nẵng", "Số 36 Bạch Đằng, Quận Hải Châu", "06:30", "23:00", "outdoor power moto_park car_park"),
    ("B09", "Vincom Ngô Quyền", "Đà Nẵng", "Tầng 1 Vincom Ngô Quyền, Quận Sơn Trà", "09:30", "22:00", "power car_park kids_chair"),
    ("B10", "Lạch Tray", "Hải Phòng", "Số 70 Lạch Tray, Quận Ngô Quyền", "07:00", "22:00", "power moto_park workspace"),
    ("B11", "Ninh Kiều", "Cần Thơ", "Số 18 Hòa Bình, Quận Ninh Kiều", "06:30", "22:00", "outdoor power moto_park car_park"),
    ("B12", "Trần Phú", "Nha Trang", "Số 40 Trần Phú, TP. Nha Trang", "06:30", "23:00", "outdoor power moto_park kids_chair"),
]
FEATURE_VI = {
    "workspace": "khu làm việc yên tĩnh", "outdoor": "chỗ ngồi ngoài trời",
    "power": "ổ cắm điện tại bàn", "car_park": "chỗ đỗ ô tô",
    "moto_park": "chỗ gửi xe máy", "kids_chair": "ghế ngồi cho trẻ em",
}
BRANCHES = [dict(branch_id=b[0], name="Highlands Coffee " + b[1], short=b[1], city=b[2], address=b[3],
                 open=b[4], close=b[5], features=b[6].split(),
                 phone="028 3000 %04d" % (100 + i)) for i, b in enumerate(_BR)]


def branches_with(feature):
    return [b for b in BRANCHES if feature in b["features"]]


# --------------------------------------------------------------------------
# FACTS - nguon su that cho FAQ + tai lieu noi bo
# --------------------------------------------------------------------------
F = dict(
    brand="Highlands Coffee",
    wifi_ssid="Highlands_Free", wifi_pw="coffee2026",
    open="07:00", close="22:00",
    hotline="1900 1234", email="cskh@highlands-sample.vn",
    reserve_min_people=8, reserve_hours_ahead=2, hold_minutes=15,
    birthday_min_people=10, birthday_days_ahead=1,
    cake_days_ahead=1, cake_from=250000,
    free_ship_km=3, free_ship_min=100000, ship_fee=15000,
    point_per=10000, redeem_points=100,
    student_pct=10, student_time="14:00 đến 17:00", student_days="Thứ Hai đến Thứ Sáu",
    remake_minutes=15,
    bulk_min_cups=20, bulk_hours_ahead=2, bulk_pct=5,
    split_max=4, cancel_app_minutes=3,
    gift_values="100.000đ, 200.000đ và 500.000đ", gift_months=12,
    lost_days=30, reply_hours=24,
    vat_deadline="22:00 cùng ngày", vat_email_hours=24,
    topping_low=10000, topping_high=15000,
)

# --------------------------------------------------------------------------
# KHUYEN MAI (thang 11/2026)
# --------------------------------------------------------------------------
PROMOS = [
    dict(id="P01", name="Thứ Ba Mua 2 Tặng 1", day="Thứ Ba hàng tuần",
         vi="Mua 2 đồ uống size M bất kỳ, tặng 1 đồ uống size M giá thấp nhất trong đơn.",
         en="Buy 2 size M drinks and get the cheapest size M drink free."),
    dict(id="P02", name="Giờ Vàng Bữa Sáng", day="mỗi ngày 07:00 đến 09:00",
         vi="Giảm 10% cho Combo Sáng Bánh Mì và Combo Sáng Croissant.",
         en="10% off the Banh Mi Breakfast Combo and Croissant Breakfast Combo."),
    dict(id="P03", name="Happy Student", day="Thứ Hai đến Thứ Sáu, 14:00 đến 17:00",
         vi="Giảm 10% đồ uống khi xuất trình thẻ học sinh hoặc sinh viên.",
         en="10% off drinks with a valid student card."),
    dict(id="P04", name="Quà Sinh Nhật Thành Viên", day="trong tháng sinh nhật",
         vi="Thành viên HL Rewards được tặng 1 đồ uống size M bất kỳ trong tháng sinh nhật.",
         en="HL Rewards members get one free size M drink during their birthday month."),
    dict(id="P05", name="Thứ Sáu Freeze Size L", day="Thứ Sáu hàng tuần",
         vi="Mua Freeze size M, nâng cấp lên size L miễn phí.",
         en="Buy a size M Freeze and upgrade to size L for free."),
    dict(id="P06", name="Đặt Nhóm 20 Ly", day="mỗi ngày",
         vi="Đơn từ 20 ly trở lên đặt trước ít nhất 2 giờ được giảm 5%.",
         en="Orders of 20 or more cups placed at least 2 hours ahead get 5% off."),
    dict(id="P07", name="Thứ Bảy Ngọt Ngào", day="Thứ Bảy hàng tuần",
         vi="Mua 1 đồ uống bất kỳ, giảm 20% bánh ngọt đi kèm.",
         en="Buy any drink and get 20% off a cake or pastry."),
    dict(id="P08", name="Giao Hàng Miễn Phí", day="mỗi ngày",
         vi="Miễn phí giao hàng trong bán kính 3km cho đơn từ 100.000đ.",
         en="Free delivery within 3 km for orders from 100,000 VND."),
    dict(id="P09", name="Thứ Tư Nhân Đôi Điểm", day="Thứ Tư hàng tuần",
         vi="Thành viên HL Rewards nhận gấp đôi điểm thưởng cho mọi đơn hàng.",
         en="HL Rewards members earn double points on every order."),
    dict(id="P10", name="Cuối Tuần Bạn Bè", day="Thứ Bảy và Chủ Nhật",
         vi="Mua Combo Bạn Bè được tặng 1 topping bất kỳ.",
         en="Buy the Friends Combo and get one free topping."),
]
PROMOS_ACTIVE_FAQ = ["P01", "P03", "P05", "P09"]

# --------------------------------------------------------------------------
# Tien ich van ban
# --------------------------------------------------------------------------

def strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def norm_text(s):
    """Chuan hoa de dedup: bo dau, lowercase, bo ky tu dac biet, gom khoang trang."""
    s = strip_accents(s).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def rng(seed_offset=0):
    return random.Random(SEED + seed_offset)
