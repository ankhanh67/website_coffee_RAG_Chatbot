# -*- coding: utf-8 -*-
"""Sinh du lieu C2: intent_extraction (SLM), cache_seed (response template), cache_eval_500."""
import json
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "cache")
os.makedirs(OUT, exist_ok=True)
R = random.Random(SEED + 99)
M = MENU_BY_VI


def p(name):   # "Ten (gia size M)"
    return "%s %s" % (name, fmt_vnd(M[name]["price_m"]))


def pe(name):
    return "%s (%s)" % (M[name]["name_en"], "{:,} VND".format(M[name]["price_m"]))


def pv(name):
    return "%s (%s)" % (name, fmt_vnd(M[name]["price_m"]))


ws = ", ".join(b["short"] for b in branches_with("workspace"))
cp = ", ".join(b["short"] for b in branches_with("car_park"))
cats = Counter(m["category"] for m in MENU)
cats_vi = ", ".join("%s (%d món)" % (k, v) for k, v in cats.items())
cats_en = {m["category"]: m["category_en"] for m in MENU}
cats_en_s = ", ".join("%s (%d items)" % (cats_en[k], v) for k, v in cats.items())
promo_vi = "; ".join("%s: %s" % (x["name"], x["vi"]) for x in PROMOS if x["id"] in PROMOS_ACTIVE_FAQ)
promo_en = "; ".join("%s: %s" % (x["name"], x["en"]) for x in PROMOS if x["id"] in PROMOS_ACTIVE_FAQ)

