import json
import os
import requests
import pandas as pd
from typing import List, Dict, Any, Optional

# Cấu hình kết nối API
API_BASE_URL = "http://localhost:8080/api/v1"  #domain
HEADERS = {
    "Content-Type": "application/json"
}   #config request api

def get_product_recommendations(product_type: str, price_range: Optional[str] = None, feature: Optional[str] = None) -> List[Dict[str, Any]]:
    #loại sp, giá, tính năng    
    try:
        # Xây dựng query params
        params = {}
        if product_type:
            params["category"] = product_type
        
        if price_range:
            # Xử lý price_range từ chuỗi (vd: "5-10 triệu")
            price_parts = price_range.lower().replace("triệu", "").strip().split("-")
            if len(price_parts) == 2:
                try:
                    min_price = float(price_parts[0].strip()) * 1000000
                    max_price = float(price_parts[1].strip()) * 1000000
                    params["minPrice"] = int(min_price)
                    params["maxPrice"] = int(max_price)
                except ValueError:
                    pass
            elif "dưới" in price_range.lower():
                try:
                    value = price_range.lower().replace("dưới", "").replace("triệu", "").strip()
                    max_price = float(value) * 1000000
                    params["maxPrice"] = int(max_price)
                except ValueError:
                    pass
            elif "trên" in price_range.lower():
                try:
                    value = price_range.lower().replace("trên", "").replace("triệu", "").strip()
                    min_price = float(value) * 1000000
                    params["minPrice"] = int(min_price)
                except ValueError:
                    pass
        
        # Gọi API lấy sản phẩm
        response = requests.get(f"{API_BASE_URL}/products", params=params, headers=HEADERS)
        
        if response.status_code == 200:
            products = response.json()
            
            # Format lại dữ liệu để hiển thị
            results = []
            for product in products[:5]:  # Lấy tối đa 5 sản phẩm
                results.append({
                    "id": product.get("id"),
                    "title": product.get("title"),
                    "price": product.get("price"),
                    "price_formatted": format_price(product.get("price")),
                    "discounted_price": product.get("discountedPrice"),
                    "discounted_price_formatted": format_price(product.get("discountedPrice")),
                    "short_description": product.get("description", "")[:100] + "..." if product.get("description") else "",
                    "brand": product.get("brand"),
                    "image_url": product.get("imageUrls", [{}])[0].get("downloadUrl") if product.get("imageUrls") else None
                })
            
            return results
        else:
            print(f"Error fetching products: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Exception in get_product_recommendations: {str(e)}")
        return []

def get_product_details_by_name(product_name: str) -> Dict[str, Any]:
    """
    Lấy thông tin chi tiết sản phẩm dựa trên tên
    """
    try:
        # Tìm kiếm sản phẩm theo tên
        response = requests.get(f"{API_BASE_URL}/products/search/{product_name}", headers=HEADERS)
        
        if response.status_code == 200:
            products = response.json()
            if products and len(products) > 0:
                product = products[0]  # Lấy sản phẩm đầu tiên khớp với tên
                
                # Format thông tin sản phẩm
                return {
                    "id": product.get("id"),
                    "title": product.get("title"),
                    "price": product.get("price"),
                    "price_formatted": format_price(product.get("price")),
                    "discounted_price": product.get("discountedPrice"),
                    "discounted_price_formatted": format_price(product.get("discountedPrice")),
                    "description": product.get("description", ""),
                    "brand": product.get("brand"),
                    "color": product.get("color"),
                    "sizes": product.get("sizes", []),
                    "image_url": product.get("imageUrls", [{}])[0].get("downloadUrl") if product.get("imageUrls") else None,
                    "specifications": get_product_specifications(product)
                }
        
        return {}
            
    except Exception as e:
        print(f"Exception in get_product_details_by_name: {str(e)}")
        return {}

