"""
VN Stock Sniper - Dashboard Generator V5
Dashboard phân tích cổ phiếu Việt Nam - Giao diện hiện đại
Features: Heatmap, Interactive Charts, Watchlist, Advanced Filtering, Stock Detail
"""

import pandas as pd
import json
import os
import math
from datetime import datetime
import pytz

from src.config import (
    ANALYZED_DATA_FILE, SIGNALS_FILE, PORTFOLIO_FILE,
    HISTORY_DIR, TIMEZONE
)


def safe_str(val, default=''):
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    s = str(val)
    if s.lower() == 'nan':
        return default
    return s


def safe_float(val, default=0):
    if val is None:
        return default
    try:
        result = float(val)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    return int(safe_float(val, default))


class DashboardGenerator:
    """Tạo HTML Dashboard hiện đại"""

    def __init__(self):
        self.timezone = pytz.timezone(TIMEZONE)
        self.now = datetime.now(self.timezone)
        self.today = self.now.strftime("%d/%m/%Y %H:%M")
        self.today_file = self.now.strftime("%Y-%m-%d")

    def load_data(self):
        self.analyzed_df = pd.DataFrame()
        self.signals_df = pd.DataFrame()
        self.portfolio = {"positions": [], "cash_percent": 100}
        self.ai_report = ""

        if os.path.exists(ANALYZED_DATA_FILE):
            self.analyzed_df = pd.read_csv(ANALYZED_DATA_FILE)

        if os.path.exists(SIGNALS_FILE):
            self.signals_df = pd.read_csv(SIGNALS_FILE)

        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                self.portfolio = json.load(f)

        ai_report_file = f"{HISTORY_DIR}/{self.today_file}_report.txt"
        if os.path.exists(ai_report_file):
            with open(ai_report_file, 'r', encoding='utf-8') as f:
                self.ai_report = f.read()

    def get_market_stats(self):
        if self.analyzed_df.empty:
            return {
                'total': 0, 'uptrend': 0, 'sideways': 0, 'downtrend': 0,
                'star_5': 0, 'star_4': 0, 'star_3': 0, 'signals': 0,
                'breakout': 0, 'momentum': 0, 'pullback': 0, 'reversal': 0,
                'uptrend_pct': 0, 'sideways_pct': 0, 'downtrend_pct': 0,
                'avg_rsi': 50, 'avg_mfi': 50, 'vol_surge_count': 0,
                'bb_squeeze_count': 0, 'macd_bullish_count': 0,
            }

        df = self.analyzed_df
        total = len(df)
        uptrend = len(df[df['channel'].str.contains('XANH', na=False)])
        sideways = len(df[df['channel'].str.contains('XÁM', na=False)])
        downtrend = len(df[df['channel'].str.contains('ĐỎ', na=False)])

        signals_df = self.signals_df
        breakout = len(signals_df[signals_df['buy_signal'] == 'BREAKOUT']) if not signals_df.empty else 0
        momentum_sig = len(signals_df[signals_df['buy_signal'] == 'MOMENTUM']) if not signals_df.empty else 0
        pullback = len(signals_df[signals_df['buy_signal'] == 'PULLBACK']) if not signals_df.empty else 0
        reversal = len(signals_df[signals_df['buy_signal'] == 'REVERSAL']) if not signals_df.empty else 0

        return {
            'total': total,
            'uptrend': uptrend,
            'sideways': sideways,
            'downtrend': downtrend,
            'star_5': len(df[df['stars'] >= 5]),
            'star_4': len(df[df['stars'] == 4]),
            'star_3': len(df[df['stars'] == 3]),
            'signals': len(signals_df),
            'breakout': breakout,
            'momentum': momentum_sig,
            'pullback': pullback,
            'reversal': reversal,
            'uptrend_pct': round(uptrend / total * 100, 1) if total > 0 else 0,
            'sideways_pct': round(sideways / total * 100, 1) if total > 0 else 0,
            'downtrend_pct': round(downtrend / total * 100, 1) if total > 0 else 0,
            'avg_rsi': round(safe_float(df['rsi'].mean(), 50), 1),
            'avg_mfi': round(safe_float(df['mfi'].mean(), 50), 1),
            'vol_surge_count': int(df['vol_surge'].sum()) if 'vol_surge' in df.columns else 0,
            'bb_squeeze_count': int(df['bb_squeeze'].sum()) if 'bb_squeeze' in df.columns else 0,
            'macd_bullish_count': int(df['macd_bullish'].sum()) if 'macd_bullish' in df.columns else 0,
        }

    def get_portfolio_with_pnl(self):
        positions = self.portfolio.get('positions', [])
        total_pnl = 0

        for pos in positions:
            symbol = pos.get('symbol', '')
            entry_price = pos.get('entry_price', 0)

            if not self.analyzed_df.empty:
                stock_data = self.analyzed_df[self.analyzed_df['symbol'] == symbol]
                if not stock_data.empty:
                    current_price = stock_data.iloc[0]['close']
                    pos['current_price'] = current_price
                    pos['pnl_percent'] = round((current_price - entry_price) / entry_price * 100, 2) if entry_price > 0 else 0
                    total_pnl += pos['pnl_percent']
                else:
                    pos['current_price'] = entry_price
                    pos['pnl_percent'] = 0
            else:
                pos['current_price'] = entry_price
                pos['pnl_percent'] = 0

        return positions, total_pnl

    def _clean_for_json(self, records):
        clean = []
        for row in records:
            item = {}
            for k, v in row.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    item[k] = None
                elif isinstance(v, (bool,)):
                    item[k] = v
                else:
                    item[k] = v
            clean.append(item)
        return clean

    def _generate_css(self):
        return '''
        :root {
            --bg-primary: #0a0e17;
            --bg-secondary: #111827;
            --bg-card: #1a1f2e;
            --bg-card-hover: #242b3d;
            --bg-input: #151a28;
            --border: #2a3148;
            --border-hover: #3d4663;
            --text-primary: #e8edf5;
            --text-secondary: #8892a8;
            --text-muted: #5a6378;
            --green: #22c55e;
            --green-dim: rgba(34,197,94,0.15);
            --red: #ef4444;
            --red-dim: rgba(239,68,68,0.15);
            --yellow: #eab308;
            --yellow-dim: rgba(234,179,8,0.15);
            --blue: #3b82f6;
            --blue-dim: rgba(59,130,246,0.15);
            --purple: #a855f7;
            --purple-dim: rgba(168,85,247,0.15);
            --cyan: #06b6d4;
            --orange: #f97316;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            overflow-x: hidden;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--border-hover); }

        /* Header */
        .header {
            background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-card) 100%);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
            backdrop-filter: blur(20px);
        }
        .header-inner {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .logo-icon {
            width: 40px; height: 40px;
            background: linear-gradient(135deg, var(--blue), var(--purple));
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 20px; font-weight: 700;
        }
        .logo-text { font-size: 1.25rem; font-weight: 700; }
        .logo-sub { font-size: 0.75rem; color: var(--text-secondary); }
        .header-search {
            flex: 1;
            max-width: 400px;
            min-width: 200px;
        }
        .header-search input {
            width: 100%;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 8px 16px;
            color: var(--text-primary);
            font-size: 0.875rem;
            outline: none;
            transition: border-color 0.2s;
        }
        .header-search input:focus {
            border-color: var(--blue);
        }
        .header-search input::placeholder { color: var(--text-muted); }
        .header-time {
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-align: right;
        }

        /* Main container */
        .main { max-width: 1600px; margin: 0 auto; padding: 20px 24px; }

        /* Stat cards row */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            transition: all 0.2s;
            cursor: default;
        }
        .stat-card:hover { border-color: var(--border-hover); transform: translateY(-2px); }
        .stat-icon { font-size: 1.5rem; margin-bottom: 4px; }
        .stat-value { font-size: 1.75rem; font-weight: 700; line-height: 1.2; }
        .stat-label { font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px; }
        .stat-badge {
            display: inline-block;
            font-size: 0.65rem;
            padding: 2px 6px;
            border-radius: 4px;
            margin-top: 4px;
        }

        /* Section */
        .section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        .section-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 8px;
        }
        .section-title {
            font-size: 1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .section-body { padding: 20px; }

        /* Tabs */
        .tabs {
            display: flex;
            gap: 4px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 4px;
            margin-bottom: 20px;
            overflow-x: auto;
        }
        .tab {
            padding: 8px 16px;
            border-radius: 7px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-secondary);
            white-space: nowrap;
            transition: all 0.2s;
            border: none;
            background: none;
        }
        .tab:hover { color: var(--text-primary); background: var(--bg-card); }
        .tab.active {
            background: var(--blue);
            color: #fff;
        }
        .tab-panel { display: none; }
        .tab-panel.active { display: block; }

        /* Filter pills */
        .filters {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        .filter-pill {
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }
        .filter-pill:hover, .filter-pill.active {
            border-color: var(--blue);
            color: var(--blue);
            background: var(--blue-dim);
        }
        .filter-pill .count {
            background: var(--bg-card);
            padding: 1px 6px;
            border-radius: 10px;
            font-size: 0.7rem;
            margin-left: 4px;
        }

        /* Stock table */
        .stock-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.85rem;
        }
        .stock-table thead th {
            position: sticky;
            top: 0;
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            white-space: nowrap;
            user-select: none;
        }
        .stock-table thead th:hover { color: var(--text-primary); }
        .stock-table thead th.sorted-asc::after { content: ' \\2191'; color: var(--blue); }
        .stock-table thead th.sorted-desc::after { content: ' \\2193'; color: var(--blue); }
        .stock-table tbody tr {
            cursor: pointer;
            transition: background 0.15s;
        }
        .stock-table tbody tr:hover { background: var(--bg-card-hover); }
        .stock-table tbody td {
            padding: 10px 12px;
            border-bottom: 1px solid rgba(42,49,72,0.5);
            white-space: nowrap;
        }

        /* Inline badges */
        .badge-channel {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-green { background: var(--green-dim); color: var(--green); }
        .badge-gray { background: rgba(136,146,168,0.15); color: var(--text-secondary); }
        .badge-red { background: var(--red-dim); color: var(--red); }
        .badge-signal {
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-breakout { background: var(--green); color: #000; }
        .badge-momentum { background: var(--blue); color: #fff; }
        .badge-pullback { background: var(--yellow); color: #000; }
        .badge-reversal { background: var(--purple); color: #fff; }

        /* RSI bar */
        .rsi-bar {
            width: 60px; height: 6px;
            background: var(--bg-secondary);
            border-radius: 3px;
            display: inline-block;
            vertical-align: middle;
            margin-left: 6px;
            position: relative;
        }
        .rsi-bar-fill {
            height: 100%;
            border-radius: 3px;
            position: absolute;
            left: 0; top: 0;
        }

        /* Stars */
        .stars-display { color: var(--yellow); letter-spacing: -2px; }

        /* Signal cards */
        .signal-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 16px;
        }
        .signal-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            transition: all 0.2s;
            cursor: pointer;
        }
        .signal-card:hover {
            border-color: var(--border-hover);
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .signal-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .signal-symbol { font-size: 1.1rem; font-weight: 700; }
        .signal-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            text-align: center;
            margin-bottom: 12px;
        }
        .signal-metric-label { font-size: 0.7rem; color: var(--text-muted); }
        .signal-metric-value { font-size: 0.9rem; font-weight: 600; }
        .signal-levels {
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: 0.8rem;
        }
        .signal-level {
            display: flex;
            justify-content: space-between;
            padding: 4px 8px;
            border-radius: 4px;
            background: rgba(255,255,255,0.03);
        }

        /* Heatmap */
        .heatmap {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
            gap: 4px;
        }
        .heatmap-cell {
            padding: 8px 4px;
            border-radius: 6px;
            text-align: center;
            cursor: pointer;
            transition: all 0.15s;
            font-size: 0.75rem;
        }
        .heatmap-cell:hover { transform: scale(1.05); z-index: 1; }
        .heatmap-symbol { font-weight: 700; font-size: 0.8rem; }
        .heatmap-score { font-size: 0.65rem; opacity: 0.8; }

        /* Gauge */
        .gauge-container {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        .gauge-ring {
            width: 100px; height: 100px;
            position: relative;
        }
        .gauge-ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
        .gauge-ring circle {
            fill: none;
            stroke-width: 8;
        }
        .gauge-ring .bg { stroke: var(--bg-secondary); }
        .gauge-ring .fg { stroke-linecap: round; transition: stroke-dashoffset 1s ease; }
        .gauge-value {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            font-size: 1.2rem;
            font-weight: 700;
        }
        .gauge-label { font-size: 0.75rem; color: var(--text-secondary); }

        /* Charts row */
        .charts-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }

        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            padding: 20px;
            overflow-y: auto;
            backdrop-filter: blur(4px);
        }
        .modal-overlay.show { display: flex; justify-content: center; align-items: flex-start; }
        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            width: 100%;
            max-width: 900px;
            margin: 20px auto;
            animation: modalIn 0.2s ease;
        }
        @keyframes modalIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .modal-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-close {
            width: 32px; height: 32px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            font-size: 18px;
            transition: all 0.2s;
        }
        .modal-close:hover { background: var(--red-dim); color: var(--red); border-color: var(--red); }
        .modal-body { padding: 24px; }

        /* Indicator grid in modal */
        .ind-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }
        .ind-item {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px;
            text-align: center;
        }
        .ind-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
        .ind-value { font-size: 1.1rem; font-weight: 600; margin-top: 2px; }

        /* Portfolio */
        .portfolio-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }

        /* AI Report */
        .ai-report-content {
            white-space: pre-wrap;
            line-height: 1.8;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        /* Watchlist */
        .watchlist-empty {
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
        }
        .watchlist-star {
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.2s;
            opacity: 0.3;
        }
        .watchlist-star:hover, .watchlist-star.active { opacity: 1; color: var(--yellow); }

        /* Pagination */
        .pagination {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            font-size: 0.85rem;
        }
        .pagination-info { color: var(--text-secondary); }
        .pagination-btns { display: flex; gap: 4px; }
        .pagination-btn {
            padding: 6px 12px;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .pagination-btn:hover, .pagination-btn.active { background: var(--blue); color: #fff; border-color: var(--blue); }
        .pagination-btn:disabled { opacity: 0.3; cursor: default; }

        /* Green/Red coloring */
        .c-green { color: var(--green); }
        .c-red { color: var(--red); }
        .c-yellow { color: var(--yellow); }
        .c-blue { color: var(--blue); }
        .c-purple { color: var(--purple); }
        .c-cyan { color: var(--cyan); }
        .c-muted { color: var(--text-muted); }

        /* Responsive */
        @media (max-width: 768px) {
            .main { padding: 12px; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .stat-value { font-size: 1.3rem; }
            .header-inner { flex-direction: column; text-align: center; }
            .header-search { max-width: 100%; }
            .signal-cards { grid-template-columns: 1fr; }
            .heatmap { grid-template-columns: repeat(auto-fill, minmax(60px, 1fr)); }
            .tabs { flex-wrap: nowrap; }
        }
        '''

    def _generate_signals_data_js(self, signals):
        items = []
        for signal in signals:
            symbol = safe_str(signal.get('symbol', ''))
            signal_type = safe_str(signal.get('buy_signal', ''))
            close = safe_float(signal.get('close', 0))
            q_score = safe_float(signal.get('quality_score', 0))
            m_score = safe_float(signal.get('momentum_score', 0))
            stars = safe_int(signal.get('stars', 0))
            rsi = safe_float(signal.get('rsi', 0))
            channel = safe_str(signal.get('channel', ''))
            vol_ratio = safe_float(signal.get('vol_ratio', 0))

            atr = safe_float(signal.get('atr', 0))
            if atr == 0:
                atr = close * 0.03
            sl = round(close - 2 * atr, 0)
            tp1 = round(close + 3 * atr, 0)
            tp2 = round(close + 5 * atr, 0)

            items.append({
                'symbol': symbol, 'signal': signal_type, 'close': close,
                'q': q_score, 'm': m_score, 'stars': stars, 'rsi': rsi,
                'channel': channel, 'vol_ratio': vol_ratio,
                'sl': sl, 'tp1': tp1, 'tp2': tp2, 'atr': atr,
            })
        return items

    def generate_html(self):
        self.load_data()
        stats = self.get_market_stats()
        positions, total_pnl = self.get_portfolio_with_pnl()

        all_stocks = self.analyzed_df.to_dict('records') if not self.analyzed_df.empty else []
        signals = self.signals_df.to_dict('records') if not self.signals_df.empty else []
        clean_stocks = self._clean_for_json(all_stocks)
        signals_data = self._generate_signals_data_js(signals)

        # Escape AI report for JS
        ai_report_escaped = self.ai_report.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') if self.ai_report else ''

        html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VN Stock Sniper - Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>{self._generate_css()}</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
    <div class="header-inner">
        <div class="logo">
            <div class="logo-icon">S</div>
            <div>
                <div class="logo-text">VN Stock Sniper</div>
                <div class="logo-sub">Dashboard Phan tich Co phieu Viet Nam</div>
            </div>
        </div>
        <div class="header-search">
            <input type="text" id="globalSearch" placeholder="Tim kiem ma co phieu... (vd: FPT, VNM, HPG)" autocomplete="off">
        </div>
        <div class="header-time">
            Cap nhat: {self.today}<br>
            {stats['total']} ma co phieu
        </div>
    </div>
