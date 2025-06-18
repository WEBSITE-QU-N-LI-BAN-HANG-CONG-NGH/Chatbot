# actions/actions.py

from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet, ActiveLoop


from .techstore_api import (
    search_products,
    get_product_details_by_id,
    check_product_availability,
    get_order_status,
    format_price
)




class ValidateProductSearchForm(FormValidationAction):
    """Lớp này chứa logic để validate các thông tin mà form thu thập."""
    def name(self) -> Text:
        return "validate_product_search_form"

    def validate_product_type(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        """Validate slot `product_type`."""
        # Hiện tại, chúng ta chấp nhận bất kỳ giá trị nào NLU trích xuất được.
        # Trong tương lai, có thể gọi API để kiểm tra xem đây có phải là danh mục hợp lệ không.
        if slot_value:
            return {"product_type": slot_value}
        return {"product_type": None}

    def validate_brand(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        """Validate slot `brand`, cho phép người dùng bỏ qua."""
        if isinstance(slot_value, str) and slot_value.lower() in ["bỏ qua", "không", "không cần", "hãng nào cũng được"]:
            return {"brand": None} # Trả về None nếu người dùng muốn bỏ qua
        return {"brand": slot_value}

    def validate_price_range(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict
    ) -> Dict[Text, Any]:
        """Validate slot `price_range`, cho phép người dùng bỏ qua."""
        if isinstance(slot_value, str) and slot_value.lower() in ["bỏ qua", "không", "không cần", "giá nào cũng được"]:
            return {"price_range": None} # Trả về None nếu người dùng muốn bỏ qua
        return {"price_range": slot_value}

class ActionSubmitSearchForm(Action):
    """
    Action này được chạy sau khi Form hoàn tất.
    Nó thay thế cho tất cả các action filter và recommend cũ.
    """
    def name(self) -> Text:
        return "action_submit_search_form"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(response="utter_now_searching")
        
        product_type = tracker.get_slot("product_type")
        brand = tracker.get_slot("brand")
        price_range_str = tracker.get_slot("price_range")
        feature = tracker.get_slot("feature")

        min_price, max_price = None, None
        if price_range_str:
            try:
                # Xử lý chuỗi giá linh hoạt hơn
                price_range_str = price_range_str.lower().replace("triệu", "e6").replace("tr", "e6")
                parts = price_range_str.strip().split("-")
                if "dưới" in price_range_str:
                    max_price = float(eval(price_range_str.replace("dưới", "").strip()))
                elif "trên" in price_range_str:
                    min_price = float(eval(price_range_str.replace("trên", "").strip()))
                elif len(parts) == 2:
                    min_price = float(eval(parts[0].strip()))
                    max_price = float(eval(parts[1].strip()))
            except Exception as e:
                print(f"Không thể xử lý khoảng giá: {price_range_str}, lỗi: {e}")

        products = search_products(
            category=product_type, brand=brand, keyword=feature,
            min_price=min_price, max_price=max_price
        )
        
        if products:
            response_text = "Đây là các sản phẩm tôi tìm thấy theo yêu cầu của bạn:\n\n"
            for product in products:
                response_text += f"- **{product.get('title', 'N/A')}** - {product.get('discounted_price_formatted', 'N/A')}\n"
        else:
            response_text = "Rất tiếc, tôi không tìm thấy sản phẩm nào phù hợp. Bạn có muốn thử lại với tiêu chí khác không?"
            
        dispatcher.utter_message(text=response_text)
        
        # --- THAY ĐỔI QUAN TRỌNG NHẤT NẰM Ở ĐÂY ---
        # Reset các slot để chuẩn bị cho lần tìm kiếm mới, tránh "nhớ" thông tin cũ.
        return [
            SlotSet("product_type", None),
            SlotSet("brand", None),
            SlotSet("price_range", None),
            SlotSet("feature", None)
        ]




class ActionProductDetails(Action):
    """Cung cấp thông tin chi tiết về một sản phẩm cụ thể."""
    def name(self) -> Text:
        return "action_product_details"

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
            response = f"**{product['title']}**\n"
            if product.get('discounted_price') and product.get('price') and product['discounted_price'] < product['price']:
                response += f"Giá: ~~{product['price_formatted']}~~ **{product['discounted_price_formatted']}**\n"
            else:
                response += f"Giá: **{product['price_formatted']}**\n"
            if product.get('description'):
                response += f"\n**Mô tả:** {product['description']}"
            dispatcher.utter_message(text=response)
        else:
            dispatcher.utter_message(f"Xin lỗi, tôi không thể lấy thông tin chi tiết cho sản phẩm '{product_name}'.")
        return []

class ActionCheckAvailability(Action):
    """Kiểm tra tình trạng còn hàng của một sản phẩm."""
    def name(self) -> Text:
        return "action_check_availability"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        product_name = next(tracker.get_latest_entity_values("product_name"), None)
        if not product_name:
            dispatcher.utter_message("Bạn muốn kiểm tra tình trạng hàng của sản phẩm nào ạ?")
            return []
        
        availability = check_product_availability(product_name)
        
        if availability:
            if availability.get('is_available'):
                response = f"Sản phẩm **{availability['product_name']}** vẫn còn hàng bạn nhé. "
                if availability.get('available_sizes'):
                    response += f"Các phiên bản còn hàng: {', '.join(availability['available_sizes'])}."
            else:
                response = f"Rất tiếc, sản phẩm **{availability['product_name']}** đã tạm hết hàng."
        else:
            response = f"Xin lỗi, tôi không tìm thấy thông tin tồn kho cho sản phẩm '{product_name}'."
        
        dispatcher.utter_message(text=response)
        return []

class ActionCheckOrderStatus(Action):
    """Kiểm tra trạng thái của một đơn hàng."""
    def name(self) -> Text:
        return "action_check_order_status"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        order_id = next(tracker.get_latest_entity_values("order_id"), None)
        if not order_id:
            dispatcher.utter_message("Vui lòng cung cấp mã đơn hàng (ví dụ: 'đơn hàng 123') để tôi kiểm tra.")
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
            if status == "DELIVERED" and order_info.get('delivery_date'):
                response += f" Đơn hàng đã được giao vào ngày {order_info['delivery_date']}."
        else:
            response = f"Xin lỗi, tôi không thể tìm thấy thông tin cho đơn hàng có mã **#{order_id_numeric}**."
        
        dispatcher.utter_message(text=response)
        return []
