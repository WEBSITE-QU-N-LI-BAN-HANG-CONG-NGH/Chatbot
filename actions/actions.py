from typing import Any, Text, Dict, List, Optional
import re
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from .techstore_api import (
    search_products,
    get_product_details_by_id,
    get_brands_for_category,
    get_order_status
)

# --- HÀM HỖ TRỢ XỬ LÝ GIÁ ---
def parse_price_range(price_range_str: str) -> (Optional[float], Optional[float]):
    if not price_range_str: return None, None
    price_range_str = str(price_range_str).lower().replace(",", "")
    min_price, max_price = None, None
    if 'k' in price_range_str: price_range_str = price_range_str.replace('k', '000')
    if 'tr' in price_range_str or 'triệu' in price_range_str: price_range_str = price_range_str.replace('tr', '000000').replace('triệu', '000000')
    try:
        numbers = [float(s) for s in re.findall(r'[\d\.]+', price_range_str)]
        if "dưới" in price_range_str or "không quá" in price_range_str:
            if numbers: max_price = numbers[0]
        elif "trên" in price_range_str:
            if numbers: min_price = numbers[0]
        elif len(numbers) == 2:
            min_price, max_price = min(numbers), max(numbers)
        elif len(numbers) == 1:
            min_price = numbers[0] * 0.8
            max_price = numbers[0] * 1.2
    except Exception as e:
        print(f"Lỗi khi xử lý giá: {e}")
        return None, None
    return min_price, max_price

class ValidateProductSearchForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_product_search_form"

    def validate_brand(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if isinstance(slot_value, str) and slot_value.lower() in ["bỏ qua", "không", "không cần", "hãng nào cũng được", "tất cả"]:
            return {"brand": None}
        return {"brand": slot_value}

class ActionSubmitSearchForm(Action):
    def name(self) -> Text:
        return "action_submit_search_form"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(response="utter_now_searching")
        
        product_type = tracker.get_slot("product_type")
        brand = tracker.get_slot("brand")
        price_range_str = tracker.get_slot("price_range")
        
        min_price, max_price = parse_price_range(price_range_str)
        
        # Dịch product_type tiếng Việt sang tiếng Anh cho API
        category_map = {"điện thoại": "Phone", "laptop": "Laptop", "phụ kiện": "Accessory"}
        product_type_en = category_map.get(product_type.lower(), product_type)

        products = search_products(
            category=product_type_en, brand=brand,
            min_price=min_price, max_price=max_price
        )
        
        if not products:
            response_text = "Rất tiếc, tôi không tìm thấy sản phẩm nào phù hợp với yêu cầu của bạn."
        elif len(products) == 1:
            product = products[0]
            product_id = product.get("id")
            product_url = f"http://localhost:5173/products/{product_id}"
            response_text = (
                f"Tôi đã tìm thấy một sản phẩm rất phù hợp:\n\n"
                f"**{product.get('title', 'N/A')}** - {product.get('discounted_price_formatted', 'N/A')}\n\n"
                f"Bạn có thể xem chi tiết tại đây:\n{product_url}"
            )
        else:
            response_text = "Đây là các sản phẩm tôi tìm thấy theo yêu cầu của bạn:\n\n"
            for product in products:
                response_text += f"- **{product.get('title', 'N/A')}** - {product.get('discounted_price_formatted', 'N/A')}\n"
            response_text += "\nBạn muốn xem chi tiết sản phẩm nào?"
            
        dispatcher.utter_message(text=response_text)
        return [SlotSet("product_type", None), SlotSet("brand", None), SlotSet("price_range", None)]

class ActionProductDetails(Action):
    def name(self) -> Text: return "action_product_details"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        product_name = next(tracker.get_latest_entity_values("product_name"), None)
        if not product_name:
            dispatcher.utter_message("Bạn muốn xem chi tiết sản phẩm nào ạ?")
            return []
            
        found_products = search_products(keyword=product_name, limit=1)
        if not found_products:
            dispatcher.utter_message(f"Xin lỗi, tôi không tìm thấy sản phẩm nào có tên '{product_name}'.")
            return []
            
        product_id = found_products[0].get('id')
        product = get_product_details_by_id(product_id)
        if product:
            product_url = f"http://localhost:5173/products/{product_id}"
            response = (
                f"Thông tin chi tiết về **{product['title']}**:\n"
                f"Giá: {product.get('discounted_price_formatted', 'N/A')}\n"
                f"Mô tả: {product.get('description', 'Chưa có mô tả.')}\n\n"
                f"Link sản phẩm: {product_url}"
            )
            dispatcher.utter_message(text=response)
        else:
            dispatcher.utter_message(f"Xin lỗi, tôi không thể lấy thông tin chi tiết cho sản phẩm '{product_name}'.")
        return []

class ActionCheckOrderStatus(Action):
    def name(self) -> Text: return "action_check_order_status"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        order_id = next(tracker.get_latest_entity_values("order_id"), None)
        if not order_id:
            dispatcher.utter_message("Vui lòng cung cấp mã đơn hàng của bạn.")
            return []
        
        order_id_numeric = "".join(filter(str.isdigit, str(order_id)))
        if not order_id_numeric:
            dispatcher.utter_message("Mã đơn hàng không hợp lệ.")
            return []
            
        order_info = get_order_status(order_id_numeric)
        if order_info and order_info.get("status"):
            status_map = {"PENDING": "Đang chờ xử lý", "CONFIRMED": "Đã xác nhận", "SHIPPED": "Đang giao", "DELIVERED": "Đã giao thành công", "CANCELLED": "Đã bị hủy"}
            status = order_info["status"]
            friendly_status = status_map.get(status, status)
            response = f"Đơn hàng **#{order_id_numeric}** của bạn có trạng thái: **{friendly_status}**."
        else:
            response = f"Xin lỗi, tôi không thể tìm thấy thông tin cho đơn hàng có mã **#{order_id_numeric}**."
        
        dispatcher.utter_message(text=response)
        return []