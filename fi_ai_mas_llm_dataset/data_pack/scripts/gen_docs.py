# -*- coding: utf-8 -*-
"""Sinh 4 tai lieu noi bo (2 docx + 2 pdf) + manifest cac section (ground truth cho RAG eval)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "kb", "docs")
os.makedirs(OUT, exist_ok=True)
D = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", D + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", D + "DejaVuSans-Bold.ttf"))

REFUND_DAYS = 5
POINT_EXPIRE_MONTHS = 12
GOLD_POINTS = 500
MAX_DELIVERY_KM = 5
kids_age = 12

# ------------------------------------------------------------------ POLICY
POLICY = ("policy", "HL_Chinh_Sach_Noi_Bo_2026", "docx", "Chính sách nội bộ Highlands Coffee 2026", [
    ("Mục đích và phạm vi áp dụng",
     "Tài liệu này quy định các chính sách phục vụ khách hàng áp dụng tại toàn bộ %d chi nhánh Highlands Coffee. Nhân viên phải nắm rõ và thực hiện thống nhất để khách hàng nhận được trải nghiệm đồng đều ở mọi chi nhánh. Mọi thay đổi chính sách được thông báo qua email nội bộ trước ngày áp dụng ít nhất 3 ngày." % len(BRANCHES)),
    ("Chính sách làm lại món",
     "Khi món được pha sai theo yêu cầu hoặc có vấn đề về chất lượng, quán làm lại món mới trong vòng %d phút kể từ khi khách nhận món. Nhân viên không yêu cầu khách giải thích dài dòng và không tranh luận với khách. Món làm lại phải được quản lý ca kiểm tra trước khi giao." % F["remake_minutes"]),
    ("Chính sách hoàn tiền",
     "Chỉ hoàn tiền khi khách bị thanh toán trùng hoặc món không thể làm lại. Khoản hoàn được chuyển về đúng phương thức thanh toán ban đầu trong vòng %d ngày làm việc. Quán không hoàn tiền mặt cho đơn đã thanh toán qua ví điện tử hoặc thẻ." % REFUND_DAYS),
    ("Chính sách dị ứng và thành phần món",
     "Mỗi món trong menu ghi rõ các nhóm dị ứng gồm sữa, hạt, gluten và trứng. Nhân viên phải hỏi khách về dị ứng khi khách có dấu hiệu quan ngại và không được tự ý khẳng định món an toàn tuyệt đối. Quán không thể đảm bảo tránh hoàn toàn lây nhiễm chéo trong quá trình pha chế."),
    ("Chính sách thú cưng",
     "Quán không cho phép mang thú cưng vào khu vực phục vụ. Ngoại lệ duy nhất là chó dẫn đường hỗ trợ người khiếm thị, nhân viên cần nhiệt tình hỗ trợ và bố trí chỗ ngồi thuận tiện cho khách."),
    ("Chính sách hút thuốc",
     "Toàn bộ khu vực trong nhà là khu vực không hút thuốc. Khách chỉ được hút thuốc tại khu vực ngoài trời ở các chi nhánh có chỗ ngồi ngoài trời gồm %s. Nhân viên nhắc nhở khách lịch sự khi phát hiện vi phạm." % ", ".join(b["short"] for b in branches_with("outdoor"))),
    ("Chính sách dành cho trẻ em",
     "Trẻ dưới %d tuổi cần có người lớn đi cùng trong suốt thời gian ở quán. Quán khuyến nghị không dùng đồ uống có caffeine cho trẻ dưới %d tuổi và gợi ý Sinh Tố Xoài, Nước Ép Cam hoặc Chocolate Nóng. Ghế ngồi cho trẻ em có tại các chi nhánh %s." % (kids_age, kids_age, ", ".join(b["short"] for b in branches_with("kids_chair")))),
    ("Chương trình thành viên HL Rewards",
     "Thành viên HL Rewards nhận 1 điểm cho mỗi %s chi tiêu. Thành viên có từ %d điểm tích lũy trong năm được nâng lên hạng Vàng và nhận thêm 10%% điểm cho mọi đơn hàng. Thành viên đăng ký qua ứng dụng Highlands hoặc tại quầy chỉ với số điện thoại." % (fmt_vnd(F["point_per"]), GOLD_POINTS)),
    ("Quy định đổi điểm thưởng",
     "%d điểm được đổi lấy 1 đồ uống size M bất kỳ trong menu, không bao gồm topping. Điểm có hạn sử dụng %d tháng kể từ ngày phát sinh và không quy đổi thành tiền mặt. Khách đổi điểm phải xuất trình mã thành viên trong ứng dụng." % (F["redeem_points"], POINT_EXPIRE_MONTHS)),
    ("Quy định thẻ quà tặng",
     "Thẻ quà tặng được bán với mệnh giá %s và có hạn sử dụng %d tháng kể từ ngày mua. Thẻ không được quy đổi thành tiền mặt và không được hoàn lại sau khi đã bán. Thẻ bị mất không được cấp lại nếu khách không còn mã thẻ." % (F["gift_values"], F["gift_months"])),
    ("Quy định xuất hóa đơn VAT",
     "Khách yêu cầu hóa đơn VAT phải thông báo trước %s và cung cấp mã số thuế cùng địa chỉ email nhận hóa đơn. Hóa đơn điện tử được gửi trong vòng %d giờ. Giá niêm yết đã bao gồm thuế VAT nên quán không tính thêm khoản nào khi xuất hóa đơn." % (F["vat_deadline"], F["vat_email_hours"])),
    ("Chính sách giao hàng",
     "Quán giao hàng qua ứng dụng Highlands, GrabFood và ShopeeFood trong bán kính tối đa %dkm. Đơn từ %s trong bán kính %dkm được miễn phí giao hàng, các đơn còn lại tính phí %s. Thời gian giao hàng dự kiến là 30 đến 45 phút tùy khoảng cách." % (MAX_DELIVERY_KM, fmt_vnd(F["free_ship_min"]), F["free_ship_km"], fmt_vnd(F["ship_fee"]))),
    ("Đặt bàn và tổ chức tiệc sinh nhật",
     "Nhóm từ %d người trở lên cần đặt bàn trước ít nhất %d giờ qua hotline %s, quán giữ bàn tối đa %d phút. Tiệc sinh nhật dành cho nhóm từ %d người, đặt trước %d ngày và được tặng trang trí bóng bay cơ bản. Bánh sinh nhật nguyên cái cần đặt trước %d ngày, giá từ %s." % (F["reserve_min_people"], F["reserve_hours_ahead"], F["hotline"], F["hold_minutes"], F["birthday_min_people"], F["birthday_days_ahead"], F["cake_days_ahead"], fmt_vnd(F["cake_from"]))),
    ("Đơn hàng số lượng lớn",
     "Đơn từ %d ly trở lên phải đặt trước ít nhất %d giờ và được giảm %d%% tổng giá trị đơn. Chi nhánh xác nhận đơn qua điện thoại và chuẩn bị trong ngày. Đơn số lượng lớn không áp dụng đồng thời với chương trình Thứ Ba Mua 2 Tặng 1." % (F["bulk_min_cups"], F["bulk_hours_ahead"], F["bulk_pct"])),
    ("Xử lý đồ thất lạc",
     "Đồ khách để quên được ghi sổ và lưu giữ tại chi nhánh trong %d ngày. Khách nhận lại phải mô tả đồ vật và xuất trình giấy tờ tùy thân. Sau %d ngày, đồ chưa có người nhận được chuyển về văn phòng khu vực." % (F["lost_days"], F["lost_days"])),
    ("Tiếp nhận góp ý và khiếu nại",
     "Khách gửi góp ý qua hotline %s hoặc email %s. Mọi phản hồi được trả lời trong vòng %d giờ. Khiếu nại liên quan an toàn thực phẩm phải được quản lý liên hệ lại với khách trong vòng 2 giờ." % (F["hotline"], F["email"], F["reply_hours"])),
    ("Giờ mở cửa và ngày lễ",
     "Giờ mở cửa tiêu chuẩn là %s đến %s mỗi ngày, các chi nhánh trong trung tâm thương mại theo giờ của trung tâm. Dịp Tết Nguyên Đán giờ hoạt động được điều chỉnh theo từng chi nhánh và công bố trước 7 ngày trên ứng dụng. Quán mở cửa vào các ngày lễ khác như thường lệ." % (F["open"], F["close"])),
])

# ------------------------------------------------------------------ SOP
SOP = ("sop", "HL_Quy_Trinh_Phuc_Vu_2026", "pdf", "Quy trình phục vụ tại quầy và pha chế", [
    ("Mục tiêu của quy trình phục vụ",
     "Quy trình này giúp nhân viên quầy và pha chế phục vụ nhanh, đúng và thân thiện. Mục tiêu là khách nhận được món đúng yêu cầu, đúng nhiệt độ và đúng thời gian cam kết. Mọi bước đều có người chịu trách nhiệm là quản lý ca."),
    ("Chào đón khách",
     "Nhân viên chào khách trong vòng 10 giây kể từ khi khách bước vào quầy, giữ giao tiếp bằng mắt và mỉm cười. Câu chào mẫu là Dạ Highlands xin chào anh chị, mình dùng gì ạ. Với khách nước ngoài, nhân viên chào bằng tiếng Anh và đưa menu song ngữ."),
    ("Nhận order tại quầy",
     "Nhân viên nhận order, hỏi rõ size, mức đường, mức đá và topping rồi lặp lại toàn bộ đơn để khách xác nhận. Khi khách phân vân, nhân viên gợi ý các món bán chạy như Trà Đào Cam Sả, Phin Sữa Đá và Bạc Xỉu. Tuyệt đối không giục khách quyết định."),
    ("Xác nhận dị ứng khi nhận order",
     "Khi khách đề cập dị ứng, nhân viên kiểm tra cột dị ứng trong menu và thông báo chính xác các thành phần gồm sữa, hạt, gluten hoặc trứng. Nếu không chắc chắn, nhân viên hỏi quản lý ca thay vì tự trả lời. Ghi chú dị ứng được viết trên ly để pha chế lưu ý."),
    ("Chuẩn hóa dung tích ly",
     "Size S dùng ly %dml, size M dùng ly %dml và size L dùng ly %dml. Freeze luôn được pha theo đúng thể tích của size, không rót thêm hoặc bớt. Khi khách yêu cầu nâng size, nhân viên báo chênh lệch giá trước khi tính tiền." % (SIZES_ML["S"], SIZES_ML["M"], SIZES_ML["L"])),
    ("Pha chế cà phê phin",
     "Mỗi ly cà phê phin dùng 20 gram cà phê rang xay và 90ml nước nóng 92 độ C, thời gian nhỏ giọt khoảng 4 đến 5 phút. Với Phin Sữa Đá, sữa đặc được cho vào ly trước, sau đó rót cà phê và thêm đá. Không pha sẵn cà phê quá 30 phút."),
    ("Pha chế Freeze",
     "Freeze được xay từ đá viên, sữa, siro và nền hương vị trong 40 giây bằng máy xay công nghiệp. Sau khi xay, nhân viên rót ra ly, thêm kem whipping và trang trí. Freeze phải giao cho khách trong vòng 2 phút để không bị tan."),
    ("Pha chế trà và trà trái cây",
     "Trà ủ được sử dụng tối đa 4 giờ kể từ khi ủ, quá thời gian phải bỏ đi và ủ mẻ mới. Trà Đào Cam Sả được pha từ trà đen, siro đào, cam tươi và sả đập dập. Thạch và trái cây miếng được cho vào ly cuối cùng."),
    ("Thời gian chuẩn bị món",
     "Đồ uống lạnh phải hoàn thành trong 5 phút, đồ uống nóng trong 4 phút, bánh ngọt trong 3 phút và món mặn nóng trong 10 phút kể từ khi nhận order. Khi quầy đông, nhân viên chủ động báo thời gian chờ dự kiến cho khách. Đơn mang đi được ưu tiên pha sau đơn tại chỗ cùng thời điểm."),
    ("Kiểm tra chất lượng trước khi giao",
     "Đồ uống nóng được giao ở nhiệt độ 65 đến 70 độ C, đồ uống lạnh dưới 8 độ C. Nhân viên kiểm tra tên món, size, mức đường và ghi chú trên ly với đơn hàng trước khi gọi tên khách. Món sai phải làm lại ngay, không giao cho khách."),
    ("Xử lý phàn nàn của khách",
     "Nhân viên lắng nghe, xin lỗi và đề xuất làm lại món trong vòng %d phút. Nếu khách vẫn chưa hài lòng, nhân viên chuyển cho quản lý ca và ghi nhận vào sổ phản hồi. Nhân viên không tranh luận hay giải thích bào chữa." % F["remake_minutes"]),
    ("Đóng gói đơn mang đi và giao hàng",
     "Đồ uống mang đi được đậy nắp kín, đặt vào túi và tách riêng phần đá với trà hoặc cà phê nóng khi giao hàng. Ly, ống hút và túi đều miễn phí. Đơn giao hàng được dán tem tên khách và mã đơn trên túi."),
    ("Vệ sinh bàn và khu vực khách",
     "Nhân viên lau bàn ngay sau khi khách rời đi và kiểm tra khu vực mỗi 15 phút. Sàn nhà được lau mỗi giờ, nhà vệ sinh kiểm tra mỗi 30 phút. Khu vực ngoài trời có gạt tàn được đổ mỗi 2 giờ."),
    ("An toàn thực phẩm và bảo quản bánh",
     "Bánh ngọt trưng bày trong tủ mát ở nhiệt độ 2 đến 6 độ C và bán tối đa trong 24 giờ kể từ khi ra lò. Bánh mì và món mặn được làm nóng ngay trước khi phục vụ. Sữa tươi mở nắp phải dùng hết trong 48 giờ."),
    ("Thanh toán và xuất hóa đơn tại quầy",
     "Nhân viên nhắc khách các hình thức thanh toán gồm tiền mặt, thẻ và ví MoMo, ZaloPay, VNPay QR. Khách yêu cầu hóa đơn VAT được ghi mã số thuế và email vào sổ, hóa đơn gửi trong %d giờ. Khách muốn tách hóa đơn được tách tối đa %d phần." % (F["vat_email_hours"], F["split_max"])),
    ("Bàn giao và đóng ca",
     "Cuối ca, nhân viên kiểm tra tiền quầy, đối chiếu doanh thu và ký bàn giao với quản lý. Nguyên liệu còn dư được ghi nhãn ngày giờ và cất trong tủ mát. Máy móc được vệ sinh trước khi tắt, và quầy đóng cửa lúc %s đối với giờ tiêu chuẩn." % F["close"]),
])

# ------------------------------------------------------------------ PROMO
promo_sections = [("Tổng quan chương trình khuyến mãi tháng 11 năm 2026",
                   "Tháng 11 năm 2026 Highlands Coffee triển khai %d chương trình khuyến mãi áp dụng tại tất cả chi nhánh. Chương trình có hiệu lực từ ngày 01/11/2026 đến hết ngày 30/11/2026. Khách hàng có thể xem chi tiết trong ứng dụng Highlands hoặc hỏi nhân viên." % len(PROMOS))]
for p in PROMOS:
    promo_sections.append(("Chương trình %s" % p["name"], "%s áp dụng vào %s. %s Khuyến mãi không quy đổi thành tiền mặt." % (p["name"], p["day"], p["vi"])))
promo_sections += [
    ("Quy định áp dụng đồng thời nhiều khuyến mãi",
     "Mỗi đơn hàng chỉ được áp dụng 1 chương trình khuyến mãi, ngoại trừ chương trình Thứ Tư Nhân Đôi Điểm có thể cộng thêm với chương trình khác. Chương trình Happy Student không áp dụng đồng thời với Thứ Ba Mua 2 Tặng 1."),
    ("Sản phẩm không áp dụng khuyến mãi",
     "Các chương trình giảm giá không áp dụng cho topping, Nước Suối, thẻ quà tặng và bánh sinh nhật đặt trước. Chương trình tặng đồ uống chỉ áp dụng cho đồ uống trong menu thường, không áp dụng cho Combo."),
    ("Điều kiện giao hàng khi áp dụng khuyến mãi",
     "Khuyến mãi áp dụng cho cả đơn tại quán, mang đi và giao hàng qua ứng dụng Highlands. Đơn giao qua GrabFood và ShopeeFood chỉ áp dụng khuyến mãi do các nền tảng đó cho phép."),
]
PROMO = ("promo", "HL_Khuyen_Mai_Thang_11_2026", "docx", "Chương trình khuyến mãi tháng 11/2026", promo_sections)

# ------------------------------------------------------------------ BRANCH
branch_sections = [("Tổng quan hệ thống chi nhánh",
                    "Highlands Coffee hiện có %d chi nhánh tại TP. Hồ Chí Minh, Hà Nội, Đà Nẵng, Hải Phòng, Cần Thơ và Nha Trang. Mỗi chi nhánh có thể khác nhau về giờ mở cửa và tiện ích. Khách nên kiểm tra thông tin chi nhánh trước khi đến." % len(BRANCHES))]
for b in BRANCHES:
    feats = ", ".join(FEATURE_VI[x] for x in b["features"])
    branch_sections.append(("Chi nhánh %s" % b["short"],
        "%s tại %s, %s. Giờ mở cửa từ %s đến %s mỗi ngày. Tiện ích gồm %s. Số điện thoại chi nhánh là %s." % (b["name"], b["address"], b["city"], b["open"], b["close"], feats, b["phone"])))
branch_sections += [
    ("Ghi chú về giờ hoạt động các chi nhánh trong trung tâm thương mại",
     "Các chi nhánh Crescent Mall, Royal City và Vincom Ngô Quyền hoạt động theo giờ của trung tâm thương mại. Giờ mở cửa có thể thay đổi vào dịp lễ và cuối tuần."),
    ("Liên hệ tổng đài",
     "Khách có thể gọi tổng đài %s hoặc email %s để hỏi thông tin chi nhánh, đặt bàn nhóm và đặt bánh sinh nhật." % (F["hotline"], F["email"])),
]
BRANCH = ("branch", "HL_Thong_Tin_Chi_Nhanh_2026", "pdf", "Thông tin hệ thống chi nhánh", branch_sections)

DOCS = [POLICY, SOP, PROMO, BRANCH]


def write_docx(path, title, sections):
    d = Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(11)
    d.add_heading(title, 0)
    for i, (h, body) in enumerate(sections, 1):
        d.add_heading("%d. %s" % (i, h), 2)
        d.add_paragraph(body)
    d.save(path)


def write_pdf(path, title, sections):
    ss = getSampleStyleSheet()
    t = ParagraphStyle("t", parent=ss["Title"], fontName="DVB", fontSize=18, leading=24)
    h = ParagraphStyle("h", parent=ss["Heading2"], fontName="DVB", fontSize=12, leading=16, spaceBefore=10)
    b = ParagraphStyle("b", parent=ss["BodyText"], fontName="DV", fontSize=10, leading=15)
    story = [Paragraph(title, t), Spacer(1, 8)]
    for i, (hd, body) in enumerate(sections, 1):
        story += [Paragraph("%d. %s" % (i, hd), h), Paragraph(body.replace("&", "&amp;"), b)]
    SimpleDocTemplate(path, pagesize=A4, title=title).build(story)


manifest = []
for doc_id, fname, ext, title, secs in DOCS:
    path = os.path.join(OUT, "%s.%s" % (fname, ext))
    (write_docx if ext == "docx" else write_pdf)(path, title, secs)
    for i, (h, body) in enumerate(secs, 1):
        manifest.append(dict(section_id="%s-%02d" % (doc_id, i), doc_id=doc_id,
                             file="%s.%s" % (fname, ext), order=i, heading=h, text=body))
with open(os.path.join(OUT, "doc_sections_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print("docs=%d sections=%d" % (len(DOCS), len(manifest)))