</div>

<div class="main">

<!-- STATS ROW -->
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-icon">&#x1F7E2;</div>
        <div class="stat-value c-green">{stats['uptrend']}</div>
        <div class="stat-label">Kenh Xanh (Uptrend)</div>
        <div class="stat-badge" style="background:var(--green-dim);color:var(--green)">{stats['uptrend_pct']}%</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">&#x26AA;</div>
        <div class="stat-value" style="color:var(--text-secondary)">{stats['sideways']}</div>
        <div class="stat-label">Kenh Xam (Sideways)</div>
        <div class="stat-badge" style="background:rgba(136,146,168,0.15);color:var(--text-secondary)">{stats['sideways_pct']}%</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">&#x1F534;</div>
        <div class="stat-value c-red">{stats['downtrend']}</div>
        <div class="stat-label">Kenh Do (Downtrend)</div>
        <div class="stat-badge" style="background:var(--red-dim);color:var(--red)">{stats['downtrend_pct']}%</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">&#x1F4E2;</div>
        <div class="stat-value c-yellow">{stats['signals']}</div>
        <div class="stat-label">Tin hieu MUA</div>
        <div class="stat-badge" style="background:var(--yellow-dim);color:var(--yellow)">BUY</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">&#x2B50;</div>
        <div class="stat-value c-yellow">{stats['star_5']}</div>
        <div class="stat-label">5 Sao</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">&#x1F4CA;</div>
        <div class="stat-value c-blue">{stats['star_4']}</div>
        <div class="stat-label">4 Sao</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">&#x1F4C8;</div>
        <div class="stat-value c-cyan">{stats['vol_surge_count']}</div>
        <div class="stat-label">Vol Surge</div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">&#x1F50D;</div>
        <div class="stat-value c-purple">{stats['bb_squeeze_count']}</div>
        <div class="stat-label">BB Squeeze</div>
    </div>