# gid, route, name, vi variants(5), en variants(4), resp_vi, resp_en, depends_on
G = [
 ("G01", "faq", "book_birthday_table",
  ["đặt bàn tiệc sinh nhật", "đặt bàn sinh nhật", "đặt chỗ tổ chức sinh nhật", "book bàn tiệc sinh nhật", "đặt bàn để tổ chức tiệc sinh nhật"],
  ["book a birthday party table", "reserve a table for a birthday party", "book a table for a birthday celebration", "set up a birthday party reservation"],
  "Quán nhận tiệc sinh nhật cho nhóm từ %d người, bạn đặt trước %d ngày qua hotline %s nhé. Quán tặng trang trí bóng bay cơ bản miễn phí." % (F["birthday_min_people"], F["birthday_days_ahead"], F["hotline"]),
  "We host birthday parties for groups of %d or more. Please book %d day ahead via hotline %s. Basic balloon decoration is free." % (F["birthday_min_people"], F["birthday_days_ahead"], F["hotline"]),
  ["faq:birthday_party", "doc:policy"]),
 ("G02", "faq", "book_group_table",
  ["đặt bàn cho nhóm đông", "đặt bàn nhóm", "đặt chỗ cho cả nhóm", "đặt trước bàn cho đoàn", "book bàn cho nhiều người"],
  ["book a table for a big group", "reserve a group table", "make a reservation for a large party", "book seating for our group"],
  "Nhóm từ %d người trở lên bạn đặt trước ít nhất %d giờ qua hotline %s nhé, quán giữ bàn tối đa %d phút." % (F["reserve_min_people"], F["reserve_hours_ahead"], F["hotline"], F["hold_minutes"]),
  "For groups of %d or more, please book at least %d hours ahead via hotline %s. We hold the table for up to %d minutes." % (F["reserve_min_people"], F["reserve_hours_ahead"], F["hotline"], F["hold_minutes"]),
  ["faq:reservation", "doc:policy"]),
 ("G03", "faq", "ask_wifi",
  ["hỏi tên wifi", "xin mật khẩu wifi", "hỏi mật khẩu wifi của quán", "xin pass wifi", "hỏi wifi của quán"],
  ["ask for the wifi password", "get the wifi name and password", "connect to your wifi", "know the wifi login"],
  "Wifi của quán tên là %s, mật khẩu là %s." % (F["wifi_ssid"], F["wifi_pw"]),
  "The wifi network is %s and the password is %s." % (F["wifi_ssid"], F["wifi_pw"]),
  ["faq:wifi"]),
 ("G04", "faq", "ask_hours",
  ["hỏi giờ mở cửa", "hỏi mấy giờ quán đóng cửa", "hỏi giờ hoạt động của quán", "biết giờ mở cửa của quán", "hỏi quán mở đến mấy giờ"],
  ["ask about your opening hours", "know what time you close", "check your closing time", "find out when you open"],
  "Hầu hết chi nhánh mở cửa từ %s đến %s mỗi ngày, riêng chi nhánh trong trung tâm thương mại theo giờ của trung tâm." % (F["open"], F["close"]),
  "Most branches are open from %s to %s daily, and mall branches follow the mall's hours." % (F["open"], F["close"]),
  ["faq:hours", "doc:branch"]),
 ("G05", "faq", "ask_payment",
  ["hỏi các hình thức thanh toán", "hỏi quán nhận thanh toán bằng gì", "hỏi có quẹt thẻ được không", "hỏi quán có nhận momo không", "biết cách thanh toán"],
  ["ask about payment methods", "know what payment you accept", "check if I can pay by card", "find out if you take e-wallets"],
  "Quán nhận tiền mặt, thẻ Visa, Mastercard, JCB, thẻ nội địa và các ví MoMo, ZaloPay, VNPay QR.",
  "We accept cash, Visa, Mastercard, JCB, domestic cards, and MoMo, ZaloPay and VNPay QR.",
  ["faq:payment"]),
 ("G06", "faq", "request_vat_invoice",
  ["xin xuất hóa đơn VAT", "xin hóa đơn đỏ", "lấy hóa đơn công ty", "hỏi cách xuất hóa đơn VAT", "xuất hóa đơn có mã số thuế"],
  ["request a VAT invoice", "get a company invoice", "ask how to get a tax invoice", "get an invoice with our tax code"],
  "Bạn yêu cầu hóa đơn VAT trước %s, cung cấp mã số thuế và email, hóa đơn điện tử được gửi trong %d giờ." % (F["vat_deadline"], F["vat_email_hours"]),
  "Request a VAT invoice before 22:00 the same day with your tax code and email, and the e-invoice arrives within %d hours." % F["vat_email_hours"],
  ["faq:vat_invoice", "doc:policy"]),
 ("G07", "order", "order_delivery",
  ["đặt giao hàng tận nơi", "hỏi quán có giao hàng không", "gọi đồ giao tận nhà", "hỏi về dịch vụ giao hàng", "đặt đồ uống giao về nhà"],
  ["order delivery", "ask if you deliver", "get my drinks delivered", "know about your delivery service"],
  "Quán giao hàng qua ứng dụng Highlands, GrabFood và ShopeeFood. Đơn từ %s trong %dkm được miễn phí giao hàng." % (fmt_vnd(F["free_ship_min"]), F["free_ship_km"]),
  "We deliver via the Highlands app, GrabFood and ShopeeFood. Orders of %s VND or more within %d km ship free." % ("{:,}".format(F["free_ship_min"]), F["free_ship_km"]),
  ["faq:delivery", "faq:delivery_fee", "doc:policy"]),
 ("G08", "faq", "ask_delivery_fee",
  ["hỏi phí giao hàng", "hỏi khi nào được miễn phí ship", "hỏi phí ship là bao nhiêu", "biết phí giao hàng", "hỏi giao hàng có mất phí không"],
  ["ask about the delivery fee", "know when delivery is free", "check the shipping cost", "find out how much delivery costs"],
  "Đơn từ %s trong bán kính %dkm được miễn phí giao hàng, ngoài ra phí giao hàng là %s." % (fmt_vnd(F["free_ship_min"]), F["free_ship_km"], fmt_vnd(F["ship_fee"])),
  "Orders of %s VND or more within %d km are free to deliver, otherwise the fee is %s VND." % ("{:,}".format(F["free_ship_min"]), F["free_ship_km"], "{:,}".format(F["ship_fee"])),
  ["faq:delivery_fee"]),
 ("G09", "faq", "ask_parking",
  ["hỏi chỗ gửi xe", "hỏi chỗ đậu ô tô", "hỏi quán có chỗ đỗ xe không", "tìm chỗ gửi xe máy", "hỏi về bãi đỗ xe"],
  ["ask about parking", "find a place to park my car", "know if there's motorbike parking", "check the parking situation"],
  "Hầu hết chi nhánh có chỗ gửi xe máy miễn phí. Chỗ đỗ ô tô có tại các chi nhánh %s." % cp,
  "Most branches have free motorbike parking. Car parking is available at %s." % cp,
  ["faq:parking", "doc:branch"]),
 ("G10", "faq", "loyalty_earn",
  ["hỏi cách tích điểm thành viên", "hỏi về thẻ HL Rewards", "đăng ký thẻ thành viên", "hỏi cách tích điểm", "hỏi về chương trình thành viên"],
  ["ask how to earn points", "learn about HL Rewards", "sign up for membership", "know how loyalty points work"],
  "Với thẻ HL Rewards, mỗi %s chi tiêu bạn nhận 1 điểm. Bạn có thể đăng ký qua ứng dụng Highlands hoặc tại quầy." % fmt_vnd(F["point_per"]),
  "With HL Rewards you earn 1 point for every %s VND spent. You can sign up in the Highlands app or at the counter." % "{:,}".format(F["point_per"]),
  ["faq:loyalty_earn", "doc:policy"]),
 ("G11", "faq", "loyalty_redeem",
  ["đổi điểm thưởng", "hỏi cách đổi điểm lấy nước", "đổi điểm lấy đồ uống", "hỏi bao nhiêu điểm đổi được ly nước", "dùng điểm thành viên"],
  ["redeem my points", "ask how to redeem points for a drink", "use my loyalty points", "know how many points a free drink costs"],
  "%d điểm đổi được 1 đồ uống size M bất kỳ trong menu, không gồm topping." % F["redeem_points"],
  "%d points can be redeemed for any size M drink on the menu, excluding toppings." % F["redeem_points"],
  ["faq:loyalty_redeem", "doc:policy"]),
 ("G12", "faq", "student_discount",
  ["hỏi giảm giá cho sinh viên", "hỏi ưu đãi học sinh sinh viên", "xin giảm giá sinh viên", "hỏi thẻ sinh viên có được giảm không", "hỏi khi nào có giảm giá sinh viên"],
  ["ask about the student discount", "get the student offer", "know if students get a discount", "use my student card for a discount"],
  "Học sinh, sinh viên được giảm %d%% đồ uống từ %s, %s khi xuất trình thẻ." % (F["student_pct"], F["student_days"], F["student_time"]),
  "Students get %d%% off drinks from Monday to Friday, 14:00 to 17:00, with a valid student card." % F["student_pct"],
  ["faq:student", "doc:promo"]),
 ("G13", "faq", "ask_promotions",
  ["hỏi khuyến mãi hôm nay", "hỏi chương trình ưu đãi", "hỏi quán đang có khuyến mãi gì", "xem các ưu đãi trong tuần", "hỏi có mua 1 tặng 1 không"],
  ["ask about today's promotions", "know what deals you have", "check current offers", "find out about this week's discounts"],
  "Các ưu đãi hiện có: " + promo_vi,
  "Current promotions: " + promo_en,
  ["faq:promotions", "doc:promo"]),
 ("G14", "faq", "buy_gift_card",
  ["mua thẻ quà tặng", "hỏi về thẻ quà tặng", "mua gift card", "hỏi thẻ quà tặng dùng được bao lâu", "mua thẻ quà tặng làm quà"],
  ["buy a gift card", "ask about gift cards", "get a gift card as a present", "know how long a gift card is valid"],
  "Quán bán thẻ quà tặng mệnh giá %s, hạn dùng %d tháng kể từ ngày mua." % (F["gift_values"], F["gift_months"]),
  "We sell gift cards of 100,000, 200,000 and 500,000 VND, valid for %d months from purchase." % F["gift_months"],
  ["faq:gift_card", "doc:policy"]),
 ("G15", "order", "order_birthday_cake",
  ["đặt bánh sinh nhật", "đặt bánh kem sinh nhật", "hỏi giá bánh sinh nhật", "đặt một cái bánh sinh nhật", "hỏi đặt bánh sinh nhật trước bao lâu"],
  ["order a birthday cake", "ask about birthday cake prices", "reserve a whole cake for a birthday", "know how early to order a birthday cake"],
  "Quán nhận đặt bánh sinh nhật nguyên cái, đặt trước %d ngày, giá từ %s." % (F["cake_days_ahead"], fmt_vnd(F["cake_from"])),
  "We take whole birthday cake orders with %d day's notice, starting from %s VND." % (F["cake_days_ahead"], "{:,}".format(F["cake_from"])),
  ["faq:birthday_cake", "doc:policy"]),
 ("G16", "faq", "feedback_complaint",
  ["góp ý về dịch vụ", "khiếu nại về món", "phản hồi chất lượng phục vụ", "hỏi số hotline để góp ý", "gửi phản ánh về quán"],
  ["give feedback about the service", "make a complaint", "contact customer service", "get your hotline number"],
  "Bạn gọi hotline %s hoặc gửi email %s, quán phản hồi trong %d giờ." % (F["hotline"], F["email"], F["reply_hours"]),
  "Call hotline %s or email %s and we will reply within %d hours." % (F["hotline"], F["email"], F["reply_hours"]),
  ["faq:complaint", "doc:policy"]),
 ("G17", "faq", "pets_policy",
  ["hỏi mang thú cưng vào quán", "hỏi quán có cho dắt chó không", "dắt thú cưng vào", "hỏi quán có cho mang mèo vào không", "hỏi chính sách thú cưng"],
  ["ask if I can bring my pet", "bring my dog in", "know your pet policy", "check if cats are allowed"],
  "Quán không cho phép mang thú cưng vào, trừ chó dẫn đường cho người khiếm thị.",
  "Pets are not allowed, except guide dogs for visually impaired guests.",
  ["faq:pets", "doc:policy"]),
 ("G18", "faq", "find_workspace",
  ["tìm chỗ yên tĩnh để làm việc", "hỏi chi nhánh nào có khu làm việc", "tìm chỗ ngồi làm việc có ổ cắm", "tìm chỗ ngồi học bài yên tĩnh", "hỏi chỗ ngồi làm việc với laptop"],
  ["find a quiet place to work", "know which branch has a workspace", "find a seat with a power outlet", "find a quiet spot to study"],
  "Khu làm việc yên tĩnh có tại các chi nhánh %s, hầu hết chi nhánh đều có ổ cắm tại bàn." % ws,
  "Quiet workspaces are at %s, and most branches have power outlets at the tables." % ws,
  ["faq:quiet_space", "faq:power", "doc:branch"]),
 ("G19", "faq", "remake_wrong_drink",
  ["đổi món pha sai", "hỏi làm lại nước bị sai", "xin làm lại ly nước", "hỏi chính sách đổi món", "phản ánh món bị pha sai"],
  ["get my wrong drink remade", "ask about your remake policy", "report a mistake with my drink", "exchange a drink that was made wrong"],
  "Nếu món pha sai hoặc có vấn đề, quán sẽ làm lại món mới trong vòng %d phút kể từ khi bạn nhận món." % F["remake_minutes"],
  "If your drink is made wrong or has a problem, we will remake it within %d minutes of you receiving it." % F["remake_minutes"],
  ["faq:refund", "doc:policy"]),
 ("G20", "faq", "allergen_info",
  ["hỏi thông tin dị ứng của món", "hỏi món nào có sữa", "hỏi món có chứa hạt không", "hỏi thành phần gây dị ứng", "hỏi món nào có gluten"],
  ["ask about allergens", "know which items contain milk", "check if an item has nuts", "find out about allergy information"],
  "Menu ghi rõ nhóm dị ứng của từng món gồm sữa, hạt, gluten và trứng. Quán không thể đảm bảo tuyệt đối không lây nhiễm chéo nên bạn nhớ báo nhân viên khi đặt món.",
  "The menu lists allergens per item: milk, nuts, gluten and egg. We cannot fully rule out cross contamination, so please tell the staff when ordering.",
  ["faq:allergens", "menu:*", "doc:policy"]),
 ("G21", "consultant", "rec_cold_drink",
  ["tìm món uống giải nhiệt", "xin gợi ý đồ uống mát", "hỏi món nào uống cho mát", "tìm đồ uống lạnh giải khát", "hỏi gợi ý nước mát"],
  ["find a refreshing drink", "get a cool drink recommendation", "ask for something cold to drink", "find a drink to cool down"],
  "Bạn có thể thử %s, %s hoặc %s." % (pv("Trà Đào Cam Sả"), pv("Freeze Trà Xanh"), pv("Nước Ép Dưa Hấu")),
  "You could try %s, %s or %s." % (pe("Trà Đào Cam Sả"), pe("Freeze Trà Xanh"), pe("Nước Ép Dưa Hấu")),
  ["menu:*"]),
 ("G22", "consultant", "rec_bestseller",
  ["hỏi món bán chạy nhất", "hỏi món nào được gọi nhiều", "hỏi quán có món gì signature", "xin gợi ý món nổi bật", "hỏi món đặc trưng của quán"],
  ["ask for your best seller", "know what's popular", "ask for your signature drink", "get your top recommendation"],
  "Món bán chạy nhất là %s, ngoài ra %s và %s cũng được gọi nhiều." % (pv("Trà Đào Cam Sả"), pv("Phin Sữa Đá"), pv("Bạc Xỉu")),
  "Our best seller is %s, and %s and %s are also very popular." % (pe("Trà Đào Cam Sả"), pe("Phin Sữa Đá"), pe("Bạc Xỉu")),
  ["menu:*"]),
 ("G23", "consultant", "rec_low_sugar",
  ["tìm món ít đường", "xin gợi ý đồ uống ít ngọt", "hỏi món nào không đường", "tìm đồ uống cho người ăn kiêng", "hỏi món ít ngọt"],
  ["find a low sugar drink", "get a less sweet recommendation", "ask for a sugar-free option", "find a drink for someone on a diet"],
  "Bạn có thể chọn %s, %s hoặc %s và chọn mức đường 0%%. Các món khác bạn cũng chọn được mức đường 30%%, 50%% hoặc 70%%." % (pv("Phin Đen Đá"), pv("Americano"), pv("Cold Brew")),
  "Try %s, %s or %s at 0%% sugar. Other drinks can be made at 30%%, 50%% or 70%% sugar too." % (pe("Phin Đen Đá"), pe("Americano"), pe("Cold Brew")),
  ["menu:*", "faq:sugar_ice"]),
 ("G24", "consultant", "rec_no_caffeine",
  ["tìm đồ uống không caffeine", "hỏi món nào không có caffeine", "xin gợi ý nước không cà phê", "tìm món uống không gây mất ngủ", "hỏi đồ uống không chứa caffeine"],
  ["find a caffeine free drink", "ask for a drink without caffeine", "get a non-coffee recommendation", "find something that won't keep me awake"],
  "Các món không caffeine gồm %s, %s, %s và %s." % (pv("Trà Hoa Cúc Mật Ong"), pv("Chocolate Nóng"), pv("Sinh Tố Xoài"), pv("Nước Ép Cam")),
  "Caffeine-free options include %s, %s, %s and %s." % (pe("Trà Hoa Cúc Mật Ong"), pe("Chocolate Nóng"), pe("Sinh Tố Xoài"), pe("Nước Ép Cam")),
  ["menu:*", "faq:decaf"]),
 ("G25", "consultant", "rec_vegan",
  ["tìm món chay", "hỏi món nào ăn chay được", "xin gợi ý món chay", "tìm đồ uống không có sữa", "hỏi đồ uống thuần chay"],
  ["find a vegan option", "ask for a vegan recommendation", "know what has no dairy", "find a plant-based drink"],
  "Món chay gồm %s, %s, %s và %s. Bạn cũng có thể đổi sang sữa yến mạch với %s." % (pv("Salad Rau Củ"), pv("Khoai Tây Chiên"), pv("Cold Brew"), pv("Nước Ép Cam"), fmt_vnd(M["Đổi Sữa Yến Mạch"]["price_m"])),
  "Vegan options include %s, %s, %s and %s. You can also swap to oat milk for %s VND." % (pe("Salad Rau Củ"), pe("Khoai Tây Chiên"), pe("Cold Brew"), pe("Nước Ép Cam"), "{:,}".format(M["Đổi Sữa Yến Mạch"]["price_m"])),
  ["menu:*", "faq:vegan"]),
 ("G26", "consultant", "rec_strong_coffee",
  ["tìm cà phê đậm vị", "xin gợi ý cà phê đậm", "hỏi món cà phê nào đắng nhất", "tìm cà phê ít sữa", "hỏi cà phê nào mạnh nhất"],
  ["find a strong coffee", "get a bold coffee recommendation", "ask which coffee is the most bitter", "find a coffee with little milk"],
  "Bạn có thể thử %s, %s hoặc %s. Muốn đậm hơn thì thêm Shot Espresso với %s." % (pv("Phin Đen Đá"), pv("Espresso"), pv("Americano"), fmt_vnd(M["Shot Espresso Thêm"]["price_m"])),
  "Try %s, %s or %s. For extra strength add an espresso shot for %s VND." % (pe("Phin Đen Đá"), pe("Espresso"), pe("Americano"), "{:,}".format(M["Shot Espresso Thêm"]["price_m"])),
  ["menu:*"]),
 ("G27", "consultant", "rec_sweet",
  ["tìm món ngọt", "xin gợi ý món tráng miệng", "hỏi bánh ngọt nào ngon", "tìm bánh ăn kèm cà phê", "hỏi món nào ngọt béo"],
  ["find something sweet", "get a dessert recommendation", "ask which cake is good", "find a cake to go with coffee"],
  "Bạn có thể thử %s, %s, %s hoặc %s." % (pv("Bánh Tiramisu"), pv("Bánh Phô Mai Chanh Dây"), pv("Bánh Brownie"), pv("Cookies & Cream Freeze")),
  "You could try %s, %s, %s or %s." % (pe("Bánh Tiramisu"), pe("Bánh Phô Mai Chanh Dây"), pe("Bánh Brownie"), pe("Cookies & Cream Freeze")),
  ["menu:*"]),
 ("G28", "consultant", "rec_kids",
  ["tìm đồ uống cho trẻ em", "xin gợi ý món cho bé", "hỏi món nào bé uống được", "tìm món cho con nhỏ", "hỏi đồ uống không caffeine cho bé"],
  ["find a drink for kids", "get a recommendation for a child", "ask what my kid can drink", "find something suitable for children"],
  "Với trẻ em bạn có thể chọn %s, %s hoặc %s. Quán khuyến nghị không dùng đồ uống có caffeine cho trẻ dưới 12 tuổi." % (pv("Sinh Tố Xoài"), pv("Nước Ép Cam"), pv("Chocolate Nóng")),
  "For kids try %s, %s or %s. We advise against caffeinated drinks for children under 12." % (pe("Sinh Tố Xoài"), pe("Nước Ép Cam"), pe("Chocolate Nóng")),
  ["menu:*", "doc:policy"]),
 ("G29", "consultant", "view_menu",
  ["xem menu", "xin xem thực đơn", "hỏi quán có những món gì", "xem các loại đồ uống", "xin xem danh sách món"],
  ["see the menu", "ask what you serve", "look at your drink list", "know what's on offer"],
  "Menu gồm %d món: %s. Bạn muốn mình giới thiệu nhóm nào trước?" % (len(MENU), cats_vi),
  "The menu has %d items: %s. Which category would you like to start with?" % (len(MENU), cats_en_s),
  ["menu:*"]),
 ("G30", "consultant", "rec_light_meal",
  ["tìm món ăn sáng", "xin gợi ý món ăn nhẹ", "hỏi món nào ăn no", "tìm món ăn trưa", "hỏi có món mặn nào ngon"],
  ["find breakfast", "get a light meal recommendation", "ask for something filling", "find a lunch option"],
  "Bạn có thể chọn %s, %s, %s hoặc %s." % (pv("Combo Sáng Bánh Mì"), pv("Combo Sáng Croissant"), pv("Mì Ý Bò Bằm"), pv("Cơm Gà Teriyaki")),
  "You could pick %s, %s, %s or %s." % (pe("Combo Sáng Bánh Mì"), pe("Combo Sáng Croissant"), pe("Mì Ý Bò Bằm"), pe("Cơm Gà Teriyaki")),
  ["menu:*"]),
]
assert len(G) == 30
GBY = {g[0]: g for g in G}

