# VN Stock Sniper

Hệ thống phân tích cổ phiếu Việt Nam tự động với AI + Dashboard.

## Tính năng

- Tự động lấy dữ liệu từ **FiinQuant** (fallback vnstock)
- Phân tích 40+ chỉ báo kỹ thuật (MA, RSI, MACD, Bollinger Bands, Stochastic, MFI, ATR...)
- AI (Claude Sonnet 4.5) phân tích và đưa ra khuyến nghị
- Dashboard tương tác trên GitHub Pages
- Chạy tự động hàng ngày trên GitHub Actions (miễn phí)

---

## Dashboard

Sau khi setup, Dashboard sẽ có tại:

```
https://YOUR_USERNAME.github.io/vn-stock-sniper_V2
```

### Gồm có:

| Tab | Mô tả |
|-----|-------|
| Tín hiệu MUA | Cards với Entry/SL/TP, lọc theo Breakout/Momentum/Pullback/Reversal |
| Heatmap | Bản đồ nhiệt theo Điểm/RSI/Volume |
| Bảng xếp hạng | 70 mã, sort/filter/pagination, RSI bar inline |
| Watchlist | Lưu localStorage, không mất khi reload |
| Portfolio | Vị thế + P&L |
| AI Report | Báo cáo phân tích đầy đủ |

Click vào bất kỳ mã nào để xem chi tiết 40+ chỉ báo.

---

## Hướng dẫn cài đặt

### Bước 1: Lấy Claude API Key

1. Vào [console.anthropic.com](https://console.anthropic.com)
2. Tạo API Key
3. Nạp credit (~$5-10/tháng)

### Bước 2: Đăng ký FiinQuant (tùy chọn)

1. Vào [fiinquant.vn](https://fiinquant.vn) đăng ký tài khoản
2. Lấy username/password
3. Nếu không có FiinQuant, hệ thống sẽ tự động dùng vnstock

### Bước 3: Fork Repository

1. Click **Fork** góc trên phải
2. Đợi tạo xong

### Bước 4: Thêm Secrets

Vào repo > **Settings** > **Secrets and variables** > **Actions**, thêm:

| Name | Value | Bắt buộc |
|------|-------|----------|
| `CLAUDE_API_KEY` | `sk-ant-api...` | Yes |
| `FIINQUANT_USERNAME` | Email FiinQuant | No |
| `FIINQUANT_PASSWORD` | Password FiinQuant | No |

### Bước 5: Bật GitHub Pages

1. Vào **Settings** > **Pages**
2. Source: **GitHub Actions**
3. Save

### Bước 6: Chạy Workflow

1. Vào tab **Actions**
2. Click **VN Stock Sniper Daily**
3. Click **Run workflow** > **Run workflow**
4. Đợi 10-15 phút

---

## Chạy local

```bash
# Cài dependencies
pip install -r requirements.txt

# Cài FiinQuantX (tùy chọn)
pip install --extra-index-url https://fiinquant.github.io/fiinquantx/simple fiinquantx

# Tạo .env
cp .env.example .env
# Sửa .env với API keys của bạn

# Chạy
python main.py
```

---

## Pipeline

```
Lấy dữ liệu (FiinQuant/vnstock)
    ↓
Phân tích kỹ thuật (40+ chỉ báo)
    ↓
Phân tích AI (Claude Sonnet 4.5)
    ↓
Lưu lịch sử
    ↓
Tạo Dashboard (GitHub Pages)
```

---

## Chi phí

| Mục | Chi phí |
|-----|---------|
| GitHub Actions | Miễn phí |
| GitHub Pages | Miễn phí |
| Claude API | ~$5-10/tháng |
| FiinQuant | Theo gói |
| **Tổng** | **~$5-10/tháng** |

---

## Cấu trúc

```
vn-stock-sniper_V2/
├── .github/workflows/daily.yml   # Tự động chạy hàng ngày
├── src/
│   ├── config.py                 # Cấu hình
│   ├── data_fetcher.py           # Lấy dữ liệu (FiinQuant + vnstock)
│   ├── analyzer.py               # Phân tích kỹ thuật
│   ├── ai_analyzer.py            # AI phân tích (Claude)
│   └── dashboard_generator.py    # Tạo Dashboard HTML
├── data/
│   └── portfolio.json            # Portfolio
├── docs/
│   └── index.html                # Dashboard (auto-generated)
├── main.py                       # Pipeline chính
└── requirements.txt
```