</div>

<!-- CHARTS ROW -->
<div class="charts-row">
    <div class="section" style="margin-bottom:0">
        <div class="section-header"><div class="section-title">Phan bo Kenh</div></div>
        <div class="section-body" style="display:flex;align-items:center;justify-content:center;">
            <div style="width:220px;height:220px;"><canvas id="channelChart"></canvas></div>
        </div>
    </div>
    <div class="section" style="margin-bottom:0">
        <div class="section-header"><div class="section-title">Phan bo Tin hieu</div></div>
        <div class="section-body" style="display:flex;align-items:center;justify-content:center;">
            <div style="width:220px;height:220px;"><canvas id="signalChart"></canvas></div>
        </div>
    </div>
    <div class="section" style="margin-bottom:0">
        <div class="section-header"><div class="section-title">Thi truong</div></div>
        <div class="section-body">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div class="ind-item">
                    <div class="ind-label">RSI Trung binh</div>
                    <div class="ind-value" style="color:{'var(--red)' if stats['avg_rsi'] > 70 else 'var(--green)' if stats['avg_rsi'] < 30 else 'var(--text-primary)'}">{stats['avg_rsi']}</div>
                </div>
                <div class="ind-item">
                    <div class="ind-label">MFI Trung binh</div>
                    <div class="ind-value">{stats['avg_mfi']}</div>
                </div>
                <div class="ind-item">
                    <div class="ind-label">MACD Bullish</div>
                    <div class="ind-value c-green">{stats['macd_bullish_count']}</div>
                </div>
                <div class="ind-item">
                    <div class="ind-label">Phan bo Sao</div>
                    <div class="ind-value" style="font-size:0.85rem">{stats['star_5']}x5 / {stats['star_4']}x4 / {stats['star_3']}x3</div>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- MAIN TABS -->
