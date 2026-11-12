# -*- coding: utf-8 -*-
"""Sinh du lieu Router (A1.2) bang template + slot-filling + augmentation.

Output (data/router/):
  router_train.json   4000 mau, can bang 1000/intent
  router_test.json     400 mau, can bang  100/intent (template KHONG xuat hien o train)
  router_*_sft.jsonl  dinh dang chat messages de SFT Qwen
Quy tac gan nhan (tie-break) cho hard samples duoc ghi trong README.
"""
import json
import os
import random
import sys
import zlib
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "router")
os.makedirs(OUT, exist_ok=True)
INTENTS = ["order", "consultant", "faq", "ignore"]
TRAIN_PER, TEST_PER = 1000, 100
HARD_TRAIN, HARD_TEST = 120, 20          # moi intent
R = random.Random(SEED)

# --------------------------------------------------------------------- slots
def clean_en(s):
    return s.split("(")[0].strip().lower()

FOOD = [m for m in MENU if m["kind"] in ("drink", "food", "combo")]
ITEMS_ALL = [m for m in MENU if m["kind"] != "extra"]
TOPPINGS = [m for m in MENU if m["kind"] == "extra"]
ALIAS_VI = ["cà phê sữa", "cà phê đen", "cà phê sữa đá", "cà phê đen đá", "nâu đá", "đen đá", "trà đào", "trà sữa",
            "trà sữa trân châu", "bạc xỉu", "bánh mì", "sinh tố bơ", "freeze", "trà vải", "cà phê muối", "latte", "cappuccino"]
ALIAS_EN = ["iced latte", "hot americano", "cappuccino", "milk tea", "black coffee", "iced coffee with milk", "croissant",
            "cheesecake", "orange juice", "peach tea", "matcha latte", "brownie", "boba milk tea", "mango smoothie"]
VI_P = ["anh", "chị", "em", "mình", "tôi", "cô", "chú", "bác"]
VI_PRE = ["", "", "", "em ơi", "bạn ơi", "chị ơi", "anh ơi", "nhờ em", "em ơi cho anh hỏi", "ê bạn"]
VI_SUF = ["", "", "", "nhé", "nha", "ạ", "với", "đi", "giúp anh", "giúp mình", "nhé em", "cảm ơn", "được không"]
VI_NUM = ["1", "2", "3", "một", "hai", "ba", "1", "2", "một", "hai"]
VI_SIZE = ["size S", "size M", "size L", "cỡ vừa", "cỡ lớn", "size nhỏ", "", "", ""]
VI_MOD = ["ít đường", "ít đá", "không đường", "nhiều đá", "đá riêng", "thêm trân châu", "nóng", "lạnh", "mang đi",
          "uống tại đây", "ít ngọt", "", ""]
VI_PAY = ["momo", "zalopay", "thẻ", "tiền mặt", "vnpay", "QR", "thẻ visa", "chuyển khoản qr"]
VI_TASTE = ["ngọt", "béo", "chua", "đắng", "thanh", "ít ngọt", "đậm vị", "mát", "nhẹ", "không quá ngọt", "thơm"]
VI_WEATHER = ["nóng", "mưa", "lạnh", "oi", "nắng", "se lạnh", "nồm"]
VI_COMP = ["bạn", "người yêu", "gia đình", "đồng nghiệp", "con nhỏ", "khách hàng", "nhóm 5 người", "bố mẹ"]
VI_OCC = ["sinh nhật", "họp nhóm", "hẹn hò", "làm việc", "học bài", "ăn sáng", "ăn trưa", "tiếp khách", "đi chơi cuối tuần"]
VI_CAT = ["cà phê", "trà", "bánh", "đồ ăn nhẹ", "nước ép", "sinh tố", "món ăn sáng", "đồ uống", "món ngọt"]
VI_BUDGET = ["30", "40", "50", "60", "70", "80", "100"]
EN_PRE = ["", "", "", "Hi, ", "Excuse me, ", "Hey, ", "Sorry, ", "Hello, ", "Um, ", "So, "]
EN_SUF = ["", "", "", " please", " thanks", " if you can", " when you get a chance"]
EN_NUM = ["a", "one", "1", "a", "one", "two", "2", "three"]
EN_SIZE = ["small", "medium", "large", "size S", "size M", "size L", "regular", "", ""]
EN_MOD = ["less sugar", "no ice", "extra ice", "with boba", "hot", "iced", "to go", "for here", "less sweet", "no sugar", "", ""]
EN_PAY = ["card", "cash", "MoMo", "QR code", "Visa", "ZaloPay"]
EN_TASTE = ["sweet", "creamy", "sour", "bitter", "light", "strong", "refreshing", "fruity", "not too sweet", "chocolatey"]
EN_WEATHER = ["hot", "rainy", "cold", "humid", "sunny", "chilly"]
EN_COMP = ["a friend", "my girlfriend", "my family", "a coworker", "my kid", "a client", "five people", "my parents"]
EN_OCC = ["a birthday", "a team meeting", "a date", "studying", "breakfast", "lunch", "a business meeting", "the weekend"]
EN_CAT = ["coffee", "tea", "cake", "light snack", "juice", "smoothie", "breakfast item", "drink", "dessert"]


