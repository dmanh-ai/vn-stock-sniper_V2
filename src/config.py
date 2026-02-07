"""
VN Stock Sniper - Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# === API KEYS ===
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "").strip().replace("\n", "").replace("\r", "").replace(" ", "")

# FiinQuant (legacy - kept for reference)
FIINQUANT_USERNAME = os.getenv("FIINQUANT_USERNAME", "").strip()
FIINQUANT_PASSWORD = os.getenv("FIINQUANT_PASSWORD", "").strip()

# === DATA SETTINGS ===
TOP_STOCKS_COUNT = 300  # Top 300 mã theo volume (HOSE + HNX)
DATA_START_DATE = "2024-01-01"  # Ngày bắt đầu lấy dữ liệu
DATA_SOURCE = "ENTRADE"  # Nguồn dữ liệu: Entrade (DNSE) REST API

# === INDEX SYMBOLS ===
INDEX_SYMBOLS = ['VNINDEX', 'HNX-INDEX', 'VN30', 'UPCOM']

# === ANALYSIS SETTINGS ===
# Moving Averages
MA_PERIODS = [5, 10, 20, 50, 200]

# RSI
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2

# Linear Regression Channel
LR_PERIOD = 50
LR_STD = 2

# Stochastic
STOCH_K = 14
STOCH_D = 3

# ATR
ATR_PERIOD = 14

# MFI
MFI_PERIOD = 14

# Volume
VOL_MA_PERIOD = 20
VOL_SURGE_THRESHOLD = 1.5  # 150%

# === SCORING SETTINGS ===
# Quality Score thresholds
Q_RATING_5 = 16  # >= 16 = Q5
Q_RATING_4 = 12  # >= 12 = Q4
Q_RATING_3 = 8   # >= 8 = Q3
Q_RATING_2 = 5   # >= 5 = Q2

# Momentum Score thresholds
M_RATING_5 = 10  # >= 10 = M5
M_RATING_4 = 7   # >= 7 = M4
M_RATING_3 = 4   # >= 4 = M3
M_RATING_2 = 2   # >= 2 = M2

# === CHANNEL SETTINGS ===
CHANNEL_UPTREND_THRESHOLD = 0.03    # Slope > 0.03% = Uptrend
CHANNEL_DOWNTREND_THRESHOLD = -0.03  # Slope < -0.03% = Downtrend

# === SIGNAL SETTINGS ===
# Minimum stars to send alert
MIN_STARS_ALERT = 4

# === FILE PATHS ===
DATA_DIR = "data"
RAW_DATA_FILE = f"{DATA_DIR}/raw_data.csv"
ANALYZED_DATA_FILE = f"{DATA_DIR}/analyzed_data.csv"
SIGNALS_FILE = f"{DATA_DIR}/signals.csv"
PORTFOLIO_FILE = f"{DATA_DIR}/portfolio.json"
HISTORY_DIR = f"{DATA_DIR}/history"

# === TIMEZONE ===
TIMEZONE = "Asia/Ho_Chi_Minh"
