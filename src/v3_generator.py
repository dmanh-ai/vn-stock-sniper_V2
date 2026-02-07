"""
VN Stock Sniper - Dashboard V3 Generator
Flow: Fetch DNSE → Calculate indicators → Call Claude API ONCE → Generate FULL_DATA → Write v3_data.js
"""

import json
import math
import os
import time
import sys
from datetime import datetime, timedelta

import numpy as np
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import CLAUDE_API_KEY

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("anthropic not installed")

# ============================================================
# DNSE Fetcher
# ============================================================
DNSE_BASE = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"
DNSE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Origin': 'https://banggia.dnse.com.vn',
    'Referer': 'https://banggia.dnse.com.vn/',
}

INDEX_LIST = [
    {'key': 'vnindex',  'name': 'VNINDEX',  'symbol': 'VNINDEX'},
    {'key': 'vn30',     'name': 'VN30',     'symbol': 'VN30'},
    {'key': 'vn100',    'name': 'VN100',    'symbol': 'VN100'},
    {'key': 'vnmidcap', 'name': 'VNMIDCAP', 'symbol': 'VNMIDCAP'},
]

VN30_STOCKS = [
    'ACB','BCM','BID','BVH','CTG','FPT','GAS','GVR','HDB','HPG',
    'KDH','MBB','MSN','MWG','PLX','POW','SAB','SHB','SSB','SSI',
    'STB','TCB','TPB','VCB','VHM','VIB','VIC','VJC','VNM','VPB',
]


def fetch_dnse(symbol, days=200):
    """Fetch OHLCV from DNSE Entrade API"""
    to_ts = int(time.time())
    from_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    params = {'symbol': symbol, 'resolution': '1D', 'from': from_ts, 'to': to_ts}
    try:
        r = requests.get(DNSE_BASE, params=params, headers=DNSE_HEADERS, timeout=15)
        r.raise_for_status()
        d = r.json()
        if not d or 't' not in d or not d['t']:
            return None
        bars = []
        for i in range(len(d['t'])):
            dt = datetime.utcfromtimestamp(d['t'][i])
            bars.append({
                'd': dt.strftime('%Y-%m-%d'),
                'o': round((d['o'][i] or 0) * 1000, 2),
                'h': round((d['h'][i] or 0) * 1000, 2),
                'l': round((d['l'][i] or 0) * 1000, 2),
                'c': round((d['c'][i] or 0) * 1000, 2),
                'v': d['v'][i] or 0,
            })
        return bars
    except Exception as e:
        print(f"  DNSE error {symbol}: {e}")
        return None


