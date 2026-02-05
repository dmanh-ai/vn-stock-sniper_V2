"""
VN Stock Sniper - Dashboard Generator V4
Tạo HTML Dashboard đầy đủ cho GitHub Pages
FIX: Xử lý NaN/None cho tất cả trường dữ liệu
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
    """Convert value to string safely, handling NaN/None"""
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    s = str(val)
    if s.lower() == 'nan':
        return default
    return s


def safe_float(val, default=0):
    """Convert value to float safely, handling NaN/None"""
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
    """Convert value to int safely"""
    return int(safe_float(val, default))


class DashboardGenerator:
    """Tạo HTML Dashboard"""
    
    def __init__(self):
        self.timezone = pytz.timezone(TIMEZONE)
        self.today = datetime.now(self.timezone).strftime("%d/%m/%Y")
        self.today_file = datetime.now(self.timezone).strftime("%Y-%m-%d")
    
    def load_data(self):
        """Load tất cả dữ liệu"""
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
        """Thống kê thị trường"""
        if self.analyzed_df.empty:
            return {
                'total': 0, 'uptrend': 0, 'sideways': 0, 'downtrend': 0,
                'star_5': 0, 'star_4': 0, 'signals': 0,
                'uptrend_pct': 0, 'sideways_pct': 0, 'downtrend_pct': 0
            }
        
        total = len(self.analyzed_df)
        uptrend = len(self.analyzed_df[self.analyzed_df['channel'].str.contains('XANH', na=False)])
        sideways = len(self.analyzed_df[self.analyzed_df['channel'].str.contains('XÁM', na=False)])
        downtrend = len(self.analyzed_df[self.analyzed_df['channel'].str.contains('ĐỎ', na=False)])
        
        return {
            'total': total,
            'uptrend': uptrend,
            'sideways': sideways,
            'downtrend': downtrend,
            'star_5': len(self.analyzed_df[self.analyzed_df['stars'] >= 5]),
            'star_4': len(self.analyzed_df[self.analyzed_df['stars'] == 4]),
            'signals': len(self.signals_df),
            'uptrend_pct': round(uptrend/total*100, 1) if total > 0 else 0,
            'sideways_pct': round(sideways/total*100, 1) if total > 0 else 0,
            'downtrend_pct': round(downtrend/total*100, 1) if total > 0 else 0
        }
    
    def get_portfolio_with_pnl(self):
        """Tính P&L portfolio"""
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
        """Clean NaN/inf from records for JSON serialization"""
        clean = []
        for row in records:
            item = {}
            for k, v in row.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    item[k] = None
                else:
                    item[k] = v
            clean.append(item)
        return clean
    
    def generate_html(self):
        """Tạo HTML dashboard"""
        self.load_data()
        stats = self.get_market_stats()
        positions, total_pnl = self.get_portfolio_with_pnl()
        
        top_stocks = self.analyzed_df.head(50).to_dict('records') if not self.analyzed_df.empty else []
        signals = self.signals_df.to_dict('records') if not self.signals_df.empty else []
        clean_stocks = self._clean_for_json(top_stocks)
        
        html = f'''<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VN Stock Sniper Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{ --bg-dark: #0d1117; --bg-card: #161b22; --border-color: #30363d; --text-primary: #e6edf3; --text-secondary: #8b949e; --green: #3fb950; --red: #f85149; --yellow: #d29922; --blue: #58a6ff; }}
        body {{ background-color: var(--bg-dark); color: var(--text-primary); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .card {{ background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; margin-bottom: 20px; }}
        .card-header {{ background-color: transparent; border-bottom: 1px solid var(--border-color); font-weight: 600; font-size: 1.1rem; }}
        .stat-card {{ text-align: center; padding: 20px; }}
        .stat-number {{ font-size: 2.5rem; font-weight: 700; }}
        .stat-label {{ color: var(--text-secondary); font-size: 0.9rem; }}
        .green {{ color: var(--green); }} .red {{ color: var(--red); }} .yellow {{ color: var(--yellow); }} .blue {{ color: var(--blue); }}
        .channel-green {{ background-color: rgba(63, 185, 80, 0.2); color: var(--green); padding: 4px 8px; border-radius: 4px; }}
        .channel-gray {{ background-color: rgba(139, 148, 158, 0.2); color: var(--text-secondary); padding: 4px 8px; border-radius: 4px; }}
        .channel-red {{ background-color: rgba(248, 81, 73, 0.2); color: var(--red); padding: 4px 8px; border-radius: 4px; }}
        .signal-badge {{ padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }}
        .signal-breakout {{ background-color: var(--green); color: #000; }}
        .signal-momentum {{ background-color: var(--blue); color: #000; }}
        .signal-pullback {{ background-color: var(--yellow); color: #000; }}
        .signal-reversal {{ background-color: #a371f7; color: #000; }}
        .stars {{ color: #d29922; font-size: 1.1rem; }}
        table {{ color: var(--text-primary) !important; }}
        table thead th {{ background-color: var(--bg-card) !important; color: var(--text-primary) !important; border-color: var(--border-color) !important; }}
        table tbody td {{ border-color: var(--border-color) !important; }}
        .dataTables_wrapper .dataTables_filter input, .dataTables_wrapper .dataTables_length select {{ background-color: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border-color); }}
        .dataTables_wrapper .dataTables_info, .dataTables_wrapper .dataTables_paginate {{ color: var(--text-secondary) !important; }}
        .page-link {{ background-color: var(--bg-card); color: var(--text-primary); border-color: var(--border-color); }}
        .ai-report {{ background-color: var(--bg-card); padding: 20px; border-radius: 12px; white-space: pre-wrap; font-family: inherit; line-height: 1.8; }}
        .indicator-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }}
        .indicator-item {{ background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; }}
        .indicator-label {{ font-size: 0.8rem; color: var(--text-secondary); }}
        .indicator-value {{ font-size: 1.2rem; font-weight: 600; }}
        .nav-tabs .nav-link {{ color: var(--text-secondary); border: none; }}
        .nav-tabs .nav-link.active {{ background-color: var(--bg-card); color: var(--text-primary); border-bottom: 2px solid var(--blue); }}
        .portfolio-card {{ border-left: 4px solid var(--blue); }}
        .pnl-positive {{ color: var(--green); }} .pnl-negative {{ color: var(--red); }}
        @media (max-width: 768px) {{ .stat-number {{ font-size: 1.8rem; }} .container {{ padding: 10px; }} }}
    </style>
</head>
<body>
    <div class="container-fluid py-4">
        <div class="text-center mb-4">
            <h1>VN Stock Sniper Dashboard</h1>
            <p class="text-secondary">Cap nhat: {self.today} | Phan tich {stats['total']} ma co phieu</p>
        </div>
        
        <div class="row mb-4">
            <div class="col-6 col-md-3"><div class="card stat-card"><div class="stat-number green">{stats['uptrend']}</div><div class="stat-label">Kenh Xanh ({stats['uptrend_pct']}%)</div></div></div>
            <div class="col-6 col-md-3"><div class="card stat-card"><div class="stat-number" style="color: var(--text-secondary)">{stats['sideways']}</div><div class="stat-label">Kenh Xam ({stats['sideways_pct']}%)</div></div></div>
            <div class="col-6 col-md-3"><div class="card stat-card"><div class="stat-number red">{stats['downtrend']}</div><div class="stat-label">Kenh Do ({stats['downtrend_pct']}%)</div></div></div>
            <div class="col-6 col-md-3"><div class="card stat-card"><div class="stat-number yellow">{stats['signals']}</div><div class="stat-label">Tin hieu MUA</div></div></div>
        </div>
        
        <div class="row mb-4">
            <div class="col-6 col-md-3"><div class="card stat-card"><div class="stat-number" style="color: #d29922">{stats['star_5']}</div><div class="stat-label">5 Sao</div></div></div>
            <div class="col-6 col-md-3"><div class="card stat-card"><div class="stat-number blue">{stats['star_4']}</div><div class="stat-label">4 Sao</div></div></div>
            <div class="col-6 col-md-6"><div class="card stat-card"><canvas id="channelChart" height="100"></canvas></div></div>
        </div>
        
        <ul class="nav nav-tabs mb-4" id="mainTabs">
            <li class="nav-item"><a class="nav-link active" data-bs-toggle="tab" href="#signals">Tin hieu MUA</a></li>
            <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#ranking">Bang xep hang</a></li>
            <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#portfolio">Portfolio</a></li>
            <li class="nav-item"><a class="nav-link" data-bs-toggle="tab" href="#ai-report">AI Report</a></li>
        </ul>
        
        <div class="tab-content">
            <div class="tab-pane fade show active" id="signals">
                <div class="card">
                    <div class="card-header">Tin hieu MUA hom nay ({len(signals)} tin hieu)</div>
                    <div class="card-body">{self._generate_signals_html(signals)}</div>
                </div>
            </div>
            
            <div class="tab-pane fade" id="ranking">
                <div class="card">
                    <div class="card-header">Top {len(top_stocks)} Co phieu theo diem</div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table id="stockTable" class="table table-dark table-striped">
                                <thead><tr><th>#</th><th>Ma</th><th>Gia</th><th>Q</th><th>M</th><th>Sao</th><th>Tin hieu</th><th>Kenh</th><th>RSI</th><th>MFI</th><th>Vol%</th></tr></thead>
                                <tbody>{self._generate_ranking_rows(top_stocks)}</tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="tab-pane fade" id="portfolio">
                <div class="card portfolio-card">
                    <div class="card-header">Portfolio cua ban</div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-6"><div class="stat-card"><div class="stat-number blue">{self.portfolio.get('cash_percent', 100)}%</div><div class="stat-label">Tien mat</div></div></div>
                            <div class="col-6"><div class="stat-card"><div class="stat-number {'pnl-positive' if total_pnl >= 0 else 'pnl-negative'}">{'+' if total_pnl >= 0 else ''}{total_pnl:.2f}%</div><div class="stat-label">Tong P&L</div></div></div>
                        </div>
                        {self._generate_portfolio_html(positions)}
                    </div>
                </div>
            </div>
            
            <div class="tab-pane fade" id="ai-report">
                <div class="card">
                    <div class="card-header">Bao cao phan tich AI</div>
                    <div class="card-body"><div class="ai-report">{self.ai_report if self.ai_report else 'Chua co bao cao AI. Chay workflow de tao bao cao.'}</div></div>
                </div>
            </div>
        </div>
        
        <div class="modal fade" id="stockModal" tabindex="-1">
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
                <div class="modal-content" style="background-color: var(--bg-card); color: var(--text-primary);">
                    <div class="modal-header" style="border-color: var(--border-color);"><h5 class="modal-title" id="stockModalTitle">Chi tiet co phieu</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
                    <div class="modal-body" id="stockModalBody"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    
    <script>
        const ctx = document.getElementById('channelChart').getContext('2d');
        new Chart(ctx, {{ type: 'doughnut', data: {{ labels: ['Xanh', 'Xam', 'Do'], datasets: [{{ data: [{stats['uptrend']}, {stats['sideways']}, {stats['downtrend']}], backgroundColor: ['#3fb950', '#8b949e', '#f85149'], borderWidth: 0 }}] }}, options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }} }});
        
        $(document).ready(function() {{
            $('#stockTable').DataTable({{ pageLength: 20, order: [[3, 'desc'], [4, 'desc']], language: {{ search: "Tim kiem:", lengthMenu: "Hien thi _MENU_ ma", info: "Hien thi _START_ - _END_ / _TOTAL_ ma", paginate: {{ first: "Dau", last: "Cuoi", next: "Sau", previous: "Truoc" }} }} }});
        }});
        
        const stockData = {json.dumps(clean_stocks, ensure_ascii=False, default=str)};
        
        function showStockDetail(symbol) {{
            const stock = stockData.find(s => s.symbol === symbol);
            if (!stock) return;
            document.getElementById('stockModalTitle').textContent = symbol + ' - Chi tiet chi bao';
            
            const n = (v) => Number(v || 0);
            const f1 = (v) => n(v).toFixed(1);
            const f2 = (v) => n(v).toFixed(2);
            const f3 = (v) => n(v).toFixed(3);
            const loc = (v) => n(v).toLocaleString();
            const yn = (v) => v ? 'YES' : 'No';
            
            let html = '<div class="row mb-4">';
            html += '<div class="col-md-4"><div class="card stat-card"><div class="stat-number">' + loc(stock.close) + '</div><div class="stat-label">Gia hien tai</div></div></div>';
            html += '<div class="col-md-4"><div class="card stat-card"><div class="stat-number">' + n(stock.quality_score) + '/' + n(stock.momentum_score) + '</div><div class="stat-label">Q / M Score</div></div></div>';
            html += '<div class="col-md-4"><div class="card stat-card"><div class="stat-number stars">' + '⭐'.repeat(n(stock.stars)) + '</div><div class="stat-label">' + n(stock.stars) + ' Sao</div></div></div>';
            html += '</div>';
            
            html += '<h6>Trend & Channel</h6><div class="indicator-grid mb-4">';
            html += '<div class="indicator-item"><div class="indicator-label">Kenh</div><div class="indicator-value">' + (stock.channel || '-') + '</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">LR Slope %</div><div class="indicator-value">' + f3(stock.lr_slope_pct) + '%</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">Channel Pos</div><div class="indicator-value">' + f1(stock.channel_position) + '%</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">MA Aligned</div><div class="indicator-value">' + yn(stock.ma_aligned) + '</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">Above MA200</div><div class="indicator-value">' + yn(stock.above_ma200) + '</div></div>';
            html += '</div>';
            
            html += '<h6>Moving Averages</h6><div class="indicator-grid mb-4">';
            ['ma5','ma10','ma20','ma50','ma200'].forEach(k => {{
                html += '<div class="indicator-item"><div class="indicator-label">' + k.toUpperCase() + '</div><div class="indicator-value">' + loc(stock[k]) + '</div></div>';
            }});
            html += '</div>';
            
            html += '<h6>Momentum</h6><div class="indicator-grid mb-4">';
            html += '<div class="indicator-item"><div class="indicator-label">RSI</div><div class="indicator-value">' + f1(stock.rsi) + '</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">MFI</div><div class="indicator-value">' + f1(stock.mfi) + '</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">MACD</div><div class="indicator-value">' + (stock.macd_bullish ? 'Bullish' : 'Bearish') + '</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">Stoch K</div><div class="indicator-value">' + f1(stock.stoch_k) + '</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">Stoch D</div><div class="indicator-value">' + f1(stock.stoch_d) + '</div></div>';
            html += '</div>';
            
            html += '<h6>Volume & Volatility</h6><div class="indicator-grid mb-4">';
            html += '<div class="indicator-item"><div class="indicator-label">Vol Ratio</div><div class="indicator-value">' + f2(stock.vol_ratio) + 'x</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">Vol Surge</div><div class="indicator-value">' + yn(stock.vol_surge) + '</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">ATR %</div><div class="indicator-value">' + f2(stock.atr_percent) + '%</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">BB %</div><div class="indicator-value">' + f1(stock.bb_percent) + '%</div></div>';
            html += '<div class="indicator-item"><div class="indicator-label">BB Squeeze</div><div class="indicator-value">' + yn(stock.bb_squeeze) + '</div></div>';
            html += '</div>';
            
            document.getElementById('stockModalBody').innerHTML = html;
            new bootstrap.Modal(document.getElementById('stockModal')).show();
        }}
    </script>
</body>
</html>'''
        
        return html
    
    def _generate_signals_html(self, signals):
        """Tạo HTML cho signals"""
        if not signals:
            return '<p class="text-secondary text-center">Khong co tin hieu MUA hom nay</p>'
        
        html = '<div class="row">'
        for signal in signals:
            symbol = safe_str(signal.get('symbol', ''))
            signal_type = safe_str(signal.get('buy_signal', ''))
            close = safe_float(signal.get('close', 0))
            q_score = safe_float(signal.get('quality_score', 0))
            m_score = safe_float(signal.get('momentum_score', 0))
            stars = safe_int(signal.get('stars', 0))
            rsi = safe_float(signal.get('rsi', 0))
            
            atr = safe_float(signal.get('atr', 0))
            if atr == 0:
                atr = close * 0.03
            entry = close
            sl = round(close - 2 * atr, 0)
            tp1 = round(close + 3 * atr, 0)
            tp2 = round(close + 5 * atr, 0)
            sl_pct = round((sl - entry) / entry * 100, 1) if entry > 0 else 0
            tp1_pct = round((tp1 - entry) / entry * 100, 1) if entry > 0 else 0
            tp2_pct = round((tp2 - entry) / entry * 100, 1) if entry > 0 else 0
            
            sig_cls = {'BREAKOUT': 'signal-breakout', 'MOMENTUM': 'signal-momentum', 'PULLBACK': 'signal-pullback', 'REVERSAL': 'signal-reversal'}.get(signal_type, '')
            
            html += f'''
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="card h-100" style="cursor: pointer;" onclick="showStockDetail('{symbol}')">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="mb-0">{symbol}</h5>
                            <span class="signal-badge {sig_cls}">{signal_type}</span>
                        </div>
                        <div class="stars mb-2">{'⭐' * stars}</div>
                        <div class="row text-center mb-3">
                            <div class="col-4"><div class="text-secondary small">Gia</div><div class="fw-bold">{close:,.0f}</div></div>
                            <div class="col-4"><div class="text-secondary small">Q/M</div><div class="fw-bold">{q_score:.0f}/{m_score:.0f}</div></div>
                            <div class="col-4"><div class="text-secondary small">RSI</div><div class="fw-bold">{rsi:.1f}</div></div>
                        </div>
                        <div class="small">
                            <div class="d-flex justify-content-between"><span>Entry:</span><span class="fw-bold">{entry:,.0f}</span></div>
                            <div class="d-flex justify-content-between"><span>Stop Loss:</span><span class="red">{sl:,.0f} ({sl_pct}%)</span></div>
                            <div class="d-flex justify-content-between"><span>Target 1:</span><span class="green">{tp1:,.0f} (+{tp1_pct}%)</span></div>
                            <div class="d-flex justify-content-between"><span>Target 2:</span><span class="green">{tp2:,.0f} (+{tp2_pct}%)</span></div>
                        </div>
                    </div>
                </div>
            </div>'''
        
        html += '</div>'
        return html
    
    def _generate_ranking_rows(self, stocks):
        """Tạo rows cho bảng xếp hạng - XỬ LÝ NaN AN TOÀN"""
        html = ''
        for i, stock in enumerate(stocks, 1):
            symbol = safe_str(stock.get('symbol', ''))
            close = safe_float(stock.get('close', 0))
            q_score = safe_float(stock.get('quality_score', 0))
            m_score = safe_float(stock.get('momentum_score', 0))
            stars = safe_int(stock.get('stars', 0))
            signal = safe_str(stock.get('buy_signal', ''))
            channel = safe_str(stock.get('channel', ''))
            rsi = safe_float(stock.get('rsi', 0))
            mfi = safe_float(stock.get('mfi', 0))
            vol_ratio = safe_float(stock.get('vol_ratio', 0))
            
            # Channel class
            if 'XANH' in channel:
                ch_cls = 'channel-green'
            elif 'ĐỎ' in channel or 'DO' in channel:
                ch_cls = 'channel-red'
            else:
                ch_cls = 'channel-gray'
            
            # Signal badge - ĐÃ SỬA BUG: signal giờ luôn là str
            if signal:
                sig_cls = {'BREAKOUT': 'signal-breakout', 'MOMENTUM': 'signal-momentum', 'PULLBACK': 'signal-pullback', 'REVERSAL': 'signal-reversal'}.get(signal, '')
                sig_html = f'<span class="signal-badge {sig_cls}">{signal}</span>'
            else:
                sig_html = '-'
            
            # Clean channel
            ch_display = channel.replace('🟢 ', '').replace('🔴 ', '').replace('⚪ ', '') if channel else '-'
            
            rsi_cls = 'red' if rsi > 70 else ('green' if rsi < 30 else '')
            vol_cls = 'green' if vol_ratio > 1.5 else ''
            
            html += f'''
            <tr onclick="showStockDetail('{symbol}')" style="cursor: pointer;">
                <td>{i}</td>
                <td><strong>{symbol}</strong></td>
                <td>{close:,.0f}</td>
                <td>{q_score:.0f}</td>
                <td>{m_score:.0f}</td>
                <td class="stars">{'⭐' * stars}</td>
                <td>{sig_html}</td>
                <td><span class="{ch_cls}">{ch_display}</span></td>
                <td class="{rsi_cls}">{rsi:.1f}</td>
                <td>{mfi:.1f}</td>
                <td class="{vol_cls}">{vol_ratio:.1f}x</td>
            </tr>'''
        
        return html
    
    def _generate_portfolio_html(self, positions):
        """Tạo HTML cho portfolio"""
        if not positions:
            return '<div class="text-center text-secondary py-4"><p>Chua co vi the nao</p><p class="small">Dung Telegram Bot de them vi the:</p><code>/buy VCI 1000 37000</code></div>'
        
        html = '<div class="table-responsive"><table class="table table-dark"><thead><tr><th>Ma</th><th>So CP</th><th>Gia mua</th><th>Gia hien tai</th><th>P&L</th></tr></thead><tbody>'
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            qty = pos.get('quantity', 0)
            entry = pos.get('entry_price', 0)
            current = pos.get('current_price', entry)
            pnl = pos.get('pnl_percent', 0)
            pnl_cls = 'pnl-positive' if pnl >= 0 else 'pnl-negative'
            pnl_sign = '+' if pnl >= 0 else ''
            
            html += f'<tr><td><strong>{symbol}</strong></td><td>{qty:,}</td><td>{entry:,.0f}</td><td>{current:,.0f}</td><td class="{pnl_cls}">{pnl_sign}{pnl:.2f}%</td></tr>'
        
        html += '</tbody></table></div>'
        return html
    
    def save_dashboard(self, output_path: str = 'docs/index.html'):
        """Lưu dashboard ra file"""
        html = self.generate_html()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ Dashboard saved: {output_path}")
    
    def run(self):
        """Chạy tạo dashboard"""
        print("="*60)
        print("🌐 TẠO DASHBOARD")
        print("="*60)
        self.save_dashboard()


if __name__ == "__main__":
    generator = DashboardGenerator()
    generator.run()