# ------------------------------------------------------------- slots / templates
SUBJ_VI = ["anh", "chị", "em", "tôi", "mình", "cô", "chú", "bác", "tụi mình", "nhà mình"]
TIME_VI = ["ngày mai lúc 7h", "tối nay", "cuối tuần này", "lúc 3 giờ chiều", "sáng mai", "thứ Bảy tuần này", "8 giờ tối nay",
           "chiều mai", "trưa nay", "vào Chủ Nhật", "hôm nay", "tuần sau", "ngày 20 tháng này", "lúc 10 giờ sáng"]
PEOPLE_VI = ["cho 6 người", "cho nhóm 10 người", "cho 4 người", "cho cả gia đình", "cho 12 người", "cho hai người", "cho 3 người", "cho 15 người"]
PLACE_VI = ["ở chi nhánh Nguyễn Huệ", "tại chi nhánh Cầu Giấy", "ở chi nhánh Bạch Đằng", "ở Crescent Mall", "tại chi nhánh Trần Phú",
            "ở chi nhánh Võ Văn Tần", "tại Royal City"]
OCC_VI = ["cho buổi họp nhóm", "cho dịp kỷ niệm", "cho bạn gái", "cho khách hàng", "cho con gái 5 tuổi", "cho ba mẹ", "cho đồng nghiệp"]
TIME_EN = ["tomorrow at 7pm", "tonight", "this weekend", "at 3 in the afternoon", "tomorrow morning", "this Saturday", "at 8 tonight",
           "tomorrow afternoon", "at noon today", "on Sunday", "today", "next week", "on the 20th", "at 10 in the morning"]
