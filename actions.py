from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet #update giá trị slot trong convers
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from techstore_api import (
    get_product_recommendations,
    get_product_details_by_name,
    get_product_details_by_type_and_brand,
    check_product_availability,
    filter_products_by_price,
    get_categories,
    format_price
)

class ActionRecommendProducts(Action):
    def name(self) -> Text:
        return "action_recommend_products"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Lấy loại sản phẩm từ slot
        product_type = tracker.get_slot("product_type")
        price_range = tracker.get_slot("price_range")
        feature = tracker.get_slot("feature")
        
        # Gọi API để lấy danh sách sản phẩm gợi ý
        recommendations = get_product_recommendations(product_type, price_range, feature)
        
        # Tạo phản hồi với các sản phẩm được in đậm
        if recommendations:
            response = f"Dựa trên yêu cầu của bạn về **{product_type}**, tôi gợi ý các sản phẩm sau:\n\n"
            for idx, product in enumerate(recommendations, 1):
                response += f"{idx}. **{product['title']}** - {product['price_formatted']}\n"
                response += f"   {product['short_description']}\n\n"
            
            response += "Bạn có muốn biết thêm chi tiết về sản phẩm nào không?"
        else:
            response = f"Hiện tại chúng tôi không có sản phẩm **{product_type}** phù hợp với yêu cầu của bạn. Bạn có thể mô tả lại nhu cầu được không?"
        
        dispatcher.utter_message(text=response)
        
        return []


class ActionProductDetails(Action):
    def name(self) -> Text:
        return "action_product_details"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        product_name = tracker.get_slot("product_name")
        product_type = tracker.get_slot("product_type")
        brand = tracker.get_slot("brand")
        
        # Lấy thông tin chi tiết sản phẩm từ API
        if product_name:
            product = get_product_details_by_name(product_name)
        elif product_type and brand:
            product = get_product_details_by_type_and_brand(product_type, brand)
        else:
            dispatcher.utter_message("Vui lòng cung cấp tên sản phẩm cụ thể để tôi có thể giúp bạn.")
            return []
        
        if product:
            # Tạo phản hồi chi tiết về sản phẩm
            response = f"**{product['title']}**\n\n"
            
            # Giá và giảm giá
            if product.get('discounted_price') and product.get('price') and product['discounted_price'] < product['price']:
                response += f"Giá: ~~{product['price_formatted']}~~ **{product['discounted_price_formatted']}** (Giảm giá)\n\n"
            else:
                response += f"Giá: **{product['price_formatted']}**\n\n"
            
            # Mô tả
            if product.get('description'):
                response += f"{product['description']}\n\n"
            
            # Thông số kỹ thuật
            if product.get('specifications'):
                response += "**Thông số kỹ thuật:**\n"
                for spec in product['specifications']:
                    response += f"- {spec['name']}: {spec['value']}\n"
            
            # Kích thước có sẵn
            if product.get('sizes'):
                response += "\n**Kích thước có sẵn:**\n"
                for size in product['sizes']:
                    response += f"- {size.get('name')}: {size.get('quantity')} sản phẩm\n"
            
            response += "\nBạn có muốn biết thêm về sản phẩm này hoặc so sánh với sản phẩm khác không?"
            
            dispatcher.utter_message(text=response)
            
            # Lưu tên sản phẩm vào slot để sử dụng sau này
            return [SlotSet("product_name", product['title'])]
        else:
            dispatcher.utter_message(f"Xin lỗi, tôi không tìm thấy thông tin về sản phẩm này. Bạn có thể cung cấp thêm chi tiết hoặc thử tìm kiếm sản phẩm khác.")
            return []