<div class="tabs" id="mainTabs">
    <button class="tab active" data-tab="signals">Tin hieu MUA ({stats['signals']})</button>
    <button class="tab" data-tab="heatmap">Heatmap</button>
    <button class="tab" data-tab="ranking">Bang xep hang</button>
    <button class="tab" data-tab="watchlist">Watchlist</button>
    <button class="tab" data-tab="portfolio">Portfolio</button>
    <button class="tab" data-tab="ai-report">AI Report</button>
</div>

<!-- TAB: SIGNALS -->
<div class="tab-panel active" id="panel-signals">
    <div class="section">
        <div class="section-header">
            <div class="section-title">Tin hieu MUA hom nay</div>
            <div class="filters" id="signalFilters">
                <button class="filter-pill active" data-signal="all">Tat ca<span class="count">{stats['signals']}</span></button>
                <button class="filter-pill" data-signal="BREAKOUT">Breakout<span class="count">{stats['breakout']}</span></button>
                <button class="filter-pill" data-signal="MOMENTUM">Momentum<span class="count">{stats['momentum']}</span></button>
                <button class="filter-pill" data-signal="PULLBACK">Pullback<span class="count">{stats['pullback']}</span></button>
                <button class="filter-pill" data-signal="REVERSAL">Reversal<span class="count">{stats['reversal']}</span></button>
            </div>
        </div>
        <div class="section-body">
            <div class="signal-cards" id="signalCards"></div>
        </div>
    </div>
</div>

<!-- TAB: HEATMAP -->
<div class="tab-panel" id="panel-heatmap">
    <div class="section">
        <div class="section-header">
            <div class="section-title">Heatmap theo Diem (Quality + Momentum)</div>
            <div class="filters" id="heatmapFilters">
                <button class="filter-pill active" data-hm="score">Theo Diem</button>
                <button class="filter-pill" data-hm="rsi">Theo RSI</button>
                <button class="filter-pill" data-hm="volume">Theo Volume</button>
            </div>
        </div>
        <div class="section-body">
            <div class="heatmap" id="heatmapGrid"></div>
        </div>
    </div>
</div>

<!-- TAB: RANKING -->
<div class="tab-panel" id="panel-ranking">
    <div class="section">
        <div class="section-header">
            <div class="section-title">Bang xep hang Co phieu</div>
            <div class="filters" id="channelFilters">
                <button class="filter-pill active" data-channel="all">Tat ca<span class="count">{stats['total']}</span></button>
                <button class="filter-pill" data-channel="XANH">Xanh<span class="count">{stats['uptrend']}</span></button>
                <button class="filter-pill" data-channel="XÁM">Xam<span class="count">{stats['sideways']}</span></button>
                <button class="filter-pill" data-channel="ĐỎ">Do<span class="count">{stats['downtrend']}</span></button>
            </div>
        </div>
        <div class="section-body" style="padding:0;overflow-x:auto;">
            <table class="stock-table" id="stockTable">
                <thead>
                    <tr>
                        <th data-sort="index">#</th>
                        <th></th>
                        <th data-sort="symbol">Ma</th>
                        <th data-sort="close">Gia</th>
                        <th data-sort="total_score">Diem</th>
                        <th data-sort="stars">Sao</th>
                        <th data-sort="buy_signal">Tin hieu</th>
                        <th data-sort="channel">Kenh</th>
                        <th data-sort="rsi">RSI</th>
                        <th data-sort="mfi">MFI</th>
                        <th data-sort="vol_ratio">Vol</th>
                        <th data-sort="macd_bullish">MACD</th>
                        <th data-sort="bb_percent">BB%</th>
                    </tr>
                </thead>
                <tbody id="stockTableBody"></tbody>
            </table>
            <div class="pagination" style="padding:12px 20px;">
                <div class="pagination-info" id="pageInfo"></div>
                <div class="pagination-btns" id="pageBtns"></div>
            </div>
        </div>
    </div>
</div>

<!-- TAB: WATCHLIST -->
<div class="tab-panel" id="panel-watchlist">
    <div class="section">
        <div class="section-header">
            <div class="section-title">Watchlist cua ban</div>
            <button class="filter-pill" onclick="clearWatchlist()" style="color:var(--red);border-color:var(--red);">Xoa tat ca</button>
        </div>
        <div class="section-body">
            <div id="watchlistContent"></div>
        </div>
    </div>
</div>

<!-- TAB: PORTFOLIO -->
<div class="tab-panel" id="panel-portfolio">
    <div class="section">
        <div class="section-header">
            <div class="section-title">Portfolio cua ban</div>
        </div>
        <div class="section-body">
            <div class="portfolio-summary">
                <div class="stat-card">
                    <div class="stat-value c-blue">{self.portfolio.get('cash_percent', 100)}%</div>
                    <div class="stat-label">Tien mat</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {'c-green' if total_pnl >= 0 else 'c-red'}">{'+'if total_pnl >= 0 else ''}{total_pnl:.2f}%</div>
                    <div class="stat-label">Tong P&L</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(positions)}</div>
                    <div class="stat-label">Vi the</div>
                </div>
            </div>
            {self._generate_portfolio_html(positions)}
        </div>
    </div>
</div>

<!-- TAB: AI REPORT -->
<div class="tab-panel" id="panel-ai-report">
    <div class="section">
        <div class="section-header">
            <div class="section-title">Bao cao Phan tich AI</div>
        </div>
        <div class="section-body">
            <div class="ai-report-content" id="aiReportContent"></div>
        </div>
    </div>
</div>

</div><!-- end main -->

<!-- STOCK DETAIL MODAL -->
<div class="modal-overlay" id="stockModal">
    <div class="modal-content">
        <div class="modal-header">
            <div>
                <div style="font-size:1.2rem;font-weight:700;" id="modalTitle"></div>
                <div style="font-size:0.8rem;color:var(--text-secondary);" id="modalSub"></div>
            </div>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body" id="modalBody"></div>
    </div>
</div>

<script>
// === DATA ===
const ALL_STOCKS = {json.dumps(clean_stocks, ensure_ascii=False, default=str)};
const SIGNALS_DATA = {json.dumps(signals_data, ensure_ascii=False, default=str)};
const AI_REPORT = `{ai_report_escaped}`;