def unit_vi(m):
    return {"drink": "ly", "food": R.choice(["phần", "cái"]), "combo": ""}.get(m["kind"], "phần")


def pl(name, n):
    return name if n in ("a", "one", "1") else (name if name.endswith("s") else name + "s")


def ctx_vi(r, mixed=False):
    m1, m2 = r.sample(ITEMS_ALL if r.random() < .5 else FOOD, 2)
    def nm(m):
        x = r.random()
        if mixed:
            return clean_en(m["name_en"]) if x < .8 else r.choice(ALIAS_EN)
        return m["name_vi"].lower() if x < .72 else r.choice(ALIAS_VI)
    c = dict(P=r.choice(VI_P), pre=r.choice(VI_PRE), suf=r.choice(VI_SUF), q=r.choice(VI_NUM), q2=r.choice(VI_NUM),
             size=r.choice(VI_SIZE), mod=r.choice(VI_MOD), pay=r.choice(VI_PAY), taste=r.choice(VI_TASTE),
             taste2=r.choice(VI_TASTE), weather=r.choice(VI_WEATHER), comp=r.choice(VI_COMP), occ=r.choice(VI_OCC),
             cat=r.choice(VI_CAT), budget=r.choice(VI_BUDGET), n=r.randint(1, 20), item=nm(m1), item2=nm(m2),
             u=unit_vi(m1), u2=unit_vi(m2), top=r.choice(TOPPINGS)["name_vi"].lower())
    if mixed:
        c["u"] = r.choice(["ly", "cái", "phần"]); c["u2"] = r.choice(["ly", "cái", "phần"])
    return c


def ctx_en(r):
    m1, m2 = r.sample(ITEMS_ALL if r.random() < .5 else FOOD, 2)
    def nm(m):
        return clean_en(m["name_en"]) if r.random() < .8 else r.choice(ALIAS_EN)
    q = r.choice(EN_NUM)
    c = dict(pre=r.choice(EN_PRE), suf=r.choice(EN_SUF), q=q, size=r.choice(EN_SIZE), mod=r.choice(EN_MOD),
             pay=r.choice(EN_PAY), taste=r.choice(EN_TASTE), weather=r.choice(EN_WEATHER), comp=r.choice(EN_COMP),
             occ=r.choice(EN_OCC), cat=r.choice(EN_CAT), budget=r.choice(VI_BUDGET), n=r.randint(1, 20),
             item=nm(m1), item2=nm(m2), top=clean_en(r.choice(TOPPINGS)["name_en"]))
    c["items"] = pl(c["item"], q)
    return c