# ============================================================
# Technical Indicators
# ============================================================
def calc_indicators(bars):
    """Calculate basic technical indicators from OHLCV bars"""
    if not bars or len(bars) < 20:
        return {}

    closes = np.array([b['c'] for b in bars], dtype=float)
    highs = np.array([b['h'] for b in bars], dtype=float)
    lows = np.array([b['l'] for b in bars], dtype=float)
    volumes = np.array([b['v'] for b in bars], dtype=float)

    n = len(closes)
    last = closes[-1]
    prev = closes[-2] if n >= 2 else last

    change = last - prev
    change_pct = (change / prev * 100) if prev != 0 else 0

    def ma(arr, period):
        if len(arr) < period:
            return None
        return float(np.mean(arr[-period:]))

    ma5 = ma(closes, 5)
    ma10 = ma(closes, 10)
    ma20 = ma(closes, 20)
    ma50 = ma(closes, 50) if n >= 50 else None
    ma200 = ma(closes, 200) if n >= 200 else None

    def calc_rsi(arr, period=14):
        if len(arr) < period + 1:
            return None
        deltas = np.diff(arr[-(period+1):])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    rsi = calc_rsi(closes)

    def ema(arr, period):
        if len(arr) < period:
            return arr[-1] if len(arr) > 0 else 0
        k = 2 / (period + 1)
        result = arr[0]
        for i in range(1, len(arr)):
            result = arr[i] * k + result * (1 - k)
        return result

    macd_line = ema(closes, 12) - ema(closes, 26) if n >= 26 else 0
    macd_bullish = macd_line > 0

    bb_mid = ma20 or last
    bb_std = float(np.std(closes[-20:])) if n >= 20 else 0
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_width = ((bb_upper - bb_lower) / bb_mid * 100) if bb_mid else 0
    bb_pct = ((last - bb_lower) / (bb_upper - bb_lower) * 100) if (bb_upper - bb_lower) != 0 else 50

    def calc_atr(highs, lows, closes, period=14):
        if len(highs) < period + 1:
            return None
        trs = []
        for i in range(-period, 0):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            trs.append(tr)
        return round(np.mean(trs), 2)

    atr = calc_atr(highs, lows, closes)
    atr_pct = round(atr / last * 100, 2) if atr and last else 0

    def range_avg(bars, n_bars):
        subset = bars[-n_bars:] if len(bars) >= n_bars else bars
        return round(np.mean([b['h'] - b['l'] for b in subset]), 2)

    range_5 = range_avg(bars, 5)
    range_20 = range_avg(bars, 20)

    recent = bars[-50:] if n >= 50 else bars
    support = min(b['l'] for b in recent)
    resistance = max(b['h'] for b in recent)

    vol_ma20 = ma(volumes, 20)
    vol_ratio = round(volumes[-1] / vol_ma20, 2) if vol_ma20 and vol_ma20 > 0 else 1.0

    kc_mid = ma20 or last
    kc_range = (1.5 * atr) if atr else 0
    kc_upper = kc_mid + kc_range
    kc_lower = kc_mid - kc_range
    squeeze = bb_upper < kc_upper and bb_lower > kc_lower

    if ma5 and ma20:
        if ma5 > ma20:
            trend = "TANG"
        elif ma5 < ma20:
            trend = "GIAM"
        else:
            trend = "DI NGANG"
    else:
        trend = "KHONG XAC DINH"

    return {
        'last_price': round(last, 2),
        'prev_close': round(prev, 2),
        'change': round(change, 2),
        'change_pct': round(change_pct, 2),
        'ma5': round(ma5, 2) if ma5 else None,
        'ma10': round(ma10, 2) if ma10 else None,
        'ma20': round(ma20, 2) if ma20 else None,
        'ma50': round(ma50, 2) if ma50 else None,
        'ma200': round(ma200, 2) if ma200 else None,
        'rsi': rsi,
        'macd_line': round(macd_line, 2),
        'macd_bullish': macd_bullish,
        'bb_upper': round(bb_upper, 2),
        'bb_mid': round(bb_mid, 2),
        'bb_lower': round(bb_lower, 2),
        'bb_width_pct': round(bb_width, 2),
        'bb_pct': round(bb_pct, 2),
        'atr': atr,
        'atr_pct': atr_pct,
        'range_5': range_5,
        'range_20': range_20,
        'support_50d': round(support, 2),
        'resistance_50d': round(resistance, 2),
        'vol_last': int(volumes[-1]),
        'vol_ma20': round(vol_ma20, 2) if vol_ma20 else 0,
        'vol_ratio': vol_ratio,
        'squeeze': squeeze,
        'trend': trend,
        'last_date': bars[-1]['d'],
    }


# ============================================================
# Claude AI - SINGLE CALL for all indices + overview
# ============================================================
SYSTEM_PROMPT = """Ban la chuyen gia phan tich chung khoan Viet Nam cap cao voi 15 nam kinh nghiem.
Ban phan tich ky thuat chuyen sau, ket hop du lieu OHLCV, chi bao ky thuat, va kinh nghiem thi truong.

QUY TAC QUAN TRONG:
- Viet TIENG VIET co dau day du
- Tra ve dung 1 JSON object duy nhat, KHONG co gi khac
- Moi section co: {"title": "...", "icon": "...", "content": "...HTML..."}
- Content dung HTML voi cac CSS class:
  * conclusion-box > conclusion-icon + conclusion-text (ket luan chinh)
  * evidence-box > evidence-icon + evidence-text (dan chung)
  * action-box > action-icon + action-text (hanh dong/khuyen nghi)
  * risk-box > risk-icon + risk-text (canh bao rui ro)
  * content-paragraph (doan van binh thuong)
  * metric-number (so lieu cu the, VD: <span class="metric-number">1,285.50</span>)
  * percentage bullish (tang, xanh) / percentage bearish (giam, do)
- Dung so lieu CU THE tu data, khong noi chung chung
- Phan biet ro tin hieu manh va yeu
- Neu thi truong xau, noi thang, khong to ve lac quan
- Moi section content co 2-4 elements (conclusion-box, evidence-box, action-box, risk-box, content-paragraph)
- GIU NGAN GON, tap trung vao nhan dinh quan trong nhat
"""