// === STATE ===
let currentTab = 'signals';
let rankingFilter = 'all';
let signalFilter = 'all';
let heatmapMode = 'score';
let sortCol = 'total_score';
let sortDir = 'desc';
let currentPage = 1;
const PAGE_SIZE = 25;
let watchlist = JSON.parse(localStorage.getItem('vn_watchlist') || '[]');

// === UTILS ===
const n = v => Number(v || 0);
const f1 = v => n(v).toFixed(1);
const f2 = v => n(v).toFixed(2);
const loc = v => n(v).toLocaleString('vi-VN');
const pct = (v) => {{ const val = n(v); return (val >= 0 ? '+' : '') + val.toFixed(1) + '%'; }};

function getRsiColor(rsi) {{
    if (rsi > 70) return 'var(--red)';
    if (rsi < 30) return 'var(--green)';
    return 'var(--text-primary)';
}}

function getChannelBadge(ch) {{
    if (!ch) return '<span class="badge-channel badge-gray">-</span>';
    const clean = ch.replace(/[^A-Za-zÀ-ỹ ]/g, '').trim();
    if (ch.includes('XANH')) return '<span class="badge-channel badge-green">' + clean + '</span>';
    if (ch.includes('ĐỎ')) return '<span class="badge-channel badge-red">' + clean + '</span>';
    return '<span class="badge-channel badge-gray">' + clean + '</span>';
}}

function getSignalBadge(sig) {{
    if (!sig) return '-';
    const cls = {{'BREAKOUT':'badge-breakout','MOMENTUM':'badge-momentum','PULLBACK':'badge-pullback','REVERSAL':'badge-reversal'}}[sig] || '';
    return '<span class="badge-signal ' + cls + '">' + sig + '</span>';
}}

function getStars(n) {{
    return '<span class="stars-display">' + '&#11088;'.repeat(Math.min(n, 5)) + '</span>';
}}

function getRsiBar(rsi) {{
    const w = Math.min(rsi, 100);
    const color = rsi > 70 ? 'var(--red)' : rsi < 30 ? 'var(--green)' : 'var(--blue)';
    return f1(rsi) + '<span class="rsi-bar"><span class="rsi-bar-fill" style="width:' + w + '%;background:' + color + '"></span></span>';
}}

function isInWatchlist(symbol) {{
    return watchlist.includes(symbol);
}}

function toggleWatchlist(symbol, e) {{
    if (e) e.stopPropagation();
    const idx = watchlist.indexOf(symbol);
    if (idx >= 0) watchlist.splice(idx, 1);
    else watchlist.push(symbol);
    localStorage.setItem('vn_watchlist', JSON.stringify(watchlist));
    renderCurrentTab();
}}

function clearWatchlist() {{
    watchlist = [];
    localStorage.setItem('vn_watchlist', JSON.stringify(watchlist));
    renderCurrentTab();
}}

// === TABS ===
document.querySelectorAll('.tab').forEach(tab => {{
    tab.addEventListener('click', () => {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        currentTab = tab.dataset.tab;
        document.getElementById('panel-' + currentTab).classList.add('active');
        renderCurrentTab();
    }});
}});

function renderCurrentTab() {{
    if (currentTab === 'signals') renderSignals();
    else if (currentTab === 'heatmap') renderHeatmap();
    else if (currentTab === 'ranking') renderRanking();
    else if (currentTab === 'watchlist') renderWatchlist();
    else if (currentTab === 'ai-report') renderAIReport();
}}

