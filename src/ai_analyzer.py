"""
VN Stock Sniper - AI Analyzer
Gọi Claude API để phân tích và đưa ra khuyến nghị
"""

import pandas as pd
import json
from datetime import datetime
import os

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ anthropic chưa được cài đặt")

from src.config import CLAUDE_API_KEY, ANALYZED_DATA_FILE, SIGNALS_FILE, PORTFOLIO_FILE


class AIAnalyzer:
    """Phân tích bằng Claude AI"""
    
    def __init__(self):
        if ANTHROPIC_AVAILABLE and CLAUDE_API_KEY:
            self.client = Anthropic(api_key=CLAUDE_API_KEY)
        else:
            self.client = None
            print("⚠️ Claude API chưa được cấu hình")
    
    def load_portfolio(self) -> dict:
        """Đọc portfolio từ file"""
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"positions": [], "cash_percent": 100}
    
    def prepare_data_summary(self, df: pd.DataFrame, signals_df: pd.DataFrame, portfolio: dict) -> str:
        """Chuẩn bị dữ liệu tóm tắt cho AI"""
        
        today = datetime.now().strftime("%d/%m/%Y")
        
        # Thống kê chung
        total_stocks = len(df)
        uptrend_count = len(df[df['channel'] == "🟢 XANH"])
        sideways_count = len(df[df['channel'] == "⚪ XÁM"])
        downtrend_count = len(df[df['channel'] == "🔴 ĐỎ"])
        
        star_5_count = len(df[df['stars'] >= 5])
        star_4_count = len(df[df['stars'] == 4])
        
        # Top 20 cổ phiếu
        top_20 = df.head(20)[['symbol', 'close', 'quality_score', 'momentum_score', 
                              'stars', 'buy_signal', 'channel', 'rsi', 'mfi', 'vol_ratio']].to_dict('records')
        
        # Tín hiệu mua
        buy_signals = signals_df[['symbol', 'close', 'quality_score', 'momentum_score',
                                   'stars', 'buy_signal', 'channel', 'rsi', 'mfi', 
                                   'vol_ratio', 'macd_bullish', 'ma_aligned']].to_dict('records') if not signals_df.empty else []
        
        # Portfolio
        positions = portfolio.get('positions', [])
        cash_percent = portfolio.get('cash_percent', 100)
        
        # Tính lãi/lỗ portfolio
        for pos in positions:
            symbol = pos.get('symbol', '')
            entry_price = pos.get('entry_price', 0)
            
            # Tìm giá hiện tại
            stock_data = df[df['symbol'] == symbol]
            if not stock_data.empty:
                current_price = stock_data.iloc[0]['close']
                pos['current_price'] = current_price
                pos['pnl_percent'] = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            else:
                pos['current_price'] = entry_price
                pos['pnl_percent'] = 0
        
        summary = f"""
=== DỮ LIỆU THỊ TRƯỜNG VIỆT NAM - {today} ===

📊 TỔNG QUAN:
- Tổng số mã phân tích: {total_stocks}
- Kênh XANH (Uptrend): {uptrend_count} mã ({uptrend_count/total_stocks*100:.1f}%)
- Kênh XÁM (Sideway): {sideways_count} mã ({sideways_count/total_stocks*100:.1f}%)
- Kênh ĐỎ (Downtrend): {downtrend_count} mã ({downtrend_count/total_stocks*100:.1f}%)
- Cổ phiếu 5 sao: {star_5_count}
- Cổ phiếu 4 sao: {star_4_count}

📈 TOP 20 CỔ PHIẾU (theo điểm):
{json.dumps(top_20, indent=2, ensure_ascii=False)}

🚀 TÍN HIỆU MUA ({len(buy_signals)} mã):
{json.dumps(buy_signals, indent=2, ensure_ascii=False)}

💼 PORTFOLIO HIỆN TẠI:
- Tiền mặt: {cash_percent}%
- Các vị thế:
{json.dumps(positions, indent=2, ensure_ascii=False)}
"""
        return summary
    
    def analyze_with_ai(self, data_summary: str) -> str:
        """Gọi Claude API để phân tích"""
        
        if not self.client:
            return "❌ Claude API chưa được cấu hình. Vui lòng thêm CLAUDE_API_KEY."
        
        prompt = f"""Bạn là chuyên gia phân tích chứng khoán Việt Nam. Dựa trên dữ liệu sau, hãy đưa ra báo cáo phân tích chi tiết:

{data_summary}

=== YÊU CẦU BÁO CÁO ===

Hãy viết báo cáo theo format sau (dùng emoji, ngắn gọn, dễ đọc trên Telegram):

1. 🌍 NHẬN ĐỊNH THỊ TRƯỜNG (3-4 câu):
   - Đánh giá xu hướng chung dựa trên tỷ lệ kênh xanh/xám/đỏ
   - Nhận định dòng tiền
   - Chiến lược chung hôm nay

2. 🏆 TOP 5 CỔ PHIẾU (cho mỗi mã):
   - Tên mã, giá, số sao
   - Điểm mạnh/yếu ngắn gọn

3. 🚀 TÍN HIỆU MUA (nếu có, chi tiết cho từng mã):
   - Loại tín hiệu (BREAKOUT/MOMENTUM/PULLBACK/REVERSAL)
   - Lý do nên mua (2-3 ý)
   - Vùng mua đề xuất
   - Stop Loss (% cụ thể)
   - Target 1, Target 2 (% cụ thể)
   - Size đề xuất (% NAV)
   - Rủi ro cần lưu ý

4. 💼 PHÂN TÍCH PORTFOLIO (nếu có vị thế):
   - Đánh giá từng vị thế đang giữ
   - Nên giữ/chốt lời/cắt lỗ?
   - Lý do cụ thể

5. ⚠️ CẢNH BÁO (nếu có):
   - Mã nào đang quá mua (RSI > 70)?
   - Mã nào đang có rủi ro?

6. 📅 HÀNH ĐỘNG HÔM NAY (tóm tắt 2-3 gạch đầu dòng):
   - Nên làm gì cụ thể?

Lưu ý:
- Viết ngắn gọn, dễ đọc trên điện thoại
- Dùng emoji phù hợp
- Đưa ra con số cụ thể (giá, %, SL, TP)
- Nếu không có tín hiệu tốt, nói rõ "Hôm nay không có tín hiệu đủ mạnh, nên chờ"
"""
        
        try:
            print("🤖 Đang gọi Claude AI phân tích...")
            
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result = response.content[0].text
            print("✅ AI phân tích xong")
            
            return result
            
        except Exception as e:
            print(f"❌ Lỗi gọi Claude API: {e}")
            return f"❌ Lỗi gọi Claude API: {str(e)}"
    
    def run(self, analyzed_df: pd.DataFrame = None, signals_df: pd.DataFrame = None) -> str:
        """Chạy phân tích AI"""
        print("="*60)
        print("🤖 BẮT ĐẦU PHÂN TÍCH AI")
        print("="*60)
        
        # Đọc dữ liệu nếu chưa có
        if analyzed_df is None:
            if os.path.exists(ANALYZED_DATA_FILE):
                analyzed_df = pd.read_csv(ANALYZED_DATA_FILE)
            else:
                return "❌ Không có dữ liệu phân tích"
        
        if signals_df is None:
            if os.path.exists(SIGNALS_FILE):
                signals_df = pd.read_csv(SIGNALS_FILE)
            else:
                signals_df = pd.DataFrame()
        
        # Đọc portfolio
        portfolio = self.load_portfolio()
        
        # Chuẩn bị dữ liệu
        data_summary = self.prepare_data_summary(analyzed_df, signals_df, portfolio)
        
        # Gọi AI
        report = self.analyze_with_ai(data_summary)
        
        return report


# Test
if __name__ == "__main__":
    ai = AIAnalyzer()
    report = ai.run()
    print("\n" + "="*60)
    print(report)
