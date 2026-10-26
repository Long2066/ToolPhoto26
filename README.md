# ToolPhoto26 - AI Image Studio

Ứng dụng tạo ảnh AI chuyên nghiệp kết nối cổng **9router Gateway** và mô hình **Gemini 3.1 Flash Image**.

## 🚀 Tính năng nổi bật
- **Động cơ 9router Gateway**: Hỗ trợ kết nối API trực tiếp hoặc qua VPS/Máy chủ từ xa (`/v1/images/generations`).
- **Model tối ưu**: Tích hợp sẵn `ag/gemini-3.1-flash-image` (Gemini 3.1 Flash Image) cho tốc độ sinh ảnh cực nhanh và chi tiết cao.
- **Tùy chỉnh đa tỷ lệ (Aspect Ratio)**: Hỗ trợ đầy đủ các tỷ lệ chuẩn điện ảnh và mạng xã hội:
  - `1:1` (Vuông)
  - `16:9` (Ngang PC / YouTube)
  - `9:16` (Dọc TikTok / Story)
  - `4:3` (Chuẩn nhiếp ảnh)
  - `3:4` (Chân dung nghệ thuật)
  - `21:9` (Điện ảnh góc siêu rộng)
- **Độ phân giải linh hoạt**: Standard (768px), HD (1024px), 2K (1536px), 4K (2048px).
- **Bộ lọc phong cách & Tối ưu tiếng Việt**: Tự động dịch và làm giàu câu lệnh mang đậm bối cảnh văn hóa Việt Nam.
- **Chế độ ImageTool Pro (Flow R2I)**: Hỗ trợ nạp ảnh tham chiếu (Khuôn mặt, Trang phục, Bối cảnh) và khóa nhận diện nhân vật.

## 🛠 Hướng dẫn cài đặt & Khởi chạy

### Cách 1: Chạy bằng file Batch (Nhanh nhất)
Nhấp đúp chuột vào file:
```bat
start.bat
```

### Cách 2: Chạy thủ công bằng Python
1. Cài đặt các thư viện cần thiết:
   ```bash
   pip install pillow
   ```
2. Khởi chạy máy chủ nội bộ:
   ```bash
   python server.py
   ```
3. Mở trình duyệt truy cập:
   ```text
   http://localhost:7860
   ```

## ⚙️ Cấu hình 9router
1. Điền địa chỉ Endpoint (mặc định: `http://localhost:20128/v1/images/generations` hoặc địa chỉ VPS).
2. Điền mã API Key của bạn.
3. Chọn tỷ lệ, nhập mô tả (prompt) và bấm **Tạo ảnh ngay**.
