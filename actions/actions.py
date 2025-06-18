from typing import Any, Text, Dict, List, Optional
import re
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from .techstore_api import search_products, get_product_details_by_id

CATEGORY_MAP = {"điện thoại": "Phone", "laptop": "Laptop", "phụ kiện": "Accessory", "acer": "Laptop", "asus": "Laptop", "dell": "Laptop", "hp": "Laptop", "apple": "Phone", "samsung": "Phone", "iphone": "Phone"}

def parse_price_range(text: Optional[str]) -> (Optional[float], Optional[float]):
    if not text: return None, None
    text = str(text).lower().replace(",", "").replace("đ", "").strip()
    min_price, max_price = None, None
    text = text.replace('k', '000').replace('tr', '000000').replace('triệu', '000000')
    try:
        numbers = [float(s) for s in re.findall(r'[\d\.]+', text)]
        if not numbers: return None, None
        if "dưới" in text: max_price = numbers[0]
        elif "trên" in text: min_price = numbers[0]
        elif len(numbers) == 2: min_price, max_price = min(numbers), max(numbers)
        elif len(numbers) == 1: max_price = numbers[0]
    except Exception as e:
        print(f"Lỗi xử lý giá: {e}")
    return min_price, max_price

class ActionHandleSearch(Action):
    def name(self) -> Text: return "action_handle_search"
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        product_type = tracker.get_slot("product_type")
        brand = tracker.get_slot("brand")
        price_range_str = tracker.get_slot("price_range")
        if not product_type and brand: product_type = CATEGORY_MAP.get(brand.lower())
        if not product_type:
            dispatcher.utter_message(response="utter_ask_product_type")
            return [SlotSet("brand", None), SlotSet("price_range", None)]
        dispatcher.utter_message(response="utter_now_searching")
        product_type_en = CATEGORY_MAP.get(product_type.lower(), product_type)
        min_price, max_price = parse_price_range(price_range_str)
        
        # --- LOGIC MỚI: Coi brand như một keyword ---
        keyword = brand if brand else None
        
        products = search_products(
            category=product_type_en, keyword=keyword,
            min_price=min_price, max_price=max_price
        )
        
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
            dispatcher.utter_message(f"Xin lỗi, tôi không tìm thấy sản phẩm có tên '{p_name}'.")
            return []
        product = get_product_details_by_id(found[0].get('id'))
        if product:
            p_url = f"http://localhost:5173/products/{product.get('id')}"
            response = f"Thông tin về **{product['title']}**:\nGiá: {product.get('discounted_price_formatted', 'N/A')}\nMô tả: {product.get('description', 'N/A')}\n\nLink: {p_url}"
            dispatcher.utter_message(text=response)
        else:
            dispatcher.utter_message(f"Xin lỗi, tôi không thể lấy thông tin chi tiết cho '{p_name}'.")
        return []