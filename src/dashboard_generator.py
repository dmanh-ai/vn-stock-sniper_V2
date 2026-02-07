"""
VN Stock Sniper - Dashboard Generator V8
Reference design: Sidebar nav, IBM Plex fonts, 11 modules
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


def safe_str(val, default=''):
    if val is None:
        return default
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return default
    s = str(val)
    if s.lower() == 'nan':
        return default
    return s


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
                'avg_rsi': 50, 'avg_mfi': 50, 'avg_score': 0,
                'vol_surge_count': 0, 'bb_squeeze_count': 0,
                'advance': 0, 'decline': 0, 'unchanged': 0,
            }
        df = self.analyzed_df
        total = len(df)
        uptrend = len(df[df['channel'].str.contains('XANH', na=False)])
        sideways = len(df[df['channel'].str.contains('XÁM', na=False)])
        downtrend = len(df[df['channel'].str.contains('ĐỎ', na=False)])
        advance = decline = unchanged = 0
        if 'change_pct' in df.columns:
            advance = len(df[df['change_pct'] > 0])
            decline = len(df[df['change_pct'] < 0])
            unchanged = len(df[df['change_pct'] == 0])
        elif 'close' in df.columns and 'open' in df.columns:
            advance = len(df[df['close'] > df['open']])
            decline = len(df[df['close'] < df['open']])
            unchanged = total - advance - decline
        buy_strong = buy = neutral = sell = sell_strong = 0
        for _, row in df.iterrows():
            label = get_signal_label(row.to_dict())
            if label == 'MUA MANH': buy_strong += 1
            elif label == 'MUA': buy += 1
            elif label == 'BAN MANH': sell_strong += 1
            elif label == 'BAN': sell += 1
            else: neutral += 1
        return {
            'total': total, 'uptrend': uptrend, 'sideways': sideways, 'downtrend': downtrend,
            'buy_strong': buy_strong, 'buy': buy, 'neutral': neutral,
            'sell': sell, 'sell_strong': sell_strong,
            'avg_rsi': round(safe_float(df['rsi'].mean(), 50), 1),
            'avg_mfi': round(safe_float(df['mfi'].mean(), 50), 1),
            'avg_score': round(safe_float(df['total_score'].mean(), 0), 1),
            'vol_surge_count': int(df['vol_surge'].sum()) if 'vol_surge' in df.columns else 0,
            'bb_squeeze_count': int(df['bb_squeeze'].sum()) if 'bb_squeeze' in df.columns else 0,
            'advance': advance, 'decline': decline, 'unchanged': unchanged,
        }

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

        all_stocks = self.analyzed_df.to_dict('records') if not self.analyzed_df.empty else []
        signals = self.signals_df.to_dict('records') if not self.signals_df.empty else []
        clean_stocks = self._clean_for_json(all_stocks)
        clean_signals = self._clean_for_json(signals)

        for stock in clean_stocks:
            stock['signal_label'] = get_signal_label(stock)
            stock['score_100'] = round(safe_float(stock.get('total_score', 0)) / 40 * 100, 0)

        positions = self.portfolio.get('positions', [])
        for pos in positions:
            symbol = pos.get('symbol', '')
            if not self.analyzed_df.empty:
                sd = self.analyzed_df[self.analyzed_df['symbol'] == symbol]
                if not sd.empty:
                    pos['current_price'] = float(sd.iloc[0]['close'])
                    ep = pos.get('entry_price', 0)
                    pos['pnl_percent'] = round((pos['current_price'] - ep) / ep * 100, 2) if ep > 0 else 0

        ai_escaped = self.ai_report.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${') if self.ai_report else ''

        stocks_json = json.dumps(clean_stocks, ensure_ascii=False, default=str)
        signals_json = json.dumps(clean_signals, ensure_ascii=False, default=str)
        stats_json = json.dumps(stats, ensure_ascii=False)
        positions_json = json.dumps(positions, ensure_ascii=False, default=str)

        html = self._build_html(stocks_json, signals_json, stats_json, positions_json, ai_escaped)
        return html

    def _build_html(self, stocks_json, signals_json, stats_json, positions_json, ai_report):
        return f'''<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VN Stock Sniper Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#06090f;--s1:#0d1117;--s2:#151b26;--s3:#1c2433;--s4:#243044;
  --brd:#1b2230;--brd2:#2a3548;
  --t1:#e6edf3;--t2:#8b949e;--t3:#545d68;--t4:#373e47;
  --g:#2ea043;--g2:#3fb950;--gd:rgba(46,160,67,.12);
  --r:#da3633;--r2:#f85149;--rd:rgba(218,54,51,.12);
  --b:#1f6feb;--b2:#58a6ff;--bd:rgba(31,111,235,.1);
  --a:#d29922;--a2:#e3b341;--ad:rgba(210,153,34,.1);
  --p:#8957e5;--p2:#a371f7;--pd:rgba(137,87,229,.1);
  --c:#39d2c0;--c2:#56d4c8;--cd:rgba(57,210,192,.1);
  --o:#db6d28;--o2:#f0883e;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'IBM Plex Sans',system-ui;background:var(--bg);color:var(--t1);-webkit-font-smoothing:antialiased}}
::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:var(--s1)}}
::-webkit-scrollbar-thumb{{background:var(--s3);border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:var(--s4)}}
.app{{display:flex;height:100vh;overflow:hidden}}
.sidebar{{width:200px;background:var(--s1);border-right:1px solid var(--brd);display:flex;flex-direction:column;flex-shrink:0}}
.sb-logo{{padding:16px 18px;border-bottom:1px solid var(--brd)}}
.sb-logo h1{{font-family:'IBM Plex Mono';font-size:12px;font-weight:700;color:var(--b2);letter-spacing:1.5px}}
.sb-logo span{{font-size:8px;color:var(--t3);letter-spacing:2px;text-transform:uppercase;display:block;margin-top:3px}}
.sb-nav{{flex:1;padding:8px;overflow-y:auto}}
.nb{{width:100%;display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;border:none;background:none;color:var(--t3);font:500 12px 'IBM Plex Sans';cursor:pointer;transition:all .12s;text-align:left}}
.nb:hover{{background:var(--s2);color:var(--t2)}}
.nb.on{{background:var(--bd);color:var(--b2);font-weight:600}}
.nb .ic{{width:18px;text-align:center;font-size:14px}}
.sb-ft{{padding:12px 16px;border-top:1px solid var(--brd);font-size:9px;color:var(--t4)}}
.main{{flex:1;display:flex;flex-direction:column;overflow:hidden}}
.hdr{{height:48px;background:var(--s1);border-bottom:1px solid var(--brd);display:flex;align-items:center;justify-content:space-between;padding:0 20px;flex-shrink:0}}
.hdr-left{{display:flex;align-items:center;gap:12px}}
.hdr h2{{font-size:14px;font-weight:700}}
.hdr-tag{{font:600 9px 'IBM Plex Mono';padding:3px 8px;border-radius:4px;letter-spacing:.5px}}
.hdr-right{{display:flex;align-items:center;gap:12px}}
.srch{{width:180px;background:var(--s2);border:1px solid var(--brd);border-radius:6px;padding:6px 10px;font:500 11px 'IBM Plex Mono';color:var(--t1);outline:none}}
.srch:focus{{border-color:var(--b)}}
.srch::placeholder{{color:var(--t4)}}
.clk{{font:500 10px 'IBM Plex Mono';color:var(--t3)}}
.view{{flex:1;overflow-y:auto;overflow-x:hidden;padding:16px 20px 32px}}
.sbar{{height:28px;background:var(--s1);border-top:1px solid var(--brd);display:flex;align-items:center;padding:0 16px;gap:20px;flex-shrink:0}}
.si{{display:flex;align-items:center;gap:5px;font-size:9px;color:var(--t4)}}
.si .dot{{width:5px;height:5px;border-radius:50%}}
.si b{{color:var(--t3);font-weight:600}}
.g1{{display:grid;gap:12px}}
.g1-3{{grid-template-columns:repeat(3,1fr)}}
.g1-4{{grid-template-columns:repeat(4,1fr)}}
.g1-2{{grid-template-columns:1fr 1fr}}
.g1-21{{grid-template-columns:2fr 1fr}}
.g1-12{{grid-template-columns:1fr 2fr}}
.mb12{{margin-bottom:12px}}
.mb16{{margin-bottom:16px}}
.mb8{{margin-bottom:8px}}
.cd{{background:var(--s1);border:1px solid var(--brd);border-radius:10px;padding:16px;transition:border .2s}}
.cd:hover{{border-color:var(--brd2)}}
.cd-sm{{padding:12px}}
.cd-title{{font:600 9px 'IBM Plex Mono';color:var(--t3);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px}}
.cd-title2{{font:600 10px 'IBM Plex Sans';color:var(--t2);margin-bottom:8px}}
.big-num{{font:700 24px 'IBM Plex Mono';letter-spacing:-1px}}
.mid-num{{font:700 18px 'IBM Plex Mono';letter-spacing:-.5px}}
.sm-num{{font:600 13px 'IBM Plex Mono'}}
.xs-num{{font:600 11px 'IBM Plex Mono'}}
.label{{font-size:10px;color:var(--t3);margin-top:2px}}
.up{{color:var(--g2)}}.dn{{color:var(--r2)}}.neu{{color:var(--a2)}}.blu{{color:var(--b2)}}
.bdg{{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:100px;font:600 10px 'IBM Plex Mono';letter-spacing:.3px}}
.bdg-g{{background:var(--gd);color:var(--g2);border:1px solid rgba(46,160,67,.2)}}
.bdg-r{{background:var(--rd);color:var(--r2);border:1px solid rgba(218,54,51,.2)}}
.bdg-b{{background:var(--bd);color:var(--b2);border:1px solid rgba(31,111,235,.2)}}
.bdg-a{{background:var(--ad);color:var(--a2);border:1px solid rgba(210,153,34,.2)}}
.bdg-p{{background:var(--pd);color:var(--p2);border:1px solid rgba(137,87,229,.2)}}
.bdg-c{{background:var(--cd);color:var(--c2);border:1px solid rgba(57,210,192,.2)}}
.spark{{display:flex;align-items:end;gap:1px;height:36px}}
.spark div{{flex:1;border-radius:1px 1px 0 0;min-width:1.5px;opacity:.7}}
.mbar{{display:flex;align-items:end;gap:2px;height:50px}}
.mbar div{{flex:1;border-radius:2px 2px 0 0;min-width:3px;transition:opacity .15s}}
.mbar div:hover{{opacity:1!important}}
.pbar{{height:4px;background:var(--s3);border-radius:2px;overflow:hidden}}
.pbar div{{height:100%;border-radius:2px;transition:width .5s}}
.gauge{{position:relative;width:100%;height:8px;background:var(--s3);border-radius:4px;overflow:visible}}
.gauge-fill{{height:100%;border-radius:4px;transition:width .5s}}
.gauge-mark{{position:absolute;top:-3px;width:2px;height:14px;background:var(--t1);border-radius:1px;transition:left .5s}}
.row{{display:flex;justify-content:space-between;align-items:center;padding:5px 0;font-size:11px}}
.row-sym{{font:600 11px 'IBM Plex Mono';color:var(--t1)}}
.row-val{{font:600 11px 'IBM Plex Mono'}}
.dvd{{border-top:1px solid var(--brd);margin:12px 0}}
.dvd-sm{{border-top:1px solid var(--brd);margin:8px 0}}
.tabs{{display:flex;gap:2px;margin-bottom:12px;background:var(--s2);padding:2px;border-radius:6px}}
.tab{{flex:1;padding:6px 8px;border-radius:5px;border:none;background:none;font:500 10px 'IBM Plex Sans';color:var(--t3);cursor:pointer;transition:all .12s;text-align:center}}
.tab:hover{{color:var(--t2)}}
.tab.on{{background:var(--s3);color:var(--t1);font-weight:600}}
.hm{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}
.hm-cell{{padding:12px 8px;border-radius:8px;text-align:center;cursor:pointer;transition:all .15s;border:1px solid transparent}}
.hm-cell:hover{{border-color:rgba(255,255,255,.08);transform:scale(1.02)}}
.hm-name{{font-size:10px;font-weight:600;color:rgba(255,255,255,.8);margin-bottom:3px}}
.hm-val{{font:700 13px 'IBM Plex Mono'}}
.hm-sub{{font-size:8px;color:rgba(255,255,255,.4);margin-top:2px}}
.sig{{display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--s2);border-radius:8px;margin-bottom:6px;border-left:3px solid}}
.sig-name{{font-size:11px;font-weight:600;color:var(--t2);flex:1}}
.sig-val{{font:700 14px 'IBM Plex Mono';margin-right:8px}}
.sbar-h{{display:flex;align-items:center;gap:8px;padding:6px 0}}
.sbar-name{{font-size:11px;font-weight:500;color:var(--t2);width:80px;flex-shrink:0}}
.sbar-track{{flex:1;height:8px;background:var(--s3);border-radius:4px;overflow:hidden;position:relative}}
.sbar-fill{{height:100%;border-radius:4px;transition:width .4s}}
.sbar-pct{{font:600 11px 'IBM Plex Mono';width:55px;text-align:right;flex-shrink:0}}
.icard{{padding:12px;background:var(--s2);border-radius:8px;border:1px solid var(--brd)}}
.icard-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.icard-name{{font-size:10px;font-weight:600;color:var(--t3);text-transform:uppercase;letter-spacing:.5px}}
.cs{{display:flex;flex-direction:column;align-items:center;justify-content:center;height:200px}}
.cs-icon{{font-size:36px;margin-bottom:12px}}
.cs-title{{font-size:15px;font-weight:700;color:var(--t2);margin-bottom:6px}}
.cs-desc{{font-size:11px;color:var(--t4)}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
.fade-in{{animation:fadeUp .3s ease-out both}}
.d1{{animation-delay:.05s}}.d2{{animation-delay:.1s}}.d3{{animation-delay:.15s}}.d4{{animation-delay:.2s}}.d5{{animation-delay:.25s}}
canvas{{display:block;width:100%;border-radius:6px}}
/* Screener table */
.scr-tbl{{width:100%;border-collapse:collapse;font-size:11px}}
.scr-tbl th{{position:sticky;top:0;background:var(--s2);padding:8px 6px;text-align:left;font:600 9px 'IBM Plex Mono';color:var(--t3);letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid var(--brd);cursor:pointer;user-select:none}}
.scr-tbl th:hover{{color:var(--t1)}}
.scr-tbl td{{padding:6px;border-bottom:1px solid var(--brd)}}
.scr-tbl tr:hover td{{background:var(--s2)}}
/* AI report */
.ai-box{{background:var(--s2);border:1px solid var(--brd);border-radius:10px;padding:20px;font-size:12px;line-height:1.8;color:var(--t2);white-space:pre-wrap;max-height:70vh;overflow-y:auto}}
.ai-box h1,.ai-box h2,.ai-box h3{{color:var(--t1);margin:16px 0 8px}}
.ai-box strong{{color:var(--t1)}}
.ai-box em{{color:var(--a2)}}
/* Filter bar */
.fbar{{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center}}
.fbar select,.fbar input{{background:var(--s2);border:1px solid var(--brd);border-radius:6px;padding:6px 10px;font:500 11px 'IBM Plex Mono';color:var(--t1);outline:none}}
.fbar select:focus,.fbar input:focus{{border-color:var(--b)}}
</style>
</head>
<body>
<div class="app">
  <nav class="sidebar">
    <div class="sb-logo"><h1>VN SNIPER</h1><span>Market Analytics v8</span></div>
    <div class="sb-nav" id="nav"></div>
    <div class="sb-ft">VN Stock Sniper<br>{self.today} • FiinQuant</div>
  </nav>
  <div class="main">
    <header class="hdr">
      <div class="hdr-left">
        <h2 id="pageTitle">Tổng Quan Thị Trường</h2>
        <span class="hdr-tag" id="pageBadge" style="background:var(--gd);color:var(--g2)">LIVE</span>
      </div>
      <div class="hdr-right">
        <input class="srch" id="symInput" placeholder="Tìm mã CK..." onkeydown="if(event.key==='Enter')searchSym()"/>
        <div class="clk" id="clk"></div>
      </div>
    </header>
    <div class="view" id="view"></div>
    <div class="sbar">
      <div class="si"><div class="dot" style="background:var(--g)"></div>Data <b>FiinQuant</b></div>
      <div class="si"><div class="dot" style="background:var(--b)"></div>Stocks <b id="stockCount">--</b></div>
      <div class="si"><div class="dot" style="background:var(--a)"></div>Updated <b>{self.today}</b></div>
      <div class="si" style="margin-left:auto">Modules <b>11/11 Active</b></div>
    </div>
  </div>
</div>

<script>
// ═══════════════════════════════════════════
// DATA — Real pipeline data
// ═══════════════════════════════════════════
const ALL_STOCKS = {stocks_json};
const ALL_SIGNALS = {signals_json};
const STATS = {stats_json};
const POSITIONS = {positions_json};
const AI_REPORT = `{ai_report}`;

// Derived data
const STOCKS = ALL_STOCKS.sort((a,b)=>(b.total_score||0)-(a.total_score||0));
document.getElementById('stockCount').textContent = STOCKS.length;

// Build index data from stocks if available
const IDX = {{}};
['VNINDEX','VN30','HNX-INDEX','UPCOM'].forEach(code=>{{
  const s = STOCKS.find(x=>x.symbol===code);
  if(s){{
    const chg = s.close && s.open ? ((s.close-s.open)/s.open*100) : 0;
    IDX[code] = {{code, price:s.close||0, chg:+(chg).toFixed(2), pct:+(chg).toFixed(2), vol:s.volume||0}};
  }}
}});
// Ensure we have at least placeholder indices
if(!IDX['VNINDEX']) IDX['VNINDEX'] = {{code:'VNINDEX',price:0,chg:0,pct:0,vol:0}};
if(!IDX['VN30']) IDX['VN30'] = {{code:'VN30',price:0,chg:0,pct:0,vol:0}};

// Filter out index symbols from stock list for display
const DISPLAY_STOCKS = STOCKS.filter(s=>!['VNINDEX','VN30','HNX-INDEX','UPCOM'].includes(s.symbol));

// Build sector map
const SECTOR_MAP = {{}};
DISPLAY_STOCKS.forEach(s=>{{
  // Use channel or a simple sector heuristic
  const sym = s.symbol || '';
  // Group by first letter as a simple heuristic, or use channel
  let sector = 'Khác';
  const bankSyms = ['VCB','BID','CTG','TCB','MBB','ACB','HDB','VPB','TPB','STB','VIB','SHB','SSB','MSB','LPB','OCB','EIB','ABB','BAB','BVB','KLB','NAB','NVB','PGB','SGB','VAB','VBB'];
  const techSyms = ['FPT','CMG','ELC'];
  const steelSyms = ['HPG','HSG','NKG','TLH','POM','SMC'];
  const reSyms = ['VHM','VRE','VIC','NVL','DXG','KDH','NLG','PDR','DIG','HDG','CEO','LDG','NBB','SCR','QCG','HBC','CTD','FCN','HUT'];
  const secSyms = ['SSI','VND','HCM','SHS','VCI','MBS','ORS','CTS','BSI','AGR','APG','FTS','TVS','VDS','WSS'];
  const oilSyms = ['GAS','PLX','PVD','PVS','PVT','OIL','BSR','PVC'];
  const foodSyms = ['VNM','SAB','MSN','QNS','KDC','MCH'];
  if(bankSyms.includes(sym)) sector='Ngân hàng';
  else if(techSyms.includes(sym)) sector='Công nghệ';
  else if(steelSyms.includes(sym)) sector='Thép';
  else if(reSyms.includes(sym)) sector='BĐS';
  else if(secSyms.includes(sym)) sector='Chứng khoán';
  else if(oilSyms.includes(sym)) sector='Dầu khí';
  else if(foodSyms.includes(sym)) sector='Tiêu dùng';
  s._sector = sector;
  if(!SECTOR_MAP[sector]) SECTOR_MAP[sector] = [];
  SECTOR_MAP[sector].push(s);
}});

const SECTORS = Object.entries(SECTOR_MAP).map(([name, stocks])=>{{
  const avgScore = stocks.reduce((a,s)=>a+(s.total_score||0),0)/stocks.length;
  const adv = stocks.filter(s=>(s.close||0)>(s.open||0)).length;
  const dec = stocks.filter(s=>(s.close||0)<(s.open||0)).length;
  const chg = stocks.length > 0 ? stocks.reduce((a,s)=>{{
    const c = s.close||0, o = s.open||0;
    return a + (o>0 ? (c-o)/o*100 : 0);
  }},0)/stocks.length : 0;
  return {{name, stocks:stocks.map(s=>s.symbol), count:stocks.length, avgScore:+avgScore.toFixed(1), chg:+chg.toFixed(2), adv, dec}};
}}).sort((a,b)=>b.chg-a.chg);

const BREADTH = {{adv:STATS.advance||0, dec:STATS.decline||0, unch:STATS.unchanged||0}};

// Regime from stats
const regimeScore = STATS.avg_score||0;
let regimeLabel = 'SIDEWAYS', regimeColor = 'a';
if(regimeScore >= 25) {{ regimeLabel='BULL'; regimeColor='g'; }}
else if(regimeScore >= 18) {{ regimeLabel='RECOVERY'; regimeColor='b'; }}
else if(regimeScore >= 12) {{ regimeLabel='SIDEWAYS'; regimeColor='a'; }}
else if(regimeScore >= 6) {{ regimeLabel='CORRECTION'; regimeColor='o'; }}
else {{ regimeLabel='BEAR'; regimeColor='r'; }}

let activeSym = DISPLAY_STOCKS.length > 0 ? DISPLAY_STOCKS[0].symbol : 'FPT';
let activeTab = 'overview';

// ═══════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════
const MODS=[
  {{id:'overview',ic:'📈',lb:'Tổng Quan',tt:'Tổng Quan Thị Trường',tag:'LIVE',tc:'g'}},
  {{id:'technical',ic:'🔬',lb:'Kỹ Thuật',tt:'Phân Tích Kỹ Thuật',tag:'ACTIVE',tc:'b'}},
  {{id:'moneyflow',ic:'💰',lb:'Dòng Tiền',tt:'Dòng Tiền & Volume',tag:'ACTIVE',tc:'a'}},
  {{id:'sector',ic:'🏭',lb:'Ngành',tt:'Phân Tích Ngành',tag:'ACTIVE',tc:'c'}},
  {{id:'signals',ic:'🎯',lb:'Tín Hiệu',tt:'Tín Hiệu Giao Dịch',tag:'ACTIVE',tc:'p'}},
  {{id:'risk',ic:'🛡️',lb:'Rủi Ro',tt:'Quản Trị Rủi Ro',tag:'ACTIVE',tc:'o'}},
  {{id:'fundamental',ic:'📋',lb:'Cơ Bản',tt:'Điểm Số & Xếp Hạng',tag:'ACTIVE',tc:'c'}},
  {{id:'macro',ic:'🌐',lb:'Vĩ Mô',tt:'Vĩ Mô & Tin Tức',tag:'LIVE',tc:'a'}},
  {{id:'screener',ic:'🔍',lb:'Bộ Lọc CP',tt:'Bộ Lọc Cổ Phiếu',tag:'NEW',tc:'b'}},
  {{id:'portfolio',ic:'💼',lb:'Portfolio',tt:'Danh Mục Đầu Tư',tag:'NEW',tc:'g'}},
  {{id:'ai',ic:'🤖',lb:'AI Insights',tt:'Khuyến Nghị AI',tag:'AI',tc:'p'}},
];

function renderNav(){{
  document.getElementById('nav').innerHTML=MODS.map(m=>
    `<button class="nb ${{activeTab===m.id?'on':''}}" onclick="go('${{m.id}}')">
      <span class="ic">${{m.ic}}</span>${{m.lb}}</button>`
  ).join('');
}}

function go(id){{
  activeTab=id;
  const m=MODS.find(x=>x.id===id);
  document.getElementById('pageTitle').textContent=m.tt;
  const b=document.getElementById('pageBadge');
  if(m.tag){{b.textContent=m.tag;b.style.display='';b.style.background=`var(--${{m.tc}}d)`;b.style.color=`var(--${{m.tc}}2)`}}
  else{{b.style.display='none'}}
  renderNav();render();
}}

function searchSym(){{
  const v=document.getElementById('symInput').value.trim().toUpperCase();
  const found = DISPLAY_STOCKS.find(s=>s.symbol===v);
  if(found){{activeSym=v;go('technical')}}
  document.getElementById('symInput').value='';
}}

// ═══════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════
const fmt=n=>n!=null?n.toLocaleString('vi-VN'):'--';
const fmtB=n=>n!=null?(n/1e9).toFixed(1)+'B':'--';
const fmtK=n=>n!=null?(n/1000).toFixed(1)+'K':'--';
const pct=n=>(n>=0?'+':'')+Number(n||0).toFixed(2)+'%';
const clr=n=>n>=0?'up':'dn';

function sparkHTML(data,isUp,h=36){{
  if(!data||data.length===0) return '<div class="spark" style="height:'+h+'px"></div>';
  const mn=Math.min(...data),mx=Math.max(...data),rng=mx-mn||1;
  const c=isUp?'var(--g)':'var(--r)';
  return`<div class="spark" style="height:${{h}}px">${{data.map(v=>{{
    const ht=4+((v-mn)/rng)*(h-4);
    return`<div style="height:${{ht}}px;background:${{c}};opacity:${{.25+((v-mn)/rng)*.6}}"></div>`
  }}).join('')}}</div>`;
}}

function gaugeHTML(val,min=0,max=100,colors='var(--r),var(--a),var(--g)'){{
  const pctVal=Math.max(0,Math.min(100,((val-min)/(max-min))*100));
  return`<div class="gauge">
    <div class="gauge-fill" style="width:${{pctVal}}%;background:linear-gradient(90deg,${{colors}})"></div>
    <div class="gauge-mark" style="left:calc(${{pctVal}}% - 1px)"></div>
  </div>`;
}}

function miniTable(rows){{
  return rows.map(r=>`<div class="row"><span class="row-sym">${{r[0]}}</span><span class="row-val ${{r[2]||''}}">${{r[1]}}</span></div>`).join('');
}}

function getStockChg(s){{
  if(!s||!s.close||!s.open||s.open===0) return 0;
  return ((s.close-s.open)/s.open*100);
}}

// ═══════════════════════════════════════════
// MODULE 1: MARKET OVERVIEW
// ═══════════════════════════════════════════
function renderOverview(){{
  const idxKeys = Object.keys(IDX);
  const idxCards = idxKeys.map((k,i)=>{{
    const ix=IDX[k];
    const up=ix.chg>=0;
    return`<div class="cd cd-sm fade-in d${{i+1}}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span class="xs-num" style="color:var(--t3)">${{ix.code}}</span>
        <span class="bdg ${{up?'bdg-g':'bdg-r'}}">${{up?'▲':'▼'}} ${{Math.abs(ix.pct).toFixed(2)}}%</span>
      </div>
      <div class="big-num ${{up?'up':'dn'}}">${{fmt(ix.price)}}</div>
      <div class="label">Vol: ${{(ix.vol/1e6).toFixed(0)}}M</div>
    </div>`;
  }}).join('');

  const total=BREADTH.adv+BREADTH.dec+BREADTH.unch||1;
  const advW=(BREADTH.adv/total*100).toFixed(0);
  const decW=(BREADTH.dec/total*100).toFixed(0);
  const unchW=(100-advW-decW);

  const sentScore=Math.min(100,Math.max(0,Math.round(STATS.avg_score/40*100)));
  const sentLabel=sentScore>65?'Tham lam':sentScore>45?'Trung tính':'Sợ hãi';
  const sentColor=sentScore>65?'g':sentScore>45?'a':'r';

  // Top gainers/losers
  const sorted = [...DISPLAY_STOCKS].sort((a,b)=>getStockChg(b)-getStockChg(a));
  const topUp = sorted.filter(s=>getStockChg(s)>0).slice(0,5);
  const topDn = sorted.filter(s=>getStockChg(s)<0).slice(-5).reverse();

  // Volume bars
  const volStocks = [...DISPLAY_STOCKS].sort((a,b)=>(b.volume||0)-(a.volume||0)).slice(0,20);
  const volMax = Math.max(...volStocks.map(s=>s.volume||0),1);

  // Regime signals
  const regimeSignals = [];
  if(STATS.avg_rsi>55) regimeSignals.push('RSI trung bình '+STATS.avg_rsi+' → Bullish momentum');
  else if(STATS.avg_rsi<45) regimeSignals.push('RSI trung bình '+STATS.avg_rsi+' → Bearish momentum');
  else regimeSignals.push('RSI trung bình '+STATS.avg_rsi+' → Trung tính');
  if(STATS.uptrend>STATS.downtrend) regimeSignals.push(STATS.uptrend+' mã uptrend vs '+STATS.downtrend+' downtrend');
  regimeSignals.push('Điểm TB: '+STATS.avg_score+'/40 → '+regimeLabel);
  if(STATS.vol_surge_count>0) regimeSignals.push(STATS.vol_surge_count+' mã volume đột biến');
  if(STATS.bb_squeeze_count>0) regimeSignals.push(STATS.bb_squeeze_count+' mã BB squeeze (chuẩn bị breakout)');

  const allocEq = regimeLabel==='BULL'?80:regimeLabel==='RECOVERY'?60:regimeLabel==='SIDEWAYS'?40:regimeLabel==='CORRECTION'?20:5;
  const allocCash = regimeLabel==='BULL'?10:regimeLabel==='RECOVERY'?25:regimeLabel==='SIDEWAYS'?40:regimeLabel==='CORRECTION'?50:70;
  const allocHedge = 100-allocEq-allocCash;

  return`
  <div class="g1 g1-4 mb12">${{idxCards}}</div>
  <div class="g1 g1-21 mb12">
    <div class="cd fade-in d2">
      <div class="cd-title">Market Breadth — ${{STATS.total}} mã</div>
      <div style="display:flex;gap:20px;align-items:center;margin-bottom:12px">
        <div style="flex:1">
          <div style="display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--s3)">
            <div style="width:${{advW}}%;background:var(--g);opacity:.75"></div>
            <div style="width:${{unchW}}%;background:var(--t4);opacity:.2"></div>
            <div style="width:${{decW}}%;background:var(--r);opacity:.75"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:6px">
            <span class="xs-num up">${{BREADTH.adv}} tăng</span>
            <span class="xs-num" style="color:var(--t4)">${{BREADTH.unch}} ref</span>
            <span class="xs-num dn">${{BREADTH.dec}} giảm</span>
          </div>
        </div>
        <div style="text-align:center;padding-left:16px;border-left:1px solid var(--brd)">
          <div class="mid-num" style="color:${{BREADTH.adv>BREADTH.dec?'var(--g2)':'var(--r2)'}}">${{(BREADTH.adv/Math.max(BREADTH.dec,1)).toFixed(2)}}</div>
          <div class="label">A/D Ratio</div>
        </div>
      </div>
      <div class="dvd-sm"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          <div class="cd-title" style="color:var(--g2);margin-bottom:6px">▲ Top Tăng</div>
          ${{miniTable(topUp.map(s=>[s.symbol,pct(getStockChg(s)),'up']))}}
        </div>
        <div>
          <div class="cd-title" style="color:var(--r2);margin-bottom:6px">▼ Top Giảm</div>
          ${{miniTable(topDn.map(s=>[s.symbol,pct(getStockChg(s)),'dn']))}}
        </div>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div class="cd fade-in d3" style="border-color:var(--${{regimeColor}})30">
        <div class="cd-title">Market Regime</div>
        <div class="bdg bdg-${{regimeColor}}" style="font-size:14px;padding:5px 14px;margin-bottom:10px">${{regimeLabel}} <span style="opacity:.5;font-size:10px">${{STATS.avg_score}}/40</span></div>
        <div style="margin-bottom:10px">${{regimeSignals.map(s=>`<div style="font-size:10px;color:var(--t3);padding:2px 0">• ${{s}}</div>`).join('')}}</div>
        <div class="dvd-sm"></div>
        <div class="cd-title" style="margin-top:8px">Phân bổ đề xuất</div>
        ${{[['Cổ phiếu',allocEq,'b'],['Tiền mặt',allocCash,'t4'],['Phòng thủ',allocHedge,'a']].map(([l,v,c])=>
          `<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px"><span style="color:var(--t3)">${{l}}</span><span class="xs-num" style="color:var(--${{c==='t4'?'t2':c+'2'}})">${{v}}%</span></div>
          <div class="pbar" style="margin-bottom:6px"><div style="width:${{v}}%;background:var(--${{c==='t4'?'t4':c}})"></div></div>`
        ).join('')}}
      </div>
      <div class="cd cd-sm fade-in d4">
        <div class="cd-title">Sentiment Index</div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
          <div class="mid-num ${{sentColor==='g'?'up':sentColor==='r'?'dn':'neu'}}">${{sentScore}}</div>
          <span class="bdg bdg-${{sentColor}}">${{sentLabel}}</span>
        </div>
        ${{gaugeHTML(sentScore)}}
        <div style="display:flex;justify-content:space-between;font-size:8px;color:var(--t4);margin-top:4px"><span>0 Sợ hãi</span><span>50</span><span>100 Tham lam</span></div>
      </div>
    </div>
  </div>
  <div class="cd fade-in d5">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <div class="cd-title" style="margin-bottom:0">Top 20 thanh khoản</div>
      <div class="xs-num" style="color:var(--t3)">Volume (triệu CP)</div>
    </div>
    <div class="mbar" style="height:60px">${{volStocks.map(s=>{{
      const ht=4+((s.volume||0)/volMax)*56;
      const up=getStockChg(s)>=0;
      return`<div style="height:${{ht}}px;background:var(--${{up?'g':'r'}});opacity:.5" title="${{s.symbol}}: ${{(s.volume/1e6).toFixed(1)}}M"></div>`;
    }}).join('')}}</div>
    <div style="display:flex;justify-content:space-between;margin-top:6px;overflow:hidden">
      ${{volStocks.map(s=>`<span style="font-size:7px;color:var(--t4);flex:1;text-align:center;overflow:hidden">${{s.symbol}}</span>`).join('')}}
    </div>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 2: TECHNICAL ANALYSIS
// ═══════════════════════════════════════════
function renderTechnical(){{
  const s=DISPLAY_STOCKS.find(x=>x.symbol===activeSym)||DISPLAY_STOCKS[0];
  if(!s) return '<div class="cs"><div class="cs-icon">📊</div><div class="cs-title">Không có dữ liệu</div></div>';
  const chg=getStockChg(s);
  const up=chg>=0;
  const rsi=s.rsi||50;
  const macd_bull=s.macd_bullish;
  const stochK=s.stoch_k||50;
  const stochD=s.stoch_d||50;
  const mfi=s.mfi||50;
  const atrPct=s.atr_percent||0;
  const volRatio=s.vol_ratio||1;
  const bbPct=s.bb_percent||50;
  const score=s.total_score||0;
  const stars=s.stars||0;
  const channel=s.channel||'';

  const rsiSig=rsi<30?['OVERSOLD','r']:rsi>70?['OVERBOUGHT','r']:rsi>55?['BULLISH','g']:rsi<45?['BEARISH','r']:['NEUTRAL','a'];
  const macdSig=macd_bull?['BULLISH','g']:['BEARISH','r'];
  const trendSig=channel.includes('XANH')?'UPTREND':channel.includes('ĐỎ')?'DOWNTREND':'SIDEWAYS';
  const trendC={{UPTREND:'g',DOWNTREND:'r',SIDEWAYS:'a'}}[trendSig];

  const topSyms = DISPLAY_STOCKS.slice(0,10).map(x=>x.symbol);
  const symPicker=`<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:12px">${{
    topSyms.map(sym=>
      `<button onclick="activeSym='${{sym}}';render()" style="padding:4px 10px;border-radius:5px;border:1px solid ${{sym===activeSym?'var(--b)':'var(--brd)'}};background:${{sym===activeSym?'var(--bd)':'var(--s2)'}};color:${{sym===activeSym?'var(--b2)':'var(--t3)'}};font:600 10px 'IBM Plex Mono';cursor:pointer">${{sym}}</button>`
    ).join('')}}</div>`;

  return`
  ${{symPicker}}
  <div class="g1 g1-21 mb12">
    <div class="cd fade-in d1">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px">
        <div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
            <span style="font:700 15px 'IBM Plex Mono';color:var(--b2)">${{s.symbol}}</span>
            <span class="bdg bdg-${{trendC}}">${{trendSig}}</span>
            <span class="bdg bdg-${{stars>=4?'g':stars>=3?'a':'r'}}">${{stars}}★</span>
          </div>
          <div class="big-num ${{clr(chg)}}" style="font-size:28px">${{fmt(s.close)}}</div>
          <div class="label">${{up?'+':''}}\${{chg.toFixed(2)}}% • Vol: ${{((s.volume||0)/1e6).toFixed(1)}}M • Score: ${{score}}/40</div>
        </div>
        <div style="text-align:right">
          <div class="label">ATR%</div>
          <div class="sm-num" style="color:var(--t2)">${{(atrPct).toFixed(1)}}%</div>
          <div class="label" style="margin-top:4px">Vol Ratio</div>
          <div class="sm-num ${{volRatio>1.5?'neu':volRatio>1?'up':'dn'}}">${{volRatio.toFixed(2)}}x</div>
        </div>
      </div>
      <div class="cd-title">Key Levels</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px">
        ${{[
          ['MA 5',s.ma5,'b'],['MA 20',s.ma20,'b'],['MA 50',s.ma50,'b'],
          ['MA 200',s.ma200,'p'],['Support',s.support,'g'],['Resistance',s.resistance,'r'],
          ['BB Lower',s.bb_lower,'t2'],['BB Upper',s.bb_upper,'t2'],['BB%',bbPct?bbPct.toFixed(0)+'%':'--','t2'],
        ].map(([l,v,c])=>{{
          const display = typeof v === 'number' ? fmt(Math.round(v)) : (v||'--');
          return`<div class="icard">
            <div class="icard-name">${{l}}</div>
            <div class="sm-num" style="color:var(--${{c==='t2'?'t2':c+'2'}})">${{display}}</div>
          </div>`;
        }}).join('')}}
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div class="cd cd-sm fade-in d2">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span class="cd-title" style="margin:0">RSI (14)</span>
          <span class="bdg bdg-${{rsiSig[1]}}">${{rsiSig[0]}}</span>
        </div>
        <div class="big-num" style="color:var(--${{rsiSig[1]}}2);margin-bottom:8px">${{rsi.toFixed(1)}}</div>
        ${{gaugeHTML(rsi,0,100,'var(--r),var(--a),var(--g),var(--a),var(--r)')}}
        <div style="display:flex;justify-content:space-between;font-size:8px;color:var(--t4);margin-top:3px"><span>0</span><span style="color:var(--r2)">30</span><span>50</span><span style="color:var(--r2)">70</span><span>100</span></div>
      </div>
      <div class="cd cd-sm fade-in d3">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span class="cd-title" style="margin:0">MACD</span>
          <span class="bdg bdg-${{macdSig[1]}}">${{macdSig[0]}}</span>
        </div>
        <div class="sm-num ${{macd_bull?'up':'dn'}}">${{macd_bull?'Bullish Cross':'Bearish'}}</div>
      </div>
      <div class="cd cd-sm fade-in d4">
        <div class="cd-title">Stochastic (14,3)</div>
        <div style="display:flex;gap:16px;margin-bottom:6px">
          <div><div class="label">%K</div><div class="sm-num" style="color:var(--b2)">${{stochK.toFixed(1)}}</div></div>
          <div><div class="label">%D</div><div class="sm-num" style="color:var(--p2)">${{stochD.toFixed(1)}}</div></div>
        </div>
        ${{gaugeHTML(stochK,0,100,'var(--r),var(--a),var(--g)')}}
      </div>
      <div class="cd cd-sm fade-in d5">
        <div class="cd-title">MFI (14)</div>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
          <div class="mid-num" style="color:var(--${{mfi>80?'r':mfi<20?'g':'a'}}2)">${{mfi.toFixed(1)}}</div>
          <span class="bdg bdg-${{mfi>80?'r':mfi<20?'g':'a'}}">${{mfi>80?'OVERBOUGHT':mfi<20?'OVERSOLD':'NEUTRAL'}}</span>
        </div>
        ${{gaugeHTML(mfi,0,100,'var(--g),var(--a),var(--r)')}}
      </div>
    </div>
  </div>
  <div class="cd fade-in d5">
    <div class="cd-title">Tổng hợp chỉ báo — ${{s.symbol}}</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px">
      ${{[
        ['MA Aligned',s.ma_aligned?'CÓ':'KHÔNG',s.ma_aligned?'g':'r'],
        ['Above MA200',s.above_ma200?'CÓ':'KHÔNG',s.above_ma200?'g':'r'],
        ['Above MA50',s.above_ma50?'CÓ':'KHÔNG',s.above_ma50?'g':'r'],
        ['OBV Rising',s.obv_rising?'CÓ':'KHÔNG',s.obv_rising?'g':'r'],
        ['Vol Surge',s.vol_surge?'CÓ':'KHÔNG',s.vol_surge?'a':'t2'],
        ['BB Squeeze',s.bb_squeeze?'CÓ':'KHÔNG',s.bb_squeeze?'p':'t2'],
        ['Breakout 20',s.breakout_20?'CÓ':'KHÔNG',s.breakout_20?'g':'t2'],
        ['Breakout 50',s.breakout_50?'CÓ':'KHÔNG',s.breakout_50?'g':'t2'],
      ].map(([l,v,c])=>`<div class="icard" style="text-align:center;border-color:var(--${{c}})20">
        <div style="font-size:10px;color:var(--t3);font-weight:600;margin-bottom:6px">${{l}}</div>
        <div class="sm-num" style="color:var(--${{c==='t2'?'t2':c+'2'}})">${{v}}</div>
      </div>`).join('')}}
    </div>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 3: MONEY FLOW
// ═══════════════════════════════════════════
function renderMoneyFlow(){{
  const s=DISPLAY_STOCKS.find(x=>x.symbol===activeSym)||DISPLAY_STOCKS[0];
  if(!s) return '<div class="cs"><div class="cs-icon">💰</div><div class="cs-title">Không có dữ liệu</div></div>';
  const mfi=s.mfi||50;
  const mfiSig=mfi>80?['OVERBOUGHT','r']:mfi<20?['OVERSOLD','g']:['NEUTRAL','a'];

  // Volume leaders
  const volLeaders=[...DISPLAY_STOCKS].sort((a,b)=>(b.volume||0)-(a.volume||0)).slice(0,10);
  // Volume anomaly
  const volAnomaly=DISPLAY_STOCKS.filter(s=>s.vol_surge).slice(0,8);
  // OBV rising
  const obvRising=DISPLAY_STOCKS.filter(s=>s.obv_rising).length;
  const obvFalling=DISPLAY_STOCKS.length-obvRising;

  return`
  <div class="g1 g1-2 mb12">
    <div class="cd fade-in d1">
      <div class="cd-title">Volume Leaders — Top 10</div>
      <div style="overflow-x:auto">
        ${{volLeaders.map((s,i)=>{{
          const volM=(s.volume||0)/1e6;
          const maxVol=volLeaders[0].volume||1;
          const w=(s.volume||0)/maxVol*100;
          const chg=getStockChg(s);
          return`<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--brd)">
            <span style="font-size:9px;color:var(--t4);width:16px">${{i+1}}</span>
            <span class="xs-num" style="color:var(--b2);width:40px">${{s.symbol}}</span>
            <div style="flex:1"><div class="pbar" style="height:6px"><div style="width:${{w}}%;background:var(--b)"></div></div></div>
            <span class="xs-num" style="color:var(--t2);width:50px;text-align:right">${{volM.toFixed(1)}}M</span>
            <span class="xs-num ${{chg>=0?'up':'dn'}}" style="width:50px;text-align:right">${{pct(chg)}}</span>
          </div>`;
        }}).join('')}}
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div class="cd fade-in d2">
        <div class="cd-title">Accumulation / Distribution</div>
        <div style="display:flex;gap:10px;margin-bottom:12px">
          <div style="flex:1;padding:12px;background:var(--gd);border-radius:8px;border:1px solid rgba(46,160,67,.15);text-align:center">
            <div style="font-size:9px;color:var(--g2);font-weight:600">OBV RISING</div>
            <div class="mid-num up" style="margin-top:4px">${{obvRising}} mã</div>
          </div>
          <div style="flex:1;padding:12px;background:var(--rd);border-radius:8px;border:1px solid rgba(218,54,51,.15);text-align:center">
            <div style="font-size:9px;color:var(--r2);font-weight:600">OBV FALLING</div>
            <div class="mid-num dn" style="margin-top:4px">${{obvFalling}} mã</div>
          </div>
        </div>
        <div style="font-size:10px;color:var(--t3)">${{obvRising>obvFalling?'Smart money đang tích lũy. Xu hướng tích cực.':'Smart money đang phân phối. Cần thận trọng.'}}</div>
      </div>
      <div class="cd cd-sm fade-in d3">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span class="cd-title" style="margin:0">MFI — ${{activeSym}}</span>
          <span class="bdg bdg-${{mfiSig[1]}}">${{mfiSig[0]}}</span>
        </div>
        <div class="big-num" style="color:var(--${{mfiSig[1]}}2);margin-bottom:8px">${{mfi.toFixed(1)}}</div>
        ${{gaugeHTML(mfi,0,100,'var(--g),var(--a),var(--r)')}}
      </div>
    </div>
  </div>
  <div class="cd fade-in d4 mb12">
    <div class="cd-title">Volume Anomaly Detection — Đột biến khối lượng</div>
    ${{volAnomaly.length>0 ? volAnomaly.map(x=>{{
      const ratio=(x.vol_ratio||1).toFixed(1);
      const spike=ratio>2;
      return`<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--brd)">
        <span class="xs-num" style="color:var(--b2);width:40px">${{x.symbol}}</span>
        <div style="flex:1"><div class="pbar"><div style="width:${{Math.min(ratio/3*100,100)}}%;background:${{spike?'var(--a)':'var(--b)'}}"></div></div></div>
        <span class="xs-num ${{spike?'neu':'blu'}}">${{ratio}}x</span>
        ${{spike?'<span class="bdg bdg-a" style="font-size:8px;padding:1px 5px">SPIKE</span>':''}}
      </div>`;
    }}).join('') : '<div style="font-size:11px;color:var(--t4)">Không có mã đột biến khối lượng trong phiên</div>'}}
    <div style="font-size:9px;color:var(--t4);margin-top:8px">Volume Ratio = Vol / MA20. Trên 2.0x = đột biến</div>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 4: SECTOR ANALYSIS
// ═══════════════════════════════════════════
function renderSector(){{
  function hc(chg){{
    if(chg>2)return'rgba(46,160,67,.35)';if(chg>1)return'rgba(46,160,67,.22)';
    if(chg>0)return'rgba(46,160,67,.10)';if(chg>-1)return'rgba(218,54,51,.10)';
    if(chg>-2)return'rgba(218,54,51,.22)';return'rgba(218,54,51,.35)';
  }}
  const sorted=[...SECTORS];
  if(sorted.length===0) return '<div class="cs"><div class="cs-icon">🏭</div><div class="cs-title">Không có dữ liệu ngành</div></div>';
  const leader=sorted[0];const laggard=sorted[sorted.length-1];

  return`
  <div class="cd mb12 fade-in d1">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div class="cd-title" style="margin:0">Sector Heatmap</div>
      <div style="display:flex;gap:6px;align-items:center;font-size:9px;color:var(--t4)">
        <div style="width:12px;height:8px;background:rgba(218,54,51,.35);border-radius:2px"></div> &lt;-2%
        <div style="width:12px;height:8px;background:var(--s3);border-radius:2px"></div> 0
        <div style="width:12px;height:8px;background:rgba(46,160,67,.35);border-radius:2px"></div> &gt;+2%
      </div>
    </div>
    <div class="hm">${{SECTORS.map(s=>{{
      const up=s.chg>=0;
      return`<div class="hm-cell" style="background:${{hc(s.chg)}}">
        <div class="hm-name">${{s.name}}</div>
        <div class="hm-val ${{up?'up':'dn'}}">${{up?'+':''}}\${{s.chg}}%</div>
        <div class="hm-sub">${{s.count}} CP • Score ${{s.avgScore}}</div>
      </div>`;
    }}).join('')}}</div>
  </div>
  <div class="g1 g1-2 mb12">
    <div class="cd fade-in d2">
      <div class="cd-title">Sector Performance Ranking</div>
      ${{sorted.map(s=>{{
        const up=s.chg>=0;
        const w=Math.min(Math.abs(s.chg)/3*100,100);
        return`<div class="sbar-h">
          <div class="sbar-name">${{s.name}}</div>
          <div class="sbar-track">${{up?`<div class="sbar-fill" style="width:${{w}}%;background:var(--g)"></div>`:`<div class="sbar-fill" style="width:${{w}}%;background:var(--r);margin-left:auto"></div>`}}</div>
          <div class="sbar-pct ${{up?'up':'dn'}}">${{up?'+':''}}\${{s.chg}}%</div>
        </div>`;
      }}).join('')}}
    </div>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div class="cd fade-in d3">
        <div class="cd-title">Leaders & Laggards</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
          <div style="padding:12px;background:var(--gd);border-radius:8px;border:1px solid rgba(46,160,67,.15)">
            <div style="font-size:9px;color:var(--g2);font-weight:700;letter-spacing:1px;text-transform:uppercase">🏆 Dẫn dắt</div>
            <div class="mid-num up" style="margin:6px 0">${{leader.name}}</div>
            <div class="xs-num up">+${{leader.chg}}%</div>
          </div>
          <div style="padding:12px;background:var(--rd);border-radius:8px;border:1px solid rgba(218,54,51,.15)">
            <div style="font-size:9px;color:var(--r2);font-weight:700;letter-spacing:1px;text-transform:uppercase">📉 Yếu nhất</div>
            <div class="mid-num dn" style="margin:6px 0">${{laggard.name}}</div>
            <div class="xs-num dn">${{laggard.chg}}%</div>
          </div>
        </div>
      </div>
      <div class="cd fade-in d4">
        <div class="cd-title">Breadth theo ngành</div>
        ${{sorted.slice(0,6).map((s,i)=>{{
          const ratio=s.count>0?s.adv/s.count*100:50;
          const c=ratio>60?'g':ratio>40?'a':'r';
          return`<div style="display:flex;align-items:center;gap:8px;padding:5px 0;${{i<5?'border-bottom:1px solid var(--brd)':''}}">
            <span style="font-size:10px;font-weight:600;color:var(--t2);width:72px">${{s.name}}</span>
            <div style="flex:1"><div class="pbar"><div style="width:${{ratio}}%;background:var(--${{c}})"></div></div></div>
            <span class="xs-num" style="color:var(--${{c}}2)">${{s.adv}}/${{s.count}}</span>
          </div>`;
        }}).join('')}}
      </div>
    </div>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 5: TRADING SIGNALS
// ═══════════════════════════════════════════
function renderSignals(){{
  const sigStocks=DISPLAY_STOCKS.map(s=>{{
    const label=s.signal_label||'TRUNG LAP';
    const type=label.includes('MUA')?'BUY':label.includes('BAN')?'SELL':'HOLD';
    const score=s.total_score||0;
    const reasons=[];
    if(s.rsi<30) reasons.push('RSI oversold');
    if(s.rsi>70) reasons.push('RSI overbought');
    if(s.macd_bullish) reasons.push('MACD bullish');
    if(s.vol_surge) reasons.push('Volume spike');
    if(s.ma_aligned) reasons.push('MA aligned');
    if(s.bb_squeeze) reasons.push('BB squeeze');
    if(s.breakout_20) reasons.push('Breakout 20');
    if(s.obv_rising) reasons.push('OBV rising');
    if(reasons.length===0) reasons.push('Mixed signals');
    return {{...s,type,reasons,score}};
  }}).sort((a,b)=>b.score-a.score);

  const buys=sigStocks.filter(s=>s.type==='BUY');
  const sells=sigStocks.filter(s=>s.type==='SELL');
  const holds=sigStocks.filter(s=>s.type==='HOLD');
  const top10=sigStocks.slice(0,10);

  return`
  <div class="g1 g1-21 mb12">
    <div class="cd fade-in d1">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div class="cd-title" style="margin:0">Signal Scanner — ${{STATS.total}} mã</div>
        <div style="display:flex;gap:6px">
          <span class="bdg bdg-g">${{buys.length}} BUY</span>
          <span class="bdg bdg-r">${{sells.length}} SELL</span>
          <span class="bdg bdg-a">${{holds.length}} HOLD</span>
        </div>
      </div>
      <div style="overflow-x:auto">
        <div style="display:grid;grid-template-columns:50px 60px 1fr 60px 50px;gap:4px;padding:6px 8px;background:var(--s2);border-radius:6px;margin-bottom:4px;font-size:9px;color:var(--t4);font-weight:600;letter-spacing:.5px;text-transform:uppercase">
          <span>Mã</span><span>Signal</span><span>Lý do</span><span>Score</span><span>Stars</span>
        </div>
        ${{top10.map(s=>{{
          const tc=s.type==='BUY'?'g':s.type==='SELL'?'r':'a';
          return`<div style="display:grid;grid-template-columns:50px 60px 1fr 60px 50px;gap:4px;padding:6px 8px;border-bottom:1px solid var(--brd);align-items:center;font-size:11px">
            <span class="xs-num" style="color:var(--b2)">${{s.symbol}}</span>
            <span class="bdg bdg-${{tc}}" style="font-size:9px;justify-self:start">${{s.type}}</span>
            <span style="color:var(--t3);font-size:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${{s.reasons.slice(0,3).join(', ')}}</span>
            <div style="display:flex;align-items:center;gap:3px">
              <div class="pbar" style="flex:1;height:3px"><div style="width:${{s.score/40*100}}%;background:var(--${{tc}})"></div></div>
              <span class="xs-num" style="color:var(--${{tc}}2)">${{s.score}}</span>
            </div>
            <span class="xs-num" style="color:var(--a2)">${{s.stars||0}}★</span>
          </div>`;
        }}).join('')}}
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div class="cd cd-sm fade-in d2">
        <div class="cd-title">Top Buy Signals</div>
        ${{buys.slice(0,5).map(s=>`
        <div class="sig" style="border-color:var(--g)">
          <span class="sig-name">${{s.symbol}}</span>
          <span class="sig-val up">${{s.score}}/40</span>
          <span class="bdg bdg-g" style="font-size:8px">${{s.stars}}★</span>
        </div>`).join('')}}
      </div>
      <div class="cd cd-sm fade-in d3">
        <div class="cd-title">Cảnh báo bán ⚠️</div>
        ${{sells.slice(0,4).map(s=>{{
          const reason=s.rsi>70?'RSI '+s.rsi.toFixed(0):s.sell_signal||'Điểm thấp';
          return`<div class="sig" style="border-color:var(--a)">
            <span class="sig-name">${{s.symbol}}</span>
            <span style="font-size:10px;color:var(--a2)">${{reason}}</span>
          </div>`;
        }}).join('')}}
      </div>
    </div>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 6: RISK MANAGEMENT
// ═══════════════════════════════════════════
let riskAccount=500000000,riskPct=2,riskEntry=100000,riskStop=95000;

function renderRisk(){{
  const riskAmt=riskAccount*riskPct/100;
  const riskPerShare=Math.abs(riskEntry-riskStop);
  const shares=riskPerShare>0?Math.floor(riskAmt/riskPerShare/100)*100:0;
  const posValue=shares*riskEntry;
  const posPct=(posValue/riskAccount*100).toFixed(1);
  const targetPrice=riskEntry+(riskEntry-riskStop)*2;
  const rrRatio=riskPerShare>0?((targetPrice-riskEntry)/riskPerShare).toFixed(1):'--';

  return`
  <div class="g1 g1-2 mb12">
    <div class="cd fade-in d1">
      <div class="cd-title">Position Size Calculator</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:14px">
        <div>
          <div class="label" style="margin-bottom:4px">Tài khoản (VND)</div>
          <input id="ri_acc" type="number" value="${{riskAccount}}" onchange="riskAccount=+this.value;render()" style="width:100%;padding:7px 10px;background:var(--s2);border:1px solid var(--brd);border-radius:6px;color:var(--t1);font:500 12px 'IBM Plex Mono';outline:none"/>
        </div>
        <div>
          <div class="label" style="margin-bottom:4px">% Rủi ro / lệnh</div>
          <div style="display:flex;gap:4px">
            ${{[1,1.5,2,3].map(v=>`<button onclick="riskPct=${{v}};render()" style="flex:1;padding:7px 0;border-radius:6px;border:1px solid ${{riskPct===v?'var(--b)':'var(--brd)'}};background:${{riskPct===v?'var(--bd)':'var(--s2)'}};color:${{riskPct===v?'var(--b2)':'var(--t3)'}};font:600 11px 'IBM Plex Mono';cursor:pointer">${{v}}%</button>`).join('')}}
          </div>
        </div>
        <div>
          <div class="label" style="margin-bottom:4px">Giá vào (Entry)</div>
          <input type="number" value="${{riskEntry}}" onchange="riskEntry=+this.value;render()" style="width:100%;padding:7px 10px;background:var(--s2);border:1px solid var(--brd);border-radius:6px;color:var(--t1);font:500 12px 'IBM Plex Mono';outline:none"/>
        </div>
        <div>
          <div class="label" style="margin-bottom:4px">Giá cắt lỗ (Stop)</div>
          <input type="number" value="${{riskStop}}" onchange="riskStop=+this.value;render()" style="width:100%;padding:7px 10px;background:var(--s2);border:1px solid var(--brd);border-radius:6px;color:var(--t1);font:500 12px 'IBM Plex Mono';outline:none"/>
        </div>
      </div>
      <div style="background:var(--s2);border-radius:8px;padding:14px">
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;text-align:center">
          <div><div class="label">Rủi ro / lệnh</div><div class="mid-num" style="color:var(--a2)">${{(riskAmt/1e6).toFixed(1)}}M</div></div>
          <div><div class="label">Số CP (lot 100)</div><div class="mid-num blu">${{fmt(shares)}}</div></div>
          <div><div class="label">Giá trị vị thế</div><div class="mid-num" style="color:var(--t1)">${{(posValue/1e6).toFixed(0)}}M</div></div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px">
        <div class="icard" style="text-align:center"><div class="icard-name">% Tài khoản</div><div class="sm-num" style="color:${{posPct>30?'var(--r2)':'var(--t1)'}}">${{posPct}}%</div></div>
        <div class="icard" style="text-align:center"><div class="icard-name">R:R Ratio</div><div class="sm-num" style="color:var(--g2)">1:${{rrRatio}}</div></div>
        <div class="icard" style="text-align:center"><div class="icard-name">Target</div><div class="sm-num up">${{fmt(targetPrice)}}</div></div>
      </div>
    </div>
    <div class="cd fade-in d2">
      <div class="cd-title">Phân bổ theo Market Regime — ${{regimeLabel}}</div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px">
        ${{[['BULL',80,10,10],['RECOVERY',60,25,15],['SIDEWAYS',40,40,20],['CORRECTION',20,50,30],['BEAR',5,70,25]].map(([regime,eq,cash,hedge])=>{{
          const active=regime===regimeLabel;
          return`<div class="icard" style="${{active?'border-color:var(--b);background:var(--bd)':''}}">
            <div style="font-size:10px;font-weight:700;color:${{active?'var(--b2)':'var(--t3)'}};margin-bottom:6px;text-align:center">${{regime}}</div>
            <div style="font-size:10px;color:var(--t3);text-align:center">
              <div style="display:flex;justify-content:space-between"><span>Eq</span><span class="xs-num" style="color:var(--t2)">${{eq}}%</span></div>
              <div style="display:flex;justify-content:space-between"><span>Cash</span><span class="xs-num" style="color:var(--t2)">${{cash}}%</span></div>
              <div style="display:flex;justify-content:space-between"><span>Hedge</span><span class="xs-num" style="color:var(--t2)">${{hedge}}%</span></div>
            </div>
            ${{active?'<div style="text-align:center;margin-top:6px"><span class="bdg bdg-b" style="font-size:8px">CURRENT</span></div>':''}}
          </div>`;
        }}).join('')}}
      </div>
    </div>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 7: FUNDAMENTAL (Score-based)
// ═══════════════════════════════════════════
function renderFundamental(){{
  const topScored=[...DISPLAY_STOCKS].sort((a,b)=>(b.total_score||0)-(a.total_score||0)).slice(0,20);
  const starDist=[5,4,3,2,1].map(s=>{{
    const count=DISPLAY_STOCKS.filter(x=>(x.stars||0)===s).length;
    return {{stars:s,count}};
  }});
  const maxCount=Math.max(...starDist.map(d=>d.count),1);

  return`
  <div class="g1 g1-2 mb12">
    <div class="cd fade-in d1">
      <div class="cd-title">Top 20 — Điểm tổng hợp cao nhất</div>
      <div style="font-size:9px;color:var(--t4);font-weight:600;letter-spacing:1px;display:grid;grid-template-columns:40px 1fr 50px 50px 50px;gap:4px;padding:4px;border-bottom:1px solid var(--brd)">
        <span>Mã</span><span>Score Bar</span><span>Score</span><span>Stars</span><span>Signal</span>
      </div>
      ${{topScored.map(s=>{{
        const score=s.total_score||0;
        const label=s.signal_label||'TRUNG LAP';
        const tc=label.includes('MUA')?'g':label.includes('BAN')?'r':'a';
        return`<div style="display:grid;grid-template-columns:40px 1fr 50px 50px 50px;gap:4px;padding:5px 4px;border-bottom:1px solid var(--brd);align-items:center;font-size:11px">
          <span class="xs-num" style="color:var(--b2)">${{s.symbol}}</span>
          <div class="pbar" style="height:5px"><div style="width:${{score/40*100}}%;background:var(--${{tc}})"></div></div>
          <span class="xs-num" style="color:var(--${{tc}}2)">${{score}}/40</span>
          <span class="xs-num" style="color:var(--a2)">${{s.stars||0}}★</span>
          <span class="bdg bdg-${{tc}}" style="font-size:8px">${{label.replace(' ','').substring(0,3)}}</span>
        </div>`;
      }}).join('')}}
    </div>
    <div style="display:flex;flex-direction:column;gap:12px">
      <div class="cd fade-in d2">
        <div class="cd-title">Phân bố Star Rating</div>
        ${{starDist.map(d=>{{
          const w=d.count/maxCount*100;
          const c=d.stars>=4?'g':d.stars>=3?'a':'r';
          return`<div style="display:flex;align-items:center;gap:8px;padding:5px 0">
            <span class="xs-num" style="color:var(--a2);width:28px">${{d.stars}}★</span>
            <div style="flex:1"><div class="pbar" style="height:8px"><div style="width:${{w}}%;background:var(--${{c}})"></div></div></div>
            <span class="xs-num" style="color:var(--t2);width:35px;text-align:right">${{d.count}}</span>
          </div>`;
        }}).join('')}}
        <div class="dvd-sm"></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">
          <div class="icard" style="text-align:center">
            <div class="icard-name">Avg Score</div>
            <div class="mid-num" style="color:var(--b2)">${{STATS.avg_score}}/40</div>
          </div>
          <div class="icard" style="text-align:center">
            <div class="icard-name">Avg RSI</div>
            <div class="mid-num" style="color:var(--${{STATS.avg_rsi>60?'g':STATS.avg_rsi<40?'r':'a'}}2)">${{STATS.avg_rsi}}</div>
          </div>
        </div>
      </div>
      <div class="cd cd-sm fade-in d3">
        <div class="cd-title">Channel Distribution</div>
        <div style="display:flex;gap:8px">
          ${{[['🟢 Uptrend',STATS.uptrend,'g'],['⚪ Sideways',STATS.sideways,'t2'],['🔴 Downtrend',STATS.downtrend,'r']].map(([l,v,c])=>`
            <div style="flex:1;padding:10px;background:var(--s2);border-radius:8px;text-align:center">
              <div style="font-size:9px;color:var(--t3);font-weight:600">${{l}}</div>
              <div class="mid-num" style="color:var(--${{c==='t2'?'t2':c+'2'}});margin-top:4px">${{v}}</div>
            </div>
          `).join('')}}
        </div>
      </div>
    </div>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 8: MACRO (Static + AI)
// ═══════════════════════════════════════════
function renderMacro(){{
  return`
  <div class="g1 g1-2 mb12">
    <div class="cd fade-in d1">
      <div class="cd-title">Tổng quan thị trường</div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px">
        ${{[
          ['Tổng mã',STATS.total,'b'],
          ['Advance',STATS.advance,'g'],
          ['Decline',STATS.decline,'r'],
        ].map(([l,v,c])=>`<div class="icard"><div class="icard-name">${{l}}</div><div class="mid-num" style="color:var(--${{c}}2);margin-top:4px">${{v}}</div></div>`).join('')}}
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
        ${{[
          ['Avg RSI',STATS.avg_rsi,'a'],
          ['Avg MFI',STATS.avg_mfi,'a'],
          ['Avg Score',STATS.avg_score+'/40','b'],
        ].map(([l,v,c])=>`<div class="icard"><div class="icard-name">${{l}}</div><div class="sm-num" style="color:var(--${{c}}2);margin-top:4px">${{v}}</div></div>`).join('')}}
      </div>
    </div>
    <div class="cd fade-in d2">
      <div class="cd-title">Signal Distribution</div>
      ${{[
        ['MUA MẠNH',STATS.buy_strong,'g'],
        ['MUA',STATS.buy,'g'],
        ['TRUNG LẬP',STATS.neutral,'a'],
        ['BÁN',STATS.sell,'r'],
        ['BÁN MẠNH',STATS.sell_strong,'r'],
      ].map(([l,v,c])=>{{
        const w=v/Math.max(STATS.total,1)*100;
        return`<div style="display:flex;align-items:center;gap:8px;padding:5px 0">
          <span style="font-size:10px;font-weight:600;color:var(--${{c}}2);width:80px">${{l}}</span>
          <div style="flex:1"><div class="pbar" style="height:6px"><div style="width:${{w}}%;background:var(--${{c}})"></div></div></div>
          <span class="xs-num" style="color:var(--t2);width:30px;text-align:right">${{v}}</span>
        </div>`;
      }}).join('')}}
    </div>
  </div>
  <div class="cd fade-in d3">
    <div class="cd-title">Thông tin chung</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px">
      ${{[
        ['Vol Surge',STATS.vol_surge_count+' mã','a'],
        ['BB Squeeze',STATS.bb_squeeze_count+' mã','p'],
        ['Uptrend',STATS.uptrend+' mã','g'],
      ].map(([l,v,c])=>`<div class="icard" style="text-align:center"><div class="icard-name">${{l}}</div><div class="sm-num" style="color:var(--${{c}}2);margin-top:4px">${{v}}</div></div>`).join('')}}
    </div>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 9: STOCK SCREENER (Bộ lọc CP)
// ═══════════════════════════════════════════
let scrSort='total_score',scrDir=-1,scrFilter='all',scrSearch='';

function renderScreener(){{
  let data=[...DISPLAY_STOCKS];

  // Filter
  if(scrFilter==='buy') data=data.filter(s=>(s.signal_label||'').includes('MUA'));
  else if(scrFilter==='sell') data=data.filter(s=>(s.signal_label||'').includes('BAN'));
  else if(scrFilter==='surge') data=data.filter(s=>s.vol_surge);
  else if(scrFilter==='squeeze') data=data.filter(s=>s.bb_squeeze);
  else if(scrFilter==='uptrend') data=data.filter(s=>(s.channel||'').includes('XANH'));

  // Search
  if(scrSearch) data=data.filter(s=>(s.symbol||'').includes(scrSearch.toUpperCase()));

  // Sort
  data.sort((a,b)=>{{
    const av=a[scrSort]||0,bv=b[scrSort]||0;
    return scrDir*(typeof av==='string'?av.localeCompare(bv):av-bv);
  }});

  const cols=[
    ['symbol','Mã',50],['close','Giá',60],['total_score','Score',50],['stars','Stars',40],
    ['rsi','RSI',45],['mfi','MFI',45],['vol_ratio','VolR',45],['channel','Channel',70],['signal_label','Signal',70]
  ];

  return`
  <div class="fbar">
    <input placeholder="Tìm mã..." value="${{scrSearch}}" oninput="scrSearch=this.value;render()" style="width:120px"/>
    <select onchange="scrFilter=this.value;render()">
      <option value="all" ${{scrFilter==='all'?'selected':''}}>Tất cả</option>
      <option value="buy" ${{scrFilter==='buy'?'selected':''}}>Tín hiệu MUA</option>
      <option value="sell" ${{scrFilter==='sell'?'selected':''}}>Tín hiệu BÁN</option>
      <option value="surge" ${{scrFilter==='surge'?'selected':''}}>Volume đột biến</option>
      <option value="squeeze" ${{scrFilter==='squeeze'?'selected':''}}>BB Squeeze</option>
      <option value="uptrend" ${{scrFilter==='uptrend'?'selected':''}}>Uptrend</option>
    </select>
    <span style="font-size:10px;color:var(--t3)">${{data.length}} / ${{DISPLAY_STOCKS.length}} mã</span>
  </div>
  <div class="cd" style="padding:0;overflow:auto;max-height:calc(100vh - 180px)">
    <table class="scr-tbl">
      <thead><tr>${{cols.map(([key,label,w])=>
        `<th style="width:${{w}}px" onclick="if(scrSort==='${{key}}')scrDir*=-1;else{{scrSort='${{key}}';scrDir=-1}};render()">${{label}} ${{scrSort===key?(scrDir>0?'↑':'↓'):''}}</th>`
      ).join('')}}</tr></thead>
      <tbody>${{data.slice(0,100).map(s=>{{
        const chg=getStockChg(s);
        const label=s.signal_label||'TRUNG LAP';
        const tc=label.includes('MUA')?'g':label.includes('BAN')?'r':'a';
        const chC=s.channel&&s.channel.includes('XANH')?'g':s.channel&&s.channel.includes('ĐỎ')?'r':'t2';
        return`<tr onclick="activeSym='${{s.symbol}}';go('technical')" style="cursor:pointer">
          <td><span class="xs-num" style="color:var(--b2)">${{s.symbol}}</span></td>
          <td><span class="xs-num ${{clr(chg)}}">${{fmt(s.close)}}</span></td>
          <td><span class="xs-num" style="color:var(--${{tc}}2)">${{(s.total_score||0)}}</span></td>
          <td><span class="xs-num" style="color:var(--a2)">${{s.stars||0}}★</span></td>
          <td><span class="xs-num" style="color:var(--${{(s.rsi||50)>70?'r':(s.rsi||50)<30?'g':'t'}}2)">${{(s.rsi||0).toFixed(0)}}</span></td>
          <td><span class="xs-num" style="color:var(--t2)">${{(s.mfi||0).toFixed(0)}}</span></td>
          <td><span class="xs-num ${{(s.vol_ratio||1)>1.5?'neu':''}}">${{(s.vol_ratio||0).toFixed(1)}}x</span></td>
          <td><span style="font-size:10px;color:var(--${{chC}}2)">${{(s.channel||'--').replace(/[🟢🔴⚪]/g,'').trim()}}</span></td>
          <td><span class="bdg bdg-${{tc}}" style="font-size:8px">${{label}}</span></td>
        </tr>`;
      }}).join('')}}</tbody>
    </table>
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 10: PORTFOLIO
// ═══════════════════════════════════════════
function renderPortfolio(){{
  if(!POSITIONS||POSITIONS.length===0){{
    return`<div class="cd fade-in d1">
      <div class="cd-title">Danh mục đầu tư</div>
      <div class="cs">
        <div class="cs-icon">💼</div>
        <div class="cs-title">Chưa có vị thế</div>
        <div class="cs-desc">Cập nhật file data/portfolio.json để theo dõi danh mục</div>
      </div>
      <div class="dvd"></div>
      <div class="cd-title">Định dạng portfolio.json</div>
      <div style="background:var(--s2);border-radius:8px;padding:12px;font:400 11px 'IBM Plex Mono';color:var(--t3);line-height:1.6">
{{"positions":[{{"symbol":"FPT","entry_price":130000,"quantity":1000}}],"cash_percent":50}}
      </div>
    </div>`;
  }}

  let totalValue=0,totalPnl=0;
  POSITIONS.forEach(p=>{{
    const cur=p.current_price||p.entry_price||0;
    const entry=p.entry_price||0;
    const qty=p.quantity||0;
    totalValue+=cur*qty;
    totalPnl+=(cur-entry)*qty;
  }});

  return`
  <div class="g1 g1-3 mb12">
    <div class="cd cd-sm fade-in d1" style="text-align:center">
      <div class="cd-title">Tổng giá trị</div>
      <div class="big-num blu">${{(totalValue/1e6).toFixed(0)}}M</div>
    </div>
    <div class="cd cd-sm fade-in d2" style="text-align:center">
      <div class="cd-title">Lãi / Lỗ</div>
      <div class="big-num ${{totalPnl>=0?'up':'dn'}}">${{totalPnl>=0?'+':''}}\${{(totalPnl/1e6).toFixed(1)}}M</div>
    </div>
    <div class="cd cd-sm fade-in d3" style="text-align:center">
      <div class="cd-title">Số vị thế</div>
      <div class="big-num" style="color:var(--t1)">${{POSITIONS.length}}</div>
    </div>
  </div>
  <div class="cd fade-in d4">
    <div class="cd-title">Chi tiết vị thế</div>
    <div style="display:grid;grid-template-columns:60px 70px 70px 70px 60px 1fr;gap:4px;padding:6px 8px;background:var(--s2);border-radius:6px;margin-bottom:4px;font-size:9px;color:var(--t4);font-weight:600;letter-spacing:.5px;text-transform:uppercase">
      <span>Mã</span><span>Entry</span><span>Current</span><span>Quantity</span><span>P&L%</span><span>Value</span>
    </div>
    ${{POSITIONS.map(p=>{{
      const cur=p.current_price||p.entry_price||0;
      const entry=p.entry_price||0;
      const qty=p.quantity||0;
      const pnlPct=entry>0?((cur-entry)/entry*100):0;
      const value=cur*qty;
      const up=pnlPct>=0;
      return`<div style="display:grid;grid-template-columns:60px 70px 70px 70px 60px 1fr;gap:4px;padding:6px 8px;border-bottom:1px solid var(--brd);align-items:center;font-size:11px">
        <span class="xs-num" style="color:var(--b2)">${{p.symbol}}</span>
        <span class="xs-num" style="color:var(--t2)">${{fmt(entry)}}</span>
        <span class="xs-num ${{up?'up':'dn'}}">${{fmt(cur)}}</span>
        <span class="xs-num" style="color:var(--t2)">${{fmt(qty)}}</span>
        <span class="xs-num ${{up?'up':'dn'}}">${{up?'+':''}}\${{pnlPct.toFixed(1)}}%</span>
        <span class="xs-num" style="color:var(--t2)">${{(value/1e6).toFixed(1)}}M</span>
      </div>`;
    }}).join('')}}
  </div>`;
}}

// ═══════════════════════════════════════════
// MODULE 11: AI INSIGHTS
// ═══════════════════════════════════════════
function renderAI(){{
  if(!AI_REPORT||AI_REPORT.trim().length===0){{
    return`<div class="cd fade-in d1">
      <div class="cs">
        <div class="cs-icon">🤖</div>
        <div class="cs-title">AI Report chưa sẵn sàng</div>
        <div class="cs-desc">Báo cáo AI sẽ được tạo tự động khi chạy pipeline hàng ngày</div>
      </div>
    </div>`;
  }}
  // Simple markdown-like rendering
  let html=AI_REPORT
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/^### (.+)$/gm,'<h3>$1</h3>')
    .replace(/^## (.+)$/gm,'<h2>$1</h2>')
    .replace(/^# (.+)$/gm,'<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/^- (.+)$/gm,'• $1');

  return`
  <div class="cd fade-in d1">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div class="cd-title" style="margin:0">AI Market Analysis — {self.today}</div>
      <span class="bdg bdg-p">Claude AI</span>
    </div>
    <div class="ai-box">${{html}}</div>
  </div>`;
}}

// ═══════════════════════════════════════════
// RENDER DISPATCHER
// ═══════════════════════════════════════════
function render(){{
  const el=document.getElementById('view');
  el.scrollTop=0;
  switch(activeTab){{
    case'overview':el.innerHTML=renderOverview();break;
    case'technical':el.innerHTML=renderTechnical();break;
    case'moneyflow':el.innerHTML=renderMoneyFlow();break;
    case'sector':el.innerHTML=renderSector();break;
    case'signals':el.innerHTML=renderSignals();break;
    case'risk':el.innerHTML=renderRisk();break;
    case'fundamental':el.innerHTML=renderFundamental();break;
    case'macro':el.innerHTML=renderMacro();break;
    case'screener':el.innerHTML=renderScreener();break;
    case'portfolio':el.innerHTML=renderPortfolio();break;
    case'ai':el.innerHTML=renderAI();break;
    default:el.innerHTML=renderOverview();
  }}
}}

// Clock
function tick(){{
  const n=new Date();
  document.getElementById('clk').textContent=n.toLocaleTimeString('vi-VN',{{hour:'2-digit',minute:'2-digit',second:'2-digit'}});
}}
setInterval(tick,1000);tick();

// Init
renderNav();render();
</script>
</body>
</html>'''

    def save_dashboard(self, output_path: str = 'docs/index.html'):
        html = self.generate_html()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Dashboard saved: {output_path} ({len(html)//1024}KB)")

    def run(self):
        print("=" * 60)
        print("TAO DASHBOARD V8 - REFERENCE DESIGN")
        print("=" * 60)
        self.save_dashboard()


if __name__ == "__main__":
    generator = DashboardGenerator()
    generator.run()