// === SIGNAL FILTERS ===
document.querySelectorAll('#signalFilters .filter-pill').forEach(pill => {{
    pill.addEventListener('click', () => {{
        document.querySelectorAll('#signalFilters .filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        signalFilter = pill.dataset.signal;
        renderSignals();
    }});
}});

// === CHANNEL FILTERS ===
document.querySelectorAll('#channelFilters .filter-pill').forEach(pill => {{
    pill.addEventListener('click', () => {{
        document.querySelectorAll('#channelFilters .filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        rankingFilter = pill.dataset.channel;
        currentPage = 1;
        renderRanking();
    }});
}});

// === HEATMAP FILTERS ===
document.querySelectorAll('#heatmapFilters .filter-pill').forEach(pill => {{
    pill.addEventListener('click', () => {{
        document.querySelectorAll('#heatmapFilters .filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        heatmapMode = pill.dataset.hm;
        renderHeatmap();
    }});
}});

// === RENDER: SIGNALS ===
function renderSignals() {{
    const container = document.getElementById('signalCards');
    let data = SIGNALS_DATA;
    if (signalFilter !== 'all') data = data.filter(s => s.signal === signalFilter);

    if (data.length === 0) {{
        container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">Khong co tin hieu MUA' + (signalFilter !== 'all' ? ' loai ' + signalFilter : '') + '</div>';
        return;
    }}

    container.innerHTML = data.map(s => {{
        const slPct = s.close > 0 ? ((s.sl - s.close) / s.close * 100).toFixed(1) : 0;
        const tp1Pct = s.close > 0 ? ((s.tp1 - s.close) / s.close * 100).toFixed(1) : 0;
        const tp2Pct = s.close > 0 ? ((s.tp2 - s.close) / s.close * 100).toFixed(1) : 0;
        const sigCls = {{'BREAKOUT':'badge-breakout','MOMENTUM':'badge-momentum','PULLBACK':'badge-pullback','REVERSAL':'badge-reversal'}}[s.signal] || '';

        return `<div class="signal-card" onclick="showStockDetail('${{s.symbol}}')">
            <div class="signal-card-header">
                <div>
                    <span class="signal-symbol">${{s.symbol}}</span>
                    <span class="stars-display" style="margin-left:8px">${{'&#11088;'.repeat(s.stars)}}</span>
                </div>
                <span class="badge-signal ${{sigCls}}">${{s.signal}}</span>
            </div>
            <div class="signal-metrics">
                <div><div class="signal-metric-label">Gia</div><div class="signal-metric-value">${{loc(s.close)}}</div></div>
                <div><div class="signal-metric-label">Q/M</div><div class="signal-metric-value">${{n(s.q).toFixed(0)}}/${{n(s.m).toFixed(0)}}</div></div>
                <div><div class="signal-metric-label">RSI</div><div class="signal-metric-value" style="color:${{getRsiColor(s.rsi)}}">${{f1(s.rsi)}}</div></div>
            </div>
            <div class="signal-levels">
                <div class="signal-level"><span>Entry</span><span style="font-weight:600">${{loc(s.close)}}</span></div>
                <div class="signal-level"><span>Stop Loss</span><span class="c-red">${{loc(s.sl)}} (${{slPct}}%)</span></div>
                <div class="signal-level"><span>Target 1</span><span class="c-green">${{loc(s.tp1)}} (+${{tp1Pct}}%)</span></div>
                <div class="signal-level"><span>Target 2</span><span class="c-green">${{loc(s.tp2)}} (+${{tp2Pct}}%)</span></div>
            </div>
        </div>`;
    }}).join('');
}}

// === RENDER: HEATMAP ===
function renderHeatmap() {{
    const container = document.getElementById('heatmapGrid');
    const stocks = [...ALL_STOCKS].sort((a, b) => n(b.total_score) - n(a.total_score));

    container.innerHTML = stocks.map(s => {{
        let val, maxVal, label;
        if (heatmapMode === 'rsi') {{
            val = n(s.rsi);
            maxVal = 100;
            label = f1(val);
        }} else if (heatmapMode === 'volume') {{
            val = Math.min(n(s.vol_ratio), 3);
            maxVal = 3;
            label = f1(s.vol_ratio) + 'x';
        }} else {{
            val = n(s.total_score);
            maxVal = 40;
            label = n(val).toFixed(0);
        }}

        let bgColor;
        if (heatmapMode === 'rsi') {{
            if (val > 70) bgColor = 'rgba(239,68,68,0.5)';
            else if (val > 60) bgColor = 'rgba(239,68,68,0.25)';
            else if (val < 30) bgColor = 'rgba(34,197,94,0.5)';
            else if (val < 40) bgColor = 'rgba(34,197,94,0.25)';
            else bgColor = 'rgba(59,130,246,0.2)';
        }} else {{
            const ratio = Math.min(val / maxVal, 1);
            if (ratio > 0.7) bgColor = 'rgba(34,197,94,' + (0.2 + ratio * 0.4) + ')';
            else if (ratio > 0.4) bgColor = 'rgba(59,130,246,' + (0.15 + ratio * 0.3) + ')';
            else bgColor = 'rgba(136,146,168,' + (0.1 + ratio * 0.15) + ')';
        }}

        return `<div class="heatmap-cell" style="background:${{bgColor}}" onclick="showStockDetail('${{s.symbol}}')">
            <div class="heatmap-symbol">${{s.symbol}}</div>
            <div class="heatmap-score">${{label}}</div>
        </div>`;
    }}).join('');
}}

// === RENDER: RANKING ===
function renderRanking() {{
    let stocks = [...ALL_STOCKS];

    // Filter by channel
    if (rankingFilter !== 'all') {{
        stocks = stocks.filter(s => (s.channel || '').includes(rankingFilter));
    }}

    // Filter by search
    const searchVal = document.getElementById('globalSearch').value.toUpperCase().trim();
    if (searchVal) {{
        stocks = stocks.filter(s => (s.symbol || '').toUpperCase().includes(searchVal));
    }}

    // Sort
    stocks.sort((a, b) => {{
        let va = a[sortCol], vb = b[sortCol];
        if (typeof va === 'string') va = va || '';
        if (typeof vb === 'string') vb = vb || '';
        if (typeof va === 'number' || typeof vb === 'number') {{
            va = n(va); vb = n(vb);
        }}
        if (sortDir === 'asc') return va > vb ? 1 : va < vb ? -1 : 0;
        return va < vb ? 1 : va > vb ? -1 : 0;
    }});

    // Pagination
    const total = stocks.length;
    const totalPages = Math.ceil(total / PAGE_SIZE);
    if (currentPage > totalPages) currentPage = totalPages || 1;
    const start = (currentPage - 1) * PAGE_SIZE;
    const pageStocks = stocks.slice(start, start + PAGE_SIZE);

    const tbody = document.getElementById('stockTableBody');
    tbody.innerHTML = pageStocks.map((s, i) => {{
        const idx = start + i + 1;
        const wlActive = isInWatchlist(s.symbol) ? 'active' : '';
        return `<tr onclick="showStockDetail('${{s.symbol}}')">
            <td style="color:var(--text-muted)">${{idx}}</td>
            <td><span class="watchlist-star ${{wlActive}}" onclick="toggleWatchlist('${{s.symbol}}', event)">&#9733;</span></td>
            <td><strong>${{s.symbol}}</strong></td>
            <td>${{loc(s.close)}}</td>
            <td><strong>${{n(s.total_score).toFixed(0)}}</strong> <span style="font-size:0.7rem;color:var(--text-muted)">${{n(s.quality_score).toFixed(0)}}/${{n(s.momentum_score).toFixed(0)}}</span></td>
            <td>${{getStars(n(s.stars))}}</td>
            <td>${{getSignalBadge(s.buy_signal)}}</td>
            <td>${{getChannelBadge(s.channel)}}</td>
            <td style="color:${{getRsiColor(n(s.rsi))}}">${{getRsiBar(n(s.rsi))}}</td>
            <td>${{f1(s.mfi)}}</td>
            <td style="color:${{n(s.vol_ratio) > 1.5 ? 'var(--green)' : 'var(--text-primary)'}}">${{f1(s.vol_ratio)}}x</td>
            <td style="color:${{s.macd_bullish ? 'var(--green)' : 'var(--red)'}}">${{s.macd_bullish ? 'Bull' : 'Bear'}}</td>
            <td>${{f1(s.bb_percent)}}%</td>
        </tr>`;
    }}).join('');

    // Update sort headers
    document.querySelectorAll('.stock-table thead th').forEach(th => {{
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (th.dataset.sort === sortCol) th.classList.add('sorted-' + sortDir);
    }});

    // Pagination info
    document.getElementById('pageInfo').textContent = `Hien thi ${{start + 1}}-${{Math.min(start + PAGE_SIZE, total)}} / ${{total}} ma`;

    // Pagination buttons
    const pageBtns = document.getElementById('pageBtns');
    let btnsHtml = '';
    btnsHtml += `<button class="pagination-btn" onclick="goPage(1)" ${{currentPage === 1 ? 'disabled' : ''}}>&laquo;</button>`;
    btnsHtml += `<button class="pagination-btn" onclick="goPage(${{currentPage - 1}})" ${{currentPage === 1 ? 'disabled' : ''}}>&lsaquo;</button>`;

    let startP = Math.max(1, currentPage - 2);
    let endP = Math.min(totalPages, currentPage + 2);
    for (let p = startP; p <= endP; p++) {{
        btnsHtml += `<button class="pagination-btn ${{p === currentPage ? 'active' : ''}}" onclick="goPage(${{p}})">${{p}}</button>`;
    }}

    btnsHtml += `<button class="pagination-btn" onclick="goPage(${{currentPage + 1}})" ${{currentPage === totalPages ? 'disabled' : ''}}>&rsaquo;</button>`;
    btnsHtml += `<button class="pagination-btn" onclick="goPage(${{totalPages}})" ${{currentPage === totalPages ? 'disabled' : ''}}>&raquo;</button>`;
    pageBtns.innerHTML = btnsHtml;
}}

function goPage(p) {{
    currentPage = Math.max(1, p);
    renderRanking();
}}

// Table sorting
document.querySelectorAll('.stock-table thead th[data-sort]').forEach(th => {{
    th.addEventListener('click', () => {{
        const col = th.dataset.sort;
        if (sortCol === col) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        else {{ sortCol = col; sortDir = 'desc'; }}
        currentPage = 1;
        renderRanking();
    }});
}});

// === RENDER: WATCHLIST ===
function renderWatchlist() {{
    const container = document.getElementById('watchlistContent');
    if (watchlist.length === 0) {{
        container.innerHTML = '<div class="watchlist-empty">Chua co ma nao trong Watchlist.<br><br>Bam <span style="color:var(--yellow)">&#9733;</span> trong Bang xep hang de them ma vao Watchlist.</div>';
        return;
    }}

    const wlStocks = ALL_STOCKS.filter(s => watchlist.includes(s.symbol));
    if (wlStocks.length === 0) {{
        container.innerHTML = '<div class="watchlist-empty">Khong tim thay du lieu cho cac ma trong Watchlist.</div>';
        return;
    }}

    let html = '<div style="overflow-x:auto;"><table class="stock-table"><thead><tr>';
    html += '<th>Ma</th><th>Gia</th><th>Diem</th><th>Sao</th><th>Tin hieu</th><th>Kenh</th><th>RSI</th><th>MFI</th><th>Vol</th><th></th>';
    html += '</tr></thead><tbody>';

    wlStocks.forEach(s => {{
        html += `<tr onclick="showStockDetail('${{s.symbol}}')" style="cursor:pointer">
            <td><strong>${{s.symbol}}</strong></td>
            <td>${{loc(s.close)}}</td>
            <td>${{n(s.total_score).toFixed(0)}}</td>
            <td>${{getStars(n(s.stars))}}</td>
            <td>${{getSignalBadge(s.buy_signal)}}</td>
            <td>${{getChannelBadge(s.channel)}}</td>
            <td style="color:${{getRsiColor(n(s.rsi))}}">${{f1(s.rsi)}}</td>
            <td>${{f1(s.mfi)}}</td>
            <td>${{f1(s.vol_ratio)}}x</td>
            <td><span class="watchlist-star active" onclick="toggleWatchlist('${{s.symbol}}', event)">&#9733;</span></td>
        </tr>`;
    }});

    html += '</tbody></table></div>';
    container.innerHTML = html;
}}

// === RENDER: AI REPORT ===
function renderAIReport() {{
    document.getElementById('aiReportContent').textContent = AI_REPORT || 'Chua co bao cao AI. Chay workflow de tao bao cao.';
}}

// === STOCK DETAIL MODAL ===
function showStockDetail(symbol) {{
    const stock = ALL_STOCKS.find(s => s.symbol === symbol);
    if (!stock) return;

    document.getElementById('modalTitle').textContent = symbol;
    document.getElementById('modalSub').textContent = (stock.channel || '') + ' | Q:' + n(stock.quality_score).toFixed(0) + ' M:' + n(stock.momentum_score).toFixed(0) + ' | ' + n(stock.stars) + ' Sao';

    let html = '';

    // Top stats
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px;">';
    html += '<div class="ind-item"><div class="ind-label">Gia hien tai</div><div class="ind-value">' + loc(stock.close) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Quality Score</div><div class="ind-value c-blue">' + n(stock.quality_score).toFixed(0) + '/25</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Momentum Score</div><div class="ind-value c-purple">' + n(stock.momentum_score).toFixed(0) + '/15</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Tong diem</div><div class="ind-value c-green">' + n(stock.total_score).toFixed(0) + '/40</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Sao</div><div class="ind-value">' + getStars(n(stock.stars)) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Tin hieu</div><div class="ind-value">' + getSignalBadge(stock.buy_signal) + '</div></div>';
    html += '</div>';

    // Trend & Channel
    html += '<h6 style="color:var(--text-secondary);margin-bottom:10px;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Xu huong & Kenh gia</h6>';
    html += '<div class="ind-grid">';
    html += '<div class="ind-item"><div class="ind-label">Kenh</div><div class="ind-value">' + getChannelBadge(stock.channel) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">LR Slope %</div><div class="ind-value">' + f2(stock.lr_slope_pct) + '%</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Channel Pos</div><div class="ind-value">' + f1(stock.channel_position) + '%</div></div>';
    html += '<div class="ind-item"><div class="ind-label">MA Aligned</div><div class="ind-value" style="color:' + (stock.ma_aligned ? 'var(--green)' : 'var(--red)') + '">' + (stock.ma_aligned ? 'YES' : 'No') + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Above MA200</div><div class="ind-value" style="color:' + (stock.above_ma200 ? 'var(--green)' : 'var(--red)') + '">' + (stock.above_ma200 ? 'YES' : 'No') + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Above MA50</div><div class="ind-value" style="color:' + (stock.above_ma50 ? 'var(--green)' : 'var(--red)') + '">' + (stock.above_ma50 ? 'YES' : 'No') + '</div></div>';
    html += '</div>';

    // Moving Averages
    html += '<h6 style="color:var(--text-secondary);margin-bottom:10px;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Moving Averages</h6>';
    html += '<div class="ind-grid">';
    ['ma5','ma10','ma20','ma50','ma200'].forEach(k => {{
        const val = n(stock[k]);
        const aboveMA = n(stock.close) >= val;
        html += '<div class="ind-item"><div class="ind-label">' + k.toUpperCase() + '</div><div class="ind-value" style="color:' + (aboveMA ? 'var(--green)' : 'var(--red)') + '">' + loc(val) + '</div></div>';
    }});
    html += '</div>';

    // Momentum
    html += '<h6 style="color:var(--text-secondary);margin-bottom:10px;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Momentum</h6>';
    html += '<div class="ind-grid">';
    html += '<div class="ind-item"><div class="ind-label">RSI (14)</div><div class="ind-value" style="color:' + getRsiColor(n(stock.rsi)) + '">' + f1(stock.rsi) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">MFI</div><div class="ind-value" style="color:' + (n(stock.mfi) > 50 ? 'var(--green)' : 'var(--red)') + '">' + f1(stock.mfi) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">MACD</div><div class="ind-value" style="color:' + (stock.macd_bullish ? 'var(--green)' : 'var(--red)') + '">' + (stock.macd_bullish ? 'Bullish' : 'Bearish') + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">MACD Accel</div><div class="ind-value" style="color:' + (stock.macd_accelerating ? 'var(--green)' : 'var(--red)') + '">' + (stock.macd_accelerating ? 'Tang toc' : 'Giam toc') + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Stoch K</div><div class="ind-value">' + f1(stock.stoch_k) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Stoch D</div><div class="ind-value">' + f1(stock.stoch_d) + '</div></div>';
    html += '</div>';

    // Volume & Volatility
    html += '<h6 style="color:var(--text-secondary);margin-bottom:10px;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Volume & Bien dong</h6>';
    html += '<div class="ind-grid">';
    html += '<div class="ind-item"><div class="ind-label">Vol Ratio</div><div class="ind-value" style="color:' + (n(stock.vol_ratio) > 1.5 ? 'var(--green)' : 'var(--text-primary)') + '">' + f2(stock.vol_ratio) + 'x</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Vol Surge</div><div class="ind-value" style="color:' + (stock.vol_surge ? 'var(--green)' : 'var(--text-muted)') + '">' + (stock.vol_surge ? 'YES' : 'No') + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">ATR %</div><div class="ind-value">' + f2(stock.atr_percent) + '%</div></div>';
    html += '<div class="ind-item"><div class="ind-label">BB %</div><div class="ind-value">' + f1(stock.bb_percent) + '%</div></div>';
    html += '<div class="ind-item"><div class="ind-label">BB Squeeze</div><div class="ind-value" style="color:' + (stock.bb_squeeze ? 'var(--yellow)' : 'var(--text-muted)') + '">' + (stock.bb_squeeze ? 'YES' : 'No') + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">BB Width</div><div class="ind-value">' + f2(stock.bb_width) + '%</div></div>';
    html += '</div>';

    // Support / Resistance
    html += '<h6 style="color:var(--text-secondary);margin-bottom:10px;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Ho tro & Khang cu</h6>';
    html += '<div class="ind-grid">';
    html += '<div class="ind-item"><div class="ind-label">Support</div><div class="ind-value c-green">' + loc(stock.support) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Resistance</div><div class="ind-value c-red">' + loc(stock.resistance) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">BB Lower</div><div class="ind-value c-green">' + loc(stock.bb_lower) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">BB Upper</div><div class="ind-value c-red">' + loc(stock.bb_upper) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">LR Lower</div><div class="ind-value c-green">' + loc(stock.lr_lower) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">LR Upper</div><div class="ind-value c-red">' + loc(stock.lr_upper) + '</div></div>';
    html += '</div>';

    // Breakout Status
    html += '<h6 style="color:var(--text-secondary);margin-bottom:10px;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.5px">Breakout Status</h6>';
    html += '<div class="ind-grid">';
    html += '<div class="ind-item"><div class="ind-label">Breakout 20D</div><div class="ind-value" style="color:' + (stock.breakout_20 ? 'var(--green)' : 'var(--text-muted)') + '">' + (stock.breakout_20 ? 'YES' : 'No') + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">Breakout 50D</div><div class="ind-value" style="color:' + (stock.breakout_50 ? 'var(--green)' : 'var(--text-muted)') + '">' + (stock.breakout_50 ? 'YES' : 'No') + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">High 20D</div><div class="ind-value">' + loc(stock.highest_20) + '</div></div>';
    html += '<div class="ind-item"><div class="ind-label">High 50D</div><div class="ind-value">' + loc(stock.highest_50) + '</div></div>';
    html += '</div>';

    document.getElementById('modalBody').innerHTML = html;
    document.getElementById('stockModal').classList.add('show');
    document.body.style.overflow = 'hidden';
}}

function closeModal() {{
    document.getElementById('stockModal').classList.remove('show');
    document.body.style.overflow = '';
}}

document.getElementById('stockModal').addEventListener('click', function(e) {{
    if (e.target === this) closeModal();
}});

document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeModal();
}});