class ActionCheckPrice(Action):
    def name(self) -> Text:
        return "action_check_price"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        product_name = tracker.get_slot("product_name")
        product_type = tracker.get_slot("product_type")
        brand = tracker.get_slot("brand")
        
        if product_name:
            product = get_product_details_by_name(product_name)
        elif product_type and brand:
            product = get_product_details_by_type_and_brand(product_type, brand)
        else:
            dispatcher.utter_message("Vui lòng cho tôi biết tên sản phẩm cụ thể để kiểm tra giá.")
            return []
        
        if product:
            # Hiển thị giá và giảm giá nếu có
            if product.get('discounted_price') and product.get('price') and product['discounted_price'] < product['price']:
                response = f"**{product['title']}** có giá niêm yết là {product['price_formatted']} nhưng hiện đang được giảm giá còn **{product['discounted_price_formatted']}**."
            else:
                response = f"**{product['title']}** có giá là **{product['price_formatted']}**."
                
            response += "\n\nBạn có muốn biết thêm thông tin về sản phẩm này không?"
            
            dispatcher.utter_message(text=response)
        else:
            dispatcher.utter_message(f"Xin lỗi, tôi không tìm thấy thông tin giá của sản phẩm này. Bạn có thể cung cấp thêm chi tiết hoặc thử tìm kiếm sản phẩm khác.")
        
        return []


class ActionCheckAvailability(Action):
    def name(self) -> Text:
        return "action_check_availability"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        product_name = tracker.get_slot("product_name")
        product_type = tracker.get_slot("product_type")
        brand = tracker.get_slot("brand")
        
        if not product_name and product_type and brand:
            # Tìm sản phẩm dựa trên loại và thương hiệu nếu không có tên cụ thể
            product = get_product_details_by_type_and_brand(product_type, brand)
            product_name = product.get('title') if product else None
        
        if not product_name:
            dispatcher.utter_message("Vui lòng cho tôi biết tên sản phẩm cụ thể để kiểm tra tồn kho.")
            return []
        
        # Kiểm tra tồn kho
        availability = check_product_availability(product_name)
        
        if availability and 'product_name' in availability:
            if availability.get('is_available'):
                response = f"**{availability['product_name']}** hiện đang có sẵn với {availability['available_quantity']} sản phẩm trong kho."
                
                # Hiển thị các size có sẵn nếu có
                if availability.get('available_sizes'):
                    response += f"\n\nCác kích thước có sẵn: {', '.join(availability['available_sizes'])}"
                
                response += "\n\nBạn có muốn đặt hàng hoặc xem thêm thông tin về sản phẩm này không?"
            else:
                response = f"Xin lỗi, **{availability['product_name']}** hiện đang hết hàng. Bạn có muốn xem các sản phẩm tương tự không?"
            
            dispatcher.utter_message(text=response)
        else:
            dispatcher.utter_message(f"Xin lỗi, tôi không tìm thấy thông tin tồn kho của sản phẩm này. Bạn có thể cung cấp thêm chi tiết hoặc thử tìm kiếm sản phẩm khác.")
        
        return []


class ActionFilterByPrice(Action):
    def name(self) -> Text:
        return "action_filter_by_price"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        product_type = tracker.get_slot("product_type")
        min_price = tracker.get_slot("min_price")
        max_price = tracker.get_slot("max_price")
        price_range = tracker.get_slot("price_range")
        
        # Xử lý price_range nếu có
        if price_range and not (min_price or max_price):
            parts = price_range.lower().replace("triệu", "").strip().split("-")
            if len(parts) == 2:
                try:
                    min_price = float(parts[0].strip()) * 1000000
                    max_price = float(parts[1].strip()) * 1000000
                except ValueError:
                    pass
            elif "dưới" in price_range.lower():
                try:
                    value = price_range.lower().replace("dưới", "").replace("triệu", "").strip()
                    max_price = float(value) * 1000000
                except ValueError:
                    pass
            elif "trên" in price_range.lower():
                try:
                    value = price_range.lower().replace("trên", "").replace("triệu", "").strip()
                    min_price = float(value) * 1000000
                except ValueError:
                    pass
        
        # Gọi API để lọc sản phẩm theo giá
        filtered_products = filter_products_by_price(product_type, min_price, max_price)
        
        if filtered_products:
            # Tạo phản hồi với các sản phẩm được lọc
            price_filter_desc = ""
            if min_price and max_price:
                price_filter_desc = f"từ {format_price(min_price)} đến {format_price(max_price)}"
            elif min_price:
                price_filter_desc = f"trên {format_price(min_price)}"
            elif max_price:
                price_filter_desc = f"dưới {format_price(max_price)}"
            
            response = f"Tôi đã tìm thấy {len(filtered_products)} sản phẩm {product_type or ''} có giá {price_filter_desc}:\n\n"
            
            for idx, product in enumerate(filtered_products, 1):
                if product.get('discounted_price') and product.get('price') and product['discounted_price'] < product['price']:
                    response += f"{idx}. **{product['title']}** - ~~{product['price_formatted']}~~ **{product['discounted_price_formatted']}**\n"
                else:
                    response += f"{idx}. **{product['title']}** - **{product['price_formatted']}**\n"
            
            response += "\nBạn có muốn xem chi tiết sản phẩm nào không?"
        else:
            response = f"Xin lỗi, tôi không tìm thấy sản phẩm nào phù hợp với tiêu chí giá của bạn. Bạn có muốn thử với khoảng giá khác không?"
        
        dispatcher.utter_message(text=response)
        
        return []