def build_mega_prompt(all_indicators, all_bars_summary):
    """Build a SINGLE prompt for ALL indices + overview analysis"""

    # Overview summary
    overview_summary = {}
    for idx_key, ind in all_indicators.items():
        overview_summary[idx_key] = {
            'price': ind.get('last_price'),
            'change_pct': ind.get('change_pct'),
            'rsi': ind.get('rsi'),
            'trend': ind.get('trend'),
            'vol_ratio': ind.get('vol_ratio'),
            'macd_bullish': ind.get('macd_bullish'),
        }

    # Per-index data blocks
    index_data_blocks = []
    for idx in INDEX_LIST:
        key = idx['key']
        name = idx['name']
        ind = all_indicators.get(key, {})
        bars_sum = all_bars_summary.get(key, [])
        index_data_blocks.append(f"""--- {name} ---
Chi bao ky thuat: {json.dumps(ind, ensure_ascii=False)}
5 phien gan nhat: {json.dumps(bars_sum, ensure_ascii=False)}""")

    combined_data = "\n".join(index_data_blocks)

    return f"""Phan tich TOAN BO thi truong chung khoan Viet Nam.

=== TONG HOP ===
{json.dumps(overview_summary, indent=2, ensure_ascii=False)}

=== DU LIEU CHI TIET ===
{combined_data}

=== YEU CAU ===
Tra ve 1 JSON object duy nhat voi cau truc:

{{
  "overview": {{
    "title": "TONG HOP - Thi truong chung khoan Viet Nam",
    "sections": [4 sections]
  }},
  "vnindex": {{
    "title": "VNINDEX - Phan tich ky thuat",
    "sections": [9 sections]
  }},
  "vn30": {{
    "title": "VN30 - Phan tich ky thuat",
    "sections": [9 sections]
  }},
  "vn100": {{
    "title": "VN100 - Phan tich ky thuat",
    "sections": [9 sections]
  }},
  "vnmidcap": {{
    "title": "VNMIDCAP - Phan tich ky thuat",
    "sections": [9 sections]
  }}
}}

OVERVIEW gom 4 sections:
1. "TONG QUAN THI TRUONG" (icon:"📊") - Xu huong chu dao, buc tranh tong the
2. "XEP HANG CHI SO" (icon:"🏆") - Xep hang chi so theo suc manh
3. "RUI RO HE THONG" (icon:"⚠️") - Rui ro chung
4. "KHUYEN NGHI CHUNG" (icon:"🎯") - Chien luoc tong the

MOI CHI SO gom 9 sections:
1. "XU HUONG GIA" (icon:"📈") - MA, trend ngan/trung/dai han
2. "XU HUONG KHOI LUONG" (icon:"📊") - Volume, vol_ratio
3. "KET HOP GIA - KHOI LUONG" (icon:"💹") - Ket hop gia + volume
4. "CUNG-CAU" (icon:"⚖️") - RSI, MACD, BB%
5. "MUC GIA QUAN TRONG" (icon:"🎯") - Support/Resistance, MA levels
6. "BIEN DONG GIA" (icon:"📉") - ATR, BB width, squeeze
7. "RUI RO" (icon:"⚠️") - Canh bao rui ro
8. "KHUYEN NGHI VI THE" (icon:"🎯") - Long/Short/Cash
9. "GIA MUC TIEU" (icon:"🎯") - Muc gia muc tieu

QUY TAC:
- Moi section PHAI co {{"title":"...","icon":"...","content":"<HTML>"}}
- Content HTML dung CSS classes: conclusion-box, evidence-box, action-box, risk-box, content-paragraph, metric-number
- Dung SO LIEU CU THE tu data
- CHI tra ve JSON object, KHONG co text/markdown nao khac
- Tong cong: 1 overview (4 sections) + 4 chi so x 9 sections = 40 sections"""


def call_claude_single(prompt):
    """Call Claude API ONCE and return full analysis dict"""
    if not ANTHROPIC_AVAILABLE or not CLAUDE_API_KEY:
        print("  Claude API not available, using fallback")
        return None

    client = Anthropic(api_key=CLAUDE_API_KEY)
    try:
        print("  Calling Claude API (single call)...")
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        print(f"  Response: {len(text)} chars, {response.usage.output_tokens} tokens")

        # Extract JSON object from response
        if text.startswith('{'):
            return json.loads(text)
        start = text.find('{')
        end = text.rfind('}')
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        print("  Could not parse JSON from Claude response")
        return None
    except Exception as e:
        print(f"  Claude API error: {e}")
        return None