// === SEARCH ===
document.getElementById('globalSearch').addEventListener('input', function() {{
    if (currentTab === 'ranking') {{
        currentPage = 1;
        renderRanking();
    }} else {{
        // Switch to ranking tab for search
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        currentTab = 'ranking';
        document.querySelector('[data-tab="ranking"]').classList.add('active');
        document.getElementById('panel-ranking').classList.add('active');
        currentPage = 1;
        renderRanking();
    }}
}});

// === CHARTS ===
function initCharts() {{
    // Channel Distribution
    const ctxChannel = document.getElementById('channelChart').getContext('2d');
    new Chart(ctxChannel, {{
        type: 'doughnut',
        data: {{
            labels: ['Xanh (Uptrend)', 'Xam (Sideways)', 'Do (Downtrend)'],
            datasets: [{{ data: [{stats['uptrend']}, {stats['sideways']}, {stats['downtrend']}], backgroundColor: ['#22c55e', '#8892a8', '#ef4444'], borderWidth: 0, borderRadius: 4 }}]
        }},
        options: {{
            responsive: true, maintainAspectRatio: true,
            cutout: '65%',
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: '#8892a8', padding: 12, font: {{ size: 11 }} }} }}
            }}
        }}
    }});

    // Signal Distribution
    const ctxSignal = document.getElementById('signalChart').getContext('2d');
    new Chart(ctxSignal, {{
        type: 'doughnut',
        data: {{
            labels: ['Breakout', 'Momentum', 'Pullback', 'Reversal'],
            datasets: [{{ data: [{stats['breakout']}, {stats['momentum']}, {stats['pullback']}, {stats['reversal']}], backgroundColor: ['#22c55e', '#3b82f6', '#eab308', '#a855f7'], borderWidth: 0, borderRadius: 4 }}]
        }},
        options: {{
            responsive: true, maintainAspectRatio: true,
            cutout: '65%',
            plugins: {{
                legend: {{ position: 'bottom', labels: {{ color: '#8892a8', padding: 12, font: {{ size: 11 }} }} }}
            }}
        }}
    }});
}}