# ------------------------------------------------------------------ templates
# Moi template: (tpl_id, text). tpl_id dung de chia train/test theo template.
ORDER_VI = [
    "Cho {P} {q} {u} {item}", "{pre} cho {P} {q} {u} {item} {size}", "{P} lấy {q} {u} {item} {mod} {suf}",
    "Cho {P} đặt {q} {u} {item} {suf}", "Gọi thêm {q} {u} {item} {suf}", "Thêm {item} nữa {suf}",
    "Bớt {q} {u} {item} {suf}", "Đổi {item} sang {item2} {suf}", "{item} {size} {mod}, {q} {u} {suf}",
    "{P} order {q} {u} {item} {mod}", "Cho {P} {q} {u} {item} và {q2} {u2} {item2}", "Hủy {item} giúp {P} {suf}",
    "Mang về {q} {u} {item} {suf}", "Cho {P} {item} {mod} {suf}", "Tính tiền {suf}", "{P} muốn thanh toán {suf}",
    "Tính tiền cho bàn số {n} {suf}", "Thanh toán bằng {pay} {suf}", "Cho {P} thanh toán bằng {pay} nhé",
    "Cho {P} cái bill đi", "Cho {P} gọi món {suf}", "Chốt đơn {suf}", "Thêm {top} vào {item} {suf}",
    "{pre} {P} lấy {item} {size} nha", "Cho {P} thêm {q} {u} {item} nữa", "{P} gọi {item} với {item2}",
    "Order cho {P} {q} {item} {size}", "Lấy giúp {P} {q} {u} {item} {mod}", "Bỏ {item} ra khỏi đơn {suf}",
    "Cho {P} {item} mang đi {suf}", "Tính tiền hết cho {P} {suf}", "Thêm {q} {u} {item} cho bàn {n}",
    "{P} đổi {item} thành {size} {suf}",
]
ORDER_EN = [
    "{pre}Can I get {q} {item} {size}?", "{pre}I'd like {q} {item}{suf}", "{pre}Give me {q} {item} {mod}",
    "{pre}One {item} to go{suf}", "{pre}Add {item} to my order{suf}", "{pre}Can we order {items}?",
    "Remove the {item}{suf}", "Switch my {item} to {item2}{suf}", "Check please", "{pre}Can I pay now?",
    "I'd like to pay by {pay}{suf}", "Put it on the bill{suf}", "{pre}Let me get {q} {item} and {item2}",
    "{item}, {size}, {mod}{suf}", "{pre}Could I have {q} {item} with {top}?", "We'll take {items}{suf}",
    "Another {item}{suf}", "Cancel the {item}{suf}", "Bill please", "{pre}Can I order?", "{pre}I'll have {q} {item}",
    "{pre}Let's pay by {pay}", "{pre}Can I add {top} to my {item}?", "Two {item} and one {item2}{suf}",
    "{pre}Could you make that {size}{suf}", "I want to change my order{suf}", "{pre}I'm ready to order",
]
CONS_VI = [
    "Có gì ngon không {suf}?", "{pre} gợi ý cho {P} món nào đi", "Quán có {cat} nào {taste} không?",
    "Trời {weather} uống gì ngon {suf}?", "{P} thích vị {taste}, nên uống gì?", "Món nào bán chạy nhất {suf}?",
    "Có {cat} nào dưới {budget}k không?", "Đi với {comp} thì nên gọi gì?", "{item} có ngon không?",
    "{item} vị thế nào vậy?", "{item} có {taste} không?", "{item} giá bao nhiêu vậy?",
    "{item} và {item2} khác nhau thế nào?", "{item} với {item2} cái nào ngon hơn?",
    "Có món nào không có caffeine không?", "Món nào ít calo nhất?", "Bánh nào ăn kèm {item} hợp nhất?",
    "Món nào hợp cho {occ}?", "Có món chay nào ngon không?", "{item} có sữa không?", "{item} làm từ gì vậy?",
    "Uống {item} có mất ngủ không?", "Combo nào có lợi nhất?", "Gợi ý món {cat} cho {occ} đi",
    "{pre} {P} muốn thử món mới, có gì hay không?", "Món nào hợp với người không uống được cà phê?",
    "Trong menu món nào {taste} nhất?", "{item} có phải món bán chạy không?", "Giá {item} size {size} là bao nhiêu?",
    "{P} đang {occ}, nên chọn {cat} nào?", "Có món nào no bụng không {suf}?", "{item} ăn có ngán không?",
]
CONS_EN = [
    "{pre}What's good here?", "{pre}What do you recommend?", "{pre}Do you have any {taste} {cat}?",
    "{pre}It's {weather} today, what should I drink?", "{pre}I like {taste} drinks, what would you suggest?",
    "{pre}What's your best seller?", "{pre}Anything under {budget}k?", "{pre}What should I order with {comp}?",
    "{pre}Is the {item} good?", "{pre}What does the {item} taste like?", "{pre}Is the {item} {taste}?",
    "{pre}How much is the {item}?", "{pre}What's the difference between {item} and {item2}?",
    "{pre}Which is better, {item} or {item2}?", "{pre}Do you have anything caffeine free?",
    "{pre}What's the lowest calorie option?", "{pre}What pairs well with the {item}?",
    "{pre}What would be good for {occ}?", "{pre}Any good vegan options?", "{pre}Does the {item} have milk in it?",
    "{pre}What's in the {item}?", "{pre}Will {item} keep me awake?", "{pre}Which combo is the best deal?",
    "{pre}Can you suggest a {cat} for {occ}?", "{pre}I want to try something new, any ideas?",
    "{pre}What's the most {taste} drink on the menu?", "{pre}Is the {item} popular?", "{pre}How big is the {item} in {size}?",
    "{pre}I'm having {occ}, which {cat} should I pick?", "{pre}Is {item} filling?", "{pre}Is the {item} too heavy?",
]
FAQ_EXTRA_VI = [
    "Quán có wifi miễn phí không?", "Quán có điều hòa không?", "Nhà vệ sinh ở đâu vậy?", "Quán ở đâu vậy?",
    "Chi nhánh gần nhất cách đây bao xa?", "Quán có mở cửa Chủ Nhật không?", "Hôm nay quán có đóng cửa sớm không?",
    "Có chỗ ngồi cho nhóm 10 người không?", "Quán có nhận đặt bàn qua điện thoại không?", "Quán có xuất hóa đơn đỏ không?",
    "Địa chỉ chi nhánh quận 1 là gì?", "Có thể thanh toán bằng thẻ tín dụng không?", "Số điện thoại của quán là gì?",
    "Có giữ xe miễn phí không?", "Giao hàng mất bao lâu?", "Có thể đặt trước qua app không?", "Thẻ thành viên làm ở đâu?",
    "Điểm thưởng có hết hạn không?", "Quán có phục vụ trẻ em không?", "Làm sao để phản hồi về chất lượng phục vụ?",
    "Quán có tuyển part-time không?", "Quán có cho mang laptop không?", "Có chỗ cho xe lăn không?",
    "Quán có tổ chức sự kiện được không?", "Giờ cao điểm là mấy giờ?", "Có miễn phí đá không?",
    "Quán có miễn phí nước lọc không?", "Quán có nhận giao hàng nội thành không?", "Thẻ quà tặng mua ở đâu?",
    "Quán có chi nhánh ở Đà Nẵng không?", "Chi nhánh Cầu Giấy mở đến mấy giờ?", "Có phụ thu ngày lễ không?",
    "Đặt tiệc cho 20 người cần cọc không?", "Hóa đơn VAT lấy ngay được không?", "Quán có chỗ đỗ ô tô không?",
]
FAQ_EXTRA_EN = [
    "Is the wifi free?", "Is there air conditioning?", "Where is the restroom?", "Where are you located?",
    "How far is the nearest branch?", "Are you open on Sundays?", "Do you close early today?",
    "Do you have seating for a group of 10?", "Can I book a table by phone?", "Can you issue a VAT invoice?",
    "What's the address of the District 1 branch?", "Can I pay with a credit card?", "What's your phone number?",
    "Is parking free?", "How long does delivery take?", "Can I order ahead in the app?", "Where can I sign up for membership?",
    "Do reward points expire?", "Are children welcome?", "How do I give feedback about the service?",
    "Are you hiring part-time staff?", "Can I bring my laptop?", "Is it wheelchair accessible?",
    "Can I host an event here?", "When is your rush hour?", "Is the ice free?", "Is tap water free?",
    "Do you deliver downtown?", "Where can I buy a gift card?", "Do you have a branch in Da Nang?",
    "How late is the Cau Giay branch open?", "Is there a holiday surcharge?", "Do I need a deposit for a 20 person party?",
    "Can I get the VAT invoice right away?", "Is there car parking?",
]
FAQ_PRE_VI = ["", "", "Cho hỏi, ", "Em ơi cho anh hỏi, ", "Bạn ơi, ", "Xin hỏi, ", "Cho mình hỏi chút, ", "Chị hỏi chút nha, ",
              "Nhờ em cho anh biết, ", "Ừm, ", "À cho hỏi, ", "Cho tôi hỏi, ", "Alo, "]