class ActionFilterByBrand(Action):
    def name(self) -> Text:
        return "action_filter_by_brand"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        product_type = tracker.get_slot("product_type")
        brand = tracker.get_slot("brand")
        
        if not brand:
            dispatcher.utter_message("Vui lòng cho tôi biết thương hiệu bạn quan tâm.")
            return []
        
        # Tìm sản phẩm theo thương hiệu và loại sản phẩm
        products = get_product_recommendations(product_type, brand=brand)
        
        if products:
            response = f"Tôi đã tìm thấy các sản phẩm **{brand}** trong danh mục **{product_type or 'sản phẩm'}**:\n\n"
            
            for idx, product in enumerate(products, 1):
                if product.get('discounted_price') and product.get('price') and product['discounted_price'] < product['price']:
                    response += f"{idx}. **{product['title']}** - ~~{product['price_formatted']}~~ **{product['discounted_price_formatted']}**\n"
                else:
                    response += f"{idx}. **{product['title']}** - **{product['price_formatted']}**\n"
            
            response += "\nBạn có muốn xem chi tiết sản phẩm nào không?"
        else:
            response = f"Xin lỗi, tôi không tìm thấy sản phẩm nào thuộc thương hiệu **{brand}** trong danh mục **{product_type or 'sản phẩm'}**. Bạn có muốn xem thương hiệu khác không?"
        
        dispatcher.utter_message(text=response)
        
        return []


class ActionFilterByFeatures(Action):
    def name(self) -> Text:
        return "action_filter_by_features"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        product_type = tracker.get_slot("product_type")
        feature = tracker.get_slot("feature")
        
        if not feature:
            dispatcher.utter_message("Vui lòng cho tôi biết tính năng bạn quan tâm.")
            return []
        
        # Tìm sản phẩm theo tính năng và loại sản phẩm
        products = get_product_recommendations(product_type, feature=feature)
        
        if products:
            response = f"Tôi đã tìm thấy các sản phẩm **{product_type or ''}** có tính năng **{feature}**:\n\n"
            
            for idx, product in enumerate(products, 1):
                if product.get('discounted_price') and product.get('price') and product['discounted_price'] < product['price']:
                    response += f"{idx}. **{product['title']}** - ~~{product['price_formatted']}~~ **{product['discounted_price_formatted']}**\n"
                else:
                    response += f"{idx}. **{product['title']}** - **{product['price_formatted']}**\n"
            
            response += "\nBạn có muốn xem chi tiết sản phẩm nào không?"
        else:
            response = f"Xin lỗi, tôi không tìm thấy sản phẩm nào có tính năng **{feature}** trong danh mục **{product_type or 'sản phẩm'}**. Bạn có muốn tìm kiếm với tính năng khác không?"
        
        dispatcher.utter_message(text=response)
        
        return []