PEOPLE_EN = ["for 6 people", "for a group of 10", "for 4 people", "for the whole family", "for 12 people", "for two", "for 3 people", "for 15 people"]
PLACE_EN = ["at the Nguyen Hue branch", "at the Cau Giay branch", "at the Bach Dang branch", "at Crescent Mall", "at the Tran Phu branch",
            "at the Vo Van Tan branch", "at Royal City"]
OCC_EN = ["for a team meeting", "for our anniversary", "for my girlfriend", "for a client", "for my 5 year old daughter", "for my parents", "for a coworker"]

# (template, uses_subject, needs_ctx_first)
TPL_VI = [
    ("Cho {S} {A} {C} nhé", 1), ("{S} muốn {A} {C}", 1), ("{S} cần {A} {C} ạ", 1), ("Em ơi, {S} muốn {A} {C}", 1),
    ("{C}, {S} muốn {A} nha", 1), ("{S} định {A} {C}, được không em", 1), ("Nhờ em giúp {S} {A} {C}", 1),
    ("{S} đang muốn {A} {C} đó em", 1), ("{S} muốn {A} {C} thì làm sao", 1), ("Chào em, cho {S} {A} {C} với", 1),
    ("Cho hỏi, {A} {C} thế nào ạ", 0), ("{A} {C} nhé", 0), ("Xin hỏi, muốn {A} {C} thì sao", 0), ("Muốn {A} {C} thì làm sao em", 0),
]
HELD_OUT_VI = {"{S} định {A} {C}, được không em", "Muốn {A} {C} thì làm sao em"}     # chi xuat hien o val/test
TPL_EN = [
    ("I'd like to {A} {C}", "I"), ("Can I {A} {C}?", "I"), ("We'd like to {A} {C}", "We"), ("I want to {A} {C}", "I"),
    ("{C}, I'd like to {A}", "I"), ("Could we {A} {C}?", "we"), ("I need to {A} {C}", "I"), ("Hi, I'd like to {A} {C}", "I"),
    ("Please help me {A} {C}", "me"), ("Can you help us {A} {C}?", "us"), ("Hey, we want to {A} {C}", "we"),
    ("How can I {A} {C}?", "I"), ("Is it possible for us to {A} {C}?", "us"),
]
HELD_OUT_EN = {"How can I {A} {C}?", "Is it possible for us to {A} {C}?"}