FAQ_SUF_VI = ["", "", " nhé", " vậy ạ", " em nhỉ", " với", " ạ", " nhỉ", " thế"]
FAQ_PRE_EN = ["", "", "Hi, ", "Excuse me, ", "Hey, quick question: ", "Sorry, ", "Could you tell me, ", "Just wondering, ",
              "Hello, ", "Um, ", "By the way, "]
FAQ_SUF_EN = ["", "", " please", " thanks", " if you don't mind", " by the way"]
IGN_VI = ["Ừm", "Ờ", "À", "Hello", "Hi", "Xin chào", "Chào em", "Alo", "Haha", "Hihi", "Hehe", "Ok", "Okay", "Cảm ơn",
          "Cảm ơn em nhé", "Cảm ơn nha", "Tạm biệt", "Bye bye", "Thôi để sau", "Không có gì đâu", "Ừ ừ", "Dạ", "Vâng",
          "Ờ được", "Ừ thôi", "Hmm", "Ơ", "Ê", "Hả", "Gì cơ", "Chờ chút", "Đợi tí", "Để xem đã", "Để anh nghĩ đã", "Xem đã",
          "Lát nữa nhé", "Không", "Không cần", "Thôi", "Khỏi", "Kệ đi", "Mày đi đâu đấy", "Tí nữa qua nhà bà ngoại nha",
          "Hôm nay trời nóng quá", "Nãy giờ chờ mãi", "Cái điện thoại này hết pin rồi", "Nhớ gọi cho mẹ nhé",
          "Bố ơi con muốn về", "Em ơi anh đến rồi", "Mai đi họp lúc mấy giờ nhỉ", "Ngoài trời đang mưa to kìa",
          "Xe mình đỗ ở đâu rồi", "Con đừng chạy nữa", "Bài này nhạc hay quá", "Kẹt xe kinh khủng luôn", "Cậu xem phim chưa",
          "Tối nay ăn gì đây", "Ủa sao lại thế", "Thật á", "Trời ơi", "Chán ghê", "Mệt quá đi", "Đúng rồi đó", "Hay đấy",
          "Ồ vậy hả", "Nghe nói vậy", "Ừ anh biết rồi", "Haha ngon thật", "Hihi vui quá", "Thôi mình đi nhé", "Chào nhé"]