// === INIT ===
document.addEventListener('DOMContentLoaded', function() {{
    initCharts();
    renderSignals();
    renderAIReport();
}});
</script>

</body>
</html>'''

        return html

    def _generate_portfolio_html(self, positions):
        if not positions:
            return '<div style="text-align:center;padding:30px;color:var(--text-muted)"><p>Chua co vi the nao</p><p style="font-size:0.85rem">Dung Telegram Bot de them vi the:</p><code style="color:var(--blue)">/buy VCI 1000 37000</code></div>'

        html = '<div style="overflow-x:auto"><table class="stock-table"><thead><tr><th>Ma</th><th>So CP</th><th>Gia mua</th><th>Gia hien tai</th><th>P&L</th></tr></thead><tbody>'

        for pos in positions:
            symbol = pos.get('symbol', '')
            qty = pos.get('quantity', 0)
            entry = pos.get('entry_price', 0)
            current = pos.get('current_price', entry)
            pnl = pos.get('pnl_percent', 0)
            pnl_cls = 'c-green' if pnl >= 0 else 'c-red'
            pnl_sign = '+' if pnl >= 0 else ''

            html += f'<tr style="cursor:pointer" onclick="showStockDetail(\'{symbol}\')"><td><strong>{symbol}</strong></td><td>{qty:,}</td><td>{entry:,.0f}</td><td>{current:,.0f}</td><td class="{pnl_cls}">{pnl_sign}{pnl:.2f}%</td></tr>'

        html += '</tbody></table></div>'
        return html

    def save_dashboard(self, output_path: str = 'docs/index.html'):
        html = self.generate_html()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Dashboard saved: {output_path}")

    def run(self):
        print("=" * 60)
        print("TẠO DASHBOARD V5")
        print("=" * 60)
        self.save_dashboard()


if __name__ == "__main__":
    generator = DashboardGenerator()
    generator.run()
