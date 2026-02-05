# 🚀 VN Stock Sniper

Hệ thống phân tích chứng khoán Việt Nam tự động với AI + Dashboard.

## ✨ Tính năng

- 📥 Tự động lấy dữ liệu Top mã thanh khoản cao
- 📊 Phân tích 40+ chỉ báo kỹ thuật (giống Pine Script)
- 🤖 AI (Claude) phân tích và đưa ra khuyến nghị
- 📱 Gửi báo cáo qua Telegram mỗi sáng
- 🌐 **Dashboard đầy đủ trên GitHub Pages**
- 💼 Quản lý portfolio qua Telegram
- ☁️ Chạy tự động trên GitHub Actions (miễn phí)

---

## 🌐 DASHBOARD

Sau khi setup, Dashboard sẽ có tại:

```
https://YOUR_USERNAME.github.io/vn-stock-sniper
```

### Dashboard bao gồm:

| Tính năng | Mô tả |
|-----------|-------|
| 📊 Tổng quan | % Kênh Xanh/Xám/Đỏ, Số tín hiệu, Biểu đồ |
| 🏆 Bảng xếp hạng | Top 50 mã, Lọc/Sắp xếp |
| 🚀 Tín hiệu MUA | Entry/SL/TP chi tiết |
| 💼 Portfolio | Vị thế + P&L |
| 🤖 AI Report | Báo cáo phân tích đầy đủ |
| 📈 Chi tiết mã | 40+ chỉ báo (click vào mã) |

---

## 📋 HƯỚNG DẪN CÀI ĐẶT

### Bước 1: Tạo Telegram Bot (3 phút)

1. Mở Telegram, tìm **@BotFather**
2. Gửi: `/newbot`
3. Đặt tên và username cho bot
4. **Copy Token** (dạng: `1234567890:ABCxyz...`)

### Bước 2: Lấy Chat ID (2 phút)

1. Tìm **@userinfobot** trên Telegram
2. Gửi `/start`
3. **Copy số Id** (dạng: `507390226`)

### Bước 3: Lấy Claude API Key (3 phút)

1. Vào [console.anthropic.com](https://console.anthropic.com)
2. Tạo API Key
3. Nạp credit (~$10-20)

### Bước 4: Fork Repository

1. Click **Fork** góc trên phải
2. Đợi tạo xong

### Bước 5: Thêm Secrets

1. Vào repo → **Settings** → **Secrets and variables** → **Actions**
2. Thêm 3 secrets:

| Name | Value |
|------|-------|
| `CLAUDE_API_KEY` | sk-ant-api... |
| `TELEGRAM_TOKEN` | 1234567890:ABC... |
| `TELEGRAM_CHAT_ID` | 507390226 |

### Bước 6: Bật GitHub Pages

1. Vào **Settings** → **Pages**
2. Source: **GitHub Actions**
3. Save

### Bước 7: Chạy Workflow

1. Vào tab **Actions**
2. Click **VN Stock Sniper Daily**
3. Click **Run workflow** → **Run workflow**
4. Đợi 10-15 phút

---

## 🎉 HOÀN THÀNH!

- ✅ Mỗi sáng 7:00 AM sẽ tự động chạy
- ✅ Telegram nhận báo cáo
- ✅ Dashboard tự động cập nhật

---

## 📱 QUẢN LÝ PORTFOLIO QUA TELEGRAM

```
/portfolio     - Xem danh mục
/buy VCI 1000 37000   - Mua
/sell MWG 500  - Bán
/cash 30       - Cập nhật % tiền mặt
/clear         - Xóa tất cả
```

---

## 💰 CHI PHÍ

| Mục | Chi phí |
|-----|---------|
| GitHub Actions | ✅ Miễn phí |
| GitHub Pages | ✅ Miễn phí |
| Telegram Bot | ✅ Miễn phí |
| Claude API | ~$15-20/tháng |
| **Tổng** | **~$15-20/tháng** |

---

## 📁 Cấu trúc

```
vn-stock-sniper/
├── .github/workflows/daily.yml   # Tự động chạy
├── src/
│   ├── config.py                 # Cấu hình
│   ├── data_fetcher.py           # Lấy dữ liệu
│   ├── analyzer.py               # Phân tích kỹ thuật
│   ├── ai_analyzer.py            # AI phân tích
│   ├── telegram_bot.py           # Telegram Bot
│   └── dashboard_generator.py    # Tạo Dashboard
├── data/
│   └── portfolio.json            # Portfolio
├── docs/
│   └── index.html                # Dashboard (auto-generated)
├── main.py
└── requirements.txt
```

---

Made with ❤️ for Vietnamese Stock Traders
