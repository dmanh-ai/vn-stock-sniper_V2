"""
VN Stock Sniper - Dashboard Generator V7
Professional Financial Dashboard - Bloomberg/TradingView inspired
Tabs: Tong Quan | Bo Loc Co Phieu | Portfolio | Khuyen Nghi AI
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
    """Generate V7 Professional Financial Dashboard"""

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
                'advance': 0, 'decline': 0, 'unchanged': 0,
            }

        df = self.analyzed_df
        total = len(df)
        uptrend = len(df[df['channel'].str.contains('XANH', na=False)])
        sideways = len(df[df['channel'].str.contains('XÁM', na=False)])
        downtrend = len(df[df['channel'].str.contains('ĐỎ', na=False)])

        # Advance/Decline
        advance = 0
        decline = 0
        unchanged = 0
        if 'change_pct' in df.columns:
            advance = len(df[df['change_pct'] > 0])
            decline = len(df[df['change_pct'] < 0])
            unchanged = len(df[df['change_pct'] == 0])
        elif 'close' in df.columns and 'open' in df.columns:
            advance = len(df[df['close'] > df['open']])
            decline = len(df[df['close'] < df['open']])
            unchanged = total - advance - decline

        signals_df = self.signals_df
        breakout = len(signals_df[signals_df['buy_signal'] == 'BREAKOUT']) if not signals_df.empty else 0
        momentum_sig = len(signals_df[signals_df['buy_signal'] == 'MOMENTUM']) if not signals_df.empty else 0
        pullback = len(signals_df[signals_df['buy_signal'] == 'PULLBACK']) if not signals_df.empty else 0
        reversal = len(signals_df[signals_df['buy_signal'] == 'REVERSAL']) if not signals_df.empty else 0

        buy_strong = buy = neutral = sell = sell_strong = 0
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
            'advance': advance,
            'decline': decline,
            'unchanged': unchanged,
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

        for stock in clean_stocks:
            stock['signal_label'] = get_signal_label(stock)
            stock['score_100'] = round(safe_float(stock.get('total_score', 0)) / 40 * 100, 0)

        ai_report_escaped = self.ai_report.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') if self.ai_report else ''

        # Top gainers / losers for overview
        sorted_by_score = sorted(clean_stocks, key=lambda x: safe_float(x.get('total_score', 0)), reverse=True)
        top_buy_signals = [s for s in clean_stocks if s.get('signal_label') in ('MUA MANH', 'MUA')][:10]

        html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VN Stock Sniper - Professional Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
{self._generate_css()}
    </style>
</head>
<body>

<!-- ===== MARKET INDICES BAR ===== -->
<div class="indices-bar">
    <div class="indices-bar-inner">
        <div class="index-item" id="idx-vnindex">
            <span class="idx-name">VNINDEX</span>
            <span class="idx-value" id="idx-vnindex-val">--</span>
            <span class="idx-change" id="idx-vnindex-chg">--</span>
        </div>
        <div class="idx-sep"></div>
        <div class="index-item" id="idx-hnx">
            <span class="idx-name">HNX-INDEX</span>
            <span class="idx-value" id="idx-hnx-val">--</span>
            <span class="idx-change" id="idx-hnx-chg">--</span>
        </div>
        <div class="idx-sep"></div>
        <div class="index-item" id="idx-vn30">
            <span class="idx-name">VN30</span>
            <span class="idx-value" id="idx-vn30-val">--</span>
            <span class="idx-change" id="idx-vn30-chg">--</span>
        </div>
        <div class="idx-sep"></div>
        <div class="index-item" id="idx-upcom">
            <span class="idx-name">UPCOM</span>
            <span class="idx-value" id="idx-upcom-val">--</span>
            <span class="idx-change" id="idx-upcom-chg">--</span>
        </div>
        <div class="idx-sep"></div>
        <div class="index-item">
            <span class="idx-name">AD Ratio</span>
            <span class="idx-value" style="color:var(--green)">{stats['advance']}</span>
            <span style="color:var(--text-muted);">/</span>
            <span class="idx-value" style="color:var(--red)">{stats['decline']}</span>
        </div>
    </div>
</div>

<!-- ===== HEADER ===== -->
<header class="header">
    <div class="header-inner">
        <div class="header-left">
            <div class="logo">
                <div class="logo-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
                </div>
                <div>
                    <div class="logo-text">VN Stock Sniper</div>
                    <div class="logo-sub">Professional Market Analysis</div>
                </div>
            </div>
        </div>
        <div class="header-center">
            <nav class="nav-tabs" id="mainNav">
                <button class="nav-tab active" data-tab="overview">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
                    Tong Quan
                </button>
                <button class="nav-tab" data-tab="screener">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
                    Bo Loc Co Phieu
                </button>
                <button class="nav-tab" data-tab="portfolio">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                    Portfolio
                </button>
                <button class="nav-tab" data-tab="ai">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a5 5 0 0 1 5 5c0 2-1.5 3.5-3 4.5V14h-4v-2.5C8.5 10.5 7 9 7 7a5 5 0 0 1 5-5z"/><line x1="10" y1="17" x2="14" y2="17"/><line x1="10" y1="20" x2="14" y2="20"/></svg>
                    Khuyen Nghi AI
                </button>
            </nav>
        </div>
        <div class="header-right">
            <div class="search-box">
                <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input type="text" id="globalSearch" placeholder="Tim ma co phieu (VD: FPT, VNM...)" autocomplete="off">
            </div>
            <div class="header-meta">
                <span class="meta-badge">{stats['total']} co phieu</span>
                <span class="meta-time">{self.today}</span>
            </div>
        </div>
    </div>
</header>

<!-- ===== MAIN CONTENT ===== -->
<main class="main-content">

<!-- ==================== TAB: TONG QUAN ==================== -->
<div class="tab-panel active" id="panel-overview">

    <!-- KPI Cards Row -->
    <div class="kpi-row">
        <div class="kpi-card kpi-green">
            <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/></svg></div>
            <div class="kpi-data">
                <div class="kpi-value">{stats['uptrend']}</div>
                <div class="kpi-label">Uptrend</div>
            </div>
            <div class="kpi-pct">{round(stats['uptrend']/max(stats['total'],1)*100)}%</div>
        </div>
        <div class="kpi-card kpi-gray">
            <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg></div>
            <div class="kpi-data">
                <div class="kpi-value">{stats['sideways']}</div>
                <div class="kpi-label">Sideways</div>
            </div>
            <div class="kpi-pct">{round(stats['sideways']/max(stats['total'],1)*100)}%</div>
        </div>
        <div class="kpi-card kpi-red">
            <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/></svg></div>
            <div class="kpi-data">
                <div class="kpi-value">{stats['downtrend']}</div>
                <div class="kpi-label">Downtrend</div>
            </div>
            <div class="kpi-pct">{round(stats['downtrend']/max(stats['total'],1)*100)}%</div>
        </div>
        <div class="kpi-card kpi-blue">
            <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div>
            <div class="kpi-data">
                <div class="kpi-value">{stats['signals']}</div>
                <div class="kpi-label">Tin hieu</div>
            </div>
            <div class="kpi-pct">hom nay</div>
        </div>
        <div class="kpi-card kpi-purple">
            <div class="kpi-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg></div>
            <div class="kpi-data">
                <div class="kpi-value">{stats['avg_score']}</div>
                <div class="kpi-label">Diem TB</div>
            </div>
            <div class="kpi-pct">/ 40</div>
        </div>
    </div>

    <!-- Signal Summary Bar -->
    <div class="signal-bar">
        <div class="signal-bar-title">Phan bo Khuyen nghi</div>
        <div class="signal-bar-items">
            <div class="sbar-item sbar-buy-strong" onclick="filterBySignal('MUA MANH')">
                <span class="sbar-count">{stats['buy_strong']}</span>
                <span class="sbar-label">MUA MANH</span>
            </div>
            <div class="sbar-item sbar-buy" onclick="filterBySignal('MUA')">
                <span class="sbar-count">{stats['buy']}</span>
                <span class="sbar-label">MUA</span>
            </div>
            <div class="sbar-item sbar-neutral" onclick="filterBySignal('TRUNG LAP')">
                <span class="sbar-count">{stats['neutral']}</span>
                <span class="sbar-label">TRUNG LAP</span>
            </div>
            <div class="sbar-item sbar-sell" onclick="filterBySignal('BAN')">
                <span class="sbar-count">{stats['sell']}</span>
                <span class="sbar-label">BAN</span>
            </div>
            <div class="sbar-item sbar-sell-strong" onclick="filterBySignal('BAN MANH')">
                <span class="sbar-count">{stats['sell_strong']}</span>
                <span class="sbar-label">BAN MANH</span>
            </div>
        </div>
        <!-- Visual Bar -->
        <div class="signal-visual-bar">
            <div class="svb-seg svb-buy-strong" style="flex:{stats['buy_strong']}" title="MUA MANH: {stats['buy_strong']}"></div>
            <div class="svb-seg svb-buy" style="flex:{stats['buy']}" title="MUA: {stats['buy']}"></div>
            <div class="svb-seg svb-neutral" style="flex:{stats['neutral']}" title="TRUNG LAP: {stats['neutral']}"></div>
            <div class="svb-seg svb-sell" style="flex:{stats['sell']}" title="BAN: {stats['sell']}"></div>
            <div class="svb-seg svb-sell-strong" style="flex:{stats['sell_strong']}" title="BAN MANH: {stats['sell_strong']}"></div>
        </div>
    </div>

    <!-- Charts + Stats Grid -->
    <div class="overview-grid">
        <!-- Market Breadth -->
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">Do Rong Thi Truong</h3>
            </div>
            <div class="card-body" style="display:flex;justify-content:center;padding:20px;">
                <div style="width:220px;height:220px;position:relative;">
                    <canvas id="breadthChart"></canvas>
                    <div class="chart-center-label">
                        <div class="ccl-value">{stats['total']}</div>
                        <div class="ccl-text">co phieu</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Signal Distribution -->
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">Phan bo Tin hieu</h3>
            </div>
            <div class="card-body" style="padding:20px;">
                <canvas id="signalBarChart" height="200"></canvas>
            </div>
        </div>

        <!-- Indicators Summary -->
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">Chi so Thi truong</h3>
            </div>
            <div class="card-body" style="padding:20px;">
                <div class="market-indicators">
                    <div class="mi-item">
                        <div class="mi-label">RSI Trung binh</div>
                        <div class="mi-bar-wrap">
                            <div class="mi-bar">
                                <div class="mi-bar-fill" style="width:{stats['avg_rsi']}%;background:{'var(--red)' if stats['avg_rsi'] > 70 else 'var(--green)' if stats['avg_rsi'] < 30 else 'var(--blue)'}"></div>
                                <div class="mi-bar-marker" style="left:30%"></div>
                                <div class="mi-bar-marker" style="left:70%"></div>
                            </div>
                            <span class="mi-val">{stats['avg_rsi']}</span>
                        </div>
                    </div>
                    <div class="mi-item">
                        <div class="mi-label">MFI Trung binh</div>
                        <div class="mi-bar-wrap">
                            <div class="mi-bar">
                                <div class="mi-bar-fill" style="width:{stats['avg_mfi']}%;background:{'var(--green)' if stats['avg_mfi'] > 50 else 'var(--red)'}"></div>
                            </div>
                            <span class="mi-val">{stats['avg_mfi']}</span>
                        </div>
                    </div>
                    <div class="mi-item">
                        <div class="mi-label">Vol Surge</div>
                        <div class="mi-bar-wrap">
                            <div class="mi-bar">
                                <div class="mi-bar-fill" style="width:{min(stats['vol_surge_count']/max(stats['total'],1)*100, 100):.0f}%;background:var(--cyan)"></div>
                            </div>
                            <span class="mi-val">{stats['vol_surge_count']}</span>
                        </div>
                    </div>
                    <div class="mi-item">
                        <div class="mi-label">BB Squeeze</div>
                        <div class="mi-bar-wrap">
                            <div class="mi-bar">
                                <div class="mi-bar-fill" style="width:{min(stats['bb_squeeze_count']/max(stats['total'],1)*100, 100):.0f}%;background:var(--yellow)"></div>
                            </div>
                            <span class="mi-val">{stats['bb_squeeze_count']}</span>
                        </div>
                    </div>
                    <div class="mi-item">
                        <div class="mi-label">Breakout</div>
                        <div class="mi-bar-wrap">
                            <div class="mi-bar">
                                <div class="mi-bar-fill" style="width:{min(stats['breakout']/max(stats['total'],1)*100*5, 100):.0f}%;background:var(--green)"></div>
                            </div>
                            <span class="mi-val">{stats['breakout']}</span>
                        </div>
                    </div>
                    <div class="mi-item">
                        <div class="mi-label">Momentum</div>
                        <div class="mi-bar-wrap">
                            <div class="mi-bar">
                                <div class="mi-bar-fill" style="width:{min(stats['momentum']/max(stats['total'],1)*100*5, 100):.0f}%;background:var(--blue)"></div>
                            </div>
                            <span class="mi-val">{stats['momentum']}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Top Signals Table -->
    <div class="card">
        <div class="card-header">
            <h3 class="card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                Top Tin hieu Hom nay
            </h3>
            <button class="btn-link" onclick="switchTab('screener')">Xem tat ca &rarr;</button>
        </div>
        <div class="card-body" style="padding:0;">
            <div style="overflow-x:auto">
                <table class="data-table" id="topSignalsTable">
                    <thead>
                        <tr>
                            <th style="width:40px">#</th>
                            <th>Ma</th>
                            <th>Khuyen nghi</th>
                            <th>Gia</th>
                            <th>Diem</th>
                            <th>RSI</th>
                            <th>Vol</th>
                            <th>Tin hieu</th>
                        </tr>
                    </thead>
                    <tbody id="topSignalsBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Heatmap -->
    <div class="card">
        <div class="card-header">
            <h3 class="card-title">Heatmap Thi truong</h3>
            <div class="pill-group" id="heatmapFilters">
                <button class="pill active" data-hm="score">Diem</button>
                <button class="pill" data-hm="rsi">RSI</button>
                <button class="pill" data-hm="volume">Volume</button>
            </div>
        </div>
        <div class="card-body">
            <div class="heatmap" id="heatmapGrid"></div>
        </div>
    </div>

</div>

<!-- ==================== TAB: BO LOC CO PHIEU ==================== -->
<div class="tab-panel" id="panel-screener">

    <!-- Filter Controls -->
    <div class="screener-controls">
        <div class="filter-section">
            <label class="filter-label">Khuyen nghi</label>
            <div class="pill-group" id="screenerFilters">
                <button class="pill active" data-sf="all">Tat ca <span class="pill-count">{stats['total']}</span></button>
                <button class="pill" data-sf="MUA MANH">MUA MANH <span class="pill-count">{stats['buy_strong']}</span></button>
                <button class="pill" data-sf="MUA">MUA <span class="pill-count">{stats['buy']}</span></button>
                <button class="pill" data-sf="TRUNG LAP">Trung Lap <span class="pill-count">{stats['neutral']}</span></button>
                <button class="pill" data-sf="BAN">BAN <span class="pill-count">{stats['sell']}</span></button>
                <button class="pill" data-sf="BAN MANH">BAN MANH <span class="pill-count">{stats['sell_strong']}</span></button>
            </div>
        </div>
        <div class="filter-section">
            <label class="filter-label">Xu huong</label>
            <div class="pill-group" id="channelFilters">
                <button class="pill active" data-ch="all">Tat ca</button>
                <button class="pill" data-ch="XANH">Uptrend</button>
                <button class="pill" data-ch="XAM">Sideways</button>
                <button class="pill" data-ch="DO">Downtrend</button>
            </div>
        </div>
        <div class="filter-section">
            <label class="filter-label">Loai tin hieu</label>
            <div class="pill-group" id="typeFilters">
                <button class="pill active" data-tp="all">Tat ca</button>
                <button class="pill" data-tp="BREAKOUT">Breakout</button>
                <button class="pill" data-tp="MOMENTUM">Momentum</button>
                <button class="pill" data-tp="PULLBACK">Pullback</button>
                <button class="pill" data-tp="REVERSAL">Reversal</button>
            </div>
        </div>
        <div class="filter-section filter-inline">
            <label class="filter-label">RSI</label>
            <select id="rsiFilter" class="filter-select">
                <option value="all">Tat ca</option>
                <option value="oversold">Qua ban (&lt;30)</option>
                <option value="neutral">Trung tinh (30-70)</option>
                <option value="overbought">Qua mua (&gt;70)</option>
            </select>
            <label class="filter-label" style="margin-left:16px">Volume</label>
            <select id="volFilter" class="filter-select">
                <option value="all">Tat ca</option>
                <option value="surge">Dot bien (&gt;1.5x)</option>
                <option value="high">Cao (&gt;2x)</option>
            </select>
        </div>
    </div>

    <!-- Screener Table -->
    <div class="card">
        <div style="overflow-x:auto">
            <table class="data-table screener-tbl" id="screenerTable">
                <thead>
                    <tr>
                        <th data-sort="index" style="width:40px">#</th>
                        <th data-sort="symbol">Ma CK</th>
                        <th data-sort="signal_label">Khuyen nghi</th>
                        <th data-sort="close">Gia (x1000)</th>
                        <th data-sort="score_100">Diem</th>
                        <th data-sort="rsi">RSI</th>
                        <th data-sort="mfi">MFI</th>
                        <th data-sort="channel">Xu huong</th>
                        <th data-sort="vol_ratio">Vol Ratio</th>
                        <th data-sort="buy_signal">Tin hieu</th>
                        <th data-sort="stars">Sao</th>
                        <th style="width:50px"></th>
                    </tr>
                </thead>
                <tbody id="screenerBody"></tbody>
            </table>
        </div>
        <div class="table-footer">
            <div class="tf-info" id="pageInfo"></div>
            <div class="tf-pages" id="pageBtns"></div>
        </div>
    </div>
</div>

<!-- ==================== TAB: PORTFOLIO ==================== -->
<div class="tab-panel" id="panel-portfolio">

    <!-- Portfolio Summary -->
    <div class="portfolio-summary">
        <div class="ps-card">
            <div class="ps-icon" style="background:rgba(59,130,246,0.15);color:var(--blue)">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
            </div>
            <div>
                <div class="ps-label">Vi the mo</div>
                <div class="ps-value">{len(positions)}</div>
            </div>
        </div>
        <div class="ps-card">
            <div class="ps-icon" style="background:rgba(16,185,129,0.15);color:var(--green)">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            </div>
            <div>
                <div class="ps-label">Tien mat</div>
                <div class="ps-value">{self.portfolio.get('cash_percent', 100)}%</div>
            </div>
        </div>
        <div class="ps-card">
            <div class="ps-icon" style="background:{'rgba(16,185,129,0.15)' if total_pnl >= 0 else 'rgba(239,68,68,0.15)'};color:{'var(--green)' if total_pnl >= 0 else 'var(--red)'}">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="{'23 6 13.5 15.5 8.5 10.5 1 18' if total_pnl >= 0 else '23 18 13.5 8.5 8.5 13.5 1 6'}"/></svg>
            </div>
            <div>
                <div class="ps-label">Tong P&L</div>
                <div class="ps-value {'c-green' if total_pnl >= 0 else 'c-red'}">{'+'if total_pnl >= 0 else ''}{total_pnl:.2f}%</div>
            </div>
        </div>
        <div class="ps-card">
            <div class="ps-icon" style="background:rgba(139,92,246,0.15);color:var(--purple)">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            </div>
            <div>
                <div class="ps-label">Cap nhat</div>
                <div class="ps-value" style="font-size:0.9rem">{self.today}</div>
            </div>
        </div>
    </div>

    <!-- Holdings Table -->
    <div class="card">
        <div class="card-header">
            <h3 class="card-title">Danh muc Dau tu</h3>
        </div>
        <div class="card-body" style="padding:0">
            {self._generate_portfolio_table(positions)}
        </div>
    </div>

    <!-- Allocation Chart -->
    <div class="overview-grid" style="grid-template-columns: 1fr 1fr;">
        <div class="card">
            <div class="card-header"><h3 class="card-title">Phan bo Ty trong</h3></div>
            <div class="card-body" style="display:flex;justify-content:center;padding:24px;">
                <div style="width:240px;height:240px;position:relative;">
                    <canvas id="allocationChart"></canvas>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">Watchlist</h3>
                <div style="display:flex;gap:8px;align-items:center;">
                    <input type="text" id="watchlistInput" class="filter-select" placeholder="Nhap ma CK..." style="width:120px;">
                    <button class="btn-primary" onclick="addWatchlist()">Them</button>
                </div>
            </div>
            <div class="card-body" style="padding:0">
                <table class="data-table" id="watchlistTable">
                    <thead><tr><th>Ma</th><th>Gia</th><th>Diem</th><th>RSI</th><th>Khuyen nghi</th><th style="width:40px"></th></tr></thead>
                    <tbody id="watchlistBody"></tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- ==================== TAB: KHUYEN NGHI AI ==================== -->
<div class="tab-panel" id="panel-ai">
    <div class="card">
        <div class="card-header">
            <h3 class="card-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" stroke-width="2"><path d="M12 2a5 5 0 0 1 5 5c0 2-1.5 3.5-3 4.5V14h-4v-2.5C8.5 10.5 7 9 7 7a5 5 0 0 1 5-5z"/><line x1="10" y1="17" x2="14" y2="17"/><line x1="10" y1="20" x2="14" y2="20"/></svg>
                Bao cao Phan tich AI
            </h3>
            <span class="meta-badge">Claude Sonnet 4.5</span>
        </div>
        <div class="card-body">
            <div class="ai-report" id="aiReportContent"></div>
        </div>
    </div>
</div>

</main>

<!-- ===== FOOTER ===== -->
<footer class="footer">
    <span>VN Stock Sniper &copy; 2024-2026</span>
    <span>Powered by Claude AI &bull; FiinQuantX &bull; vnstock</span>
</footer>

<script>
{self._generate_javascript(clean_stocks, stats, positions, ai_report_escaped)}
</script>

</body>
</html>'''

        return html

    def _generate_css(self):
        return '''
    :root {
        --bg-body: #0b0f19;
        --bg-card: #111827;
        --bg-card-hover: #1a2332;
        --bg-header: rgba(11, 15, 25, 0.95);
        --bg-input: #0d1117;
        --border: #1e293b;
        --border-hover: #334155;
        --text-primary: #e5e7eb;
        --text-secondary: #9ca3af;
        --text-muted: #6b7280;
        --green: #22c55e;
        --green-dim: rgba(34, 197, 94, 0.15);
        --red: #ef4444;
        --red-dim: rgba(239, 68, 68, 0.15);
        --blue: #3b82f6;
        --blue-dim: rgba(59, 130, 246, 0.15);
        --purple: #8b5cf6;
        --purple-dim: rgba(139, 92, 246, 0.15);
        --yellow: #eab308;
        --yellow-dim: rgba(234, 179, 8, 0.15);
        --cyan: #06b6d4;
        --orange: #f97316;
        --radius: 10px;
        --radius-sm: 6px;
        --shadow: 0 1px 3px rgba(0,0,0,0.3);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        background: var(--bg-body);
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        line-height: 1.5;
        overflow-x: hidden;
        font-size: 14px;
    }

    .mono { font-family: 'JetBrains Mono', monospace; }
    .c-green { color: var(--green) !important; }
    .c-red { color: var(--red) !important; }
    .c-blue { color: var(--blue) !important; }
    .c-purple { color: var(--purple) !important; }
    .c-yellow { color: var(--yellow) !important; }
    .c-muted { color: var(--text-muted) !important; }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--border-hover); }

    /* ========== INDICES BAR ========== */
    .indices-bar {
        background: #080c14;
        border-bottom: 1px solid var(--border);
        padding: 0 24px;
        height: 36px;
        display: flex;
        align-items: center;
    }
    .indices-bar-inner {
        max-width: 1440px;
        margin: 0 auto;
        width: 100%;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .index-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.8rem;
        white-space: nowrap;
    }
    .idx-name {
        color: var(--text-muted);
        font-weight: 500;
        font-size: 0.7rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .idx-value {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        color: var(--text-primary);
        font-size: 0.8rem;
    }
    .idx-change {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .idx-sep {
        width: 1px;
        height: 16px;
        background: var(--border);
    }

    /* ========== HEADER ========== */
    .header {
        background: var(--bg-header);
        border-bottom: 1px solid var(--border);
        padding: 0 24px;
        position: sticky;
        top: 0;
        z-index: 100;
        backdrop-filter: blur(16px);
    }
    .header-inner {
        max-width: 1440px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        height: 56px;
        gap: 24px;
    }
    .header-left { flex-shrink: 0; }
    .header-center { flex: 1; display: flex; justify-content: center; }
    .header-right { flex-shrink: 0; display: flex; align-items: center; gap: 16px; }
    .logo { display: flex; align-items: center; gap: 10px; }
    .logo-icon {
        width: 36px; height: 36px;
        background: linear-gradient(135deg, var(--blue), var(--purple));
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        color: #fff;
    }
    .logo-text { font-size: 1rem; font-weight: 700; letter-spacing: -0.3px; white-space: nowrap; }
    .logo-sub { font-size: 0.65rem; color: var(--text-muted); letter-spacing: 0.5px; }

    /* ========== NAV TABS ========== */
    .nav-tabs { display: flex; gap: 2px; background: rgba(17,24,39,0.8); border: 1px solid var(--border); border-radius: 10px; padding: 3px; }
    .nav-tab {
        padding: 7px 16px;
        border-radius: 8px;
        cursor: pointer;
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-muted);
        white-space: nowrap;
        transition: all 0.2s;
        border: none;
        background: none;
        display: flex;
        align-items: center;
        gap: 6px;
        font-family: inherit;
    }
    .nav-tab:hover { color: var(--text-primary); background: rgba(59,130,246,0.08); }
    .nav-tab.active {
        background: linear-gradient(135deg, var(--blue), var(--purple));
        color: #fff;
        box-shadow: 0 2px 8px rgba(59,130,246,0.3);
    }
    .nav-tab svg { opacity: 0.7; }
    .nav-tab.active svg { opacity: 1; }

    /* ========== SEARCH ========== */
    .search-box { position: relative; }
    .search-box input {
        background: var(--bg-input);
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        padding: 6px 12px 6px 34px;
        color: var(--text-primary);
        font-size: 0.8rem;
        width: 220px;
        outline: none;
        transition: all 0.2s;
        font-family: inherit;
    }
    .search-box input:focus { border-color: var(--blue); width: 280px; }
    .search-box input::placeholder { color: var(--text-muted); }
    .search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-muted); }

    .header-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
    .meta-badge {
        background: linear-gradient(135deg, var(--blue-dim), var(--purple-dim));
        border: 1px solid rgba(59,130,246,0.2);
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        color: var(--blue);
    }
    .meta-time { font-size: 0.7rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }

    .tab-panel { display: none; }
    .tab-panel.active { display: block; }

    /* ========== MAIN CONTENT ========== */
    .main-content { max-width: 1440px; margin: 0 auto; padding: 20px 24px 40px; }

    /* ========== KPI ROW ========== */
    .kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 20px; }
    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 16px 18px;
        display: flex;
        align-items: center;
        gap: 14px;
        transition: all 0.2s;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::after {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 3px;
        height: 100%;
    }
    .kpi-green::after { background: var(--green); }
    .kpi-gray::after { background: var(--text-muted); }
    .kpi-red::after { background: var(--red); }
    .kpi-blue::after { background: var(--blue); }
    .kpi-purple::after { background: var(--purple); }
    .kpi-card:hover { border-color: var(--border-hover); transform: translateY(-1px); }
    .kpi-icon { opacity: 0.6; flex-shrink: 0; }
    .kpi-green .kpi-icon { color: var(--green); }
    .kpi-gray .kpi-icon { color: var(--text-muted); }
    .kpi-red .kpi-icon { color: var(--red); }
    .kpi-blue .kpi-icon { color: var(--blue); }
    .kpi-purple .kpi-icon { color: var(--purple); }
    .kpi-data { flex: 1; }
    .kpi-value { font-size: 1.5rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1.2; }
    .kpi-green .kpi-value { color: var(--green); }
    .kpi-gray .kpi-value { color: var(--text-secondary); }
    .kpi-red .kpi-value { color: var(--red); }
    .kpi-blue .kpi-value { color: var(--blue); }
    .kpi-purple .kpi-value { color: var(--purple); }
    .kpi-label { font-size: 0.75rem; color: var(--text-muted); font-weight: 500; }
    .kpi-pct { font-size: 0.8rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }

    /* ========== SIGNAL BAR ========== */
    .signal-bar {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    .signal-bar-title { font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; }
    .signal-bar-items { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
    .sbar-item {
        display: flex; flex-direction: column; align-items: center;
        padding: 8px 20px; border-radius: var(--radius-sm);
        cursor: pointer; transition: all 0.2s; min-width: 90px;
    }
    .sbar-item:hover { transform: translateY(-1px); }
    .sbar-count { font-size: 1.4rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1.2; }
    .sbar-label { font-size: 0.65rem; font-weight: 600; letter-spacing: 0.5px; margin-top: 2px; }
    .sbar-buy-strong { background: var(--green-dim); }
    .sbar-buy-strong .sbar-count, .sbar-buy-strong .sbar-label { color: var(--green); }
    .sbar-buy { background: rgba(34,197,94,0.08); }
    .sbar-buy .sbar-count, .sbar-buy .sbar-label { color: #4ade80; }
    .sbar-neutral { background: rgba(107,114,128,0.1); }
    .sbar-neutral .sbar-count { color: var(--text-secondary); }
    .sbar-neutral .sbar-label { color: var(--text-muted); }
    .sbar-sell { background: rgba(249,115,22,0.1); }
    .sbar-sell .sbar-count, .sbar-sell .sbar-label { color: var(--orange); }
    .sbar-sell-strong { background: var(--red-dim); }
    .sbar-sell-strong .sbar-count, .sbar-sell-strong .sbar-label { color: var(--red); }

    .signal-visual-bar { display: flex; height: 6px; border-radius: 3px; overflow: hidden; gap: 2px; }
    .svb-seg { border-radius: 3px; min-width: 2px; transition: flex 0.5s; }
    .svb-buy-strong { background: var(--green); }
    .svb-buy { background: #4ade80; }
    .svb-neutral { background: #6b7280; }
    .svb-sell { background: var(--orange); }
    .svb-sell-strong { background: var(--red); }

    /* ========== CARDS ========== */
    .card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        margin-bottom: 20px;
        overflow: hidden;
    }
    .card-header {
        padding: 14px 20px;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }
    .card-title { font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 8px; }
    .card-body { padding: 16px 20px; }

    .btn-link {
        background: none; border: none; color: var(--blue);
        font-size: 0.8rem; cursor: pointer; font-weight: 500;
        font-family: inherit; transition: color 0.2s;
    }
    .btn-link:hover { color: var(--purple); }
    .btn-primary {
        background: var(--blue); color: #fff; border: none;
        padding: 6px 14px; border-radius: var(--radius-sm);
        font-size: 0.8rem; cursor: pointer; font-weight: 600;
        font-family: inherit; transition: all 0.2s;
    }
    .btn-primary:hover { background: #2563eb; }

    /* ========== OVERVIEW GRID ========== */
    .overview-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-bottom: 20px;
    }
    .overview-grid .card { margin-bottom: 0; }

    .chart-center-label {
        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;
    }
    .ccl-value { font-size: 1.5rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .ccl-text { font-size: 0.7rem; color: var(--text-muted); }

    /* ========== MARKET INDICATORS ========== */
    .market-indicators { display: flex; flex-direction: column; gap: 14px; }
    .mi-item { display: flex; flex-direction: column; gap: 4px; }
    .mi-label { font-size: 0.75rem; color: var(--text-muted); font-weight: 500; }
    .mi-bar-wrap { display: flex; align-items: center; gap: 10px; }
    .mi-bar {
        flex: 1; height: 6px; background: rgba(30,41,59,0.6); border-radius: 3px;
        overflow: hidden; position: relative;
    }
    .mi-bar-fill { height: 100%; border-radius: 3px; transition: width 0.8s ease; }
    .mi-bar-marker { position: absolute; top: -2px; width: 1px; height: 10px; background: rgba(255,255,255,0.15); }
    .mi-val { font-family: 'JetBrains Mono', monospace; font-weight: 600; font-size: 0.85rem; min-width: 36px; text-align: right; }

    /* ========== PILLS ========== */
    .pill-group { display: flex; gap: 4px; flex-wrap: wrap; }
    .pill {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        border: 1px solid var(--border);
        background: transparent;
        color: var(--text-secondary);
        cursor: pointer;
        transition: all 0.2s;
        font-family: inherit;
        display: flex; align-items: center; gap: 4px;
    }
    .pill:hover { border-color: var(--blue); color: var(--blue); }
    .pill.active {
        background: var(--blue-dim);
        border-color: var(--blue);
        color: var(--blue);
    }
    .pill-count {
        background: rgba(59,130,246,0.2);
        padding: 0 6px;
        border-radius: 8px;
        font-size: 0.7rem;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
    }

    /* ========== DATA TABLE ========== */
    .data-table { width: 100%; border-collapse: separate; border-spacing: 0; }
    .data-table thead th {
        background: rgba(11,15,25,0.9);
        color: var(--text-muted);
        font-weight: 600;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        padding: 10px 14px;
        border-bottom: 1px solid var(--border);
        cursor: pointer;
        white-space: nowrap;
        user-select: none;
        transition: color 0.15s;
        position: sticky;
        top: 0;
        z-index: 2;
    }
    .data-table thead th:hover { color: var(--text-primary); }
    .data-table thead th.sorted-asc::after { content: ' \\2191'; color: var(--blue); }
    .data-table thead th.sorted-desc::after { content: ' \\2193'; color: var(--blue); }
    .data-table tbody tr {
        cursor: pointer;
        transition: background 0.12s;
    }
    .data-table tbody tr:hover { background: rgba(59,130,246,0.04); }
    .data-table tbody td {
        padding: 10px 14px;
        border-bottom: 1px solid rgba(30,41,59,0.3);
        white-space: nowrap;
        vertical-align: middle;
        font-size: 0.85rem;
    }
    .stock-sym {
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        color: var(--text-primary);
    }

    /* ========== SIGNAL BADGES ========== */
    .sig-badge {
        display: inline-flex; align-items: center; gap: 3px;
        padding: 3px 10px; border-radius: 20px;
        font-size: 0.7rem; font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.3px;
    }
    .sig-mua-manh { background: var(--green-dim); color: var(--green); border: 1px solid rgba(34,197,94,0.25); }
    .sig-mua { background: rgba(34,197,94,0.08); color: #4ade80; border: 1px solid rgba(34,197,94,0.15); }
    .sig-trung-lap { background: rgba(107,114,128,0.1); color: var(--text-secondary); border: 1px solid rgba(107,114,128,0.15); }
    .sig-ban { background: rgba(249,115,22,0.1); color: var(--orange); border: 1px solid rgba(249,115,22,0.15); }
    .sig-ban-manh { background: var(--red-dim); color: var(--red); border: 1px solid rgba(239,68,68,0.25); }

    .type-badge {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 0.7rem; font-weight: 600; font-family: 'JetBrains Mono', monospace;
    }
    .type-breakout { background: rgba(34,197,94,0.15); color: var(--green); }
    .type-momentum { background: rgba(59,130,246,0.15); color: var(--blue); }
    .type-pullback { background: rgba(234,179,8,0.15); color: var(--yellow); }
    .type-reversal { background: rgba(139,92,246,0.15); color: var(--purple); }

    .ch-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
    .ch-xanh { background: rgba(34,197,94,0.12); color: var(--green); }
    .ch-xam { background: rgba(107,114,128,0.1); color: var(--text-secondary); }
    .ch-do { background: rgba(239,68,68,0.12); color: var(--red); }

    /* ========== SCORE GAUGE ========== */
    .gauge { position: relative; display: inline-block; }
    .gauge svg { transform: rotate(-90deg); }
    .gauge-val {
        position: absolute; top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 0.75rem;
    }

    /* RSI inline bar */
    .rsi-inline { display: flex; align-items: center; gap: 6px; }
    .rsi-bar { width: 44px; height: 4px; background: rgba(30,41,59,0.5); border-radius: 2px; overflow: hidden; }
    .rsi-bar-fill { height: 100%; border-radius: 2px; }

    /* Stars */
    .stars { color: var(--yellow); font-size: 0.8rem; letter-spacing: 1px; }

    /* ========== EXPAND ROW ========== */
    .expand-row { display: none; }
    .expand-row.show { display: table-row; }
    .expand-content {
        background: rgba(11,15,25,0.6);
        padding: 20px;
        border-bottom: 2px solid var(--border);
    }
    .expand-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
    .exp-section-title {
        font-size: 0.7rem; color: var(--text-muted);
        text-transform: uppercase; letter-spacing: 0.8px;
        margin-bottom: 10px; font-weight: 600;
        padding-bottom: 6px; border-bottom: 1px solid var(--border);
    }
    .ind-list { display: flex; flex-direction: column; gap: 5px; }
    .ind-row { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 0.8rem; }
    .ind-label { color: var(--text-secondary); }
    .ind-val { font-family: 'JetBrains Mono', monospace; font-weight: 600; }

    /* ========== HEATMAP ========== */
    .heatmap { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 3px; }
    .hm-cell {
        padding: 8px 4px; border-radius: 6px; text-align: center;
        cursor: pointer; transition: all 0.12s;
        font-family: 'JetBrains Mono', monospace;
    }
    .hm-cell:hover { transform: scale(1.06); z-index: 1; }
    .hm-sym { font-weight: 700; font-size: 0.75rem; }
    .hm-val { font-size: 0.6rem; opacity: 0.75; margin-top: 1px; }

    /* ========== SCREENER CONTROLS ========== */
    .screener-controls {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 16px 20px;
        margin-bottom: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .filter-section { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .filter-inline { align-items: center; }
    .filter-label { font-size: 0.7rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; min-width: 70px; }
    .filter-select {
        background: var(--bg-input); border: 1px solid var(--border);
        color: var(--text-primary); padding: 5px 10px; border-radius: var(--radius-sm);
        font-size: 0.8rem; outline: none; font-family: inherit;
    }
    .filter-select:focus { border-color: var(--blue); }

    /* ========== TABLE FOOTER ========== */
    .table-footer {
        display: flex; justify-content: space-between; align-items: center;
        padding: 12px 20px; border-top: 1px solid var(--border);
    }
    .tf-info { color: var(--text-muted); font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }
    .tf-pages { display: flex; gap: 3px; }
    .pg-btn {
        padding: 5px 10px; border: 1px solid var(--border); background: transparent;
        color: var(--text-secondary); border-radius: var(--radius-sm);
        cursor: pointer; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
        transition: all 0.15s;
    }
    .pg-btn:hover, .pg-btn.active { background: var(--blue); color: #fff; border-color: var(--blue); }
    .pg-btn:disabled { opacity: 0.3; cursor: default; pointer-events: none; }

    /* ========== PORTFOLIO ========== */
    .portfolio-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
    .ps-card {
        background: var(--bg-card); border: 1px solid var(--border);
        border-radius: var(--radius); padding: 18px 20px;
        display: flex; align-items: center; gap: 14px;
    }
    .ps-icon {
        width: 44px; height: 44px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
    }
    .ps-label { font-size: 0.75rem; color: var(--text-muted); }
    .ps-value { font-size: 1.25rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }

    /* ========== AI REPORT ========== */
    .ai-report { line-height: 1.8; font-size: 0.9rem; color: var(--text-secondary); }
    .ai-report h2 {
        color: var(--text-primary); font-size: 1.15rem; margin: 24px 0 10px;
        padding-bottom: 8px; border-bottom: 1px solid var(--border);
        display: flex; align-items: center; gap: 8px;
    }
    .ai-report h3 { color: var(--blue); font-size: 0.95rem; margin: 18px 0 6px; }
    .ai-report strong { color: var(--text-primary); }
    .ai-report ul, .ai-report ol { padding-left: 20px; margin: 6px 0; }
    .ai-report li { margin-bottom: 3px; }
    .ai-report p { margin: 6px 0; }
    .ai-report hr { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
    .ai-report code {
        background: var(--blue-dim); padding: 2px 6px; border-radius: 4px;
        font-family: 'JetBrains Mono', monospace; font-size: 0.85em; color: var(--blue);
    }
    .ai-report table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.85rem; }
    .ai-report table th, .ai-report table td { padding: 8px 12px; border: 1px solid var(--border); text-align: left; }
    .ai-report table th { background: rgba(11,15,25,0.6); color: var(--text-primary); font-weight: 600; }

    /* ========== FOOTER ========== */
    .footer {
        border-top: 1px solid var(--border);
        padding: 16px 24px;
        text-align: center;
        font-size: 0.75rem;
        color: var(--text-muted);
        display: flex;
        justify-content: center;
        gap: 24px;
    }

    /* ========== WEIGHT BAR ========== */
    .weight-bar { height: 4px; background: rgba(30,41,59,0.5); border-radius: 2px; overflow: hidden; margin-top: 3px; }
    .weight-bar-fill { height: 100%; border-radius: 2px; }

    /* ========== RESPONSIVE ========== */
    @media (max-width: 1200px) {
        .overview-grid { grid-template-columns: repeat(2, 1fr); }
        .kpi-row { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 900px) {
        .kpi-row { grid-template-columns: repeat(2, 1fr); }
        .portfolio-summary { grid-template-columns: repeat(2, 1fr); }
        .expand-grid { grid-template-columns: 1fr; }
        .header-inner { flex-wrap: wrap; height: auto; padding: 10px 0; }
        .header-center { order: 3; width: 100%; justify-content: flex-start; overflow-x: auto; }
        .nav-tabs { overflow-x: auto; }
        .indices-bar-inner { overflow-x: auto; }
    }
    @media (max-width: 640px) {
        .main-content { padding: 12px; }
        .kpi-row { grid-template-columns: 1fr 1fr; }
        .overview-grid { grid-template-columns: 1fr; }
        .portfolio-summary { grid-template-columns: 1fr; }
        .signal-bar-items { gap: 4px; }
        .sbar-item { min-width: 70px; padding: 6px 12px; }
    }
'''

    def _generate_javascript(self, clean_stocks, stats, positions, ai_report_escaped):
        return f'''
// ===========================
// DATA
// ===========================
const ALL_STOCKS = {json.dumps(clean_stocks, ensure_ascii=False, default=str)};
const AI_REPORT = `{ai_report_escaped}`;
const POSITIONS = {json.dumps(self._clean_for_json(positions), ensure_ascii=False, default=str)};

// ===========================
// STATE
// ===========================
let currentTab = 'overview';
let screenerFilter = 'all';
let channelFilter = 'all';
let typeFilter = 'all';
let rsiFilter = 'all';
let volFilter = 'all';
let heatmapMode = 'score';
let sortCol = 'score_100';
let sortDir = 'desc';
let currentPage = 1;
const PAGE_SIZE = 25;
let expandedRow = null;
let watchlist = JSON.parse(localStorage.getItem('vns_watchlist') || '[]');

// ===========================
// UTILS
// ===========================
const n = v => Number(v || 0);
const f1 = v => n(v).toFixed(1);
const f2 = v => n(v).toFixed(2);
const loc = v => n(v).toLocaleString('vi-VN');

function sigBadge(label) {{
    if (!label) label = 'TRUNG LAP';
    const m = {{'MUA MANH':'sig-mua-manh','MUA':'sig-mua','TRUNG LAP':'sig-trung-lap','BAN':'sig-ban','BAN MANH':'sig-ban-manh'}};
    return '<span class="sig-badge '+(m[label]||'sig-trung-lap')+'">'+label+'</span>';
}}

function typeBadge(sig) {{
    if (!sig) return '<span class="c-muted">-</span>';
    const m = {{'BREAKOUT':'type-breakout','MOMENTUM':'type-momentum','PULLBACK':'type-pullback','REVERSAL':'type-reversal'}};
    return '<span class="type-badge '+(m[sig]||'')+'">'+sig+'</span>';
}}

function chBadge(ch) {{
    if (!ch) return '<span class="ch-badge ch-xam">-</span>';
    if (ch.includes('XANH')) return '<span class="ch-badge ch-xanh">XANH</span>';
    if (ch.includes('\\u0110\\u1ece') || ch.includes('DO')) return '<span class="ch-badge ch-do">DO</span>';
    return '<span class="ch-badge ch-xam">XAM</span>';
}}

function rsiColor(r) {{ return r > 70 ? 'var(--red)' : r < 30 ? 'var(--green)' : 'var(--text-primary)'; }}
function scoreColor(s) {{ return s >= 70 ? 'var(--green)' : s >= 45 ? 'var(--blue)' : s >= 25 ? 'var(--yellow)' : 'var(--red)'; }}

function gauge(score, sz) {{
    sz = sz || 38;
    const r = (sz - 5) / 2;
    const c = 2 * Math.PI * r;
    const pct = Math.min(Math.max(score, 0), 100);
    const off = c * (1 - pct / 100);
    const col = scoreColor(pct);
    return `<div class="gauge" style="width:${{sz}}px;height:${{sz}}px">
        <svg width="${{sz}}" height="${{sz}}" viewBox="0 0 ${{sz}} ${{sz}}">
            <circle cx="${{sz/2}}" cy="${{sz/2}}" r="${{r}}" fill="none" stroke="rgba(30,41,59,0.5)" stroke-width="3.5"/>
            <circle cx="${{sz/2}}" cy="${{sz/2}}" r="${{r}}" fill="none" stroke="${{col}}" stroke-width="3.5"
                stroke-dasharray="${{c}}" stroke-dashoffset="${{off}}" stroke-linecap="round"/>
        </svg>
        <span class="gauge-val" style="color:${{col}};font-size:${{sz<36?0.6:0.75}}rem">${{Math.round(pct)}}</span>
    </div>`;
}}

function rsiBar(rsi) {{
    const w = Math.min(n(rsi), 100);
    const col = rsi > 70 ? 'var(--red)' : rsi < 30 ? 'var(--green)' : 'var(--blue)';
    return `<div class="rsi-inline"><span class="mono" style="color:${{rsiColor(rsi)}};font-size:0.85rem">${{f1(rsi)}}</span><span class="rsi-bar"><span class="rsi-bar-fill" style="width:${{w}}%;background:${{col}}"></span></span></div>`;
}}

function starsHtml(count) {{
    let s = '';
    for (let i = 0; i < 5; i++) s += i < count ? '&#9733;' : '&#9734;';
    return '<span class="stars">' + s + '</span>';
}}

// ===========================
// TABS
// ===========================
function switchTab(tab) {{
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const btn = document.querySelector('[data-tab="'+tab+'"]');
    if (btn) btn.classList.add('active');
    currentTab = tab;
    document.getElementById('panel-' + tab).classList.add('active');
    renderCurrentTab();
}}

document.querySelectorAll('.nav-tab').forEach(tab => {{
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
}});

function renderCurrentTab() {{
    if (currentTab === 'overview') {{ renderHeatmap(); renderTopSignals(); }}
    else if (currentTab === 'screener') {{ renderScreener(); }}
    else if (currentTab === 'portfolio') {{ renderWatchlist(); }}
    else if (currentTab === 'ai') {{ renderAIReport(); }}
}}

// ===========================
// INDEX BAR (computed from data)
// ===========================
function initIndexBar() {{
    // Compute pseudo-index from data
    const total = ALL_STOCKS.length;
    if (total === 0) return;
    const adv = ALL_STOCKS.filter(s => n(s.close) > n(s.open)).length;
    const dec = ALL_STOCKS.filter(s => n(s.close) < n(s.open)).length;
    const avgScore = (ALL_STOCKS.reduce((a,s) => a + n(s.score_100), 0) / total).toFixed(1);
    // Set AD ratio is already in HTML
}}

// ===========================
// TOP SIGNALS TABLE
// ===========================
function renderTopSignals() {{
    const buyStocks = ALL_STOCKS
        .filter(s => s.signal_label === 'MUA MANH' || s.signal_label === 'MUA')
        .sort((a,b) => n(b.total_score) - n(a.total_score))
        .slice(0, 15);

    const tbody = document.getElementById('topSignalsBody');
    if (!tbody) return;

    if (buyStocks.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px">Khong co tin hieu MUA hom nay</td></tr>';
        return;
    }}

    tbody.innerHTML = buyStocks.map((s, i) => `
        <tr onclick="goToScreener('${{s.symbol}}')">
            <td class="c-muted mono">${{i+1}}</td>
            <td class="stock-sym">${{s.symbol}}</td>
            <td>${{sigBadge(s.signal_label)}}</td>
            <td class="mono">${{loc(s.close)}}</td>
            <td>${{gauge(n(s.score_100), 36)}}</td>
            <td>${{rsiBar(n(s.rsi))}}</td>
            <td class="mono" style="color:${{n(s.vol_ratio)>1.5?'var(--green)':'var(--text-primary)'}}">${{f1(s.vol_ratio)}}x</td>
            <td>${{typeBadge(s.buy_signal)}}</td>
        </tr>
    `).join('');
}}

// ===========================
// HEATMAP
// ===========================
document.querySelectorAll('#heatmapFilters .pill').forEach(pill => {{
    pill.addEventListener('click', () => {{
        document.querySelectorAll('#heatmapFilters .pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        heatmapMode = pill.dataset.hm;
        renderHeatmap();
    }});
}});

function renderHeatmap() {{
    const el = document.getElementById('heatmapGrid');
    if (!el) return;
    const stocks = [...ALL_STOCKS].sort((a,b) => n(b.total_score) - n(a.total_score));
    if (stocks.length === 0) {{
        el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)">Chua co du lieu</div>';
        return;
    }}

    el.innerHTML = stocks.map(s => {{
        let val, mx, lbl;
        if (heatmapMode === 'rsi') {{ val = n(s.rsi); mx = 100; lbl = f1(val); }}
        else if (heatmapMode === 'volume') {{ val = Math.min(n(s.vol_ratio), 3); mx = 3; lbl = f1(s.vol_ratio)+'x'; }}
        else {{ val = n(s.score_100); mx = 100; lbl = Math.round(val)+'pt'; }}

        let bg;
        if (heatmapMode === 'rsi') {{
            bg = val > 70 ? 'rgba(239,68,68,0.4)' : val > 60 ? 'rgba(239,68,68,0.18)' : val < 30 ? 'rgba(34,197,94,0.4)' : val < 40 ? 'rgba(34,197,94,0.18)' : 'rgba(59,130,246,0.12)';
        }} else {{
            const r = Math.min(val / mx, 1);
            bg = r > 0.6 ? 'rgba(34,197,94,'+(0.12+r*0.3)+')' : r > 0.3 ? 'rgba(59,130,246,'+(0.08+r*0.2)+')' : 'rgba(107,114,128,'+(0.05+r*0.1)+')';
        }}

        return `<div class="hm-cell" style="background:${{bg}}" onclick="goToScreener('${{s.symbol}}')">
            <div class="hm-sym">${{s.symbol}}</div>
            <div class="hm-val">${{lbl}}</div>
        </div>`;
    }}).join('');
}}

function goToScreener(sym) {{
    document.getElementById('globalSearch').value = sym;
    switchTab('screener');
    currentPage = 1;
    renderScreener();
}}

function filterBySignal(label) {{
    screenerFilter = label;
    switchTab('screener');
    document.querySelectorAll('#screenerFilters .pill').forEach(p => {{
        p.classList.remove('active');
        if (p.dataset.sf === label) p.classList.add('active');
    }});
    currentPage = 1;
    renderScreener();
}}

// ===========================
// SCREENER
// ===========================
// Filter event listeners
document.querySelectorAll('#screenerFilters .pill').forEach(p => {{
    p.addEventListener('click', () => {{
        document.querySelectorAll('#screenerFilters .pill').forEach(x => x.classList.remove('active'));
        p.classList.add('active');
        screenerFilter = p.dataset.sf;
        currentPage = 1; expandedRow = null;
        renderScreener();
    }});
}});
document.querySelectorAll('#channelFilters .pill').forEach(p => {{
    p.addEventListener('click', () => {{
        document.querySelectorAll('#channelFilters .pill').forEach(x => x.classList.remove('active'));
        p.classList.add('active');
        channelFilter = p.dataset.ch;
        currentPage = 1; expandedRow = null;
        renderScreener();
    }});
}});
document.querySelectorAll('#typeFilters .pill').forEach(p => {{
    p.addEventListener('click', () => {{
        document.querySelectorAll('#typeFilters .pill').forEach(x => x.classList.remove('active'));
        p.classList.add('active');
        typeFilter = p.dataset.tp;
        currentPage = 1; expandedRow = null;
        renderScreener();
    }});
}});
document.getElementById('rsiFilter').addEventListener('change', function() {{
    rsiFilter = this.value; currentPage = 1; expandedRow = null; renderScreener();
}});
document.getElementById('volFilter').addEventListener('change', function() {{
    volFilter = this.value; currentPage = 1; expandedRow = null; renderScreener();
}});

function renderScreener() {{
    let stocks = [...ALL_STOCKS];

    // Filters
    if (screenerFilter !== 'all') stocks = stocks.filter(s => s.signal_label === screenerFilter);
    if (channelFilter !== 'all') {{
        stocks = stocks.filter(s => {{
            const ch = (s.channel || '').toUpperCase();
            if (channelFilter === 'XANH') return ch.includes('XANH');
            if (channelFilter === 'DO') return ch.includes('\\u0110\\u1ece') || ch.includes('DO');
            if (channelFilter === 'XAM') return ch.includes('X\\u00c1M') || ch.includes('XAM');
            return true;
        }});
    }}
    if (typeFilter !== 'all') stocks = stocks.filter(s => s.buy_signal === typeFilter);
    if (rsiFilter === 'oversold') stocks = stocks.filter(s => n(s.rsi) < 30);
    else if (rsiFilter === 'overbought') stocks = stocks.filter(s => n(s.rsi) > 70);
    else if (rsiFilter === 'neutral') stocks = stocks.filter(s => n(s.rsi) >= 30 && n(s.rsi) <= 70);
    if (volFilter === 'surge') stocks = stocks.filter(s => n(s.vol_ratio) > 1.5);
    else if (volFilter === 'high') stocks = stocks.filter(s => n(s.vol_ratio) > 2);

    // Search
    const q = document.getElementById('globalSearch').value.toUpperCase().trim();
    if (q) stocks = stocks.filter(s => (s.symbol||'').toUpperCase().includes(q));

    // Sort
    stocks.sort((a,b) => {{
        let va = a[sortCol], vb = b[sortCol];
        if (typeof va === 'string') va = va || '';
        if (typeof vb === 'string') vb = vb || '';
        if (typeof va === 'number' || typeof vb === 'number') {{ va = n(va); vb = n(vb); }}
        return sortDir === 'asc' ? (va > vb ? 1 : va < vb ? -1 : 0) : (va < vb ? 1 : va > vb ? -1 : 0);
    }});

    // Pagination
    const total = stocks.length;
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    if (currentPage > totalPages) currentPage = totalPages;
    const start = (currentPage - 1) * PAGE_SIZE;
    const page = stocks.slice(start, start + PAGE_SIZE);

    const tbody = document.getElementById('screenerBody');
    let html = '';

    page.forEach((s, i) => {{
        const idx = start + i + 1;
        const isExp = expandedRow === s.symbol;
        html += `<tr onclick="toggleExpand('${{s.symbol}}')" style="${{isExp?'background:rgba(59,130,246,0.06)':''}}">
            <td class="c-muted mono">${{idx}}</td>
            <td class="stock-sym">${{s.symbol}}</td>
            <td>${{sigBadge(s.signal_label)}}</td>
            <td class="mono">${{loc(s.close)}}</td>
            <td>${{gauge(n(s.score_100), 36)}}</td>
            <td>${{rsiBar(n(s.rsi))}}</td>
            <td class="mono" style="color:${{n(s.mfi)>50?'var(--green)':'var(--red)'}}">${{f1(s.mfi)}}</td>
            <td>${{chBadge(s.channel)}}</td>
            <td class="mono" style="color:${{n(s.vol_ratio)>1.5?'var(--green)':'var(--text-primary)'}}">${{f1(s.vol_ratio)}}x</td>
            <td>${{typeBadge(s.buy_signal)}}</td>
            <td>${{starsHtml(n(s.stars))}}</td>
            <td style="text-align:center;color:var(--text-muted)">${{isExp?'&#9650;':'&#9660;'}}</td>
        </tr>`;

        // Expand detail
        html += `<tr class="expand-row ${{isExp?'show':''}}" id="expand-${{s.symbol}}">
            <td colspan="12" style="padding:0">
                <div class="expand-content">
                    <div class="expand-grid">
                        <div>
                            <div class="exp-section-title">Chi bao Ky thuat</div>
                            <div class="ind-list">
                                <div class="ind-row"><span class="ind-label">RSI (14)</span><span class="ind-val" style="color:${{rsiColor(n(s.rsi))}}">${{f1(s.rsi)}}</span></div>
                                <div class="ind-row"><span class="ind-label">MFI</span><span class="ind-val" style="color:${{n(s.mfi)>50?'var(--green)':'var(--red)'}}">${{f1(s.mfi)}}</span></div>
                                <div class="ind-row"><span class="ind-label">MACD</span><span class="ind-val" style="color:${{s.macd_bullish?'var(--green)':'var(--red)'}}">${{s.macd_bullish?'Bullish':'Bearish'}}</span></div>
                                <div class="ind-row"><span class="ind-label">Stoch K/D</span><span class="ind-val">${{f1(s.stoch_k)}} / ${{f1(s.stoch_d)}}</span></div>
                                <div class="ind-row"><span class="ind-label">BB %</span><span class="ind-val">${{f1(s.bb_percent)}}%</span></div>
                                <div class="ind-row"><span class="ind-label">ATR %</span><span class="ind-val">${{f2(s.atr_percent)}}%</span></div>
                                <div class="ind-row"><span class="ind-label">Vol Ratio</span><span class="ind-val" style="color:${{n(s.vol_ratio)>1.5?'var(--green)':'var(--text-primary)'}}">${{f2(s.vol_ratio)}}x</span></div>
                                <div class="ind-row"><span class="ind-label">OBV</span><span class="ind-val" style="color:${{s.obv_rising?'var(--green)':'var(--red)'}}">${{s.obv_rising?'Tang':'Giam'}}</span></div>
                            </div>
                        </div>
                        <div>
                            <div class="exp-section-title">Xu huong & Kenh gia</div>
                            <div class="ind-list">
                                <div class="ind-row"><span class="ind-label">LR Slope</span><span class="ind-val">${{f2(s.lr_slope_pct)}}%</span></div>
                                <div class="ind-row"><span class="ind-label">Channel Pos</span><span class="ind-val">${{f1(s.channel_position)}}%</span></div>
                                <div class="ind-row"><span class="ind-label">MA Aligned</span><span class="ind-val" style="color:${{s.ma_aligned?'var(--green)':'var(--red)'}}">${{s.ma_aligned?'Co':'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-label">Above MA200</span><span class="ind-val" style="color:${{s.above_ma200?'var(--green)':'var(--red)'}}">${{s.above_ma200?'Co':'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-label">Above MA50</span><span class="ind-val" style="color:${{s.above_ma50?'var(--green)':'var(--red)'}}">${{s.above_ma50?'Co':'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-label">BB Squeeze</span><span class="ind-val" style="color:${{s.bb_squeeze?'var(--yellow)':'var(--text-muted)'}}">${{s.bb_squeeze?'Co':'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-label">Breakout 20D</span><span class="ind-val" style="color:${{s.breakout_20?'var(--green)':'var(--text-muted)'}}">${{s.breakout_20?'Co':'Khong'}}</span></div>
                                <div class="ind-row"><span class="ind-label">Breakout 50D</span><span class="ind-val" style="color:${{s.breakout_50?'var(--green)':'var(--text-muted)'}}">${{s.breakout_50?'Co':'Khong'}}</span></div>
                            </div>
                        </div>
                        <div>
                            <div class="exp-section-title">Diem so & Ho tro / Khang cu</div>
                            <div class="ind-list">
                                <div class="ind-row"><span class="ind-label">Quality Score</span><span class="ind-val c-blue">${{f1(s.quality_score)}} / 25</span></div>
                                <div class="ind-row"><span class="ind-label">Momentum Score</span><span class="ind-val c-purple">${{f1(s.momentum_score)}} / 15</span></div>
                                <div class="ind-row"><span class="ind-label">Tong diem</span><span class="ind-val c-green">${{f1(s.total_score)}} / 40</span></div>
                                <div class="ind-row"><span class="ind-label">Support</span><span class="ind-val c-green">${{loc(s.support)}}</span></div>
                                <div class="ind-row"><span class="ind-label">Resistance</span><span class="ind-val c-red">${{loc(s.resistance)}}</span></div>
                                <div class="ind-row"><span class="ind-label">BB Lower</span><span class="ind-val c-green">${{loc(s.bb_lower)}}</span></div>
                                <div class="ind-row"><span class="ind-label">BB Upper</span><span class="ind-val c-red">${{loc(s.bb_upper)}}</span></div>
                                <div class="ind-row"><span class="ind-label">BB Width</span><span class="ind-val">${{f2(s.bb_width)}}%</span></div>
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

    // Radar for expanded
    if (expandedRow) {{
        const s = ALL_STOCKS.find(x => x.symbol === expandedRow);
        if (s) drawRadar(s);
    }}

    // Sort header styles
    document.querySelectorAll('.screener-tbl thead th').forEach(th => {{
        th.classList.remove('sorted-asc','sorted-desc');
        if (th.dataset.sort === sortCol) th.classList.add('sorted-'+sortDir);
    }});

    // Pagination
    document.getElementById('pageInfo').textContent = total > 0 ? (start+1)+'-'+Math.min(start+PAGE_SIZE,total)+' / '+total+' co phieu' : '0 co phieu';
    const pb = document.getElementById('pageBtns');
    let btns = `<button class="pg-btn" onclick="goPage(1)" ${{currentPage===1?'disabled':''}}>&laquo;</button>`;
    btns += `<button class="pg-btn" onclick="goPage(${{currentPage-1}})" ${{currentPage===1?'disabled':''}}>&lsaquo;</button>`;
    let sp = Math.max(1, currentPage-2), ep = Math.min(totalPages, currentPage+2);
    for (let p=sp; p<=ep; p++) btns += `<button class="pg-btn ${{p===currentPage?'active':''}}" onclick="goPage(${{p}})">${{p}}</button>`;
    btns += `<button class="pg-btn" onclick="goPage(${{currentPage+1}})" ${{currentPage===totalPages?'disabled':''}}>&rsaquo;</button>`;
    btns += `<button class="pg-btn" onclick="goPage(${{totalPages}})" ${{currentPage===totalPages?'disabled':''}}>&raquo;</button>`;
    pb.innerHTML = btns;
}}

function toggleExpand(sym) {{ expandedRow = expandedRow === sym ? null : sym; renderScreener(); }}
function goPage(p) {{ currentPage = Math.max(1,p); expandedRow = null; renderScreener(); }}

// Sort headers
document.querySelectorAll('.screener-tbl thead th[data-sort]').forEach(th => {{
    th.addEventListener('click', e => {{
        e.stopPropagation();
        const col = th.dataset.sort;
        if (sortCol === col) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        else {{ sortCol = col; sortDir = 'desc'; }}
        currentPage = 1; expandedRow = null; renderScreener();
    }});
}});

// ===========================
// RADAR CHART
// ===========================
function drawRadar(stock) {{
    const canvas = document.getElementById('radar-' + stock.symbol);
    if (!canvas) return;
    new Chart(canvas.getContext('2d'), {{
        type: 'radar',
        data: {{
            labels: ['RSI', 'MFI', 'Volume', 'Quality', 'Momentum', 'Channel'],
            datasets: [{{
                data: [
                    Math.min(n(stock.rsi),100),
                    Math.min(n(stock.mfi),100),
                    Math.min(n(stock.vol_ratio)/3*100,100),
                    Math.min(n(stock.quality_score)/25*100,100),
                    Math.min(n(stock.momentum_score)/15*100,100),
                    Math.min(n(stock.channel_position),100)
                ],
                backgroundColor: 'rgba(59,130,246,0.12)',
                borderColor: 'rgba(59,130,246,0.7)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(59,130,246,1)',
                pointRadius: 3,
            }}]
        }},
        options: {{
            responsive: false,
            scales: {{
                r: {{
                    beginAtZero: true, max: 100,
                    ticks: {{ display: false }},
                    grid: {{ color: 'rgba(30,41,59,0.4)' }},
                    angleLines: {{ color: 'rgba(30,41,59,0.4)' }},
                    pointLabels: {{ color: '#9ca3af', font: {{ size: 10, family: "'JetBrains Mono', monospace" }} }}
                }}
            }},
            plugins: {{ legend: {{ display: false }} }}
        }}
    }});
}}

// ===========================
// WATCHLIST
// ===========================
function addWatchlist() {{
    const input = document.getElementById('watchlistInput');
    const sym = input.value.toUpperCase().trim();
    if (!sym || watchlist.includes(sym)) return;
    watchlist.push(sym);
    localStorage.setItem('vns_watchlist', JSON.stringify(watchlist));
    input.value = '';
    renderWatchlist();
}}

function removeWatchlist(sym) {{
    watchlist = watchlist.filter(s => s !== sym);
    localStorage.setItem('vns_watchlist', JSON.stringify(watchlist));
    renderWatchlist();
}}

function renderWatchlist() {{
    const tbody = document.getElementById('watchlistBody');
    if (!tbody) return;
    if (watchlist.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:24px">Chua co ma nao trong watchlist</td></tr>';
        return;
    }}
    tbody.innerHTML = watchlist.map(sym => {{
        const s = ALL_STOCKS.find(x => x.symbol === sym);
        if (!s) return `<tr><td class="stock-sym">${{sym}}</td><td colspan="4" class="c-muted">Khong co du lieu</td><td><button class="btn-link" onclick="removeWatchlist('${{sym}}')" style="color:var(--red)">Xoa</button></td></tr>`;
        return `<tr onclick="goToScreener('${{sym}}')">
            <td class="stock-sym">${{sym}}</td>
            <td class="mono">${{loc(s.close)}}</td>
            <td>${{gauge(n(s.score_100),32)}}</td>
            <td>${{rsiBar(n(s.rsi))}}</td>
            <td>${{sigBadge(s.signal_label)}}</td>
            <td><button class="btn-link" onclick="event.stopPropagation();removeWatchlist('${{sym}}')" style="color:var(--red)">Xoa</button></td>
        </tr>`;
    }}).join('');
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
        .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
        .replace(/\\*(.+?)\\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\\/li>\\n?)+/g, m => '<ul>' + m + '</ul>')
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
    if (currentTab !== 'screener') switchTab('screener');
    else {{ currentPage = 1; expandedRow = null; renderScreener(); }}
}});

// Enter on watchlist input
document.getElementById('watchlistInput').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') addWatchlist();
}});

// ===========================
// CHARTS
// ===========================
function initCharts() {{
    const chartFont = {{ family: "'JetBrains Mono', monospace", size: 10 }};
    const legendOpts = {{
        position: 'bottom',
        labels: {{ color: '#9ca3af', padding: 10, font: chartFont }}
    }};

    // Breadth donut
    new Chart(document.getElementById('breadthChart'), {{
        type: 'doughnut',
        data: {{
            labels: ['Uptrend', 'Sideways', 'Downtrend'],
            datasets: [{{
                data: [{stats['uptrend']}, {stats['sideways']}, {stats['downtrend']}],
                backgroundColor: ['#22c55e', '#6b7280', '#ef4444'],
                borderWidth: 0, borderRadius: 3
            }}]
        }},
        options: {{
            responsive: true, cutout: '68%',
            plugins: {{ legend: legendOpts }}
        }}
    }});

    // Signal bar chart
    new Chart(document.getElementById('signalBarChart'), {{
        type: 'bar',
        data: {{
            labels: ['Breakout', 'Momentum', 'Pullback', 'Reversal'],
            datasets: [{{
                data: [{stats['breakout']}, {stats['momentum']}, {stats['pullback']}, {stats['reversal']}],
                backgroundColor: ['#22c55e', '#3b82f6', '#eab308', '#8b5cf6'],
                borderWidth: 0, borderRadius: 4, maxBarThickness: 40
            }}]
        }},
        options: {{
            responsive: true, maintainAspectRatio: false,
            scales: {{
                y: {{
                    beginAtZero: true,
                    grid: {{ color: 'rgba(30,41,59,0.4)' }},
                    ticks: {{ color: '#6b7280', font: chartFont }}
                }},
                x: {{
                    grid: {{ display: false }},
                    ticks: {{ color: '#9ca3af', font: chartFont }}
                }}
            }},
            plugins: {{ legend: {{ display: false }} }}
        }}
    }});

    // Allocation donut (portfolio)
    const allocCanvas = document.getElementById('allocationChart');
    if (allocCanvas) {{
        const pos = POSITIONS || [];
        if (pos.length > 0) {{
            const labels = pos.map(p => p.symbol || '?');
            const values = pos.map(p => (p.quantity||0) * (p.current_price||p.entry_price||0));
            const colors = ['#3b82f6','#22c55e','#eab308','#8b5cf6','#06b6d4','#f97316','#ef4444','#ec4899'];
            new Chart(allocCanvas, {{
                type: 'doughnut',
                data: {{
                    labels: labels,
                    datasets: [{{ data: values, backgroundColor: colors.slice(0, labels.length), borderWidth: 0, borderRadius: 3 }}]
                }},
                options: {{
                    responsive: true, cutout: '65%',
                    plugins: {{ legend: legendOpts }}
                }}
            }});
        }} else {{
            allocCanvas.parentElement.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)">Chua co vi the</div>';
        }}
    }}
}}

// ===========================
// INIT
// ===========================
document.addEventListener('DOMContentLoaded', function() {{
    initIndexBar();
    initCharts();
    renderHeatmap();
    renderTopSignals();
    renderAIReport();
    renderWatchlist();
}});
'''

    def _generate_portfolio_table(self, positions):
        if not positions:
            return '<div style="text-align:center;padding:40px;color:var(--text-muted)">Chua co vi the nao. Portfolio dang 100% tien mat.</div>'

        total_value = sum(pos.get('quantity', 0) * pos.get('current_price', pos.get('entry_price', 0)) for pos in positions)

        rows = ''
        for pos in positions:
            symbol = pos.get('symbol', '')
            qty = pos.get('quantity', 0)
            entry = pos.get('entry_price', 0)
            current = pos.get('current_price', entry)
            pnl = pos.get('pnl_percent', 0)
            pnl_cls = 'c-green' if pnl >= 0 else 'c-red'
            pnl_sign = '+' if pnl >= 0 else ''
            weight = round(qty * current / total_value * 100, 1) if total_value > 0 else 0

            rows += f'''<tr>
                <td class="stock-sym">{symbol}</td>
                <td class="mono">{qty:,}</td>
                <td class="mono">{entry:,.0f}</td>
                <td class="mono">{current:,.0f}</td>
                <td class="mono {pnl_cls}">{pnl_sign}{pnl:.2f}%</td>
                <td>
                    <span class="mono">{weight}%</span>
                    <div class="weight-bar"><div class="weight-bar-fill" style="width:{weight}%;background:var(--blue)"></div></div>
                </td>
            </tr>'''

        return f'''<div style="overflow-x:auto">
            <table class="data-table">
                <thead><tr><th>Ma CK</th><th>So CP</th><th>Gia vao</th><th>Gia hien tai</th><th>P&L</th><th>Ty trong</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>'''

    def save_dashboard(self, output_path: str = 'docs/index.html'):
        html = self.generate_html()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Dashboard saved: {output_path}")

    def run(self):
        print("=" * 60)
        print("TAO DASHBOARD V7 - PROFESSIONAL FINANCIAL")
        print("=" * 60)
        self.save_dashboard()


if __name__ == "__main__":
    generator = DashboardGenerator()
    generator.run()