def make_ctx(lang, r, force_empty=None):
    T, Pp, Pl, O = (TIME_VI, PEOPLE_VI, PLACE_VI, OCC_VI) if lang == "vi" else (TIME_EN, PEOPLE_EN, PLACE_EN, OCC_EN)
    if force_empty or r.random() < .12:
        return ""
    k = r.choices([1, 2, 3], weights=[.5, .4, .1])[0]
    parts = []
    for pool in r.sample([T, Pp, Pl, O], k):
        parts.append(r.choice(pool))
    # thu tu tu nhien: thoi gian truoc, nguoi, dia diem, dip
    order = {id(T): 0, id(Pp): 1, id(Pl): 2, id(O): 3}
    return " ".join(parts) if k == 1 else " ".join(sorted(parts, key=lambda x: (x in O, x in Pl, x in Pp)))


def build_sample(gid, lang, split, r, variants_scope):
    g = GBY[gid]
    vi_v, en_v = g[3], g[4]
    if variants_scope == "seen":
        A = r.choice(vi_v[:3] if lang == "vi" else en_v[:2])
    else:
        A = r.choice(vi_v if lang == "vi" else en_v)
    C = make_ctx(lang, r)
    if lang == "vi":
        pool = [t for t in TPL_VI if (variants_scope == "all" or t[0] not in HELD_OUT_VI)]
        tpl, has_s = r.choice(pool)
        if tpl.startswith("{C}") and not C:
            return None
        S = r.choice(SUBJ_VI) if has_s else ""
        text = tpl.format(S=S, A=A, C=C)
    else:
        pool = [t for t in TPL_EN if (variants_scope == "all" or t[0] not in HELD_OUT_EN)]
        tpl, S = r.choice(pool)
        if tpl.startswith("{C}") and not C:
            return None
        text = tpl.format(A=A, C=C)
    text = " ".join(text.split()).replace(" ,", ",").replace(" ?", "?")
    text = text.rstrip(" ,")
    subj, act, ctx = S, A, C
    # augmentation dong bo voi nhan
    if r.random() < .25:
        text, subj, act, ctx = text.lower(), subj.lower(), act.lower(), ctx.lower()
    if lang == "vi" and r.random() < .08:
        text, subj, act, ctx = strip_accents(text), strip_accents(subj), strip_accents(act), strip_accents(ctx)
    if r.random() < .4:
        text = text.rstrip("?.!")
    assert act in text and (not ctx or ctx in text) and (not subj or subj in text), (text, subj, act, ctx)
    return dict(text=text, language=lang, subject=subj, action=act, context=ctx, action_group=gid, route=g[1], tpl=tpl)


