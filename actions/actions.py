from typing import Any, Text, Dict, List, Optional
import re
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from .techstore_api import search_products, get_product_details_by_id, get_order_status

# Bảng "biên dịch" và suy luận category
CATEGORY_MAP = {
    "điện thoại": "Phone", "iphone": "Phone", "samsung": "Phone", "xiaomi": "Phone", "oppo": "Phone", "oneplus": "Phone",
    "laptop": "Laptop", "máy tính xách tay": "Laptop", "acer": "Laptop", "asus": "Laptop", "dell": "Laptop", "hp": "Laptop", "msi": "Laptop", "lenovo": "Laptop",
    "phụ kiện": "Accessory", "tai nghe": "Accessory", "bàn phím": "Accessory", "chuột": "Accessory", "màn hình": "Accessory", "sạc dự phòng": "Accessory",
    "máy tính bàn": "desktop-computers", "pc": "desktop-computers",
}

# --- HÀM XỬ LÝ GIÁ ĐÃ ĐƯỢC VIẾT LẠI HOÀN TOÀN ĐỂ ĐẢM BẢO ĐỘ CHÍNH XÁC ---
def parse_price_range(text: Optional[str]) -> (Optional[float], Optional[float]):
    if not text:
        return None, None
    
    text = str(text).lower()
    min_price, max_price = None, None
    
    try:
        # Chuẩn hóa các đơn vị tiền tệ
        multiplier = 1
        if 'triệu' in text or 'tr' in text:
            multiplier = 1000000
        elif 'k' in text:
            multiplier = 1000

        # Tìm tất cả các chuỗi số (có thể có dấu chấm)
        # và loại bỏ các dấu chấm ngăn cách hàng nghìn trước khi chuyển đổi
        numbers = [float(n.replace('.', '')) for n in re.findall(r'[\d\.]+', text)]
        
        if not numbers:
            return None, None

        # Nhân các số tìm được với hệ số (triệu, k)
        numbers = [n * multiplier for n in numbers]
        
        # Xác định khoảng min/max dựa trên từ khóa
        if "dưới" in text or "tối đa" in text:
            max_price = numbers[0]
        elif "trên" in text or ("từ" in text and len(numbers) == 1):
            min_price = numbers[0]
        elif len(numbers) == 2:
            min_price, max_price = min(numbers), max(numbers)
        elif len(numbers) == 1:
            # Nếu chỉ có 1 số, ví dụ "giá 20 triệu", mặc định là giá tối đa
            max_price = numbers[0]
    
    except Exception as e:
        print(f"Không thể xử lý chuỗi giá '{text}': {e}")
        return None, None
        
    return min_price, max_price

# --- CÁC LỚP ACTION ---
class ValidateProductSearchForm(FormValidationAction):
    def name(self) -> Text: return "validate_product_search_form"
    def validate_brand(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        if isinstance(slot_value, str) and slot_value.lower() in ["bỏ qua", "không"]: return {"brand": "skip"}
        return {"brand": slot_value}
    def validate_price_range(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> Dict[Text, Any]:
        if isinstance(slot_value, str) and slot_value.lower() in ["bỏ qua", "không"]: return {"price_range": "skip"}
        min_p, max_p = parse_price_range(slot_value)
        if min_p is None and max_p is None:
            dispatcher.utter_message(text="Tôi chưa hiểu yêu cầu về giá của bạn. Vui lòng thử lại (ví dụ: 'dưới 20 triệu').")
            return {"price_range": None}
        return {"price_range": slot_value}

class ActionSubmitSearchForm(Action):
    def name(self) -> Text: return "action_submit_search_form"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(response="utter_now_searching")
        product_type = tracker.get_slot("product_type")
        brand = tracker.get_slot("brand")
        price_range_str = tracker.get_slot("price_range")
        if brand == "skip": brand = None
        if price_range_str == "skip": price_range_str = None
        min_price, max_price = parse_price_range(price_range_str)
        product_type_en = CATEGORY_MAP.get(product_type.lower()) if product_type else None
        
        products = search_products(category=product_type_en, brand=brand, min_price=min_price, max_price=max_price)
        
        if not products: response_text = "Rất tiếc, tôi không tìm thấy sản phẩm nào phù hợp với yêu cầu của bạn."
        elif len(products) == 1:
            prod = products[0]
            prod_url = f"http://localhost:5173/products/{prod.get('id')}"
            response_text = f"Tôi đã tìm thấy một sản phẩm rất phù hợp: **{prod.get('title', 'N/A')}** - {prod.get('discounted_price_formatted', 'N/A')}\n\nXem chi tiết tại đây: {prod_url}"
        else:
            response_text = "Đây là các sản phẩm tôi tìm thấy:\n\n"
            for p in products: response_text += f"- **{p.get('title', 'N/A')}** - {p.get('discounted_price_formatted', 'N/A')}\n"
            response_text += "\nBạn muốn xem chi tiết sản phẩm nào?"
        dispatcher.utter_message(text=response_text)
        return [SlotSet("product_type", None), SlotSet("brand", None), SlotSet("price_range", None)]

class ActionProductDetails(Action):
    def name(self) -> Text: return "action_product_details"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        p_name = next(tracker.get_latest_entity_values("product_name"), None)
        if not p_name:
            dispatcher.utter_message("Bạn muốn xem chi tiết sản phẩm nào ạ?")
            return []
        found = search_products(keyword=p_name, limit=1)
        if not found:
            dispatcher.utter_message(f"Xin lỗi, tôi không tìm thấy sản phẩm nào có tên '{p_name}'.")
            return []
        product = get_product_details_by_id(found[0].get('id'))
        if product:
            p_url = f"http://localhost:5173/products/{product.get('id')}"
            response = f"Thông tin về **{product['title']}**:\nGiá: {product.get('discounted_price_formatted', 'N/A')}\nMô tả: {product.get('description', 'N/A')}\n\nLink: {p_url}"
            dispatcher.utter_message(text=response)
        else:
            dispatcher.utter_message(f"Xin lỗi, tôi không thể lấy thông tin chi tiết cho '{p_name}'.")
        return []