IGN_EN = ["Um", "Uh", "Hmm", "Hello", "Hi there", "Hey", "Hi", "Okay", "Ok", "Alright", "Thanks", "Thank you",
          "Thank you so much", "Bye", "Goodbye", "See you", "Never mind", "Nothing", "Wait a sec", "Hold on", "Let me think",
          "Just looking", "Haha", "Lol", "Yeah", "Yep", "Nope", "No thanks", "I'm good", "What", "Pardon", "Sorry", "Wow",
          "Oh nice", "Cool", "Hmm let me see", "Where did I put my keys", "Did you see the game last night",
          "It's so hot today", "My phone is dead", "Honey come here", "Traffic was terrible", "I'm so tired",
          "What time is the movie", "Let's go home", "See you tomorrow", "That was funny", "Good night", "Yeah okay"]
FILL_VI = ["ừm", "ờ", "à", "haha", "hihi", "hm", "ơ", "ê", "há", "hể", "ha", "he", "ừ", "ê ê", "ới"]
FILL_EN = ["uh", "um", "hmm", "ah", "oh", "eh", "aha", "mm", "huh", "ha", "heh", "yeah"]
JUNK = ["la la la", "ba ba ba", "xì xào", "[noise]", "(tiếng ồn)", "[music]", "(background chatter)", "...", "zzz", "ầm ầm", "rè rè"]