class ActionCompareProducts(Action):
    def name(self) -> Text:
        return "action_compare_products"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Xử lý 2 sản phẩm cần so sánh
        product_entities = [e for e in tracker.latest_message.get("entities", []) if e["entity"] == "product_name"]
        
        if len(product_entities) < 2:
            dispatcher.utter_message("Vui lòng cung cấp tên của hai sản phẩm bạn muốn so sánh.")
            return []
        
        product1_name = product_entities[0]["value"]
        product2_name = product_entities[1]["value"]
        
        # Lấy thông tin chi tiết của cả hai sản phẩm
        product1 = get_product_details_by_name(product1_name)
        product2 = get_product_details_by_name(product2_name)
        
        if not product1 or not product2:
            missing_product = "sản phẩm đầu tiên" if not product1 else "sản phẩm thứ hai"
            dispatcher.utter_message(f"Xin lỗi, tôi không tìm thấy thông tin về {missing_product}. Vui lòng kiểm tra lại tên sản phẩm.")
            return []
        
        # Tạo bảng so sánh
        response = f"**So sánh giữa {product1['title']} và {product2['title']}:**\n\n"
        
        # So sánh giá
        response += "**Giá bán:**\n"
        response += f"- {product1['title']}: {product1['price_formatted']}"
        if product1.get('discounted_price') and product1.get('price') and product1['discounted_price'] < product1['price']:
            response += f" (Giảm giá còn {product1['discounted_price_formatted']})\n"
        else:
            response += "\n"
            
        response += f"- {product2['title']}: {product2['price_formatted']}"
        if product2.get('discounted_price') and product2.get('price') and product2['discounted_price'] < product2['price']:
            response += f" (Giảm giá còn {product2['discounted_price_formatted']})\n"
        else:
            response += "\n"
        
        # So sánh thông số kỹ thuật (nếu có)
        if product1.get('specifications') and product2.get('specifications'):
            response += "\n**Thông số kỹ thuật:**\n"
            
            # Tạo danh sách tất cả các loại thông số có trong cả hai sản phẩm
            all_specs = set()
            for spec in product1.get('specifications', []):
                all_specs.add(spec['name'])
            for spec in product2.get('specifications', []):
                all_specs.add(spec['name'])
            
            # Tạo bảng so sánh
            for spec_name in sorted(all_specs):
                spec1_value = next((spec['value'] for spec in product1.get('specifications', []) if spec['name'] == spec_name), "N/A")
                spec2_value = next((spec['value'] for spec in product2.get('specifications', []) if spec['name'] == spec_name), "N/A")
                
                response += f"- **{spec_name}**:\n"
                response += f"  - {product1['title']}: {spec1_value}\n"
                response += f"  - {product2['title']}: {spec2_value}\n"
        
        response += "\nBạn có muốn biết thêm thông tin về sản phẩm nào không?"
        
        dispatcher.utter_message(text=response)
        
        return []


class ActionCheckOrderStatus(Action):
    def name(self) -> Text:
        return "action_check_order_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Trong thực tế, bạn sẽ tích hợp với API để kiểm tra trạng thái đơn hàng
        order_entities = [e for e in tracker.latest_message.get("entities", []) if e["entity"] == "order_id"]
        
        if not order_entities:
            dispatcher.utter_message("Vui lòng cung cấp mã đơn hàng để tôi kiểm tra trạng thái.")
            return []
        
        order_id = order_entities[0]["value"]
        
        # Đây là phản hồi mẫu, trong thực tế bạn sẽ gọi API để lấy trạng thái đơn hàng
        response = f"Đơn hàng **{order_id}** đang trong trạng thái **Đang giao hàng**. Dự kiến sẽ được giao vào ngày mai. Bạn có thể kiểm tra chi tiết tại trang Đơn hàng của tài khoản hoặc liên hệ với bộ phận CSKH qua số hotline 1900 xxxx nếu cần hỗ trợ thêm."
        
        dispatcher.utter_message(text=response)
        
        return []