"""
VN Stock Sniper - Dashboard Generator V6
Redesigned: Dark navy/purple theme, 3-tab layout, signal screener, score gauges
Inspired by React StockDashboard template
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


def get_signal_label(row):
    """Map scoring + signals to Vietnamese signal labels"""
    buy_sig = safe_str(row.get('buy_signal', ''))
    sell_sig = safe_str(row.get('sell_signal', ''))
    stars = safe_int(row.get('stars', 0))
    score = safe_float(row.get('total_score', 0))

    if buy_sig and stars >= 4:
        return 'MUA MANH'
    if buy_sig and stars >= 3:
        return 'MUA'
    if sell_sig and stars <= 1:
        return 'BAN MANH'
    if sell_sig:
        return 'BAN'

    if score >= 28:
        return 'MUA'
    if score <= 8:
        return 'BAN'
    return 'TRUNG LAP'


class DashboardGenerator:
    """Generate V6 HTML Dashboard - React-inspired design"""

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
                'buy_strong': 0, 'buy': 0, 'neutral': 0, 'sell': 0, 'sell_strong': 0,
                'signals': 0, 'breakout': 0, 'momentum': 0, 'pullback': 0, 'reversal': 0,
                'avg_rsi': 50, 'avg_mfi': 50, 'avg_score': 0,
                'vol_surge_count': 0, 'bb_squeeze_count': 0,
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

        # Count signal labels
        buy_strong = 0
        buy = 0
        neutral = 0
        sell = 0
        sell_strong = 0
        for _, row in df.iterrows():
            label = get_signal_label(row.to_dict())
            if label == 'MUA MANH':
                buy_strong += 1
            elif label == 'MUA':
                buy += 1
            elif label == 'BAN MANH':
                sell_strong += 1
            elif label == 'BAN':
                sell += 1
            else:
                neutral += 1

        return {
            'total': total,
            'uptrend': uptrend,
            'sideways': sideways,
            'downtrend': downtrend,
            'buy_strong': buy_strong,
            'buy': buy,
            'neutral': neutral,
            'sell': sell,
            'sell_strong': sell_strong,
            'signals': len(signals_df),
            'breakout': breakout,
            'momentum': momentum_sig,
            'pullback': pullback,
            'reversal': reversal,
            'avg_rsi': round(safe_float(df['rsi'].mean(), 50), 1),
            'avg_mfi': round(safe_float(df['mfi'].mean(), 50), 1),
            'avg_score': round(safe_float(df['total_score'].mean(), 0), 1),
            'vol_surge_count': int(df['vol_surge'].sum()) if 'vol_surge' in df.columns else 0,
            'bb_squeeze_count': int(df['bb_squeeze'].sum()) if 'bb_squeeze' in df.columns else 0,
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

    def generate_html(self):
        self.load_data()
        stats = self.get_market_stats()
        positions, total_pnl = self.get_portfolio_with_pnl()

        all_stocks = self.analyzed_df.to_dict('records') if not self.analyzed_df.empty else []
        signals = self.signals_df.to_dict('records') if not self.signals_df.empty else []
        clean_stocks = self._clean_for_json(all_stocks)

        # Add signal_label to each stock for JS
        for stock in clean_stocks:
            stock['signal_label'] = get_signal_label(stock)
            stock['score_100'] = round(safe_float(stock.get('total_score', 0)) / 40 * 100, 0)

        ai_report_escaped = self.ai_report.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') if self.ai_report else ''

        html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VN Stock Sniper - Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
    :root {{
        --bg-body: #030712;
        --bg-card: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        --bg-card-solid: #0f172a;
        --bg-card-hover: #1a2340;
        --bg-input: #0c1222;
        --bg-header: rgba(15, 23, 42, 0.95);
        --border: #1e293b;
        --border-hover: #334155;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #475569;
        --accent-green: #10b981;
        --accent-green-glow: 0 0 12px rgba(16, 185, 129, 0.4);
        --accent-red: #ef4444;
        --accent-red-glow: 0 0 12px rgba(239, 68, 68, 0.4);
        --accent-blue: #3b82f6;
        --accent-purple: #8b5cf6;
        --accent-yellow: #f59e0b;
        --accent-cyan: #06b6d4;
        --accent-orange: #f97316;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
        background: var(--bg-body);
        color: var(--text-primary);
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        line-height: 1.6;
        overflow-x: hidden;
    }}

    .mono {{ font-family: 'JetBrains Mono', monospace; }}

    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-body); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

    /* === MARKET TICKER === */
    .ticker-bar {{
        background: linear-gradient(90deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        border-bottom: 1px solid var(--border);
        padding: 8px 0;
        overflow: hidden;
        position: relative;
    }}
    .ticker-track {{
        display: flex;
        animation: ticker 40s linear infinite;
        gap: 32px;
        width: max-content;
    }}
    @keyframes ticker {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
    .ticker-item {{
        display: flex;
        align-items: center;
        gap: 8px;
        white-space: nowrap;
        font-size: 0.8rem;
    }}
    .ticker-symbol {{ font-weight: 600; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }}
    .ticker-price {{ color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; }}

    /* === HEADER === */
    .header {{
        background: var(--bg-header);
        border-bottom: 1px solid var(--border);
        padding: 16px 24px;
        position: sticky;
        top: 0;
        z-index: 100;
        backdrop-filter: blur(20px);
    }}
    .header-inner {{
        max-width: 1600px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
    }}
    .logo {{ display: flex; align-items: center; gap: 12px; }}
    .logo-icon {{
        width: 42px; height: 42px;
        background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px; font-weight: 700; color: #fff;
        font-family: 'JetBrains Mono', monospace;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }}
    .logo-text {{ font-size: 1.2rem; font-weight: 700; letter-spacing: -0.5px; }}
    .logo-sub {{ font-size: 0.7rem; color: var(--text-muted); }}
    .header-search {{
        flex: 1; max-width: 360px; min-width: 180px;
    }}
    .header-search input {{
        width: 100%;
        background: var(--bg-input);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 8px 16px 8px 36px;
        color: var(--text-primary);
        font-size: 0.85rem;
        outline: none;
        transition: border-color 0.2s;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23475569' stroke-width='2'%3E%3Ccircle cx='11' cy='11' r='8'/%3E%3Cline x1='21' y1='21' x2='16.65' y2='16.65'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: 12px center;
    }}
    .header-search input:focus {{ border-color: var(--accent-blue); }}
    .header-search input::placeholder {{ color: var(--text-muted); }}
    .header-right {{ text-align: right; }}
    .header-time {{ font-size: 0.75rem; color: var(--text-muted); }}
    .header-badge {{
        display: inline-block;
        background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-top: 4px;
    }}

    /* === MAIN === */
    .main {{ max-width: 1600px; margin: 0 auto; padding: 20px 24px; }}

    /* === TABS === */
    .tabs {{
        display: flex;
        gap: 2px;
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 4px;
        margin-bottom: 24px;
    }}
    .tab {{
        flex: 1;
        padding: 10px 20px;
        border-radius: 9px;
        cursor: pointer;
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-secondary);
        white-space: nowrap;
        transition: all 0.25s;
        border: none;
        background: none;
        text-align: center;
    }}
    .tab:hover {{ color: var(--text-primary); background: rgba(59, 130, 246, 0.1); }}
    .tab.active {{
        background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
        color: #fff;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}

    /* === SIGNAL SUMMARY CARDS === */
    .signal-summary {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-bottom: 24px;
    }}
    .signal-summary-card {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        cursor: pointer;
        transition: all 0.25s;
        position: relative;
        overflow: hidden;
    }}
    .signal-summary-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
    }}
    .signal-summary-card:hover {{ border-color: var(--border-hover); transform: translateY(-2px); }}
    .signal-summary-card.active {{ border-color: var(--accent-blue); }}
    .ssc-buy-strong::before {{ background: var(--accent-green); box-shadow: var(--accent-green-glow); }}
    .ssc-buy::before {{ background: var(--accent-green); opacity: 0.7; }}
    .ssc-neutral::before {{ background: var(--text-muted); }}
    .ssc-sell::before {{ background: var(--accent-orange); }}
    .ssc-sell-strong::before {{ background: var(--accent-red); box-shadow: var(--accent-red-glow); }}
    .ssc-count {{ font-size: 2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1; }}
    .ssc-label {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px; }}

    /* === STAT CARDS === */
    .stat-row {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin-bottom: 24px;
    }}
    .stat-card {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        transition: all 0.2s;
    }}
    .stat-card:hover {{ border-color: var(--border-hover); }}
    .stat-card-label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
    .stat-card-value {{ font-size: 1.5rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
    .stat-card-sub {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px; }}

    /* === SECTION === */
    .section {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        margin-bottom: 24px;
        overflow: hidden;
    }}
    .section-header {{
        padding: 16px 24px;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .section-title {{ font-size: 1rem; font-weight: 600; display: flex; align-items: center; gap: 8px; }}
    .section-body {{ padding: 24px; }}

    /* === CHARTS GRID === */
    .charts-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }}

    /* === SIGNAL BADGES === */
    .signal-badge {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.5px;
        white-space: nowrap;
    }}
    .signal-mua-manh {{
        background: rgba(16, 185, 129, 0.15);
        color: var(--accent-green);
        box-shadow: var(--accent-green-glow);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    .signal-mua {{
        background: rgba(16, 185, 129, 0.1);
        color: var(--accent-green);
        border: 1px solid rgba(16, 185, 129, 0.2);
    }}
    .signal-trung-lap {{
        background: rgba(148, 163, 184, 0.1);
        color: var(--text-secondary);
        border: 1px solid rgba(148, 163, 184, 0.2);
    }}
    .signal-ban {{
        background: rgba(249, 115, 22, 0.1);
        color: var(--accent-orange);
        border: 1px solid rgba(249, 115, 22, 0.2);
    }}
    .signal-ban-manh {{
        background: rgba(239, 68, 68, 0.15);
        color: var(--accent-red);
        box-shadow: var(--accent-red-glow);
        border: 1px solid rgba(239, 68, 68, 0.3);
    }}

    /* === BUY TYPE BADGES === */
    .type-badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }}
    .type-breakout {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); }}
    .type-momentum {{ background: rgba(59, 130, 246, 0.2); color: var(--accent-blue); }}
    .type-pullback {{ background: rgba(245, 158, 11, 0.2); color: var(--accent-yellow); }}
    .type-reversal {{ background: rgba(139, 92, 246, 0.2); color: var(--accent-purple); }}

    /* === FILTER PILLS === */
    .filters {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .filter-pill {{
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        border: 1px solid var(--border);
        background: transparent;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all 0.2s;
    }}
    .filter-pill:hover {{ border-color: var(--accent-blue); color: var(--accent-blue); }}
    .filter-pill.active {{
        background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(139,92,246,0.2));
        border-color: var(--accent-blue);
        color: var(--accent-blue);
    }}
    .filter-pill .cnt {{
        background: rgba(59,130,246,0.2);
        padding: 1px 6px;
        border-radius: 10px;
        font-size: 0.7rem;
        margin-left: 4px;
        font-family: 'JetBrains Mono', monospace;
    }}

    /* === SCREENER TABLE === */
    .screener-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.85rem;
    }}
    .screener-table thead th {{
        position: sticky;
        top: 0;
        background: rgba(15, 23, 42, 0.95);
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 12px 14px;
        border-bottom: 1px solid var(--border);
        cursor: pointer;
        white-space: nowrap;
        user-select: none;
        transition: color 0.2s;
    }}
    .screener-table thead th:hover {{ color: var(--text-primary); }}
    .screener-table thead th.sorted-asc::after {{ content: ' \\2191'; color: var(--accent-blue); }}
    .screener-table thead th.sorted-desc::after {{ content: ' \\2193'; color: var(--accent-blue); }}
    .screener-table tbody tr {{
        cursor: pointer;
        transition: background 0.15s;
        border-bottom: 1px solid rgba(30, 41, 59, 0.5);
    }}
    .screener-table tbody tr:hover {{ background: rgba(59, 130, 246, 0.05); }}
    .screener-table tbody td {{
        padding: 12px 14px;
        border-bottom: 1px solid rgba(30, 41, 59, 0.3);
        white-space: nowrap;
        vertical-align: middle;
    }}
    .screener-table .stock-name {{
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
    }}

    /* === SCORE GAUGE (SVG circle) === */
    .score-gauge {{ position: relative; display: inline-block; }}
    .score-gauge svg {{ transform: rotate(-90deg); }}
    .score-gauge .gauge-val {{
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 0.8rem;
    }}

    /* === MINI SPARKLINE === */
    .sparkline {{ display: inline-block; vertical-align: middle; }}

    /* === EXPAND ROW === */
    .expand-row {{ display: none; }}
    .expand-row.show {{ display: table-row; }}
    .expand-content {{
        background: rgba(15, 23, 42, 0.5);
        padding: 20px;
        border-bottom: 1px solid var(--border);
    }}
    .expand-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 20px;
    }}
    .expand-section-title {{
        font-size: 0.75rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 12px;
        font-weight: 600;
    }}
    .ind-list {{ display: flex; flex-direction: column; gap: 6px; }}
    .ind-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0;
        font-size: 0.8rem;
    }}
    .ind-row-label {{ color: var(--text-secondary); }}
    .ind-row-value {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; }}

    /* === PORTFOLIO TABLE === */
    .portfolio-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-bottom: 24px;
    }}
    .pf-card {{
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }}
    .pf-value {{ font-size: 1.5rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
    .pf-label {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; }}

    /* === WEIGHT BAR === */
    .weight-bar {{
        height: 6px;
        background: rgba(30, 41, 59, 0.5);
        border-radius: 3px;
        overflow: hidden;
        margin-top: 4px;
    }}
    .weight-bar-fill {{
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }}

    /* === AI REPORT === */
    .ai-report {{
        line-height: 1.9;
        font-size: 0.9rem;
        color: var(--text-secondary);
    }}
    .ai-report h2 {{
        color: var(--text-primary);
        font-size: 1.2rem;
        margin: 28px 0 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .ai-report h3 {{
        color: var(--accent-blue);
        font-size: 1rem;
        margin: 20px 0 8px;
    }}
    .ai-report strong {{ color: var(--text-primary); }}
    .ai-report ul, .ai-report ol {{ padding-left: 20px; margin: 8px 0; }}
    .ai-report li {{ margin-bottom: 4px; }}
    .ai-report p {{ margin: 8px 0; }}
    .ai-report hr {{ border: none; border-top: 1px solid var(--border); margin: 24px 0; }}
    .ai-report code {{
        background: rgba(59, 130, 246, 0.1);
        padding: 2px 6px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85em;
        color: var(--accent-blue);
    }}
    .ai-report table {{
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0;
        font-size: 0.85rem;
    }}
    .ai-report table th, .ai-report table td {{
        padding: 8px 12px;
        border: 1px solid var(--border);
        text-align: left;
    }}
    .ai-report table th {{
        background: rgba(15, 23, 42, 0.5);
        color: var(--text-primary);
        font-weight: 600;
    }}

    /* === PAGINATION === */
    .pagination {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        font-size: 0.85rem;
    }}
    .pagination-info {{ color: var(--text-muted); font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }}
    .pagination-btns {{ display: flex; gap: 4px; }}
    .pg-btn {{
        padding: 6px 12px;
        border: 1px solid var(--border);
        background: transparent;
        color: var(--text-secondary);
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
    }}
    .pg-btn:hover, .pg-btn.active {{
        background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
        color: #fff;
        border-color: transparent;
    }}
    .pg-btn:disabled {{ opacity: 0.3; cursor: default; }}

    /* === UTILITY === */
    .c-green {{ color: var(--accent-green); }}
    .c-red {{ color: var(--accent-red); }}
    .c-blue {{ color: var(--accent-blue); }}
    .c-purple {{ color: var(--accent-purple); }}
    .c-yellow {{ color: var(--accent-yellow); }}
    .c-cyan {{ color: var(--accent-cyan); }}
    .c-muted {{ color: var(--text-muted); }}

    /* === CHANNEL BADGE === */
    .ch-badge {{
        display: inline-block;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }}
    .ch-green {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }}
    .ch-gray {{ background: rgba(148, 163, 184, 0.1); color: var(--text-secondary); }}
    .ch-red {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }}

    /* === RSI BAR === */
    .rsi-bar {{
        width: 50px; height: 4px;
        background: rgba(30,41,59,0.5);
        border-radius: 2px;
        display: inline-block;
        vertical-align: middle;
        margin-left: 6px;
        overflow: hidden;
    }}
    .rsi-bar-fill {{
        height: 100%;
        border-radius: 2px;
    }}

    /* === HEATMAP === */
    .heatmap {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(85px, 1fr));
        gap: 4px;
    }}
    .heatmap-cell {{
        padding: 10px 4px;
        border-radius: 8px;
        text-align: center;
        cursor: pointer;
        transition: all 0.15s;
        font-family: 'JetBrains Mono', monospace;
    }}
    .heatmap-cell:hover {{ transform: scale(1.08); z-index: 1; }}
    .hm-sym {{ font-weight: 700; font-size: 0.8rem; }}
    .hm-val {{ font-size: 0.65rem; opacity: 0.8; margin-top: 2px; }}

    /* === RESPONSIVE === */
    @media (max-width: 900px) {{
        .signal-summary {{ grid-template-columns: repeat(3, 1fr); }}
        .expand-grid {{ grid-template-columns: 1fr; }}
        .tabs {{ overflow-x: auto; }}
    }}
    @media (max-width: 640px) {{
        .main {{ padding: 12px; }}
        .signal-summary {{ grid-template-columns: repeat(2, 1fr); }}
        .stat-row {{ grid-template-columns: repeat(2, 1fr); }}
        .header-inner {{ flex-direction: column; text-align: center; }}
        .header-search {{ max-width: 100%; }}
    }}
    </style>
</head>
<body>

<!-- MARKET TICKER -->
<div class="ticker-bar">
    <div class="ticker-track" id="tickerTrack"></div>
</div>

<!-- HEADER -->
<div class="header">
    <div class="header-inner">
        <div class="logo">
            <div class="logo-icon">VS</div>
            <div>
                <div class="logo-text">VN Stock Sniper</div>
                <div class="logo-sub">Phan tich ky thuat & AI</div>
            </div>
        </div>
        <div class="header-search">
            <input type="text" id="globalSearch" placeholder="Tim kiem ma co phieu..." autocomplete="off">
        </div>
        <div class="header-right">
            <div class="header-time">{self.today}</div>
            <div class="header-badge">{stats['total']} co phieu</div>
        </div>
    </div>
</div>

<div class="main">

<!-- TABS -->
<div class="tabs" id="mainTabs">
    <button class="tab active" data-tab="overview">Tong quan</button>
    <button class="tab" data-tab="screener">Bo Loc Tin Hieu</button>
    <button class="tab" data-tab="ai-report">Khuyen Nghi AI</button>
</div>

<!-- ==================== TAB 1: TONG QUAN ==================== -->
<div class="tab-panel active" id="panel-overview">

    <!-- Signal Summary Cards -->
    <div class="signal-summary">
        <div class="signal-summary-card ssc-buy-strong" onclick="filterBySignal('MUA MANH')">
            <div class="ssc-count c-green">{stats['buy_strong']}</div>
            <div class="ssc-label">MUA MANH</div>
        </div>
        <div class="signal-summary-card ssc-buy" onclick="filterBySignal('MUA')">
            <div class="ssc-count c-green" style="opacity:0.8">{stats['buy']}</div>
            <div class="ssc-label">MUA</div>
        </div>
        <div class="signal-summary-card ssc-neutral" onclick="filterBySignal('TRUNG LAP')">
            <div class="ssc-count" style="color:var(--text-secondary)">{stats['neutral']}</div>
            <div class="ssc-label">TRUNG LAP</div>
        </div>
        <div class="signal-summary-card ssc-sell" onclick="filterBySignal('BAN')">
            <div class="ssc-count" style="color:var(--accent-orange)">{stats['sell']}</div>
            <div class="ssc-label">BAN</div>
        </div>
        <div class="signal-summary-card ssc-sell-strong" onclick="filterBySignal('BAN MANH')">
            <div class="ssc-count c-red">{stats['sell_strong']}</div>
            <div class="ssc-label">BAN MANH</div>
        </div>
    </div>

    <!-- Stat Cards -->
    <div class="stat-row">
        <div class="stat-card">
            <div class="stat-card-label">Kenh Xanh (Uptrend)</div>
            <div class="stat-card-value c-green">{stats['uptrend']}</div>
            <div class="stat-card-sub">{round(stats['uptrend']/max(stats['total'],1)*100,1)}% thi truong</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Kenh Xam (Sideways)</div>
            <div class="stat-card-value" style="color:var(--text-secondary)">{stats['sideways']}</div>
            <div class="stat-card-sub">{round(stats['sideways']/max(stats['total'],1)*100,1)}% thi truong</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Kenh Do (Downtrend)</div>
            <div class="stat-card-value c-red">{stats['downtrend']}</div>
            <div class="stat-card-sub">{round(stats['downtrend']/max(stats['total'],1)*100,1)}% thi truong</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">Diem Trung binh</div>
            <div class="stat-card-value c-blue">{stats['avg_score']}</div>
            <div class="stat-card-sub">/ 40 diem</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-label">RSI Trung binh</div>
            <div class="stat-card-value" style="color:{'var(--accent-red)' if stats['avg_rsi'] > 70 else 'var(--accent-green)' if stats['avg_rsi'] < 30 else 'var(--text-primary)'}">{stats['avg_rsi']}</div>
            <div class="stat-card-sub">{'Qua mua' if stats['avg_rsi'] > 70 else 'Qua ban' if stats['avg_rsi'] < 30 else 'Trung tinh'}</div>
        </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-grid">
        <div class="section" style="margin-bottom:0">
            <div class="section-header"><div class="section-title">Phan bo Kenh</div></div>
            <div class="section-body" style="display:flex;justify-content:center;">
                <div style="width:240px;height:240px;"><canvas id="channelChart"></canvas></div>
            </div>
        </div>
        <div class="section" style="margin-bottom:0">
            <div class="section-header"><div class="section-title">Phan bo Tin hieu</div></div>
            <div class="section-body" style="display:flex;justify-content:center;">
                <div style="width:240px;height:240px;"><canvas id="signalDistChart"></canvas></div>
            </div>
        </div>
        <div class="section" style="margin-bottom:0">
            <div class="section-header"><div class="section-title">Khuyen nghi</div></div>
            <div class="section-body" style="display:flex;justify-content:center;">
                <div style="width:240px;height:240px;"><canvas id="recoChart"></canvas></div>
            </div>
        </div>
    </div>

    <!-- Heatmap -->
    <div class="section">
        <div class="section-header">
            <div class="section-title">Heatmap theo Diem</div>
            <div class="filters" id="heatmapFilters">
                <button class="filter-pill active" data-hm="score">Diem</button>
                <button class="filter-pill" data-hm="rsi">RSI</button>
                <button class="filter-pill" data-hm="volume">Volume</button>
            </div>
        </div>
        <div class="section-body">
            <div class="heatmap" id="heatmapGrid"></div>
        </div>
    </div>

    <!-- Portfolio -->
    <div class="section">
        <div class="section-header">
            <div class="section-title">Portfolio</div>
        </div>
        <div class="section-body">
            <div class="portfolio-grid">
                <div class="pf-card">
                    <div class="pf-value c-blue">{self.portfolio.get('cash_percent', 100)}%</div>
                    <div class="pf-label">Tien mat</div>
                </div>
                <div class="pf-card">
                    <div class="pf-value {'c-green' if total_pnl >= 0 else 'c-red'}">{'+'if total_pnl >= 0 else ''}{total_pnl:.2f}%</div>
                    <div class="pf-label">Tong P&L</div>
                </div>
                <div class="pf-card">
                    <div class="pf-value">{len(positions)}</div>
                    <div class="pf-label">Vi the</div>
                </div>
            </div>
            {self._generate_portfolio_html(positions)}
        </div>
    </div>

</div>

<!-- ==================== TAB 2: BO LOC TIN HIEU ==================== -->
<div class="tab-panel" id="panel-screener">

    <!-- Signal Filter Pills -->
    <div style="margin-bottom:20px;">
        <div class="filters" id="screenerFilters">
            <button class="filter-pill active" data-sf="all">Tat ca<span class="cnt">{stats['total']}</span></button>
            <button class="filter-pill" data-sf="MUA MANH">MUA MANH<span class="cnt">{stats['buy_strong']}</span></button>
            <button class="filter-pill" data-sf="MUA">MUA<span class="cnt">{stats['buy']}</span></button>
            <button class="filter-pill" data-sf="TRUNG LAP">TRUNG LAP<span class="cnt">{stats['neutral']}</span></button>
            <button class="filter-pill" data-sf="BAN">BAN<span class="cnt">{stats['sell']}</span></button>
            <button class="filter-pill" data-sf="BAN MANH">BAN MANH<span class="cnt">{stats['sell_strong']}</span></button>
        </div>
    </div>

    <!-- Screener Table -->
    <div class="section">
        <div style="overflow-x:auto;">
            <table class="screener-table" id="screenerTable">
                <thead>
                    <tr>
                        <th data-sort="index" style="width:40px">#</th>
                        <th data-sort="symbol">Ma</th>
                        <th data-sort="signal_label">Khuyen nghi</th>
                        <th data-sort="close">Gia</th>
                        <th data-sort="score_100">Diem</th>
                        <th data-sort="rsi">RSI</th>
                        <th data-sort="channel">Kenh</th>
                        <th data-sort="vol_ratio">Vol</th>
                        <th data-sort="buy_signal">Tin hieu</th>
                        <th style="width:60px">Chi tiet</th>
                    </tr>
                </thead>
                <tbody id="screenerBody"></tbody>
            </table>
        </div>
        <div class="pagination">
            <div class="pagination-info" id="pageInfo"></div>
            <div class="pagination-btns" id="pageBtns"></div>
        </div>
    </div>
</div>

<!-- ==================== TAB 3: KHUYEN NGHI AI ==================== -->
<div class="tab-panel" id="panel-ai-report">
    <div class="section">
        <div class="section-header">
            <div class="section-title">Bao cao Phan tich AI</div>
            <div class="header-time">Claude Sonnet 4.5</div>
        </div>
        <div class="section-body">
            <div class="ai-report" id="aiReportContent"></div>
        </div>
    </div>
</div>

</div><!-- end main -->

<script>
// ===========================
// DATA
// ===========================
const ALL_STOCKS = {json.dumps(clean_stocks, ensure_ascii=False, default=str)};
const AI_REPORT = `{ai_report_escaped}`;

// ===========================
// STATE
// ===========================
let currentTab = 'overview';
let screenerFilter = 'all';
let heatmapMode = 'score';
let sortCol = 'score_100';
let sortDir = 'desc';
let currentPage = 1;
const PAGE_SIZE = 20;
let expandedRow = null;

// ===========================
// UTILS
// ===========================
const n = v => Number(v || 0);
const f1 = v => n(v).toFixed(1);
const f2 = v => n(v).toFixed(2);
const loc = v => n(v).toLocaleString('vi-VN');

function getSignalBadge(label) {{
    if (!label) label = 'TRUNG LAP';
    const cls = {{
        'MUA MANH': 'signal-mua-manh',
        'MUA': 'signal-mua',
        'TRUNG LAP': 'signal-trung-lap',
        'BAN': 'signal-ban',
        'BAN MANH': 'signal-ban-manh'
    }}[label] || 'signal-trung-lap';
    return '<span class="signal-badge ' + cls + '">' + label + '</span>';
}}

function getTypeBadge(sig) {{
    if (!sig) return '<span class="c-muted">-</span>';
    const cls = {{'BREAKOUT':'type-breakout','MOMENTUM':'type-momentum','PULLBACK':'type-pullback','REVERSAL':'type-reversal'}}[sig] || '';
    return '<span class="type-badge ' + cls + '">' + sig + '</span>';
}}

function getChannelBadge(ch) {{
    if (!ch) return '<span class="ch-badge ch-gray">-</span>';
    if (ch.includes('XANH')) return '<span class="ch-badge ch-green">XANH</span>';
    if (ch.includes('ĐỎ') || ch.includes('DO')) return '<span class="ch-badge ch-red">DO</span>';
    return '<span class="ch-badge ch-gray">XAM</span>';
}}

function getRsiColor(rsi) {{
    if (rsi > 70) return 'var(--accent-red)';
    if (rsi < 30) return 'var(--accent-green)';
    return 'var(--text-primary)';
}}

function getScoreColor(score) {{
    if (score >= 70) return 'var(--accent-green)';
    if (score >= 45) return 'var(--accent-blue)';
    if (score >= 25) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
}}

// SVG Score Gauge
function renderGauge(score, size) {{
    size = size || 44;
    const r = (size - 6) / 2;
    const circ = 2 * Math.PI * r;
    const pct = Math.min(Math.max(score, 0), 100);
    const offset = circ * (1 - pct / 100);
    const color = getScoreColor(pct);
    return `<div class="score-gauge" style="width:${{size}}px;height:${{size}}px">
        <svg width="${{size}}" height="${{size}}" viewBox="0 0 ${{size}} ${{size}}">
            <circle cx="${{size/2}}" cy="${{size/2}}" r="${{r}}" fill="none" stroke="rgba(30,41,59,0.5)" stroke-width="4"/>
            <circle cx="${{size/2}}" cy="${{size/2}}" r="${{r}}" fill="none" stroke="${{color}}" stroke-width="4"
                stroke-dasharray="${{circ}}" stroke-dashoffset="${{offset}}" stroke-linecap="round"
                style="transition:stroke-dashoffset 0.8s ease"/>
        </svg>
        <span class="gauge-val" style="color:${{color}};font-size:${{size < 40 ? 0.65 : 0.8}}rem">${{Math.round(pct)}}</span>
    </div>`;
}}

// RSI bar
function renderRsiBar(rsi) {{
    const w = Math.min(n(rsi), 100);
    const color = rsi > 70 ? 'var(--accent-red)' : rsi < 30 ? 'var(--accent-green)' : 'var(--accent-blue)';
    return `<span class="mono" style="color:${{getRsiColor(rsi)}}">${{f1(rsi)}}</span>
        <span class="rsi-bar"><span class="rsi-bar-fill" style="width:${{w}}%;background:${{color}}"></span></span>`;
}}

// ===========================
// TABS
// ===========================
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
    if (currentTab === 'overview') {{ renderHeatmap(); }}
    else if (currentTab === 'screener') {{ renderScreener(); }}
    else if (currentTab === 'ai-report') {{ renderAIReport(); }}
}}

// ===========================
// MARKET TICKER
// ===========================
function initTicker() {{
    const top = [...ALL_STOCKS].sort((a, b) => n(b.total_score) - n(a.total_score)).slice(0, 20);
    if (top.length === 0) return;
    const track = document.getElementById('tickerTrack');
    let html = '';
    // Duplicate for infinite scroll
    for (let rep = 0; rep < 3; rep++) {{
        top.forEach(s => {{
            const score = n(s.score_100);
            const color = score >= 55 ? 'var(--accent-green)' : score <= 25 ? 'var(--accent-red)' : 'var(--text-secondary)';
            html += `<div class="ticker-item">
                <span class="ticker-symbol">${{s.symbol}}</span>
                <span class="ticker-price">${{loc(s.close)}}</span>
                <span style="color:${{color}};font-size:0.75rem;font-family:'JetBrains Mono',monospace">${{Math.round(score)}}pt</span>
            </div>`;
        }});
    }}
    track.innerHTML = html;
}}

// ===========================
// HEATMAP
// ===========================
document.querySelectorAll('#heatmapFilters .filter-pill').forEach(pill => {{
    pill.addEventListener('click', () => {{
        document.querySelectorAll('#heatmapFilters .filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        heatmapMode = pill.dataset.hm;
        renderHeatmap();
    }});
}});

function renderHeatmap() {{
    const container = document.getElementById('heatmapGrid');
    const stocks = [...ALL_STOCKS].sort((a, b) => n(b.total_score) - n(a.total_score));
    if (stocks.length === 0) {{
        container.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)">Chua co du lieu</div>';
        return;
    }}

    container.innerHTML = stocks.map(s => {{
        let val, maxVal, label;
        if (heatmapMode === 'rsi') {{
            val = n(s.rsi); maxVal = 100; label = f1(val);
        }} else if (heatmapMode === 'volume') {{
            val = Math.min(n(s.vol_ratio), 3); maxVal = 3; label = f1(s.vol_ratio) + 'x';
        }} else {{
            val = n(s.score_100); maxVal = 100; label = Math.round(val) + 'pt';
        }}

        let bgColor;
        if (heatmapMode === 'rsi') {{
            bgColor = val > 70 ? 'rgba(239,68,68,0.45)' : val > 60 ? 'rgba(239,68,68,0.2)' : val < 30 ? 'rgba(16,185,129,0.45)' : val < 40 ? 'rgba(16,185,129,0.2)' : 'rgba(59,130,246,0.15)';
        }} else {{
            const ratio = Math.min(val / maxVal, 1);
            bgColor = ratio > 0.6 ? 'rgba(16,185,129,' + (0.15 + ratio * 0.35) + ')' : ratio > 0.3 ? 'rgba(59,130,246,' + (0.1 + ratio * 0.25) + ')' : 'rgba(148,163,184,' + (0.05 + ratio * 0.12) + ')';
        }}

        return `<div class="heatmap-cell" style="background:${{bgColor}}" onclick="goToScreener('${{s.symbol}}')">
            <div class="hm-sym">${{s.symbol}}</div>
            <div class="hm-val">${{label}}</div>
        </div>`;
    }}).join('');
}}

function goToScreener(symbol) {{
    // Switch to screener tab and search for symbol
    document.getElementById('globalSearch').value = symbol;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    currentTab = 'screener';
    document.querySelector('[data-tab="screener"]').classList.add('active');
    document.getElementById('panel-screener').classList.add('active');
    currentPage = 1;
    renderScreener();
}}

function filterBySignal(label) {{
    // Switch to screener tab with filter
    screenerFilter = label;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    currentTab = 'screener';
    document.querySelector('[data-tab="screener"]').classList.add('active');
    document.getElementById('panel-screener').classList.add('active');
    // Update filter pills
    document.querySelectorAll('#screenerFilters .filter-pill').forEach(p => {{
        p.classList.remove('active');
        if (p.dataset.sf === label) p.classList.add('active');
    }});
    currentPage = 1;
    renderScreener();
}}

// ===========================
// SCREENER TABLE
// ===========================
document.querySelectorAll('#screenerFilters .filter-pill').forEach(pill => {{
    pill.addEventListener('click', () => {{
        document.querySelectorAll('#screenerFilters .filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        screenerFilter = pill.dataset.sf;
        currentPage = 1;
        expandedRow = null;
        renderScreener();
    }});
}});

function renderScreener() {{
    let stocks = [...ALL_STOCKS];

    // Filter by signal
    if (screenerFilter !== 'all') {{
        stocks = stocks.filter(s => s.signal_label === screenerFilter);
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
        if (typeof va === 'number' || typeof vb === 'number') {{ va = n(va); vb = n(vb); }}
        if (sortDir === 'asc') return va > vb ? 1 : va < vb ? -1 : 0;
        return va < vb ? 1 : va > vb ? -1 : 0;
    }});

    // Pagination
    const total = stocks.length;
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    if (currentPage > totalPages) currentPage = totalPages;
    const start = (currentPage - 1) * PAGE_SIZE;
    const pageStocks = stocks.slice(start, start + PAGE_SIZE);

    const tbody = document.getElementById('screenerBody');
    let html = '';

    pageStocks.forEach((s, i) => {{
        const idx = start + i + 1;
        const isExpanded = expandedRow === s.symbol;

        html += `<tr onclick="toggleExpand('${{s.symbol}}')" class="${{isExpanded ? 'expanded-parent' : ''}}">
            <td class="c-muted mono">${{idx}}</td>
            <td class="stock-name">${{s.symbol}}</td>
            <td>${{getSignalBadge(s.signal_label)}}</td>
            <td class="mono">${{loc(s.close)}}</td>
            <td>${{renderGauge(n(s.score_100), 40)}}</td>
            <td>${{renderRsiBar(n(s.rsi))}}</td>
            <td>${{getChannelBadge(s.channel)}}</td>
            <td class="mono" style="color:${{n(s.vol_ratio) > 1.5 ? 'var(--accent-green)' : 'var(--text-primary)'}}">${{f1(s.vol_ratio)}}x</td>
            <td>${{getTypeBadge(s.buy_signal)}}</td>
            <td style="text-align:center;color:var(--text-muted);font-size:0.9rem">${{isExpanded ? '&#9650;' : '&#9660;'}}</td>
        </tr>`;

        // Expandable detail row
        html += `<tr class="expand-row ${{isExpanded ? 'show' : ''}}" id="expand-${{s.symbol}}">
            <td colspan="10" style="padding:0">
                <div class="expand-content">
                    <div class="expand-grid">
                        <div>
                            <div class="expand-section-title">Chi bao Ky thuat</div>
                            <div class="ind-list">
                                <div class="ind-row"><span class="ind-row-label">RSI (14)</span><span class="ind-row-value" style="color:${{getRsiColor(n(s.rsi))}}">${{f1(s.rsi)}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">MFI</span><span class="ind-row-value" style="color:${{n(s.mfi) > 50 ? 'var(--accent-green)' : 'var(--accent-red)'}}">${{f1(s.mfi)}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">MACD</span><span class="ind-row-value" style="color:${{s.macd_bullish ? 'var(--accent-green)' : 'var(--accent-red)'}}">${{s.macd_bullish ? 'Bullish' : 'Bearish'}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">Stoch K/D</span><span class="ind-row-value">${{f1(s.stoch_k)}} / ${{f1(s.stoch_d)}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">BB %</span><span class="ind-row-value">${{f1(s.bb_percent)}}%</span></div>
                                <div class="ind-row"><span class="ind-row-label">ATR %</span><span class="ind-row-value">${{f2(s.atr_percent)}}%</span></div>
                                <div class="ind-row"><span class="ind-row-label">Vol Ratio</span><span class="ind-row-value" style="color:${{n(s.vol_ratio) > 1.5 ? 'var(--accent-green)' : 'var(--text-primary)'}}">${{f2(s.vol_ratio)}}x</span></div>
                                <div class="ind-row"><span class="ind-row-label">OBV</span><span class="ind-row-value" style="color:${{s.obv_rising ? 'var(--accent-green)' : 'var(--accent-red)'}}">${{s.obv_rising ? 'Tang' : 'Giam'}}</span></div>
                            </div>
                        </div>
                        <div>
                            <div class="expand-section-title">Xu huong & Kenh gia</div>
                            <div class="ind-list">
                                <div class="ind-row"><span class="ind-row-label">LR Slope</span><span class="ind-row-value">${{f2(s.lr_slope_pct)}}%</span></div>
                                <div class="ind-row"><span class="ind-row-label">Channel Pos</span><span class="ind-row-value">${{f1(s.channel_position)}}%</span></div>
                                <div class="ind-row"><span class="ind-row-label">MA Aligned</span><span class="ind-row-value" style="color:${{s.ma_aligned ? 'var(--accent-green)' : 'var(--accent-red)'}}">${{s.ma_aligned ? 'Co' : 'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">Above MA200</span><span class="ind-row-value" style="color:${{s.above_ma200 ? 'var(--accent-green)' : 'var(--accent-red)'}}">${{s.above_ma200 ? 'Co' : 'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">Above MA50</span><span class="ind-row-value" style="color:${{s.above_ma50 ? 'var(--accent-green)' : 'var(--accent-red)'}}">${{s.above_ma50 ? 'Co' : 'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">BB Squeeze</span><span class="ind-row-value" style="color:${{s.bb_squeeze ? 'var(--accent-yellow)' : 'var(--text-muted)'}}">${{s.bb_squeeze ? 'Co' : 'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">Breakout 20D</span><span class="ind-row-value" style="color:${{s.breakout_20 ? 'var(--accent-green)' : 'var(--text-muted)'}}">${{s.breakout_20 ? 'Co' : 'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">Breakout 50D</span><span class="ind-row-value" style="color:${{s.breakout_50 ? 'var(--accent-green)' : 'var(--text-muted)'}}">${{s.breakout_50 ? 'Co' : 'Khong'}}</span></div>
                            </div>
                        </div>
                        <div>
                            <div class="expand-section-title">Diem so & Ho tro / Khang cu</div>
                            <div class="ind-list">
                                <div class="ind-row"><span class="ind-row-label">Quality Score</span><span class="ind-row-value c-blue">${{f1(s.quality_score)}} / 25</span></div>
                                <div class="ind-row"><span class="ind-row-label">Momentum Score</span><span class="ind-row-value c-purple">${{f1(s.momentum_score)}} / 15</span></div>
                                <div class="ind-row"><span class="ind-row-label">Tong diem</span><span class="ind-row-value c-green">${{f1(s.total_score)}} / 40</span></div>
                                <div class="ind-row"><span class="ind-row-label">Support</span><span class="ind-row-value c-green">${{loc(s.support)}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">Resistance</span><span class="ind-row-value c-red">${{loc(s.resistance)}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">BB Lower</span><span class="ind-row-value c-green">${{loc(s.bb_lower)}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">BB Upper</span><span class="ind-row-value c-red">${{loc(s.bb_upper)}}</span></div>
                                <div class="ind-row"><span class="ind-row-label">BB Width</span><span class="ind-row-value">${{f2(s.bb_width)}}%</span></div>
                            </div>
                        </div>
                    </div>
                    <div style="margin-top:16px;text-align:center">
                        <canvas id="radar-${{s.symbol}}" width="260" height="200"></canvas>
                    </div>
                </div>
            </td>
        </tr>`;
    }});

    tbody.innerHTML = html;

    // Draw radar chart for expanded row
    if (expandedRow) {{
        const s = ALL_STOCKS.find(x => x.symbol === expandedRow);
        if (s) drawRadar(s);
    }}

    // Update sort headers
    document.querySelectorAll('.screener-table thead th').forEach(th => {{
        th.classList.remove('sorted-asc', 'sorted-desc');
        if (th.dataset.sort === sortCol) th.classList.add('sorted-' + sortDir);
    }});

    // Pagination
    document.getElementById('pageInfo').textContent = total > 0 ? (start + 1) + '-' + Math.min(start + PAGE_SIZE, total) + ' / ' + total + ' ma' : '0 ma';

    const pageBtns = document.getElementById('pageBtns');
    let btns = '';
    btns += `<button class="pg-btn" onclick="goPage(1)" ${{currentPage === 1 ? 'disabled' : ''}}>&laquo;</button>`;
    btns += `<button class="pg-btn" onclick="goPage(${{currentPage-1}})" ${{currentPage === 1 ? 'disabled' : ''}}>&lsaquo;</button>`;
    let sp = Math.max(1, currentPage - 2);
    let ep = Math.min(totalPages, currentPage + 2);
    for (let p = sp; p <= ep; p++) {{
        btns += `<button class="pg-btn ${{p === currentPage ? 'active' : ''}}" onclick="goPage(${{p}})">${{p}}</button>`;
    }}
    btns += `<button class="pg-btn" onclick="goPage(${{currentPage+1}})" ${{currentPage === totalPages ? 'disabled' : ''}}>&rsaquo;</button>`;
    btns += `<button class="pg-btn" onclick="goPage(${{totalPages}})" ${{currentPage === totalPages ? 'disabled' : ''}}>&raquo;</button>`;
    pageBtns.innerHTML = btns;
}}

function toggleExpand(symbol) {{
    expandedRow = expandedRow === symbol ? null : symbol;
    renderScreener();
}}

function goPage(p) {{
    currentPage = Math.max(1, p);
    expandedRow = null;
    renderScreener();
}}

// Table sorting
document.querySelectorAll('.screener-table thead th[data-sort]').forEach(th => {{
    th.addEventListener('click', (e) => {{
        e.stopPropagation();
        const col = th.dataset.sort;
        if (sortCol === col) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        else {{ sortCol = col; sortDir = 'desc'; }}
        currentPage = 1;
        expandedRow = null;
        renderScreener();
    }});
}});

// ===========================
// RADAR CHART
// ===========================
function drawRadar(stock) {{
    const canvas = document.getElementById('radar-' + stock.symbol);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const rsi_norm = Math.min(n(stock.rsi) / 100, 1);
    const mfi_norm = Math.min(n(stock.mfi) / 100, 1);
    const vol_norm = Math.min(n(stock.vol_ratio) / 3, 1);
    const q_norm = Math.min(n(stock.quality_score) / 25, 1);
    const m_norm = Math.min(n(stock.momentum_score) / 15, 1);
    const ch_norm = Math.min(n(stock.channel_position) / 100, 1);

    new Chart(ctx, {{
        type: 'radar',
        data: {{
            labels: ['RSI', 'MFI', 'Volume', 'Quality', 'Momentum', 'Channel'],
            datasets: [{{
                data: [rsi_norm * 100, mfi_norm * 100, vol_norm * 100, q_norm * 100, m_norm * 100, ch_norm * 100],
                backgroundColor: 'rgba(59, 130, 246, 0.15)',
                borderColor: 'rgba(59, 130, 246, 0.8)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(59, 130, 246, 1)',
                pointRadius: 3,
            }}]
        }},
        options: {{
            responsive: false,
            maintainAspectRatio: false,
            scales: {{
                r: {{
                    beginAtZero: true,
                    max: 100,
                    ticks: {{ display: false }},
                    grid: {{ color: 'rgba(30, 41, 59, 0.5)' }},
                    angleLines: {{ color: 'rgba(30, 41, 59, 0.5)' }},
                    pointLabels: {{
                        color: '#94a3b8',
                        font: {{ size: 10, family: "'JetBrains Mono', monospace" }}
                    }}
                }}
            }},
            plugins: {{ legend: {{ display: false }} }}
        }}
    }});
}}

// ===========================
// AI REPORT
// ===========================
function renderAIReport() {{
    const raw = AI_REPORT || 'Chua co bao cao AI. Chay pipeline de tao bao cao.';
    let html = raw
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        .replace(/^---$/gm, '<hr>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\\/li>\\n?)+/g, function(m) {{ return '<ul>' + m + '</ul>'; }})
        .replace(/\\n\\n/g, '</p><p>')
        .replace(/\\n/g, '<br>');
    html = '<p>' + html + '</p>';
    html = html.replace(/<p><h([23])>/g, '<h$1>').replace(/<\\/h([23])><\\/p>/g, '</h$1>');
    html = html.replace(/<p><hr><\\/p>/g, '<hr>');
    html = html.replace(/<p><ul>/g, '<ul>').replace(/<\\/ul><\\/p>/g, '</ul>');
    document.getElementById('aiReportContent').innerHTML = html;
}}

// ===========================
// SEARCH
// ===========================
document.getElementById('globalSearch').addEventListener('input', function() {{
    if (currentTab !== 'screener') {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        currentTab = 'screener';
        document.querySelector('[data-tab="screener"]').classList.add('active');
        document.getElementById('panel-screener').classList.add('active');
    }}
    currentPage = 1;
    expandedRow = null;
    renderScreener();
}});

// ===========================
// CHARTS
// ===========================
function initCharts() {{
    const chartOpts = {{
        responsive: true,
        maintainAspectRatio: true,
        cutout: '65%',
        plugins: {{
            legend: {{
                position: 'bottom',
                labels: {{
                    color: '#94a3b8',
                    padding: 12,
                    font: {{ size: 10, family: "'JetBrains Mono', monospace" }}
                }}
            }}
        }}
    }};

    // Channel distribution
    new Chart(document.getElementById('channelChart').getContext('2d'), {{
        type: 'doughnut',
        data: {{
            labels: ['Xanh', 'Xam', 'Do'],
            datasets: [{{
                data: [{stats['uptrend']}, {stats['sideways']}, {stats['downtrend']}],
                backgroundColor: ['#10b981', '#64748b', '#ef4444'],
                borderWidth: 0,
                borderRadius: 4
            }}]
        }},
        options: chartOpts
    }});

    // Signal type distribution
    new Chart(document.getElementById('signalDistChart').getContext('2d'), {{
        type: 'doughnut',
        data: {{
            labels: ['Breakout', 'Momentum', 'Pullback', 'Reversal'],
            datasets: [{{
                data: [{stats['breakout']}, {stats['momentum']}, {stats['pullback']}, {stats['reversal']}],
                backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6'],
                borderWidth: 0,
                borderRadius: 4
            }}]
        }},
        options: chartOpts
    }});

    // Recommendation distribution
    new Chart(document.getElementById('recoChart').getContext('2d'), {{
        type: 'doughnut',
        data: {{
            labels: ['MUA MANH', 'MUA', 'TRUNG LAP', 'BAN', 'BAN MANH'],
            datasets: [{{
                data: [{stats['buy_strong']}, {stats['buy']}, {stats['neutral']}, {stats['sell']}, {stats['sell_strong']}],
                backgroundColor: ['#10b981', '#34d399', '#64748b', '#f97316', '#ef4444'],
                borderWidth: 0,
                borderRadius: 4
            }}]
        }},
        options: chartOpts
    }});
}}

// ===========================
// INIT
// ===========================
document.addEventListener('DOMContentLoaded', function() {{
    initTicker();
    initCharts();
    renderHeatmap();
    renderAIReport();
}});
</script>

</body>
</html>'''

        return html

    def _generate_portfolio_html(self, positions):
        if not positions:
            return '<div style="text-align:center;padding:30px;color:var(--text-muted)">Chua co vi the nao trong portfolio.</div>'

        html = '<div style="overflow-x:auto"><table class="screener-table"><thead><tr><th>Ma</th><th>So CP</th><th>Gia mua</th><th>Gia hien tai</th><th>P&L</th><th>Ty trong</th></tr></thead><tbody>'

        total_value = sum(pos.get('quantity', 0) * pos.get('current_price', pos.get('entry_price', 0)) for pos in positions)

        for pos in positions:
            symbol = pos.get('symbol', '')
            qty = pos.get('quantity', 0)
            entry = pos.get('entry_price', 0)
            current = pos.get('current_price', entry)
            pnl = pos.get('pnl_percent', 0)
            pnl_cls = 'c-green' if pnl >= 0 else 'c-red'
            pnl_sign = '+' if pnl >= 0 else ''
            weight = round(qty * current / total_value * 100, 1) if total_value > 0 else 0

            html += f'''<tr>
                <td class="stock-name">{symbol}</td>
                <td class="mono">{qty:,}</td>
                <td class="mono">{entry:,.0f}</td>
                <td class="mono">{current:,.0f}</td>
                <td class="mono {pnl_cls}">{pnl_sign}{pnl:.2f}%</td>
                <td>
                    <span class="mono">{weight}%</span>
                    <div class="weight-bar"><div class="weight-bar-fill" style="width:{weight}%;background:var(--accent-blue)"></div></div>
                </td>
            </tr>'''

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
        print("TẠO DASHBOARD V6")
        print("=" * 60)
        self.save_dashboard()


if __name__ == "__main__":
    generator = DashboardGenerator()
    generator.run()