# --------------------------------------------------------------- hard samples
HARD = {
    "order": {
        "vi": ["Cho {P} {q} {u} {item}, có ngọt không em?", "Lấy {q} {u} {item} luôn, giá nhiêu vậy?",
               "{item} bao nhiêu tiền vậy? Lấy cho {P} {q} {u} nhé", "Cho {P} hỏi chút, thôi cứ lấy {q} {u} {item} đi",
               "Ừm... cho {P} {q} {u} {item} {suf}", "Em ơi cho {P} {item}, à mà thôi cho {item2}",
               "Hello, cho {P} {q} {u} {item} nhé", "Quẹt thẻ được không, tính tiền cho {P}",
               "Cho {P} {item} {size} nhé, quán còn bàn không?", "Thanh toán bằng {pay} được không em, tính tiền giúp {P}",
               "Lấy {item} đi, ngon thì {P} lấy thêm", "Cho {P} {item}, rồi gợi ý thêm món ăn kèm nhé",
               "Cho {P} {q} {u} {item} xong tính tiền luôn", "Hi, cho {P} {item}, {item} có sữa không?",
               "Alo em, cho {P} {q} {u} {item} mang đi nha"],
        "en": ["Can I get {q} {item}? Is it sweet?", "Give me {q} {item}, how much is it?", "Hi, I'd like {q} {item} to go",
               "Um, {q} {item} please", "I'll take the {item}, and can I pay by {pay}?", "Check please, do you take {pay}?",
               "Just get me {q} {item} then", "Hello, can I order {q} {item}? Do you have wifi?",
               "Let me get the {item} and can you recommend a cake with it?", "Okay {q} {item} and the bill please"],
    },
    "consultant": {
        "vi": ["Có gì ngon rẻ không?", "Cho {P} món nào ngon nhất đi", "Em thấy nên uống gì thì cho {P} cái đó",
               "Món nào {taste} {taste2}, cho {P} xin", "Lấy món nào bán chạy nhất đi", "Cho {P} một ly gì đó mát mát đi",
               "{P} chưa biết gọi gì, em tư vấn giúp", "Gợi ý cho {P} rồi {P} gọi", "{item} có đáng thử không, ngon thì {P} lấy",
               "Hello, có gì ngon không?", "Ừm... không biết uống gì nhỉ", "Cho {P} xem menu, món nào ngon?",
               "Chọn giúp {P} món nào dưới {budget}k", "{item} giá bao nhiêu thì cho {P} biết", "Hôm nay có món mới không?",
               "Chọn giùm {P} món {cat} nào cũng được, miễn ngon"],
        "en": ["What's good and cheap?", "Just give me whatever is best", "Surprise me with something {taste}",
               "I can't decide, what do you recommend?", "Is the {item} worth trying? Maybe I'll get it", "Hi, what's good here?",
               "Hmm, what should I drink?", "Anything cold and sweet?", "What's new today?", "Pick something {taste} for me",
               "Give me your best {cat}", "Which one would you get, {item} or {item2}?"],
    },
    "faq": {
        "vi": ["Cho hỏi quán có nhận {pay} không?", "{item} có giao tận nơi không?", "Bánh sinh nhật đặt trước bao lâu?",
               "Hello, wifi tên gì vậy?", "Ừm cho hỏi mấy giờ quán đóng cửa?", "Mua mang về có tính phí túi không?",
               "Mình đặt bàn {n} người được không?", "Quán có chỗ đậu xe không, mình sắp tới",
               "Đơn mang về có xuất hóa đơn VAT không?", "Mua {item} bằng điểm thành viên được không?",
               "Giá trên menu có bao gồm VAT không?", "Quán có ổ cắm điện không, mình muốn gọi {item} ngồi làm việc",
               "Hi em, quán mở đến mấy giờ?", "Muốn mua {item} giao tận nhà thì tính phí ship sao?"],
        "en": ["Do you accept {pay}?", "Is delivery available for the {item}?", "Hello, what's the wifi password?",
               "Um, what time do you close?", "Can I reserve a table for {n}?", "Do you charge for takeaway bags?",
               "Can I use points to buy a {item}?", "Does the price include tax?", "Hi, do you have power outlets? I want to work",
               "I want a {item} delivered, what is the fee?"],
    },
    "ignore": {
        "vi": ["Ừm... cho anh... à thôi", "Ờ cái đó... thôi", "Alo? Nghe được không?", "Anh... à không có gì",
               "Cho... thôi để anh xem menu đã", "Ừ hello hello", "Để anh xem menu rồi gọi sau", "À ừ cảm ơn em",
               "Thôi không cần đâu em", "Chờ anh tí rồi anh gọi món", "Ơ cái gì thế", "Hello em ơi... à không",
               "Anh đang gọi điện, đợi anh tí", "Đang bận, lát nữa nhé", "Ừ ừ anh biết rồi", "Cho... ừm... thôi khỏi"],
        "en": ["Um, can I... never mind", "Hello? Can you hear me?", "I'll look at the menu first", "Hold on, I'm on the phone",
               "Uh, actually no thanks", "Hi... oh never mind", "Wait, let me think a second", "Sorry, wrong person",
               "Thanks, I'm just looking", "Hmm, give me a minute", "Can I... no wait, forget it", "Okay okay thanks bye"],
    },
}

# ------------------------------------------------------------- augmentation
def typo(s, r):
    if len(s) < 6:
        return s
    i = r.randrange(1, len(s) - 1)
    k = r.random()
    if k < .4:
        return s[:i] + s[i + 1:]
    if k < .7:
        return s[:i] + s[i] + s[i:]
    return s[:i] + s[i + 1] + s[i] + s[i + 2:]


def augment(s, lang, r):
    s = " ".join(s.split())
    s = s.replace(" ,", ",").replace(" ?", "?").replace("?,", "?")
    if r.random() < .35:
        s = s.lower()
    if r.random() < .45:
        s = s.rstrip("?.!, ")
    if lang != "en" and r.random() < .10:
        s = strip_accents(s)
    if r.random() < .05:
        s = typo(s, r)
    if r.random() < .05:
        s = r.choice(FILL_VI if lang != "en" else FILL_EN) + (", " if r.random() < .5 else "... ") + s
    return s.strip()


def ensure_punct(s, r, q=False):
    if r.random() < .5:
        return s
    return s.rstrip("?.!") + ("?" if q else r.choice([".", "", "!"]))