# ============================================================
# Fallback sections (no AI)
# ============================================================
def make_fallback_sections(name, indicators):
    """Generate basic sections without AI"""
    ind = indicators
    price = ind.get('last_price', 0)
    chg = ind.get('change_pct', 0)
    rsi = ind.get('rsi', 50)
    trend = ind.get('trend', 'N/A')

    return [
        {"title": "XU HUONG GIA", "icon": "\u{1f4c8}",
         "content": f'<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">Xu h\u01b0\u1edbng {name}: {trend}. Gi\u00e1 hi\u1ec7n t\u1ea1i <span class="metric-number">{price:,.2f}</span>, thay \u0111\u1ed5i <span class="metric-number">{chg:+.2f}%</span></span></div><p class="content-paragraph">MA5: {ind.get("ma5","N/A")}, MA20: {ind.get("ma20","N/A")}, MA50: {ind.get("ma50","N/A")}</p>'},
        {"title": "XU HUONG KHOI LUONG", "icon": "\u{1f4ca}",
         "content": f'<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">Kh\u1ed1i l\u01b0\u1ee3ng phi\u00ean cu\u1ed1i: <span class="metric-number">{ind.get("vol_last",0):,.0f}</span>. Vol ratio: <span class="metric-number">{ind.get("vol_ratio",1):.2f}x</span> so v\u1edbi MA20.</span></div>'},
        {"title": "KET HOP GIA - KHOI LUONG", "icon": "\u{1f4b9}",
         "content": f'<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">Gi\u00e1 {trend.lower()}, volume {"t\u0103ng" if ind.get("vol_ratio",1)>1 else "gi\u1ea3m"} so v\u1edbi trung b\u00ecnh.</span></div>'},
        {"title": "CUNG-CAU", "icon": "\u2696\ufe0f",
         "content": f'<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">RSI: <span class="metric-number">{rsi}</span> - {"Qu\u00e1 mua" if rsi and rsi>70 else "Qu\u00e1 b\u00e1n" if rsi and rsi<30 else "Trung t\u00ednh"}. MACD: {"Bullish" if ind.get("macd_bullish") else "Bearish"}.</span></div>'},
        {"title": "MUC GIA QUAN TRONG", "icon": "\u{1f3af}",
         "content": f'<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">H\u1ed7 tr\u1ee3 50 phi\u00ean: <span class="metric-number">{ind.get("support_50d","N/A")}</span>. Kh\u00e1ng c\u1ef1 50 phi\u00ean: <span class="metric-number">{ind.get("resistance_50d","N/A")}</span>.</span></div>'},
        {"title": "BIEN DONG GIA", "icon": "\u{1f4c9}",
         "content": f'<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">ATR: <span class="metric-number">{ind.get("atr","N/A")}</span> ({ind.get("atr_pct",0):.2f}%). BB Width: <span class="metric-number">{ind.get("bb_width_pct",0):.1f}%</span>. Squeeze: {"C\u00d3" if ind.get("squeeze") else "KH\u00d4NG"}.</span></div>'},
        {"title": "RUI RO", "icon": "\u26a0\ufe0f",
         "content": f'<div class="risk-box"><span class="risk-icon">\u26a0\ufe0f</span><span class="risk-text">C\u1ea7n theo d\u00f5i s\u00e1t xu h\u01b0\u1edbng. RSI {rsi}, {"c\u1ea9n th\u1eadn v\u00f9ng qu\u00e1 mua" if rsi and rsi>65 else "v\u00f9ng an to\u00e0n" if rsi and rsi>35 else "c\u1ea9n th\u1eadn v\u00f9ng qu\u00e1 b\u00e1n"}.</span></div>'},
        {"title": "KHUYEN NGHI VI THE", "icon": "\u{1f3af}",
         "content": f'<div class="action-box"><span class="action-icon">\u{1f3af}</span><span class="action-text">{"\u01afu ti\u00ean Long" if trend=="TANG" else "\u01afu ti\u00ean Short/Cash" if trend=="GIAM" else "Ch\u1edd t\u00edn hi\u1ec7u r\u00f5 h\u01a1n"}. Qu\u1ea3n l\u00fd r\u1ee7i ro ch\u1eb7t ch\u1ebd.</span></div>'},
        {"title": "GIA MUC TIEU", "icon": "\u{1f3af}",
         "content": f'<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">M\u1ee5c ti\u00eau t\u0103ng: <span class="metric-number">{ind.get("resistance_50d","N/A")}</span>. M\u1ee5c ti\u00eau gi\u1ea3m: <span class="metric-number">{ind.get("support_50d","N/A")}</span>.</span></div>'},
    ]