def main():
    # ---------------- intent_extraction ----------------
    seen = set()
    rows = []
    plan = [("train", 1200, "seen"), ("val", 150, "all"), ("test", 150, "all")]
    gids = [g[0] for g in G]
    for split, n, scope in plan:
        k = 0
        guard = 0
        while k < n and guard < 400000:
            guard += 1
            gid = gids[k % 30]
            lang = "vi" if R.random() < .6 else "en"
            s = build_sample(gid, lang, split, R, scope)
            if not s:
                continue
            nm = norm_text(s["text"])
            if nm in seen:
                continue
            seen.add(nm)
            s["split"] = split
            rows.append(s)
            k += 1
    for i, s in enumerate(rows, 1):
        s["id"] = "IE-%04d" % i
        s["cache_key"] = s["action"]
        s.pop("tpl")
    cols = ["id", "split", "text", "language", "subject", "action", "context", "cache_key", "action_group", "route"]
    rows = [{c: s[c] for c in cols} for s in rows]
    json.dump(rows, open(os.path.join(OUT, "intent_extraction.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sysmsg = ('Tách câu nói của khách thành 3 thành phần và chỉ trả JSON: {"subject": chủ ngữ (ai nói/yêu cầu, "" nếu không có), '
              '"action": hành động/yêu cầu cốt lõi (dùng làm cache key, KHÔNG gồm thời gian/số người/địa điểm), '
              '"context": ngữ cảnh/thời gian/số lượng người/dịp ("" nếu không có)}. Giữ nguyên chữ trong câu gốc.')
    for split in ("train", "val", "test"):
        with open(os.path.join(OUT, "intent_extraction_%s_sft.jsonl" % split), "w", encoding="utf-8") as f:
            for s in rows:
                if s["split"] != split:
                    continue
                f.write(json.dumps({"messages": [
                    {"role": "system", "content": sysmsg}, {"role": "user", "content": s["text"]},
                    {"role": "assistant", "content": json.dumps({"subject": s["subject"], "action": s["action"], "context": s["context"]}, ensure_ascii=False)}]},
                    ensure_ascii=False) + "\n")

    # ---------------- cache_seed + invalidation map ----------------
    seed = []
    inval = defaultdict(list)
    for gid, route, name, vi_v, en_v, rvi, ren, deps in G:
        seed.append(dict(group_id=gid, name=name, route=route,
                         canonical_action_vi=vi_v[0], canonical_action_en=en_v[0],
                         seed_actions_vi=vi_v[:3], seed_actions_en=en_v[:2],
                         response_template_vi=rvi, response_template_en=ren, depends_on=deps, ttl_hours=24 * 7))
        for d in deps:
            inval[d].append(gid)
    seed_doc = dict(
        note="Cache hit: render = opening + response_template + (neu co context) tail.format(context=...) + closing. Chon ngau nhien 1 phan tu moi muc de paraphrase tu nhien.",
        openings_vi=["Dạ vâng ạ,", "Dạ,", "Dạ được ạ,", "Vâng ạ,"], closings_vi=["Mình hỗ trợ thêm gì nữa không ạ?", "Bạn cần mình giúp gì thêm không ạ?", ""],
        context_tails_vi=["Mình lưu ý thêm thông tin: {context}.", "Mình đã ghi chú thêm: {context}.", "Thông tin kèm theo của bạn là {context}, mình đã ghi nhận."],
        openings_en=["Sure,", "Of course,", "Certainly,", ""], closings_en=["Is there anything else I can help with?", "Anything else I can do for you?", ""],
        context_tails_en=["I've also noted: {context}.", "Noted, {context}.", "I'll keep in mind: {context}."],
        groups=seed)
    json.dump(seed_doc, open(os.path.join(OUT, "cache_seed.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(dict(note="Khi nguon thay doi -> xoa cac group_id tuong ung khoi cache. 'menu:*' = bat ky thay doi menu.csv; 'faq:<topic_id>' = dong faq.csv; 'doc:<doc_id>' = tai lieu.",
                   map=inval), open(os.path.join(OUT, "cache_invalidation_map.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---------------- cache_eval_500 ----------------
    OOS_VI = ["đặt tiệc cưới 200 khách", "xin việc làm phục vụ", "mượn micro để phát biểu", "chụp ảnh sản phẩm trong quán", "thuê cả quán một ngày",
              "đặt xe taxi về nhà", "hỏi đường đi sân bay", "đổi tiền ngoại tệ", "sửa điện thoại bị hỏng", "mua cà phê hạt rang xay mang về nhà",
              "in tài liệu tại quán", "gửi hành lý ở quán", "thuê phòng họp riêng có máy chiếu", "đặt hoa tặng vợ"]
    OOS_EN = ["book a wedding reception for 200 guests", "apply for a barista job", "borrow a microphone for a speech", "shoot a product photo here",
              "rent the whole cafe for a day", "call a taxi home", "ask for directions to the airport", "exchange foreign currency",
              "repair my broken phone", "buy whole roasted beans to take home", "print some documents", "leave my luggage here",
              "rent a private meeting room with a projector", "order flowers for my wife"]
    ev = []
    ev_seen = set(seen)
    r = random.Random(SEED + 500)
    hit_per = [15] * 5 + [14] * 25     # 425
    r.shuffle(hit_per)
    for gid, cnt in zip(gids, hit_per):
        k = guard = 0
        while k < cnt and guard < 5000:
            guard += 1
            lang = "vi" if r.random() < .6 else "en"
            s = build_sample(gid, lang, "eval", r, "all")
            if not s:
                continue
            nm = norm_text(s["text"])
            if nm in ev_seen:
                continue
            ev_seen.add(nm)
            ev.append(dict(text=s["text"], language=lang, expected_hit=True, expected_group=gid, expected_route=s["route"],
                           gold_subject=s["subject"], gold_action=s["action"], gold_context=s["context"], has_context=bool(s["context"])))
            k += 1
    miss = 0
    guard = 0
    while miss < 75 and guard < 5000:
        guard += 1
        lang = "vi" if r.random() < .6 else "en"
        A = r.choice(OOS_VI if lang == "vi" else OOS_EN)
        C = make_ctx(lang, r)
        if lang == "vi":
            tpl, has_s = r.choice(TPL_VI)
            if tpl.startswith("{C}") and not C:
                continue
            S = r.choice(SUBJ_VI) if has_s else ""
            text = tpl.format(S=S, A=A, C=C)
        else:
            tpl, S = r.choice(TPL_EN)
            if tpl.startswith("{C}") and not C:
                continue
            text = tpl.format(A=A, C=C)
        text = " ".join(text.split()).replace(" ,", ",").replace(" ?", "?").rstrip(" ,")
        nm = norm_text(text)
        if nm in ev_seen:
            continue
        ev_seen.add(nm)
        ev.append(dict(text=text, language=lang, expected_hit=False, expected_group=None, expected_route=None,
                       gold_subject=S, gold_action=A, gold_context=C, has_context=bool(C)))
        miss += 1
    r.shuffle(ev)
    for i, e in enumerate(ev, 1):
        e["id"] = "CE-%03d" % i
    ev = [dict(id=e.pop("id"), **e) for e in ev]
    json.dump(ev, open(os.path.join(OUT, "cache_eval_500.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("intent_extraction:", Counter(x["split"] for x in rows), Counter(x["language"] for x in rows),
          "no-subject=%d no-ctx=%d" % (sum(not x["subject"] for x in rows), sum(not x["context"] for x in rows)))
    print("cache_eval:", len(ev), "hit=%d miss=%d" % (sum(e["expected_hit"] for e in ev), sum(not e["expected_hit"] for e in ev)),
          Counter(e["language"] for e in ev), "ctx=%d" % sum(e["has_context"] for e in ev))


if __name__ == "__main__":
    main()