# ------------------------------------------------------------- generators
def gen_order(r, lang):
    if lang == "vi":
        t = r.randrange(len(ORDER_VI)); return "O:vi:%d" % t, ORDER_VI[t].format(**ctx_vi(r)), "vi"
    if lang == "vi-en":
        idx = [i for i, x in enumerate(ORDER_VI) if "{item}" in x]
        t = r.choice(idx); return "O:vi:%d" % t, ORDER_VI[t].format(**ctx_vi(r, True)), "vi-en"
    t = r.randrange(len(ORDER_EN)); return "O:en:%d" % t, ORDER_EN[t].format(**ctx_en(r)), "en"


def gen_cons(r, lang):
    if lang == "vi":
        t = r.randrange(len(CONS_VI)); return "C:vi:%d" % t, CONS_VI[t].format(**ctx_vi(r)), "vi"
    if lang == "vi-en":
        idx = [i for i, x in enumerate(CONS_VI) if "{item}" in x]
        t = r.choice(idx); return "C:vi:%d" % t, CONS_VI[t].format(**ctx_vi(r, True)), "vi-en"
    t = r.randrange(len(CONS_EN)); return "C:en:%d" % t, CONS_EN[t].format(**ctx_en(r)), "en"


FAQ_BASES = {"vi": [], "en": []}
_topics = json.load(open(os.path.join(OUT, "..", "kb", "faq_topics.json"), encoding="utf-8"))
for tp in _topics:
    for k, q in enumerate(tp["q"]):
        FAQ_BASES["vi" if k < 2 else "en"].append(("F:%s:%d" % (tp["topic_id"], k), q))
for i, q in enumerate(FAQ_EXTRA_VI):
    FAQ_BASES["vi"].append(("F:xv:%d" % i, q))
for i, q in enumerate(FAQ_EXTRA_EN):
    FAQ_BASES["en"].append(("F:xe:%d" % i, q))


def gen_faq(r, lang):
    lg = "vi" if lang in ("vi", "vi-en") else "en"
    tid, base = r.choice(FAQ_BASES[lg])
    pre = r.choice(FAQ_PRE_VI if lg == "vi" else FAQ_PRE_EN)
    suf = r.choice(FAQ_SUF_VI if lg == "vi" else FAQ_SUF_EN)
    body = base.rstrip("?.! ")
    if pre and lg == "en":
        body = body[0].lower() + body[1:] if not body.startswith("I") else body
    return tid, pre + body + suf + "?", lg


def gen_ignore(r, lang):
    lg = "en" if lang == "en" else "vi"
    bases = IGN_EN if lg == "en" else IGN_VI
    fill = FILL_EN if lg == "en" else FILL_VI
    x = r.random()
    if x < .45:
        i = r.randrange(len(bases)); b = bases[i]
        pre = r.choice(["", "", fill[0] + ", ", r.choice(fill) + "... ", "Haha, " if lg == "vi" else "Haha, "])
        suf = r.choice(["", "", "...", "!", " haha" if lg == "vi" else " lol", " nhé" if lg == "vi" else " yeah"])
        return "I:b%s:%d" % (lg, i), pre + b + suf, lg
    if x < .70:
        i, j = r.sample(range(len(bases)), 2)
        return "I:pair%s:%d" % (lg, i % 12), bases[i] + r.choice([", ", "... ", ". "]) + bases[j], lg
    if x < .92:
        n = r.randint(1, 5)
        return "I:noise%s:%d" % (lg, n), r.choice(["", "", "..."]) .join([""]) + " ".join(
            r.choice(fill) + r.choice(["", "", "...", ","]) for _ in range(n)).strip(), lg
    return "I:junk%s:%d" % (lg, r.randrange(3)), r.choice(JUNK) + (" " + r.choice(fill) if r.random() < .4 else ""), lg


GEN = {"order": gen_order, "consultant": gen_cons, "faq": gen_faq, "ignore": gen_ignore}
LANG_W = {"order": (.50, .40, .10), "consultant": (.50, .40, .10), "faq": (.54, .46, 0.0), "ignore": (.50, .50, 0.0)}


def pick_lang(r, intent):
    return r.choices(["vi", "en", "vi-en"], weights=LANG_W[intent])[0]


def hard_gen(r, intent):
    lang = r.choice(["vi", "vi", "en"])
    tpls = HARD[intent][lang]
    t = r.randrange(len(tpls))
    c = ctx_vi(r) if lang == "vi" else ctx_en(r)
    if lang == "vi" and r.random() < .15:
        c = ctx_vi(r, True); lang = "vi-en"
    return "H:%s:%s:%d" % (intent, "vi" if lang != "en" else "en", t), tpls[t].format(**c), lang