def make_fallback_overview(all_indicators):
    """Generate basic overview sections without AI"""
    lines = []
    for k, ind in all_indicators.items():
        lines.append(f'{k.upper()}: {ind.get("last_price","N/A")} ({ind.get("change_pct",0):+.2f}%)')

    return [
        {"title": "TONG QUAN THI TRUONG", "icon": "\u{1f4ca}",
         "content": f'<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">T\u1ed5ng quan th\u1ecb tr\u01b0\u1eddng - D\u1eef li\u1ec7u t\u1eeb DNSE API</span></div><p class="content-paragraph">{" | ".join(lines)}</p>'},
        {"title": "XEP HANG CHI SO", "icon": "\u{1f3c6}",
         "content": '<div class="conclusion-box"><span class="conclusion-icon">\u{1f4cc}</span><span class="conclusion-text">X\u1ebfp h\u1ea1ng c\u00e1c ch\u1ec9 s\u1ed1 theo s\u1ee9c m\u1ea1nh t\u01b0\u01a1ng \u0111\u1ed1i.</span></div>'},
        {"title": "RUI RO HE THONG", "icon": "\u26a0\ufe0f",
         "content": '<div class="risk-box"><span class="risk-icon">\u26a0\ufe0f</span><span class="risk-text">C\u1ea7n theo d\u00f5i s\u00e1t di\u1ec5n bi\u1ebfn th\u1ecb tr\u01b0\u1eddng. Qu\u1ea3n l\u00fd r\u1ee7i ro ch\u1eb7t ch\u1ebd.</span></div>'},
        {"title": "KHUYEN NGHI CHUNG", "icon": "\u{1f3af}",
         "content": '<div class="action-box"><span class="action-icon">\u{1f3af}</span><span class="action-text">Giao d\u1ecbch theo xu h\u01b0\u1edbng. Kh\u00f4ng FOMO. \u0110\u1eb7t stop loss.</span></div>'},
    ]


# ============================================================
# Heatmap data for VN30 stocks
# ============================================================
def fetch_stock_heatmap():
    """Fetch VN30 stocks for heatmap"""
    result = {'gainers': [], 'losers': [], 'date': ''}
    print("  Fetching VN30 stocks for heatmap...")

    for i, sym in enumerate(VN30_STOCKS):
        bars = fetch_dnse(sym, 5)
        if not bars or len(bars) < 2:
            continue
        last = bars[-1]
        prev = bars[-2]
        pct = ((last['c'] - prev['c']) / prev['c'] * 100) if prev['c'] else 0
        item = {
            'symbol': sym,
            'change_pct': round(pct, 2),
            'price': round(last['c'] / 1000, 2),
            'volume': last['v'],
            'value': round(last['c'] * last['v'] / 1e9, 2),
        }
        if pct >= 0:
            result['gainers'].append(item)
        else:
            result['losers'].append(item)
        result['date'] = last['d']

        if (i + 1) % 10 == 0:
            print(f"    {i+1}/{len(VN30_STOCKS)} stocks done")
        time.sleep(0.15)

    result['gainers'].sort(key=lambda x: x['change_pct'], reverse=True)
    result['losers'].sort(key=lambda x: x['change_pct'])
    return result


