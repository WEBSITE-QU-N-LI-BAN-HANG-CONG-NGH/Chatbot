from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tech_store_api import *

def format_price(price):
    """Helper function để format giá tiền"""
    if isinstance(price, (int, float)):
        if price >= 1000000:
            return f"{price/1000000:.1f} triệu đồng"
        else:
            return f"{price:,.0f} đồng"
    return price


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
            return