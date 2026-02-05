"""
VN Stock Sniper - Technical Analyzer
Phân tích kỹ thuật đầy đủ giống Pine Script
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

from src.config import (
    MA_PERIODS, RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD, LR_PERIOD, LR_STD,
    STOCH_K, STOCH_D, ATR_PERIOD, MFI_PERIOD,
    VOL_MA_PERIOD, VOL_SURGE_THRESHOLD,
    Q_RATING_5, Q_RATING_4, Q_RATING_3, Q_RATING_2,
    M_RATING_5, M_RATING_4, M_RATING_3, M_RATING_2,
    CHANNEL_UPTREND_THRESHOLD, CHANNEL_DOWNTREND_THRESHOLD,
    RAW_DATA_FILE, ANALYZED_DATA_FILE, SIGNALS_FILE, DATA_DIR
)


class TechnicalAnalyzer:
    """Phân tích kỹ thuật đầy đủ"""
    
    def __init__(self):
        pass
    
    def calculate_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính Moving Averages"""
        for period in MA_PERIODS:
            if period == 200:
                df[f'ma{period}'] = df['close'].rolling(window=period).mean()
            else:
                df[f'ma{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # MA Alignment
        df['ma_aligned'] = (
            (df['ma5'] > df['ma10']) & 
            (df['ma10'] > df['ma20']) & 
            (df['ma20'] > df['ma50'])
        )
        
        df['ma_partial_aligned'] = (
            (df['ma10'] > df['ma20']) & 
            (df['ma20'] > df['ma50'])
        )
        
        df['above_ma200'] = df['close'] > df['ma200']
        df['above_ma50'] = df['close'] > df['ma50']
        df['above_ma20'] = df['close'] > df['ma20']
        
        return df
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / (loss + 0.0001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df['rsi_overbought'] = df['rsi'] > RSI_OVERBOUGHT
        df['rsi_oversold'] = df['rsi'] < RSI_OVERSOLD
        
        # RSI MA
        df['rsi_ma'] = df['rsi'].rolling(window=14).mean()
        df['rsi_above_ma'] = df['rsi'] > df['rsi_ma']
        
        return df
    
    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính MACD"""
        exp1 = df['close'].ewm(span=MACD_FAST, adjust=False).mean()
        exp2 = df['close'].ewm(span=MACD_SLOW, adjust=False).mean()
        
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=MACD_SIGNAL, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        df['macd_bullish'] = df['macd'] > df['macd_signal']
        df['macd_cross_up'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        df['macd_cross_down'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        df['macd_above_zero'] = df['macd'] > 0
        
        # MACD Acceleration
        df['macd_accel'] = df['macd_hist'] - df['macd_hist'].shift(1)
        df['macd_accelerating'] = df['macd_accel'] > 0
        
        return df
    
    def calculate_bollinger(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính Bollinger Bands"""
        df['bb_mid'] = df['close'].rolling(window=BB_PERIOD).mean()
        df['bb_std'] = df['close'].rolling(window=BB_PERIOD).std()
        df['bb_upper'] = df['bb_mid'] + BB_STD * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - BB_STD * df['bb_std']
        
        df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']) * 100
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid'] * 100
        
        # BB Squeeze (volatility thấp)
        bb_width_ma = df['bb_width'].rolling(window=20).mean()
        df['bb_squeeze'] = df['bb_width'] < bb_width_ma * 0.8
        
        df['near_bb_lower'] = df['bb_percent'] < 20
        df['near_bb_upper'] = df['bb_percent'] > 80
        
        return df
    
    def calculate_stochastic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính Stochastic"""
        low_min = df['low'].rolling(window=STOCH_K).min()
        high_max = df['high'].rolling(window=STOCH_K).max()
        
        df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min + 0.0001)
        df['stoch_d'] = df['stoch_k'].rolling(window=STOCH_D).mean()
        
        df['stoch_overbought'] = df['stoch_k'] > 80
        df['stoch_oversold'] = df['stoch_k'] < 20
        df['stoch_bullish_cross'] = (df['stoch_k'] > df['stoch_d']) & (df['stoch_k'].shift(1) <= df['stoch_d'].shift(1))
        
        return df
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính ATR"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=ATR_PERIOD).mean()
        df['atr_percent'] = df['atr'] / df['close'] * 100
        
        return df
    
    def calculate_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính Volume indicators"""
        df['vol_ma'] = df['volume'].rolling(window=VOL_MA_PERIOD).mean()
        df['vol_ratio'] = df['volume'] / (df['vol_ma'] + 1)
        df['vol_surge'] = df['vol_ratio'] > VOL_SURGE_THRESHOLD
        df['vol_above_avg'] = df['vol_ratio'] > 1
        
        return df
    
    def calculate_mfi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính Money Flow Index"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(MFI_PERIOD).sum()
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(MFI_PERIOD).sum()
        
        mfi_ratio = positive_flow / (negative_flow + 0.0001)
        df['mfi'] = 100 - (100 / (1 + mfi_ratio))
        
        df['mfi_bullish'] = df['mfi'] > 50
        df['mfi_overbought'] = df['mfi'] > 80
        df['mfi_oversold'] = df['mfi'] < 20
        
        return df
    
    def calculate_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính On-Balance Volume"""
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        
        df['obv'] = obv
        df['obv_ma'] = df['obv'].rolling(window=20).mean()
        df['obv_rising'] = df['obv'] > df['obv_ma']
        
        return df
    
    def calculate_linear_regression(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính Linear Regression Channel"""
        
        def calc_lr_value(x):
            if len(x) < LR_PERIOD:
                return np.nan
            y = x.values
            x_range = np.arange(len(y))
            slope, intercept = np.polyfit(x_range, y, 1)
            return intercept + slope * (len(y) - 1)
        
        def calc_lr_slope(x):
            if len(x) < LR_PERIOD:
                return np.nan
            y = x.values
            x_range = np.arange(len(y))
            slope, _ = np.polyfit(x_range, y, 1)
            return slope
        
        df['lr_value'] = df['close'].rolling(window=LR_PERIOD).apply(calc_lr_value, raw=False)
        df['lr_slope'] = df['close'].rolling(window=LR_PERIOD).apply(calc_lr_slope, raw=False)
        df['lr_slope_pct'] = df['lr_slope'] / df['close'] * 100
        
        # Standard deviation cho channel
        lr_std = df['close'].rolling(window=LR_PERIOD).std()
        df['lr_upper'] = df['lr_value'] + LR_STD * lr_std
        df['lr_lower'] = df['lr_value'] - LR_STD * lr_std
        
        # Channel type
        df['is_uptrend_channel'] = df['lr_slope_pct'] > CHANNEL_UPTREND_THRESHOLD
        df['is_downtrend_channel'] = df['lr_slope_pct'] < CHANNEL_DOWNTREND_THRESHOLD
        df['is_sideways_channel'] = ~df['is_uptrend_channel'] & ~df['is_downtrend_channel']
        
        # Slope direction
        df['channel_slope_up'] = df['lr_slope_pct'] > 0.02
        df['channel_slope_down'] = df['lr_slope_pct'] < -0.02
        df['channel_slope_flat'] = ~df['channel_slope_up'] & ~df['channel_slope_down']
        
        # Position in channel
        df['channel_position'] = (df['close'] - df['lr_lower']) / (df['lr_upper'] - df['lr_lower'] + 0.0001) * 100
        df['near_channel_bottom'] = df['channel_position'] < 30
        df['near_channel_top'] = df['channel_position'] > 70
        
        return df
    
    def calculate_breakout(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính Breakout signals"""
        df['highest_20'] = df['high'].shift(1).rolling(window=20).max()
        df['highest_50'] = df['high'].shift(1).rolling(window=50).max()
        df['lowest_20'] = df['low'].shift(1).rolling(window=20).min()
        df['lowest_50'] = df['low'].shift(1).rolling(window=50).min()
        
        df['breakout_20'] = df['close'] > df['highest_20']
        df['breakout_50'] = df['close'] > df['highest_50']
        df['breakdown_20'] = df['close'] < df['lowest_20']
        df['breakdown_50'] = df['close'] < df['lowest_50']
        
        return df
    
    def calculate_support_resistance(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính Support/Resistance"""
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        df['near_support'] = (df['close'] - df['support']) / df['close'] < 0.03
        df['near_resistance'] = (df['resistance'] - df['close']) / df['close'] < 0.03
        
        return df
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính tất cả chỉ báo"""
        df = df.copy()
        df = df.sort_values('time').reset_index(drop=True)
        
        # Đảm bảo columns đúng tên
        df.columns = df.columns.str.lower()
        
        # Tính tất cả
        df = self.calculate_ma(df)
        df = self.calculate_rsi(df)
        df = self.calculate_macd(df)
        df = self.calculate_bollinger(df)
        df = self.calculate_stochastic(df)
        df = self.calculate_atr(df)
        df = self.calculate_volume(df)
        df = self.calculate_mfi(df)
        df = self.calculate_obv(df)
        df = self.calculate_linear_regression(df)
        df = self.calculate_breakout(df)
        df = self.calculate_support_resistance(df)
        
        return df
    
    def calculate_quality_score(self, row: dict) -> float:
        """Tính Quality Score (max 25)"""
        score = 0
        
        # MA Alignment (4 điểm)
        if row.get('ma_aligned', False):
            score += 3
        elif row.get('ma_partial_aligned', False):
            score += 2
        
        if row.get('above_ma200', False):
            score += 1
        
        # Kênh xu hướng (3 điểm)
        if row.get('is_uptrend_channel', False):
            score += 3
        elif row.get('is_sideways_channel', False):
            score += 1.5
        
        # Slope (2 điểm)
        if row.get('channel_slope_up', False):
            score += 2
        elif row.get('channel_slope_flat', False):
            score += 1
        
        # RSI (2 điểm)
        rsi = row.get('rsi', 50)
        if 40 <= rsi <= 60:
            score += 2
        elif 30 <= rsi <= 70:
            score += 1
        
        # MFI (2 điểm)
        if row.get('mfi_bullish', False):
            score += 2
        elif row.get('mfi', 50) > 40:
            score += 1
        
        # Volume (2 điểm)
        if row.get('vol_surge', False):
            score += 2
        elif row.get('vol_above_avg', False):
            score += 1
        
        # MACD (2 điểm)
        if row.get('macd_bullish', False):
            score += 2
        
        # Channel position (2 điểm)
        if row.get('near_channel_bottom', False):
            score += 2
        elif row.get('channel_position', 50) < 50:
            score += 1
        
        # BB Squeeze bonus (2 điểm)
        if row.get('bb_squeeze', False) and row.get('is_uptrend_channel', False):
            score += 2
        
        # Penalties
        if row.get('rsi_overbought', False):
            score -= 2
        if row.get('near_channel_top', False):
            score -= 1
        
        return min(max(score, 0), 25)
    
    def calculate_momentum_score(self, row: dict) -> float:
        """Tính Momentum Score (max 15)"""
        score = 0
        
        # Breakout (4 điểm)
        if row.get('breakout_50', False):
            score += 4
        elif row.get('breakout_20', False):
            score += 2
        
        # Volume (4 điểm)
        vol_ratio = row.get('vol_ratio', 1)
        if vol_ratio > 2:
            score += 4
        elif vol_ratio > 1.5:
            score += 3
        elif vol_ratio > 1:
            score += 2
        
        # MACD (3 điểm)
        if row.get('macd_cross_up', False):
            score += 3
        elif row.get('macd_bullish', False) and row.get('macd_accelerating', False):
            score += 2
        elif row.get('macd_bullish', False):
            score += 1
        
        # RSI momentum (2 điểm)
        rsi = row.get('rsi', 50)
        if 50 <= rsi <= 70:
            score += 2
        elif rsi > 40:
            score += 1
        
        # Stochastic (2 điểm)
        if row.get('stoch_bullish_cross', False):
            score += 2
        
        # Penalties
        if row.get('rsi_overbought', False):
            score -= 2
        if row.get('stoch_overbought', False):
            score -= 1
        
        return min(max(score, 0), 15)
    
    def get_quality_rating(self, q_score: float) -> int:
        """Chuyển Q Score thành rating 1-5"""
        if q_score >= Q_RATING_5:
            return 5
        elif q_score >= Q_RATING_4:
            return 4
        elif q_score >= Q_RATING_3:
            return 3
        elif q_score >= Q_RATING_2:
            return 2
        return 1
    
    def get_momentum_rating(self, m_score: float) -> int:
        """Chuyển M Score thành rating 1-5"""
        if m_score >= M_RATING_5:
            return 5
        elif m_score >= M_RATING_4:
            return 4
        elif m_score >= M_RATING_3:
            return 3
        elif m_score >= M_RATING_2:
            return 2
        return 1
    
    def get_star_rating(self, q_rating: int, m_rating: int) -> int:
        """Tính số sao từ Q và M rating"""
        if q_rating >= 4 and m_rating >= 4:
            return 5
        elif q_rating >= 4 and m_rating >= 3:
            return 4
        elif q_rating >= 3 and m_rating >= 3:
            return 3
        elif q_rating >= 2 or m_rating >= 2:
            return 2
        return 1
    
    def get_buy_signal(self, row: dict) -> str:
        """Xác định tín hiệu mua"""
        is_uptrend = row.get('is_uptrend_channel', False)
        is_sideways = row.get('is_sideways_channel', False)
        is_downtrend = row.get('is_downtrend_channel', False)
        
        slope_up = row.get('channel_slope_up', False)
        slope_down = row.get('channel_slope_down', False)
        
        breakout = row.get('breakout_20', False) or row.get('breakout_50', False)
        vol_surge = row.get('vol_surge', False)
        macd_bullish = row.get('macd_bullish', False)
        
        m_score = row.get('momentum_score', 0)
        q_score = row.get('quality_score', 0)
        
        near_bottom = row.get('near_channel_bottom', False) or row.get('near_bb_lower', False)
        
        # BREAKOUT: Kênh xanh + slope lên + vol surge + phá đỉnh
        if breakout and is_uptrend and slope_up and vol_surge:
            return "BREAKOUT"
        
        # MOMENTUM: Kênh xanh + slope lên + MACD bullish + M >= 7
        if is_uptrend and slope_up and macd_bullish and m_score >= 7:
            return "MOMENTUM"
        
        # PULLBACK: Kênh xanh/xám + slope không xuống + gần đáy + Q >= 2
        if (is_uptrend or is_sideways) and not slope_down and near_bottom and q_score >= 8:
            return "PULLBACK"
        
        # REVERSAL: Kênh đỏ + gần đáy + slope đang chuyển
        lr_slope_pct = row.get('lr_slope_pct', 0)
        if is_downtrend and near_bottom and lr_slope_pct > -0.05:
            return "REVERSAL"
        
        return ""
    
    def get_sell_signal(self, row: dict) -> str:
        """Xác định tín hiệu bán"""
        # Channel break
        if row.get('is_downtrend_channel', False) and row.get('channel_slope_down', False):
            return "CHANNEL_BREAK"
        
        # Technical
        if row.get('macd_cross_down', False) and not row.get('above_ma20', False):
            return "TECHNICAL"
        
        # Breakdown
        if row.get('breakdown_20', False):
            return "BREAKDOWN"
        
        return ""
    
    def analyze_single_stock(self, df: pd.DataFrame) -> dict:
        """Phân tích 1 mã cổ phiếu"""
        if df.empty:
            return {}
        
        # Tính chỉ báo
        df = self.calculate_all_indicators(df)
        
        # Lấy dòng cuối
        latest = df.iloc[-1].to_dict()
        
        # Tính điểm
        latest['quality_score'] = self.calculate_quality_score(latest)
        latest['momentum_score'] = self.calculate_momentum_score(latest)
        latest['total_score'] = latest['quality_score'] + latest['momentum_score']
        
        # Ratings
        q_rating = self.get_quality_rating(latest['quality_score'])
        m_rating = self.get_momentum_rating(latest['momentum_score'])
        
        latest['quality_rating'] = q_rating
        latest['momentum_rating'] = m_rating
        latest['stars'] = self.get_star_rating(q_rating, m_rating)
        
        # Signals
        latest['buy_signal'] = self.get_buy_signal(latest)
        latest['sell_signal'] = self.get_sell_signal(latest)
        
        # Channel text
        if latest.get('is_uptrend_channel', False):
            latest['channel'] = "🟢 XANH"
        elif latest.get('is_downtrend_channel', False):
            latest['channel'] = "🔴 ĐỎ"
        else:
            latest['channel'] = "⚪ XÁM"
        
        return latest
    
    def analyze_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Phân tích tất cả các mã"""
        if df.empty:
            return pd.DataFrame()
        
        print("\n📊 Đang phân tích kỹ thuật...")
        
        results = []
        symbols = df['symbol'].unique()
        
        for i, symbol in enumerate(symbols):
            try:
                stock_df = df[df['symbol'] == symbol].copy()
                result = self.analyze_single_stock(stock_df)
                
                if result:
                    results.append(result)
                
                if (i + 1) % 50 == 0:
                    print(f"   Đã phân tích {i+1}/{len(symbols)} mã...")
                    
            except Exception as e:
                print(f"   ❌ {symbol}: {e}")
                continue
        
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('total_score', ascending=False)
        
        print(f"✅ Phân tích xong {len(results_df)} mã")
        
        return results_df
    
    def save_results(self, df: pd.DataFrame, filepath: str = ANALYZED_DATA_FILE):
        """Lưu kết quả phân tích"""
        if df.empty:
            return
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df.to_csv(filepath, index=False)
        print(f"✅ Đã lưu: {filepath}")
    
    def get_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Lọc các mã có tín hiệu"""
        if df.empty:
            return pd.DataFrame()
        
        # Có tín hiệu mua
        signals = df[df['buy_signal'] != ""].copy()
        
        # Lưu signals
        if not signals.empty:
            signals.to_csv(SIGNALS_FILE, index=False)
            print(f"✅ Đã lưu {len(signals)} tín hiệu: {SIGNALS_FILE}")
        
        return signals
    
    def run(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """Chạy phân tích"""
        print("="*60)
        print("📊 BẮT ĐẦU PHÂN TÍCH KỸ THUẬT")
        print("="*60)
        
        if df is None:
            # Đọc từ file
            if os.path.exists(RAW_DATA_FILE):
                df = pd.read_csv(RAW_DATA_FILE)
            else:
                print("❌ Không có dữ liệu để phân tích")
                return pd.DataFrame()
        
        # Phân tích
        results = self.analyze_all(df)
        
        # Lưu
        self.save_results(results)
        
        # Lọc signals
        signals = self.get_signals(results)
        
        return results


# Test
if __name__ == "__main__":
    analyzer = TechnicalAnalyzer()
    results = analyzer.run()
    
    if not results.empty:
        print("\n📊 TOP 10 CỔ PHIẾU:")
        print(results[['symbol', 'close', 'quality_score', 'momentum_score', 'stars', 'buy_signal', 'channel']].head(10))