# ============================================================
# Main Generator
# ============================================================
def generate_v3():
    """Main: fetch data, call Claude ONCE, generate dashboard data"""
    print("=" * 60)
    print("DASHBOARD V3 GENERATOR")
    print("=" * 60)

    # Step 1: Fetch index OHLCV
    print("\n[1/4] Fetching index OHLCV from DNSE...")
    index_data = {}
    for idx in INDEX_LIST:
        print(f"  Fetching {idx['name']}...")
        bars = fetch_dnse(idx['symbol'], 200)
        if bars:
            index_data[idx['key']] = {
                'name': idx['name'],
                'symbol': idx['symbol'],
                'bars': bars,
            }
            print(f"    Got {len(bars)} bars")
        else:
            print(f"    FAILED")
        time.sleep(0.2)

    # Step 2: Calculate indicators
    print("\n[2/4] Calculating technical indicators...")
    all_indicators = {}
    all_bars_summary = {}
    for key, data in index_data.items():
        ind = calc_indicators(data['bars'])
        all_indicators[key] = ind
        all_bars_summary[key] = data['bars'][-5:] if len(data['bars']) >= 5 else data['bars']
        print(f"  {key}: price={ind.get('last_price')}, change={ind.get('change_pct')}%, RSI={ind.get('rsi')}")

    # Step 3: Call Claude API ONCE
    print("\n[3/4] Calling Claude API (SINGLE CALL)...")
    mega_prompt = build_mega_prompt(all_indicators, all_bars_summary)
    ai_result = call_claude_single(mega_prompt)

    # Build FULL_DATA from AI result or fallback
    full_data = {}
    if ai_result:
        print("  AI analysis received!")
        # Use AI result, fill in any missing keys with fallback
        for key_name in ['overview', 'vnindex', 'vn30', 'vn100', 'vnmidcap']:
            if key_name in ai_result and 'sections' in ai_result[key_name]:
                full_data[key_name] = ai_result[key_name]
                print(f"    {key_name}: {len(ai_result[key_name]['sections'])} sections (AI)")
            else:
                # Fallback for this key
                if key_name == 'overview':
                    full_data[key_name] = {
                        'title': 'TONG HOP - Thi truong chung khoan Viet Nam',
                        'sections': make_fallback_overview(all_indicators),
                    }
                elif key_name in all_indicators:
                    idx_name = key_name.upper()
                    full_data[key_name] = {
                        'title': f'{idx_name} - Phan tich ky thuat',
                        'sections': make_fallback_sections(idx_name, all_indicators[key_name]),
                    }
                print(f"    {key_name}: fallback")
    else:
        print("  Using ALL fallback sections (no AI)")
        full_data['overview'] = {
            'title': 'TONG HOP - Thi truong chung khoan Viet Nam',
            'sections': make_fallback_overview(all_indicators),
        }
        for idx in INDEX_LIST:
            key = idx['key']
            if key in all_indicators:
                full_data[key] = {
                    'title': f'{idx["name"]} - Phan tich ky thuat',
                    'sections': make_fallback_sections(idx['name'], all_indicators[key]),
                }

    # Step 4: Fetch heatmap + build output
    print("\n[4/4] Fetching stock heatmap & building output...")
    heatmap = fetch_stock_heatmap()

    # Build index OHLCV export (last 100 bars for charts)
    index_ohlcv = {'indices': {}}
    for key, data in index_data.items():
        index_ohlcv['indices'][key] = {
            'name': data['name'],
            'bars': data['bars'][-100:],
        }

    # Generate metadata
    now = datetime.now()
    date_str = now.strftime('%d/%m/%Y')
    time_str = now.strftime('%d/%m/%Y %H:%M')
    meta = {
        'human_date': date_str,
        'human_updated_at': f'Cap nhat: {time_str}',
        'generated_at': now.isoformat(),
    }

    # Write to docs/v3_data.js
    os.makedirs('docs', exist_ok=True)
    data_file = 'docs/v3_data.js'
    with open(data_file, 'w', encoding='utf-8') as f:
        f.write(f'// Auto-generated {now.isoformat()}\n')
        f.write(f'const FULL_DATA = {json.dumps(full_data, ensure_ascii=False)};\n')
        f.write(f'const UI_GLM_INDEX_OHLCV = {json.dumps(index_ohlcv, ensure_ascii=False)};\n')
        f.write(f'const UI_GLM_VNINDEX_HEATMAP = {json.dumps(heatmap, ensure_ascii=False)};\n')
        f.write(f'const UI_GLM_REPORT_META = {json.dumps(meta, ensure_ascii=False)};\n')

    print(f"\n  Data written to {data_file}")
    print(f"  FULL_DATA has {len(full_data)} keys")
    for k, v in full_data.items():
        print(f"    {k}: {len(v.get('sections', []))} sections")

    print("\n" + "=" * 60)
    print("DONE! Open docs/dashboard_v3.html to view.")
    print("=" * 60)

    return {'full_data': full_data, 'index_ohlcv': index_ohlcv, 'heatmap': heatmap, 'meta': meta}


if __name__ == '__main__':
    generate_v3()
