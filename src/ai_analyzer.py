"""
VN Stock Sniper - AI Analyzer V2
Phân tích đa góc nhìn bằng Claude AI cho Dashboard
"""

import pandas as pd
import numpy as np
import json
import math
from datetime import datetime
import os

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️ anthropic chưa được cài đặt")

from src.config import CLAUDE_API_KEY, ANALYZED_DATA_FILE, SIGNALS_FILE, PORTFOLIO_FILE


def _safe(val, default=0):
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    return val


class AIAnalyzer:
    """Phân tích đa góc nhìn bằng Claude AI"""

    SYSTEM_PROMPT = """Bạn là một chuyên gia phân tích chứng khoán Việt Nam cấp cao với hơn 15 năm kinh nghiệm. Bạn kết hợp phân tích kỹ thuật (Technical Analysis), phân tích dòng tiền (Money Flow), và quản trị rủi ro (Risk Management) để đưa ra đánh giá toàn diện.

Nguyên tắc phân tích của bạn:
- Luôn nhìn BỨC TRANH TỔNG THỂ trước khi đi vào chi tiết từng mã
- Đánh giá SỨC KHỎE THỊ TRƯỜNG qua market breadth (tỷ lệ uptrend/downtrend) và dòng tiền
- Phân biệt rõ giữa TÍN HIỆU MẠNH và TÍN HIỆU YẾU - không phải mọi tín hiệu đều đáng giao dịch
- Luôn đưa ra CẢ HAI MẶT (thuận lợi & rủi ro) cho mỗi nhận định
- Quản trị rủi ro là ưu tiên số 1: luôn có Stop Loss, position sizing hợp lý
- Thẳng thắn: nếu thị trường xấu, nói rõ "không nên mua", đừng cố tìm cơ hội khi không có
- Viết bằng tiếng Việt, rõ ràng, có cấu trúc, dễ đọc trên web dashboard"""

    def __init__(self):
        if ANTHROPIC_AVAILABLE and CLAUDE_API_KEY:
            self.client = Anthropic(api_key=CLAUDE_API_KEY)
        else:
            self.client = None
            print("⚠️ Claude API chưa được cấu hình")

    def load_portfolio(self) -> dict:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"positions": [], "cash_percent": 100}

    def prepare_data_summary(self, df: pd.DataFrame, signals_df: pd.DataFrame, portfolio: dict) -> str:
        """Chuẩn bị dữ liệu chi tiết cho AI"""

        today = datetime.now().strftime("%d/%m/%Y")
        total = len(df)
        if total == 0:
            return "Không có dữ liệu."

        # === MARKET BREADTH ===
        uptrend = len(df[df['channel'].str.contains('XANH', na=False)])
        sideways = len(df[df['channel'].str.contains('XÁM', na=False)])
        downtrend = len(df[df['channel'].str.contains('ĐỎ', na=False)])

        avg_rsi = round(_safe(df['rsi'].mean(), 50), 1)
        avg_mfi = round(_safe(df['mfi'].mean(), 50), 1)

        rsi_ob = len(df[df['rsi'] > 70])
        rsi_os = len(df[df['rsi'] < 30])
        macd_bull = int(df['macd_bullish'].sum()) if 'macd_bullish' in df.columns else 0
        macd_bear = total - macd_bull
        vol_surge = int(df['vol_surge'].sum()) if 'vol_surge' in df.columns else 0
        bb_squeeze = int(df['bb_squeeze'].sum()) if 'bb_squeeze' in df.columns else 0
        ma_aligned = int(df['ma_aligned'].sum()) if 'ma_aligned' in df.columns else 0
        above_ma200 = int(df['above_ma200'].sum()) if 'above_ma200' in df.columns else 0

        star_5 = len(df[df['stars'] >= 5])
        star_4 = len(df[df['stars'] == 4])
        star_3 = len(df[df['stars'] == 3])

        # === TOP 15 STOCKS ===
        cols_top = ['symbol', 'close', 'quality_score', 'momentum_score', 'total_score',
                    'stars', 'buy_signal', 'sell_signal', 'channel',
                    'rsi', 'mfi', 'vol_ratio', 'macd_bullish', 'macd_accelerating',
                    'ma_aligned', 'above_ma200', 'above_ma50',
                    'bb_percent', 'bb_squeeze', 'bb_width',
                    'stoch_k', 'stoch_d',
                    'breakout_20', 'breakout_50',
                    'support', 'resistance',
                    'lr_slope_pct', 'channel_position', 'atr_percent']
        available_cols = [c for c in cols_top if c in df.columns]
        top_15 = df.head(10)[available_cols].to_dict('records')

        # === SIGNALS DETAIL ===
        sig_cols = ['symbol', 'close', 'quality_score', 'momentum_score', 'total_score',
                    'stars', 'buy_signal', 'channel',
                    'rsi', 'mfi', 'vol_ratio', 'vol_surge',
                    'macd_bullish', 'macd_accelerating', 'ma_aligned',
                    'bb_percent', 'bb_squeeze', 'stoch_k', 'stoch_d',
                    'support', 'resistance', 'atr_percent',
                    'breakout_20', 'breakout_50',
                    'lr_slope_pct', 'channel_position',
                    'above_ma200', 'above_ma50', 'above_ma20']
        available_sig = [c for c in sig_cols if c in signals_df.columns] if not signals_df.empty else []
        buy_signals = signals_df[available_sig].head(15).to_dict('records') if available_sig else []

        # === SELL SIGNALS ===
        sell_df = df[df['sell_signal'].notna() & (df['sell_signal'] != '')]
        sell_cols = ['symbol', 'close', 'sell_signal', 'channel', 'rsi', 'mfi',
                     'macd_bullish', 'vol_ratio', 'stars']
        available_sell = [c for c in sell_cols if c in sell_df.columns]
        sell_signals = sell_df[available_sell].head(10).to_dict('records') if not sell_df.empty else []

        # === WORST STOCKS (downtrend, low score) ===
        worst = df.tail(10)[['symbol', 'close', 'total_score', 'stars', 'channel',
                              'rsi', 'sell_signal']].to_dict('records') if len(df) >= 10 else []

        # === PORTFOLIO ===
        positions = portfolio.get('positions', [])
        cash_pct = portfolio.get('cash_percent', 100)
        for pos in positions:
            sym = pos.get('symbol', '')
            entry = pos.get('entry_price', 0)
            stock_row = df[df['symbol'] == sym]
            if not stock_row.empty:
                cur = stock_row.iloc[0]['close']
                pos['current_price'] = cur
                pos['pnl_percent'] = round((cur - entry) / entry * 100, 2) if entry > 0 else 0
                pos['rsi'] = round(_safe(stock_row.iloc[0].get('rsi', 0)), 1)
                pos['channel'] = stock_row.iloc[0].get('channel', '')
                pos['macd_bullish'] = bool(stock_row.iloc[0].get('macd_bullish', False))
                pos['sell_signal'] = stock_row.iloc[0].get('sell_signal', '')

        # === CLEAN NaN ===
        def clean(records):
            out = []
            for r in records:
                item = {}
                for k, v in r.items():
                    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                        item[k] = None
                    elif isinstance(v, (np.integer,)):
                        item[k] = int(v)
                    elif isinstance(v, (np.floating,)):
                        item[k] = round(float(v), 2)
                    elif isinstance(v, (np.bool_,)):
                        item[k] = bool(v)
                    else:
                        item[k] = v
                out.append(item)
            return out

        top_15 = clean(top_15)
        buy_signals = clean(buy_signals)
        sell_signals = clean(sell_signals)
        worst = clean(worst)

        summary = f"""
=== DỮ LIỆU THỊ TRƯỜNG CHỨNG KHOÁN VIỆT NAM - {today} ===

1. MARKET BREADTH (Sức khỏe thị trường):
- Tổng mã phân tích: {total}
- Kênh XANH (Uptrend): {uptrend} ({uptrend/total*100:.0f}%)
- Kênh XÁM (Sideway): {sideways} ({sideways/total*100:.0f}%)
- Kênh ĐỎ (Downtrend): {downtrend} ({downtrend/total*100:.0f}%)
- MA Alignment (MA5>MA10>MA20>MA50): {ma_aligned}/{total} mã
- Trên MA200: {above_ma200}/{total} mã

2. CHỈ BÁO TRUNG BÌNH THỊ TRƯỜNG:
- RSI trung bình: {avg_rsi} (>50 = bullish, <50 = bearish)
- MFI trung bình: {avg_mfi} (>50 = dòng tiền vào, <50 = dòng tiền ra)
- Quá mua (RSI>70): {rsi_ob} mã | Quá bán (RSI<30): {rsi_os} mã
- MACD Bullish: {macd_bull} | MACD Bearish: {macd_bear}
- Volume Surge (>1.5x): {vol_surge} mã
- BB Squeeze (biến động thấp, sắp bùng nổ): {bb_squeeze} mã

3. PHÂN BỐ CHẤT LƯỢNG:
- 5 sao: {star_5} mã | 4 sao: {star_4} mã | 3 sao: {star_3} mã

4. TOP 10 CỔ PHIẾU (xếp theo tổng điểm Quality + Momentum):
{json.dumps(top_15, indent=2, ensure_ascii=False)}

5. TÍN HIỆU MUA ({len(buy_signals)} mã):
{json.dumps(buy_signals, indent=2, ensure_ascii=False) if buy_signals else "Không có tín hiệu mua hôm nay."}

6. TÍN HIỆU BÁN ({len(sell_signals)} mã):
{json.dumps(sell_signals, indent=2, ensure_ascii=False) if sell_signals else "Không có tín hiệu bán."}

7. CỔ PHIẾU YẾU NHẤT (bottom 10):
{json.dumps(worst, indent=2, ensure_ascii=False)}

8. PORTFOLIO HIỆN TẠI:
- Tiền mặt: {cash_pct}%
- Vị thế: {json.dumps(positions, indent=2, ensure_ascii=False) if positions else "Chưa có vị thế nào."}
"""
        return summary

    def build_analysis_prompt(self, data_summary: str) -> str:
        return f"""Dựa trên dữ liệu thị trường chứng khoán Việt Nam dưới đây, hãy viết báo cáo phân tích chuyên sâu.

{data_summary}

=== YÊU CẦU BÁO CÁO ===

Viết báo cáo theo đúng cấu trúc sau. Mỗi phần phải có nội dung thực chất, phân tích sâu, không viết chung chung.

---

## 1. TỔNG QUAN THỊ TRƯỜNG

Phân tích BỨC TRANH TỔNG THỂ dựa trên market breadth:
- **Xu hướng chủ đạo**: Dựa trên tỷ lệ Uptrend/Sideway/Downtrend, thị trường đang ở trạng thái gì? (Tăng mạnh / Tăng nhẹ / Tích lũy / Phân phối / Giảm)
- **Dòng tiền**: MFI trung bình cho thấy dòng tiền đang vào hay ra? Volume surge ở bao nhiêu mã?
- **Động lực**: MACD bullish chiếm bao nhiêu %? MA Alignment ra sao? Có bao nhiêu mã trên MA200?
- **Rủi ro hệ thống**: Bao nhiêu mã quá mua? Bao nhiêu mã BB Squeeze (sắp bùng nổ biến động)?
- **Kết luận ngắn**: 1 câu đánh giá tình trạng thị trường

## 2. PHÂN TÍCH CƠ HỘI ĐẦU TƯ

Cho MỖI tín hiệu mua (nếu có), phân tích CHI TIẾT:

**[MÃ CỔ PHIẾU] - [Loại tín hiệu: BREAKOUT/MOMENTUM/PULLBACK/REVERSAL]**
- **Điểm mạnh**: Liệt kê 3-4 yếu tố kỹ thuật hỗ trợ (dựa trên data thực)
- **Điểm yếu / Rủi ro**: Liệt kê 2-3 yếu tố cần cảnh giác
- **Độ tin cậy tín hiệu**: Cao / Trung bình / Thấp (và lý do)
- **Chiến lược vào lệnh**:
  - Entry: Giá vào lệnh đề xuất
  - Stop Loss: Giá cắt lỗ (và % từ entry)
  - Target 1: Mục tiêu ngắn hạn (và % kỳ vọng)
  - Target 2: Mục tiêu trung hạn (và % kỳ vọng)
  - Risk/Reward ratio
- **Position size đề xuất**: % NAV nên phân bổ

Nếu KHÔNG có tín hiệu mua hoặc tín hiệu quá yếu, nói rõ: "Hôm nay không có cơ hội đủ mạnh để vào lệnh mới. Nên giữ tiền mặt và chờ đợi."

## 3. CẢNH BÁO RỦI RO

- **Mã quá mua (RSI > 70)**: Liệt kê và đánh giá nguy cơ điều chỉnh
- **Mã có tín hiệu bán**: Phân tích từng mã có sell signal
- **Mã đang yếu nhất**: Những mã nào cần tránh?
- **Rủi ro vĩ mô**: Nhận định ngắn về rủi ro chung

## 4. PHÂN TÍCH PORTFOLIO

(Nếu có vị thế đang giữ)
Cho mỗi vị thế:
- Tình trạng hiện tại (P&L, xu hướng, RSI, MACD)
- Khuyến nghị: GIỮ / CHỐT LỜI / CẮT LỖ / THÊM VỊ THẾ
- Lý do cụ thể
- Mức giá hành động (SL mới, TP mới)

(Nếu không có vị thế: bỏ qua phần này)

## 5. CHIẾN LƯỢC NGÀY HÔM NAY

Tóm tắt 3-5 hành động cụ thể nhà đầu tư nên làm hôm nay:
- Nên mua gì, ở giá nào, bao nhiêu?
- Nên bán gì?
- Nên chờ đợi gì?
- Tỷ lệ tiền mặt khuyến nghị

## 6. GÓC NHÌN NGƯỢC (CONTRARIAN VIEW)

Đưa ra 2-3 câu về những gì CÓ THỂ SAI với nhận định trên:
- Nếu bạn đang bullish → rủi ro giảm là gì?
- Nếu bạn đang bearish → yếu tố nào có thể đảo chiều?
- Điều kiện nào sẽ khiến bạn thay đổi quan điểm?

---

LƯU Ý QUAN TRỌNG:
- Dùng con số CỤ THỂ từ data (giá, %, RSI, MFI...), không nói chung chung
- Phân biệt rõ tín hiệu mạnh vs yếu
- Nếu thị trường xấu → nói thẳng, đừng cố gắng tìm cơ hội
- Viết cho nhà đầu tư có kiến thức cơ bản về PTKT, không cần giải thích thuật ngữ
- Format: dùng markdown headings, bold, bullet points cho dễ đọc trên web
"""

    def analyze_with_ai(self, data_summary: str) -> str:
        if not self.client:
            return "❌ Claude API chưa được cấu hình. Vui lòng thêm CLAUDE_API_KEY."

        prompt = self.build_analysis_prompt(data_summary)

        try:
            print("🤖 Đang gọi Claude AI phân tích...")

            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=6000,
                system=self.SYSTEM_PROMPT,
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
        print("="*60)
        print("🤖 BẮT ĐẦU PHÂN TÍCH AI")
        print("="*60)

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

        portfolio = self.load_portfolio()
        data_summary = self.prepare_data_summary(analyzed_df, signals_df, portfolio)
        report = self.analyze_with_ai(data_summary)

        return report


if __name__ == "__main__":
    ai = AIAnalyzer()
    report = ai.run()
    print("\n" + "="*60)
    print(report)