def is_test_group(tpl):
    return zlib.crc32(tpl.encode()) % 5 == 0


def balanced_pick(pool, n, r):
    """Chon n mau, dan deu theo template (round-robin) de tranh 1 template chiem het."""
    by = defaultdict(list)
    for p in pool:
        by[p["tpl"]].append(p)
    for v in by.values():
        r.shuffle(v)
    keys = list(by); r.shuffle(keys)
    out = []
    while len(out) < n and keys:
        nxt = []
        for k in keys:
            if by[k]:
                out.append(by[k].pop())
                if len(out) == n:
                    break
            if by[k]:
                nxt.append(k)
        keys = nxt
    assert len(out) == n, "pool qua nho: %d < %d" % (len(out), n)
    return out


seen = {}           # norm -> intent (chong trung + chong xung dot nhan)
conflict = set()


def build_pool(intent, hard, target_train, target_test, r, max_iter=60000):
    pools = {"train": [], "test": []}
    for _ in range(max_iter):
        if len(pools["train"]) >= target_train and len(pools["test"]) >= target_test:
            break
        if hard:
            tpl, text, lang = hard_gen(r, intent)
        else:
            lang = pick_lang(r, intent)
            tpl, text, lang = GEN[intent](r, lang)
        text = augment(text, lang, r)
        if intent in ("consultant", "faq") and r.random() < .3 and not text.endswith("?"):
            text = ensure_punct(text, r, True)
        nm = norm_text(text)
        if len(nm) < 1:
            continue
        if nm in seen:
            if seen[nm] != intent:
                conflict.add(nm)
            continue
        split = "test" if is_test_group(tpl) else "train"
        if len(pools[split]) >= (target_test if split == "test" else target_train):
            continue
        seen[nm] = intent
        pools[split].append(dict(text=text, intent=intent, tpl=tpl, language=lang, is_hard=hard, norm=nm))
    return pools


def main():
    r = random.Random(SEED + 7)
    rows = {"train": [], "test": []}
    for intent in INTENTS:
        # 1) hard truoc (de chiem cho trong 'seen' truoc, tranh easy lap)
        hp = build_pool(intent, True, 400, 120, r)
        ep = build_pool(intent, False, 3500, 500, r)
        for split, n_easy, n_hard in (("train", TRAIN_PER - HARD_TRAIN, HARD_TRAIN), ("test", TEST_PER - HARD_TEST, HARD_TEST)):
            rows[split] += balanced_pick(hp[split], n_hard, r) + balanced_pick(ep[split], n_easy, r)
    # bo mau gay xung dot nhan
    for split in rows:
        rows[split] = [x for x in rows[split] if x["norm"] not in conflict]
    out = {}
    for split in rows:
        r.shuffle(rows[split])
        recs = []
        for i, x in enumerate(rows[split], 1):
            lab = INTENTS.index(x["intent"])
            recs.append(dict(id="R-%s-%05d" % (split.upper(), i), text=x["text"], label=lab, intent=x["intent"],
                             is_noise=(x["intent"] == "ignore"), language=x["language"], is_hard=x["is_hard"]))
        out[split] = recs
        with open(os.path.join(OUT, "router_%s.json" % split), "w", encoding="utf-8") as f:
            json.dump(recs, f, ensure_ascii=False, indent=1)
    sysmsg = ("Bạn là Router của robot tư vấn F&B. Phân loại câu của khách thành đúng 1 intent: "
              "order (đặt món, thêm/bớt/đổi món, tính tiền), consultant (tư vấn, gợi ý, hỏi về món), "
              "faq (hỏi đáp thông tin quán, chính sách), ignore (chào hỏi, ồn, không liên quan). "
              'Chỉ trả JSON: {"action": "<intent>"}')
    for split, recs in out.items():
        with open(os.path.join(OUT, "router_%s_sft.jsonl" % split), "w", encoding="utf-8") as f:
            for x in recs:
                f.write(json.dumps({"messages": [
                    {"role": "system", "content": sysmsg},
                    {"role": "user", "content": x["text"]},
                    {"role": "assistant", "content": json.dumps({"action": x["intent"]}, ensure_ascii=False)}]},
                    ensure_ascii=False) + "\n")
    for split, recs in out.items():
        print(split, len(recs), dict(Counter(x["intent"] for x in recs)),
              "hard=%d" % sum(x["is_hard"] for x in recs), dict(Counter(x["language"] for x in recs)))


if __name__ == "__main__":
    main()
