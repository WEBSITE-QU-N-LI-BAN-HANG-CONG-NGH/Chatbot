# actions/techstore_api.py

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

API_BASE_URL = "http://localhost:8080/api/v1"
HEADERS = {"Content-Type": "application/json"}

def _call_api(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Hàm chung để gọi API, xử lý lỗi và cấu trúc ApiResponse."""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", params=params, headers=HEADERS, timeout=10)
        response.raise_for_status() # Ném lỗi nếu status code là 4xx hoặc 5xx
        json_response = response.json()
        
        # --- LOGIC SỬA LỖI NẰM Ở ĐÂY ---
        # Kiểm tra xem có phải là cấu trúc ApiResponse (có key 'data') không
        if isinstance(json_response, dict) and 'data' in json_response:
            # Nếu có, trả về nội dung của 'data'
            return json_response['data']
        
        # Nếu không, trả về toàn bộ json_response (dành cho API public trả về list trực tiếp)
        return json_response

    except requests.exceptions.RequestException as e:
        print(f"Lỗi gọi API đến endpoint {endpoint}: {e}")
        return None
    except ValueError: # Bắt lỗi nếu response không phải là JSON hợp lệ
        print(f"Lỗi: Phản hồi từ endpoint {endpoint} không phải là JSON.")
        return None

def format_price(price: Any) -> str:
    """Định dạng giá tiền sang kiểu Việt Nam."""
    if price is None: return "N/A"
    try: return f"{int(price):,} đ".replace(",", ".")
    except (ValueError, TypeError): return str(price)

def search_products(
    category: Optional[str] = None, brand: Optional[str] = None, keyword: Optional[str] = None,
    min_price: Optional[float] = None, max_price: Optional[float] = None, limit: int = 5
) -> List[Dict[str, Any]]:
    """Hàm tìm kiếm sản phẩm đa năng, gọi đến API public."""
    api_endpoint = "/products/" 
    
    params = {
        "topLevelCategory": category,
        "brand": brand,
        "keyword": keyword,
        "minPrice": int(min_price) if min_price else None,
        "maxPrice": int(max_price) if max_price else None,
    }
    params = {k: v for k, v in params.items() if v is not None}
    
    product_list = _call_api(api_endpoint, params=params)
    
    # Logic xử lý product_list giờ đã đúng
    if product_list and isinstance(product_list, list):
        results = []
        for product in product_list[:limit]:
            results.append({
                "id": product.get("id"),
                "title": product.get("title"),
                "price_formatted": format_price(product.get("price")),
                "discounted_price_formatted": format_price(product.get("discountedPrice")),
            })
        return results
    return []

def get_product_details_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Lấy chi tiết sản phẩm bằng ID."""
    api_endpoint = f"/products/id/{product_id}"
    data = _call_api(api_endpoint)
    
    if data and isinstance(data, dict):
        return {
            "id": data.get("id"), "title": data.get("title"), "price": data.get("price"),
            "price_formatted": format_price(data.get("price")),
            "discounted_price": data.get("discountedPrice"),
            "discounted_price_formatted": format_price(data.get("discountedPrice")),
            "description": data.get("description", ""), "sizes": data.get("sizes", [])
        }
    return None

# ... các hàm check_product_availability và get_order_status giữ nguyên ...
def check_product_availability(product_name: str) -> Optional[Dict[str, Any]]:
    products = search_products(keyword=product_name, limit=1)
    if not products: return None
    
    product_details = get_product_details_by_id(products[0]['id'])

    if product_details:
        total_quantity = sum(size.get('quantity', 0) for size in product_details.get('sizes', []))
        return {
            "product_name": product_details.get("title"), "is_available": total_quantity > 0,
            "available_quantity": total_quantity,
            "available_sizes": [size.get('name') for size in product_details.get("sizes", []) if size.get('quantity', 0) > 0]
        }
    return None

def get_order_status(order_id: str) -> Optional[Dict[str, Any]]:
    api_endpoint = f"/orders/{order_id}"
    data = _call_api(api_endpoint)
    
    if data and isinstance(data, dict):
        delivery_date_str = data.get('deliveryDate')
        delivery_date_formatted = ''
        if delivery_date_str:
            try:
                delivery_date_formatted = datetime.fromisoformat(delivery_date_str).strftime('%d/%m/%Y')
            except (ValueError, TypeError): delivery_date_formatted = delivery_date_str
        return {"status": data.get("orderStatus"), "delivery_date": delivery_date_formatted}
    return None