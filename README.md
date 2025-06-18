# Chatbot cho Tech Shop 

Đây là dự án chatbot được xây dựng trên nền tảng **Rasa Open Source**, đóng vai trò là một nhân viên tư vấn cho website thương mại điện tử Tech Shop. Chatbot được thiết kế để hiểu ngôn ngữ tự nhiên (tiếng Việt) và giúp người dùng tìm kiếm sản phẩm, tra cứu thông tin và kiểm tra đơn hàng một cách nhanh chóng.

## 🤖 Các tính năng chính

* **Tư vấn và tìm kiếm sản phẩm:**
* **Tra cứu thông tin chi tiết sản phẩm:**

## ⚙️ Hướng dẫn cài đặt và cấu hình


### Bước 1: Cài đặt Chatbot (Rasa)

1.  **Clone Repository Chatbot:** Tải mã nguồn của dự án chatbot này về máy.
2.  **Tạo và Kích hoạt Môi trường ảo (Optional):**
    * Mở terminal trong thư mục gốc của dự án chatbot.
    * Chạy lệnh để tạo môi trường ảo tên là `myenv`:
        ```bash
        python3 -m venv myenv
        ```
    * Kích hoạt môi trường ảo:
        * Trên macOS/Linux: `source myenv/bin/activate`
        * Trên Windows: `myenv\Scripts\activate`
3.  **Cài đặt các thư viện cần thiết:**
    * Sau khi kích hoạt môi trường ảo, chạy lệnh sau để cài đặt tất cả các thư viện trong `requirements.txt`:
        ```bash
        pip install -r requirements.txt
        ```

### Bước 2: Huấn luyện Chatbot

Sau khi cài đặt xong và mỗi khi bạn có thay đổi trong các tệp `.yml` (trong thư mục `data/`), bạn cần huấn luyện lại chatbot.

* Chạy lệnh sau trong terminal (đã kích hoạt môi trường ảo):
    ```bash
    rasa train
    ```
    *(Lưu ý: Lệnh này hoạt động khi `domain.yml` nằm ở thư mục gốc. Nếu bạn đặt nó trong `data/`, hãy dùng lệnh `rasa train --domain data/domain.yml --data data`)*

## 🚀 Hướng dẫn khởi chạy chatbot
### **Terminal 1: Khởi động Action Server**

* Mở terminal mới, điều hướng đến thư mục dự án **Chatbot**.
* Kích hoạt môi trường ảo: `source myenv/bin/activate`
* Chạy lệnh:
    ```bash
    rasa run actions
    ```
* Đảm bảo máy chủ khởi động thành công trên cổng `5055`.

### **Terminal 2: Khởi động Rasa Server**

* Mở terminal mới, điều hướng đến thư mục dự án **Chatbot**.
* Kích hoạt môi trường ảo: `source myenv/bin/activate`
* Chạy lệnh để mở API cho frontend kết nối:
    ```bash
    rasa run --enable-api --cors "*"
    ```

