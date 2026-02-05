"""
VN Stock Sniper - Main (với Dashboard)
Chạy toàn bộ quy trình: Lấy data → Phân tích → AI → Gửi Telegram → Tạo Dashboard
"""

import os
import sys
from datetime import datetime
import pytz

# Thêm path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_fetcher import DataFetcher
from src.analyzer import TechnicalAnalyzer
from src.ai_analyzer import AIAnalyzer
from src.telegram_bot import TelegramBot
from src.dashboard_generator import DashboardGenerator
from src.config import TIMEZONE, HISTORY_DIR, DATA_DIR


def save_history(report: str, analyzed_df):
    """Lưu lịch sử báo cáo"""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    today = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d")
    
    # Lưu báo cáo
    report_file = f"{HISTORY_DIR}/{today}_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Lưu data
    if analyzed_df is not None and not analyzed_df.empty:
        data_file = f"{HISTORY_DIR}/{today}_data.csv"
        analyzed_df.to_csv(data_file, index=False)
    
    print(f"✅ Đã lưu lịch sử: {today}")


def run():
    """Chạy toàn bộ quy trình"""
    
    start_time = datetime.now()
    
    print("="*60)
    print("🚀 VN STOCK SNIPER - BẮT ĐẦU")
    print(f"⏰ {start_time.strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)
    
    try:
        # Tạo thư mục
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs('docs', exist_ok=True)
        
        # === BƯỚC 1: LẤY DỮ LIỆU ===
        print("\n" + "="*60)
        print("📥 BƯỚC 1: LẤY DỮ LIỆU")
        print("="*60)
        
        fetcher = DataFetcher()
        raw_df = fetcher.run()
        
        if raw_df.empty:
            error_msg = "❌ Không lấy được dữ liệu!"
            print(error_msg)
            
            # Gửi thông báo lỗi
            bot = TelegramBot()
            bot.send_message_sync(f"⚠️ VN Stock Sniper\n\n{error_msg}")
            return
        
        # === BƯỚC 2: PHÂN TÍCH KỸ THUẬT ===
        print("\n" + "="*60)
        print("📊 BƯỚC 2: PHÂN TÍCH KỸ THUẬT")
        print("="*60)
        
        analyzer = TechnicalAnalyzer()
        analyzed_df = analyzer.run(raw_df)
        signals_df = analyzer.get_signals(analyzed_df)
        
        # === BƯỚC 3: PHÂN TÍCH AI ===
        print("\n" + "="*60)
        print("🤖 BƯỚC 3: PHÂN TÍCH AI")
        print("="*60)
        
        ai = AIAnalyzer()
        report = ai.run(analyzed_df, signals_df)
        
        # === BƯỚC 4: GỬI TELEGRAM ===
        print("\n" + "="*60)
        print("📱 BƯỚC 4: GỬI TELEGRAM")
        print("="*60)
        
        bot = TelegramBot()
        bot.send_report(report)
        
        # === BƯỚC 5: LƯU LỊCH SỬ ===
        print("\n" + "="*60)
        print("💾 BƯỚC 5: LƯU LỊCH SỬ")
        print("="*60)
        
        save_history(report, analyzed_df)
        
        # === BƯỚC 6: TẠO DASHBOARD ===
        print("\n" + "="*60)
        print("🌐 BƯỚC 6: TẠO DASHBOARD")
        print("="*60)
        
        dashboard = DashboardGenerator()
        dashboard.run()
        
        # === HOÀN THÀNH ===
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("✅ HOÀN THÀNH!")
        print(f"⏱️ Thời gian: {duration:.1f} giây")
        print("="*60)
        
    except Exception as e:
        error_msg = f"❌ Lỗi: {str(e)}"
        print(error_msg)
        
        import traceback
        traceback.print_exc()
        
        # Gửi thông báo lỗi
        try:
            bot = TelegramBot()
            bot.send_message_sync(f"⚠️ VN Stock Sniper - LỖI\n\n{error_msg}")
        except:
            pass
        
        raise e


if __name__ == "__main__":
    run()
