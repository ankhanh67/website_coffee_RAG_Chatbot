# -*- coding: utf-8 -*-
"""Sinh data/kb/menu.csv va data/kb/faq.csv (+ faq_topics.json cho rag_eval)."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "kb")
os.makedirs(OUT, exist_ok=True)

# ----------------------------- MENU CSV ------------------------------------
MENU_COLS = ["item_id", "name_vi", "name_en", "category", "category_en", "price_s", "price_m", "price_l",
             "sizes", "temperature", "caffeine", "vegan", "allergens", "ingredients",
             "description_vi", "description_en"]
with open(os.path.join(OUT, "menu.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=MENU_COLS, extrasaction="ignore")
    w.writeheader()
    w.writerows(MENU)

# ----------------------------- FAQ -----------------------------------------
ws = ", ".join(b["short"] for b in branches_with("workspace"))
cp = ", ".join(b["short"] for b in branches_with("car_park"))
kc = ", ".join(b["short"] for b in branches_with("kids_chair"))
wsE = ws
promo = {p["id"]: p for p in PROMOS}
late = [b["short"] for b in BRANCHES if b["close"] > F["close"]]
promos_vi = "; ".join("%s (%s): %s" % (promo[i]["name"], promo[i]["day"], promo[i]["vi"]) for i in PROMOS_ACTIVE_FAQ)
promos_en = "; ".join("%s (%s): %s" % (promo[i]["name"], promo[i]["day"], promo[i]["en"]) for i in PROMOS_ACTIVE_FAQ)
S = SIZES_ML

TOPICS = []


def T(tid, cat, qv1, qv2, qe1, qe2, av, ae):
    TOPICS.append(dict(topic_id=tid, category=cat, q=[qv1, qv2, qe1, qe2], a_vi=av, a_en=ae))


T("wifi", "Tiện ích", "Wifi tên gì vậy?", "Cho mình xin mật khẩu wifi với.",
  "What's the wifi name?", "Can I get the wifi password?",
  "Wifi của quán tên là %s, mật khẩu là %s ạ." % (F["wifi_ssid"], F["wifi_pw"]),
  "The wifi network is %s and the password is %s." % (F["wifi_ssid"], F["wifi_pw"]))
T("hours", "Giờ hoạt động", "Mấy giờ quán đóng cửa vậy?", "Quán mở cửa lúc mấy giờ?",
  "What time do you close?", "What are your opening hours?",
  "Hầu hết chi nhánh mở cửa từ %s đến %s mỗi ngày. Một số chi nhánh trong trung tâm thương mại theo giờ của trung tâm, bạn cho mình biết chi nhánh để mình kiểm tra chính xác nhé." % (F["open"], F["close"]),
  "Most branches are open from %s to %s every day. Branches inside shopping malls follow the mall's hours, so tell me which branch and I will check." % (F["open"], F["close"]))
T("hours_late", "Giờ hoạt động", "Quán có mở khuya không?", "Chi nhánh nào mở cửa trễ nhất?",
  "Are you open late at night?", "Which branch closes the latest?",
  "Chi nhánh đóng cửa trễ nhất là %s, mở đến 23:00. Các chi nhánh Nguyễn Huệ và Cầu Giấy đóng lúc 22:30, còn lại đóng lúc 22:00." % ", ".join(b["short"] for b in BRANCHES if b["close"] == "23:00"),
  "The latest closing time is 23:00 at %s. Nguyen Hue and Cau Giay close at 22:30, and the rest close at 22:00." % ", ".join(b["short"] for b in BRANCHES if b["close"] == "23:00"))
T("hours_holiday", "Giờ hoạt động", "Dịp Tết quán có mở cửa không?", "Ngày lễ quán có làm việc không?",
  "Are you open on public holidays?", "Do you open during Tet?",
  "Quán mở cửa vào ngày lễ. Dịp Tết Nguyên Đán giờ mở cửa có thể thay đổi theo từng chi nhánh, thông tin được cập nhật trên ứng dụng và gọi hotline %s để biết thêm." % F["hotline"],
  "We are open on public holidays. During Lunar New Year the hours may change by branch, and updates are posted in the app or via our hotline %s." % F["hotline"])
T("payment", "Thanh toán", "Quán nhận thanh toán bằng gì?", "Có quẹt thẻ hay trả bằng Momo được không?",
  "What payment methods do you accept?", "Can I pay by card or e-wallet?",
  "Quán nhận tiền mặt, thẻ Visa, Mastercard, JCB, thẻ nội địa, và các ví MoMo, ZaloPay, VNPay QR ạ.",
  "We accept cash, Visa, Mastercard, JCB, domestic cards, and the MoMo, ZaloPay and VNPay QR wallets.")
T("split_bill", "Thanh toán", "Có tách hóa đơn được không?", "Nhóm mình muốn chia tiền riêng thì sao?",
  "Can we split the bill?", "Is it possible to pay separately?",
  "Bạn có thể tách hóa đơn tối đa %d phần cho một bàn, vui lòng báo nhân viên trước khi thanh toán." % F["split_max"],
  "You can split the bill into up to %d parts per table. Please tell the staff before paying." % F["split_max"])
T("vat_invoice", "Thanh toán", "Làm sao để xuất hóa đơn VAT?", "Mình cần hóa đơn công ty thì làm thế nào?",
  "How do I get a VAT invoice?", "Can I get a company invoice?",
  "Bạn yêu cầu xuất hóa đơn VAT trước %s, cung cấp mã số thuế và email. Hóa đơn điện tử được gửi qua email trong vòng %d giờ." % (F["vat_deadline"], F["vat_email_hours"]),
  "Request a VAT invoice before 22:00 on the same day with your tax code and email. The e-invoice is emailed within %d hours." % F["vat_email_hours"])
T("price_vat", "Thanh toán", "Giá trên menu đã gồm thuế chưa?", "Có phụ thu phí dịch vụ không?",
  "Do menu prices include tax?", "Is there any service charge?",
  "Giá niêm yết trên menu đã bao gồm thuế VAT. Quán không thu phí dịch vụ.",
  "Menu prices already include VAT. There is no service charge.")
T("reservation", "Đặt bàn", "Mình muốn đặt bàn cho nhóm đông thì làm sao?", "Đặt bàn trước bao lâu và giữ bàn bao lâu?",
  "How do I reserve a table for a big group?", "How far ahead should I book and how long do you hold the table?",
  "Nhóm từ %d người trở lên vui lòng đặt trước ít nhất %d giờ qua hotline %s. Quán giữ bàn tối đa %d phút so với giờ hẹn." % (F["reserve_min_people"], F["reserve_hours_ahead"], F["hotline"], F["hold_minutes"]),
  "Groups of %d or more should book at least %d hours ahead via hotline %s. We hold the table for up to %d minutes after the booking time." % (F["reserve_min_people"], F["reserve_hours_ahead"], F["hotline"], F["hold_minutes"]))
T("birthday_party", "Đặt bàn", "Quán có nhận tổ chức tiệc sinh nhật không?", "Đặt bàn tiệc sinh nhật cần chuẩn bị gì?",
  "Do you host birthday parties?", "What do I need to book a birthday party?",
  "Quán nhận tiệc sinh nhật cho nhóm từ %d người, vui lòng đặt trước %d ngày qua hotline. Quán tặng trang trí bóng bay cơ bản miễn phí." % (F["birthday_min_people"], F["birthday_days_ahead"]),
  "We host birthday parties for groups of %d or more. Please book %d day ahead via the hotline. Basic balloon decoration is free." % (F["birthday_min_people"], F["birthday_days_ahead"]))
T("birthday_cake", "Đặt bàn", "Quán có bán bánh sinh nhật nguyên cái không?", "Đặt bánh sinh nhật giá bao nhiêu?",
  "Do you sell whole birthday cakes?", "How much is a birthday cake order?",
  "Quán nhận đặt bánh sinh nhật nguyên cái, đặt trước %d ngày, giá từ %s." % (F["cake_days_ahead"], fmt_vnd(F["cake_from"])),
  "We take orders for whole birthday cakes with %d day's notice, starting from %s." % (F["cake_days_ahead"], "{:,}".format(F["cake_from"]) + " VND"))
T("delivery", "Giao hàng", "Quán có giao hàng tận nơi không?", "Đặt giao hàng qua đâu được?",
  "Do you deliver?", "Where can I order delivery?",
  "Quán có giao hàng qua ứng dụng Highlands, GrabFood và ShopeeFood.",
  "Yes, we deliver through the Highlands app, GrabFood and ShopeeFood.")
T("delivery_fee", "Giao hàng", "Phí giao hàng là bao nhiêu?", "Khi nào được miễn phí ship?",
  "How much is the delivery fee?", "When is delivery free?",
  "Đơn từ %s trong bán kính %dkm được miễn phí giao hàng. Ngoài ra phí giao hàng là %s." % (fmt_vnd(F["free_ship_min"]), F["free_ship_km"], fmt_vnd(F["ship_fee"])),
  "Orders of %s or more within %d km get free delivery. Otherwise the delivery fee is %s." % ("{:,}".format(F["free_ship_min"]) + " VND", F["free_ship_km"], "{:,}".format(F["ship_fee"]) + " VND"))
T("takeaway", "Giao hàng", "Mình mua mang đi được không?", "Mang về có tính thêm phí không?",
  "Can I get my order to go?", "Is there an extra charge for takeaway?",
  "Bạn có thể mua mang đi, ly và túi đều không tính thêm phí.",
  "Yes, takeaway is available and cups and bags are free of charge.")
T("cancel_order", "Giao hàng", "Mình muốn hủy đơn thì có được không?", "Đặt nhầm món có hủy được không?",
  "Can I cancel my order?", "I ordered by mistake, can I cancel?",
  "Đơn đặt qua ứng dụng được hủy trong %d phút sau khi đặt. Tại quầy bạn có thể hủy trước khi món được pha chế." % F["cancel_app_minutes"],
  "Orders in the app can be cancelled within %d minutes. At the counter you can cancel before the drink is prepared." % F["cancel_app_minutes"])
T("loyalty_earn", "Thành viên", "Tích điểm thành viên như thế nào?", "Thẻ HL Rewards tích điểm ra sao?",
  "How do I earn loyalty points?", "How does HL Rewards work?",
  "Với thẻ HL Rewards, mỗi %s chi tiêu bạn nhận 1 điểm." % fmt_vnd(F["point_per"]),
  "With HL Rewards you earn 1 point for every %s spent." % ("{:,}".format(F["point_per"]) + " VND"))
T("loyalty_redeem", "Thành viên", "Đổi điểm lấy gì được?", "Bao nhiêu điểm thì đổi được ly nước?",
  "What can I redeem my points for?", "How many points for a free drink?",
  "%d điểm đổi được 1 đồ uống size M bất kỳ trong menu." % F["redeem_points"],
  "%d points can be redeemed for any size M drink on the menu." % F["redeem_points"])
T("student", "Khuyến mãi", "Học sinh sinh viên có được giảm giá không?", "Giảm giá cho sinh viên áp dụng khi nào?",
  "Is there a student discount?", "When does the student discount apply?",
  "Học sinh, sinh viên được giảm %d%% đồ uống từ %s, %s khi xuất trình thẻ." % (F["student_pct"], F["student_days"], F["student_time"]),
  "Students get %d%% off drinks from Monday to Friday, 14:00 to 17:00, with a valid student card." % F["student_pct"])
T("promotions", "Khuyến mãi", "Hiện tại quán có khuyến mãi gì?", "Có chương trình ưu đãi nào trong tuần không?",
  "What promotions are on right now?", "Are there any deals this week?",
  "Các ưu đãi đang áp dụng: " + promos_vi, "Current promotions: " + promos_en)
T("bulk_order", "Giao hàng", "Mình đặt 30 ly cho công ty được không?", "Đặt số lượng lớn có được giảm giá không?",
  "Can I place a bulk order of 30 cups for my office?", "Is there a discount for large orders?",
  "Đơn từ %d ly trở lên cần đặt trước ít nhất %d giờ và được giảm %d%%." % (F["bulk_min_cups"], F["bulk_hours_ahead"], F["bulk_pct"]),
  "Orders of %d cups or more must be placed at least %d hours ahead and get %d%% off." % (F["bulk_min_cups"], F["bulk_hours_ahead"], F["bulk_pct"]))
T("gift_card", "Thành viên", "Quán có bán thẻ quà tặng không?", "Thẻ quà tặng dùng được bao lâu?",
  "Do you sell gift cards?", "How long is a gift card valid?",
  "Quán bán thẻ quà tặng mệnh giá %s, hạn sử dụng %d tháng kể từ ngày mua." % (F["gift_values"], F["gift_months"]),
  "We sell gift cards worth 100,000, 200,000 and 500,000 VND, valid for %d months from purchase." % F["gift_months"])
T("app", "Thành viên", "Có ứng dụng đặt món không?", "Tải app Highlands ở đâu?",
  "Is there an app for ordering?", "Where can I download the Highlands app?",
  "Ứng dụng Highlands có trên App Store và Google Play, dùng để đặt món, tích điểm và xem ưu đãi.",
  "The Highlands app is on the App Store and Google Play for ordering, collecting points and viewing offers.")
T("sizes", "Món uống", "Size S M L khác nhau bao nhiêu ml?", "Ly size M đựng được bao nhiêu?",
  "How big are sizes S, M and L?", "How many ml is a medium cup?",
  "Size S là %dml, size M là %dml và size L là %dml. Size M cộng thêm 6.000đ so với S, size L cộng thêm 10.000đ so với M." % (S["S"], S["M"], S["L"]),
  "Size S is %d ml, M is %d ml and L is %d ml. M costs 6,000 VND more than S and L costs 10,000 VND more than M." % (S["S"], S["M"], S["L"]))
T("sugar_ice", "Món uống", "Mình có chọn được mức đường và đá không?", "Mình muốn ít đường ít đá được không?",
  "Can I choose the sugar and ice level?", "Can I get less sugar and less ice?",
  "Bạn chọn được mức đường 0%, 30%, 50%, 70% hoặc 100% và mức đá 0%, 30%, 50% hoặc 100%.",
  "You can choose sugar at 0%, 30%, 50%, 70% or 100%, and ice at 0%, 30%, 50% or 100%.")
T("toppings", "Món uống", "Topping thêm giá bao nhiêu?", "Quán có những topping nào?",
  "How much are extra toppings?", "What toppings do you have?",
  "Quán có các topping: Trân Châu Đường Đen, Thạch Đào, Kem Cheese, Shot Espresso Thêm, Kem Whipping và Đổi Sữa Yến Mạch. Giá từ %s đến %s." % (fmt_vnd(8000), fmt_vnd(F["topping_high"])),
  "Toppings include Brown Sugar Boba, Peach Jelly, Cream Cheese Foam, Extra Espresso Shot, Whipped Cream and Oat Milk Upgrade, priced from 8,000 to %s VND." % "{:,}".format(F["topping_high"]))
T("decaf", "Món uống", "Có cà phê không caffeine không?", "Quán có cà phê decaf không?",
  "Do you have decaf coffee?", "Is there a caffeine-free coffee?",
  "Quán không có cà phê decaf. Các thức uống không caffeine gồm Trà Hoa Cúc Mật Ong, Trà Gừng Mật Ong, Chocolate Nóng, sinh tố, nước ép và soda.",
  "We do not offer decaf coffee. Caffeine-free options include Chamomile Honey Tea, Ginger Honey Tea, Hot Chocolate, smoothies, juices and sodas.")
T("allergens", "Món uống", "Mình bị dị ứng sữa thì nên lưu ý gì?", "Món nào có chứa hạt hoặc gluten?",
  "I have a dairy allergy, what should I know?", "Which items contain nuts or gluten?",
  "Thông tin dị ứng của từng món có trong menu: các món có sữa, hạt, gluten hoặc trứng đều được ghi rõ. Quán không thể đảm bảo tuyệt đối không lây nhiễm chéo, vui lòng báo nhân viên khi đặt món.",
  "Allergen details are listed per item for milk, nuts, gluten and egg. We cannot fully guarantee against cross contamination, so please tell the staff when ordering.")
T("vegan", "Món uống", "Quán có món chay không?", "Có đồ uống nào không có sữa không?",
  "Do you have vegan options?", "Are there any dairy-free drinks?",
  "Quán có các món chay như Salad Rau Củ, Khoai Tây Chiên, Phin Đen, Cold Brew, các loại trà trái cây, nước ép và soda. Bạn cũng có thể Đổi Sữa Yến Mạch với %s." % fmt_vnd(15000),
  "Vegan choices include Garden Salad, French Fries, black coffee, Cold Brew, fruit teas, juices and sodas. You can also swap to oat milk for 15,000 VND.")
T("refund", "Chính sách", "Nước pha sai thì có được đổi không?", "Món có vấn đề thì xử lý thế nào?",
  "What if my drink is made wrong?", "What happens if there is a problem with my item?",
  "Nếu món pha sai hoặc có vấn đề, quán sẽ làm lại món mới trong vòng %d phút kể từ khi bạn nhận món." % F["remake_minutes"],
  "If your drink is made wrong or has a problem, we will remake it within %d minutes of you receiving it." % F["remake_minutes"])
T("complaint", "Chính sách", "Mình muốn góp ý hoặc khiếu nại thì liên hệ ai?", "Số hotline của quán là gì?",
  "Who do I contact for feedback or a complaint?", "What is your hotline number?",
  "Bạn gọi hotline %s hoặc gửi email %s. Quán phản hồi trong vòng %d giờ." % (F["hotline"], F["email"], F["reply_hours"]),
  "Call hotline %s or email %s. We reply within %d hours." % (F["hotline"], F["email"], F["reply_hours"]))
T("lost_found", "Chính sách", "Mình để quên đồ ở quán thì sao?", "Đồ thất lạc được giữ bao lâu?",
  "I left something behind, what should I do?", "How long do you keep lost items?",
  "Đồ để quên được lưu giữ tại chi nhánh trong %d ngày. Bạn liên hệ chi nhánh hoặc hotline %s để nhận lại." % (F["lost_days"], F["hotline"]),
  "Lost items are kept at the branch for %d days. Contact the branch or hotline %s to claim them." % (F["lost_days"], F["hotline"]))
T("pets", "Chính sách", "Mang thú cưng vào quán được không?", "Quán có cho dắt chó vào không?",
  "Are pets allowed?", "Can I bring my dog in?",
  "Quán không cho phép mang thú cưng vào, trừ chó dẫn đường cho người khiếm thị.",
  "Pets are not allowed, except guide dogs for visually impaired guests.")
T("smoking", "Chính sách", "Quán có chỗ hút thuốc không?", "Hút thuốc ở đâu được?",
  "Is there a smoking area?", "Where can I smoke?",
  "Trong nhà là khu vực không hút thuốc. Bạn có thể hút thuốc ở khu vực ngoài trời tại các chi nhánh có chỗ ngồi ngoài trời.",
  "Indoors is smoke-free. You can smoke in the outdoor seating area at branches that have one.")
T("parking", "Tiện ích", "Quán có chỗ gửi xe không?", "Đỗ ô tô ở đâu được?",
  "Is there parking?", "Where can I park my car?",
  "Hầu hết chi nhánh có chỗ gửi xe máy miễn phí. Chỗ đỗ ô tô có tại các chi nhánh: %s." % cp,
  "Most branches offer free motorbike parking. Car parking is available at: %s." % cp)
T("power", "Tiện ích", "Có ổ cắm sạc điện thoại không?", "Mình mang laptop đến ngồi làm việc được không?",
  "Are there power outlets?", "Can I work on my laptop there?",
  "Hầu hết chi nhánh có ổ cắm tại bàn. Khu làm việc yên tĩnh có tại các chi nhánh: %s." % ws,
  "Most branches have power outlets at the tables. Quiet workspaces are available at: %s." % ws)
T("quiet_space", "Tiện ích", "Chỗ nào yên tĩnh để học bài?", "Chi nhánh nào có khu làm việc?",
  "Where can I find a quiet place to study?", "Which branches have a workspace area?",
  "Các chi nhánh có khu làm việc yên tĩnh gồm: %s." % ws,
  "Branches with a quiet workspace area: %s." % ws)
T("kids", "Tiện ích", "Quán có ghế cho em bé không?", "Đi cùng trẻ nhỏ thì chi nhánh nào tiện?",
  "Do you have high chairs for kids?", "Which branches are good for families with small children?",
  "Ghế ngồi cho trẻ em có tại các chi nhánh: %s." % kc,
  "Child seats are available at: %s." % kc)
T("outdoor", "Tiện ích", "Quán có chỗ ngồi ngoài trời không?", "Chi nhánh nào có sân ngoài?",
  "Is there outdoor seating?", "Which branches have an outdoor area?",
  "Chỗ ngồi ngoài trời có tại các chi nhánh: %s." % ", ".join(b["short"] for b in branches_with("outdoor")),
  "Outdoor seating is available at: %s." % ", ".join(b["short"] for b in branches_with("outdoor")))
T("branches", "Chi nhánh", "Quán có những chi nhánh nào?", "Có chi nhánh ở Hà Nội không?",
  "Where are your branches?", "Do you have a branch in Hanoi?",
  "Quán có %d chi nhánh tại TP. Hồ Chí Minh, Hà Nội, Đà Nẵng, Hải Phòng, Cần Thơ và Nha Trang. Tại Hà Nội có: %s." % (len(BRANCHES), ", ".join(b["short"] for b in BRANCHES if b["city"] == "Hà Nội")),
  "We have %d branches in Ho Chi Minh City, Hanoi, Da Nang, Hai Phong, Can Tho and Nha Trang. In Hanoi: %s." % (len(BRANCHES), ", ".join(b["short"] for b in BRANCHES if b["city"] == "Hà Nội")))
T("recruitment", "Chính sách", "Quán có đang tuyển nhân viên không?", "Nộp hồ sơ xin việc ở đâu?",
  "Are you hiring?", "Where do I apply for a job?",
  "Bạn gửi hồ sơ ứng tuyển qua email %s hoặc nộp trực tiếp tại quản lý chi nhánh." % F["email"],
  "Send your application to %s or hand it to the branch manager." % F["email"])

assert len(TOPICS) == 40, len(TOPICS)

rows = []
n = 0
langs = ["vi", "vi", "en", "en"]
for t in TOPICS:
    for k in range(4):
        n += 1
        lang = langs[k]
        rows.append(dict(faq_id="F%03d" % n, topic_id=t["topic_id"], category=t["category"], language=lang,
                         question=t["q"][k], answer=t["a_vi"] if lang == "vi" else t["a_en"]))
with open(os.path.join(OUT, "faq.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["faq_id", "topic_id", "category", "language", "question", "answer"])
    w.writeheader()
    w.writerows(rows)
with open(os.path.join(OUT, "faq_topics.json"), "w", encoding="utf-8") as f:
    json.dump(TOPICS, f, ensure_ascii=False, indent=1)
print("menu=%d faq=%d topics=%d" % (len(MENU), len(rows), len(TOPICS)))
