import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

# Cấu hình kết nối API
API_BASE_URL = "http://localhost:8080/api/v1"
HEADERS = {"Content-Type": "application/json"}

def _call_api(endpoint: str, params: Optional[Dict] = None) -> Any:
    """Hàm chung để gọi API, xử lý lỗi và cấu trúc ApiResponse."""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        json_response = response.json()
        if isinstance(json_response, dict) and 'data' in json_response:
            return json_response['data']
        return json_response
    except requests.exceptions.RequestException as e:
        print(f"Lỗi gọi API đến endpoint {endpoint}: {e}")
        return None
    except ValueError:
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
        "topLevelCategory": category, "brand": brand, "keyword": keyword,
        "minPrice": int(min_price) if min_price else None,
        "maxPrice": int(max_price) if max_price else None,
    }
    params = {k: v for k, v in params.items() if v is not None}
    product_list = _call_api(api_endpoint, params=params)
    if product_list and isinstance(product_list, list):
        results = []
        for product in product_list[:limit]:
            results.append({
                "id": product.get("id"), "title": product.get("title"),
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

def get_brands_for_category(category_name: str) -> List[str]:
    """Lấy danh sách thương hiệu (category cấp 2) cho một danh mục cấp 1."""
    # Backend của bạn có endpoint GET /api/v1/categories/{topCategory}
    api_endpoint = f"/categories/{category_name}"
    
    sub_categories = _call_api(api_endpoint)
    
    if sub_categories and isinstance(sub_categories, list):
        # Trích xuất ra danh sách tên thương hiệu
        brands = [cat.get("name") for cat in sub_categories if cat.get("name")]
        return brands
    return []

def get_order_status(order_id: str) -> Optional[Dict[str, Any]]:
    """Lấy trạng thái đơn hàng từ backend."""
    api_endpoint = f"/orders/{order_id}"
    data = _call_api(api_endpoint)
    if data and isinstance(data, dict):
        delivery_date_str = data.get('deliveryDate')
        delivery_date_formatted = ''
        if delivery_date_str:
            try: delivery_date_formatted = datetime.fromisoformat(delivery_date_str).strftime('%d/%m/%Y')
            except (ValueError, TypeError): delivery_date_formatted = delivery_date_str
        return {"status": data.get("orderStatus"), "delivery_date": delivery_date_formatted}
    return None