def get_product_details_by_type_and_brand(product_type: str, brand: str) -> Dict[str, Any]:
    """
    Lấy thông tin chi tiết sản phẩm dựa trên loại và thương hiệu
    """
    try:
        # Tìm kiếm sản phẩm theo loại và thương hiệu
        params = {
            "category": product_type,
            "brand": brand
        }
        
        response = requests.get(f"{API_BASE_URL}/products", params=params, headers=HEADERS)
        
        if response.status_code == 200:
            products = response.json()
            if products and len(products) > 0:
                product = products[0]  # Lấy sản phẩm đầu tiên khớp với điều kiện
                
                # Format thông tin sản phẩm (tương tự như hàm get_product_details_by_name)
                return {
                    "id": product.get("id"),
                    "title": product.get("title"),
                    "price": product.get("price"),
                    "price_formatted": format_price(product.get("price")),
                    "discounted_price": product.get("discountedPrice"),
                    "discounted_price_formatted": format_price(product.get("discountedPrice")),
                    "description": product.get("description", ""),
                    "brand": product.get("brand"),
                    "color": product.get("color"),
                    "sizes": product.get("sizes", []),
                    "image_url": product.get("imageUrls", [{}])[0].get("downloadUrl") if product.get("imageUrls") else None,
                    "specifications": get_product_specifications(product)
                }
        
        return {}
            
    except Exception as e:
        print(f"Exception in get_product_details_by_type_and_brand: {str(e)}")
        return {}

def get_product_specifications(product: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Trích xuất thông số kỹ thuật từ sản phẩm
    """
    specs = []
    
    # Trích xuất thông số từ các trường trong sản phẩm
    if "sizes" in product and product["sizes"]:
        sizes_str = ", ".join([size.get("name", "") for size in product["sizes"]])
        specs.append({"name": "Sizes", "value": sizes_str})
    
    if "brand" in product and product["brand"]:
        specs.append({"name": "Brand", "value": product["brand"]})
    
    if "color" in product and product["color"]:
        specs.append({"name": "Color", "value": product["color"]})
    
    # Thêm các thông số khác nếu có
    
    return specs

def format_price(price) -> str:
    """
    Format giá tiền theo định dạng Việt Nam
    """
    if price is None:
        return "Liên hệ"
    
    try:
        price = int(price)
        if price >= 1000000:
            return f"{price/1000000:.1f} triệu đồng"
        else:
            return f"{price:,} đồng".replace(",", ".")
    except:
        return str(price)

# Các hàm bổ sung khác
def get_categories() -> List[Dict[str, Any]]:
    """
    Lấy danh sách các danh mục sản phẩm
    """
    try:
        response = requests.get(f"{API_BASE_URL}/categories/all", headers=HEADERS)
        
        if response.status_code == 200:
            categories = response.json()
            return categories.get("data", [])
        else:
            print(f"Error fetching categories: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Exception in get_categories: {str(e)}")
        return []

def check_product_availability(product_name: str) -> Dict[str, Any]:
    """
    Kiểm tra tình trạng tồn kho của sản phẩm
    """
    product = get_product_details_by_name(product_name)
    
    if product:
        is_available = False
        available_quantity = 0
        
        if "sizes" in product and product["sizes"]:
            for size in product["sizes"]:
                quantity = size.get("quantity", 0)
                available_quantity += quantity
                if quantity > 0:
                    is_available = True
        
        return {
            "product_id": product.get("id"),
            "product_name": product.get("title"),
            "is_available": is_available,
            "available_quantity": available_quantity,
            "available_sizes": [size.get("name") for size in product.get("sizes", []) if size.get("quantity", 0) > 0]
        }
    
    return {
        "product_name": product_name,
        "is_available": False,
        "available_quantity": 0,
        "available_sizes": []
    }

def filter_products_by_price(product_type: str, min_price: float = None, max_price: float = None) -> List[Dict[str, Any]]:
    """
    Lọc sản phẩm theo khoảng giá
    """
    params = {}
    
    if product_type:
        params["category"] = product_type
    
    if min_price is not None:
        params["minPrice"] = int(min_price)
    
    if max_price is not None:
        params["maxPrice"] = int(max_price)
    
    try:
        response = requests.get(f"{API_BASE_URL}/products", params=params, headers=HEADERS)
        
        if response.status_code == 200:
            products = response.json()
            
            results = []
            for product in products[:5]:  # Lấy tối đa 5 sản phẩm
                results.append({
                    "id": product.get("id"),
                    "title": product.get("title"),
                    "price": product.get("price"),
                    "price_formatted": format_price(product.get("price")),
                    "discounted_price": product.get("discountedPrice"),
                    "discounted_price_formatted": format_price(product.get("discountedPrice")),
                    "brand": product.get("brand")
                })
            
            return results
        else:
            print(f"Error filtering products by price: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Exception in filter_products_by_price: {str(e)}")
        return []