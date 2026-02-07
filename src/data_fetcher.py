"""
VN Stock Sniper - Data Fetcher V9
Universe: Top ~300 ma theo volume (HOSE + HNX)
Multi-source: TCBS API (primary) + VCI/Vietcap API (fallback)

Sources (from vnstock community research):
  1. TCBS: https://apiextaws.tcbs.com.vn/stock-insight/v2/stock/bars-long-term
     - GET, params: resolution=D, ticker, type=stock, to (unix), countBack
  2. VCI:  https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart
     - POST, json: {timeFrame, symbols, to (unix), countBack}
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import json
import requests

from src.config import (
    DATA_START_DATE, DATA_DIR, RAW_DATA_FILE, TOP_STOCKS_COUNT
)

REQUEST_DELAY = 0.15  # 150ms between requests
REQUEST_TIMEOUT = 15  # 15s timeout per request


class TCBSFetcher:
    """TCBS API v2 - Updated endpoint (apiextaws)"""

    BASE_URL = "https://apiextaws.tcbs.com.vn/stock-insight/v2/stock/bars-long-term"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })

    def get_price_history(self, symbol: str, count_back: int = 365) -> pd.DataFrame:
        to_ts = int(time.time())
        url = (
            f"{self.BASE_URL}?resolution=D&ticker={symbol}"
            f"&type=stock&to={to_ts}&countBack={count_back}"
        )

        resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if not data or 'data' not in data or not data['data']:
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])

        # Map TCBS columns: tradingDate -> time
        col_map = {}
        for col in df.columns:
            cl = col.lower()
            if 'trading' in cl and 'date' in cl:
                col_map[col] = 'time'
            elif cl == 'open':
                col_map[col] = 'open'
            elif cl == 'high':
                col_map[col] = 'high'
            elif cl == 'low':
                col_map[col] = 'low'
            elif cl == 'close':
                col_map[col] = 'close'
            elif cl == 'volume':
                col_map[col] = 'volume'

        if col_map:
            df = df.rename(columns=col_map)

        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])

        df['symbol'] = symbol

        required = ['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']
        if all(c in df.columns for c in required):
            return df[required]

        return pd.DataFrame()


class VCIFetcher:
    """VCI (Vietcap/VNDirect) API - Recommended long-term source"""

    BASE_URL = "https://trading.vietcap.com.vn/api/chart/OHLCChart/gap-chart"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })

    def get_price_history(self, symbol: str, count_back: int = 365) -> pd.DataFrame:
        to_ts = int(time.time())
        payload = {
            "timeFrame": "ONE_DAY",
            "symbols": [symbol],
            "to": to_ts,
            "countBack": count_back,
        }

        resp = self.session.post(self.BASE_URL, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        # VCI response can be: list, dict with 'data', or vectorized {t:[], o:[], ...}
        records = data
        if isinstance(data, dict):
            if 'data' in data:
                records = data['data']

        # Handle vectorized format: {t: [...], o: [...], h: [...], ...}
        if isinstance(records, dict) and 't' in records:
            df = pd.DataFrame(records)
            col_map = {'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}
            df = df.rename(columns=col_map)
        elif isinstance(records, list) and len(records) > 0:
            df = pd.DataFrame(records)
            # Try common column name patterns
            col_map = {}
            for col in df.columns:
                cl = col.lower()
                if cl in ('t', 'time', 'tradingdate', 'trading_date', 'date'):
                    col_map[col] = 'time'
                elif cl in ('o', 'open'):
                    col_map[col] = 'open'
                elif cl in ('h', 'high'):
                    col_map[col] = 'high'
                elif cl in ('l', 'low'):
                    col_map[col] = 'low'
                elif cl in ('c', 'close'):
                    col_map[col] = 'close'
                elif cl in ('v', 'volume'):
                    col_map[col] = 'volume'
            if col_map:
                df = df.rename(columns=col_map)
        else:
            return pd.DataFrame()

        if df.empty:
            return pd.DataFrame()

        # Convert time: try unix seconds, then unix milliseconds, then datetime string
        if 'time' in df.columns:
            sample = df['time'].iloc[0]
            if isinstance(sample, (int, float, np.integer, np.floating)):
                if sample > 1e12:  # milliseconds
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                else:  # seconds
                    df['time'] = pd.to_datetime(df['time'], unit='s')
            else:
                df['time'] = pd.to_datetime(df['time'])

        df['symbol'] = symbol

        required = ['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']
        if all(c in df.columns for c in required):
            return df[required]

        return pd.DataFrame()


class MultiSourceFetcher:
    """Try multiple data sources with automatic fallback"""

    def __init__(self):
        self.tcbs = TCBSFetcher()
        self.vci = VCIFetcher()
        self._request_count = 0
        self._last_request_time = 0
        self._active_source = None  # Will be set after probe

    def _throttle(self):
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1

    def probe_sources(self) -> str:
        """Test which data source works by fetching ACB data"""
        test_symbol = "ACB"

        # Try TCBS first
        print("   Testing TCBS API (apiextaws.tcbs.com.vn)...")
        try:
            df = self.tcbs.get_price_history(test_symbol, count_back=5)
            if not df.empty and len(df) > 0:
                print(f"   TCBS: OK ({len(df)} rows)")
                return "TCBS"
            else:
                print("   TCBS: Empty response")
        except Exception as e:
            print(f"   TCBS: Failed - {type(e).__name__}: {e}")

        # Try VCI fallback
        print("   Testing VCI API (trading.vietcap.com.vn)...")
        try:
            df = self.vci.get_price_history(test_symbol, count_back=5)
            if not df.empty and len(df) > 0:
                print(f"   VCI: OK ({len(df)} rows)")
                return "VCI"
            else:
                print("   VCI: Empty response")
        except Exception as e:
            print(f"   VCI: Failed - {type(e).__name__}: {e}")

        print("   Both sources failed!")
        return ""

    def get_price_history(self, symbol: str, count_back: int = 365) -> pd.DataFrame:
        self._throttle()

        # Use the active source determined by probe
        try:
            if self._active_source == "TCBS":
                df = self.tcbs.get_price_history(symbol, count_back)
                if not df.empty:
                    return df
                # Fallback to VCI
                df = self.vci.get_price_history(symbol, count_back)
                return df
            elif self._active_source == "VCI":
                df = self.vci.get_price_history(symbol, count_back)
                if not df.empty:
                    return df
                # Fallback to TCBS
                df = self.tcbs.get_price_history(symbol, count_back)
                return df
            else:
                # No source determined, try both
                try:
                    df = self.tcbs.get_price_history(symbol, count_back)
                    if not df.empty:
                        return df
                except Exception:
                    pass
                try:
                    df = self.vci.get_price_history(symbol, count_back)
                    if not df.empty:
                        return df
                except Exception:
                    pass
                return pd.DataFrame()

        except Exception as e:
            if self._request_count <= 5:
                print(f"   {symbol}: {type(e).__name__}: {e}")
            return pd.DataFrame()


class DataFetcher:
    """Lay du lieu chung khoan Viet Nam - Top 300 ma - Multi-source"""

    # === DANH SACH CO DINH ===
    VN100_SYMBOLS = [
        # VN30
        'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
        'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
        'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE',
        # VNMidCap (70 ma)
        'ANV', 'APH', 'ASM', 'BAF', 'BMP', 'BSR', 'BWE', 'CII', 'CMG', 'CTD',
        'DBC', 'DCM', 'DGC', 'DGW', 'DHC', 'DIG', 'DPM', 'DXG', 'DXS', 'EVF',
        'FCN', 'FRT', 'GEX', 'GMD', 'HAH', 'HCM', 'HDC', 'HDG', 'HSG', 'HT1',
        'IDI', 'IMP', 'KBC', 'KDC', 'KDH', 'KOS', 'LPB', 'MSH', 'NKG', 'NLG',
        'NT2', 'NVL', 'ORS', 'PAN', 'PC1', 'PDR', 'PGV', 'PHR', 'PNJ', 'PPC',
        'PVD', 'PVT', 'REE', 'SBT', 'SCS', 'SIP', 'SJS', 'STG', 'SZC', 'TCH',
        'TLG', 'TNH', 'VCG', 'VCI', 'VGC', 'VHC', 'VND', 'VOS', 'VPI', 'VTP',
    ]

    HNX30_SYMBOLS = [
        'BAB', 'BVS', 'CEO', 'DTD', 'HUT', 'IDC', 'L14', 'MBS', 'NDN', 'NRC',
        'NTP', 'PLC', 'PVB', 'PVI', 'PVS', 'S99', 'SHN', 'SHS', 'TDC', 'THD',
        'TIG', 'TNG', 'TVS', 'VC3', 'VCS', 'VGS', 'VIX', 'VLA', 'VMC', 'VNR',
    ]

    # === MA BO SUNG de dat ~300 ===
    EXTRA_HOSE_SYMBOLS = [
        'AAA', 'ABB', 'AGG', 'AGR', 'APG', 'BCG', 'BFC', 'BHN', 'BIC', 'BMI',
        'BRC', 'BSI', 'BTS', 'BVB', 'CAV', 'CHP', 'CIG', 'CLC', 'CLW', 'CMX',
        'CNG', 'COM', 'CRC', 'CRE', 'CSM', 'CSV', 'CTF', 'CTI', 'CTR', 'D2D',
        'DAH', 'DAT', 'DBD', 'DHA', 'DHG', 'DLG', 'DMC', 'DPG', 'DPR', 'DRC',
        'DRL', 'DSN', 'DTA', 'DTL', 'DVP', 'ELC', 'EMC', 'EVG', 'FDC', 'FIT',
        'FMC', 'FOX', 'FTS', 'GDT', 'GIL', 'GLW', 'GSP', 'GTA', 'GTN', 'HAG',
        'HAI', 'HAP', 'HAS', 'HAX', 'HBC', 'HCD', 'HCT', 'HDG', 'HHP', 'HHS',
        'HID', 'HII', 'HLG', 'HMC', 'HNG', 'HOT', 'HPX', 'HQC', 'HRC', 'HSL',
        'HTI', 'HTL', 'HTN', 'HTV', 'HU1', 'HUB', 'ICT', 'IJC', 'ILB', 'ITA',
        'ITD', 'JVC', 'KHA', 'KHP', 'KMR', 'KPF', 'KSB', 'KSH', 'L10', 'LAF',
        'LBM', 'LCD', 'LCG', 'LDG', 'LEC', 'LGC', 'LGL', 'LHG', 'LIX', 'LM8',
        'LSS', 'MCP', 'MDG', 'MHC', 'NAF', 'NAV', 'NBB', 'NCT', 'NET', 'NHH',
        'NNC', 'NTL', 'OPC', 'OGC', 'PAC', 'PBC', 'PDN', 'PET', 'PGD', 'PGI',
        'PIT', 'PLP', 'PMG', 'POM', 'PTB', 'PTL', 'QBS', 'QCG', 'RAL', 'RDP',
        'S4A', 'SAM', 'SBA', 'SBV', 'SC5', 'SCD', 'SCR', 'SGN', 'SGR', 'SGT',
        'SHA', 'SHI', 'SMB', 'SMC', 'SPM', 'SRC', 'SRF', 'SSC', 'ST8', 'STK',
        'SVD', 'SVT', 'SZL', 'TBC', 'TCL', 'TCM', 'TCO', 'TCR', 'TDH', 'TDM',
    ]

    EXTRA_HNX_SYMBOLS = [
        'AMV', 'BCC', 'BDB', 'BKC', 'CAG', 'CIA', 'CPC', 'CVT', 'DAD',
        'DAS', 'DHP', 'DNP', 'DS3', 'DTK', 'DTV', 'DVG', 'EVS', 'GKM',
        'HBS', 'HGM', 'HKB', 'HLC', 'HLD', 'HMH', 'HNM', 'HOM', 'ICG',
        'KMT', 'KSD', 'KTS', 'LAS', 'LCS', 'LHC', 'MAC', 'MBG', 'MCO',
        'NBC', 'NHC', 'NHT', 'NSH', 'PHP', 'PMC', 'PMS', 'PPE', 'PSC',
    ]

    def __init__(self):
        self.fetcher = MultiSourceFetcher()

    def get_symbols(self) -> list:
        print(f"📋 Lay danh sach top {TOP_STOCKS_COUNT} ma...")

        all_symbols = list(dict.fromkeys(self.VN100_SYMBOLS + self.HNX30_SYMBOLS))
        print(f"   📋 VN100 + HNX30: {len(all_symbols)} ma (co dinh)")

        if len(all_symbols) < TOP_STOCKS_COUNT:
            extra = [s for s in self.EXTRA_HOSE_SYMBOLS + self.EXTRA_HNX_SYMBOLS
                     if s not in all_symbols]
            need = TOP_STOCKS_COUNT - len(all_symbols)
            all_symbols.extend(extra[:need])

        print(f"   📊 Tong: {len(all_symbols)} ma")
        return all_symbols

    def fetch_all_data(self) -> pd.DataFrame:
        symbols = self.get_symbols()

        # Probe which source works before fetching all
        print("\n🔍 Kiem tra nguon du lieu...")
        source = self.fetcher.probe_sources()
        if not source:
            print("❌ Khong the ket noi den bat ky nguon du lieu nao!")
            print("   - TCBS: apiextaws.tcbs.com.vn")
            print("   - VCI:  trading.vietcap.com.vn")
            return pd.DataFrame()

        self.fetcher._active_source = source
        print(f"✅ Su dung nguon: {source}\n")

        print(f"📥 Lay du lieu {len(symbols)} ma tu {source}...")
        print(f"⏰ Rate limit: {REQUEST_DELAY}s/req | Timeout: {REQUEST_TIMEOUT}s/ma\n")

        all_data = []
        ok = 0
        fail = 0
        t0 = time.time()

        for i, symbol in enumerate(symbols):
            elapsed = time.time() - t0
            if elapsed > 1800:
                print(f"\n⚠️ QUA 30 PHUT - Dung ({ok} ma)")
                break

            df = self.fetcher.get_price_history(symbol)

            if not df.empty:
                all_data.append(df)
                ok += 1
                if (i + 1) % 20 == 0 or (i + 1) == len(symbols):
                    print(f"   [{i+1}/{len(symbols)}] ✅ {ok} ma OK / {fail} fail")
            else:
                fail += 1
                if fail <= 10:
                    print(f"   [{i+1}/{len(symbols)}] ❌ {symbol}")

            # Early abort if first 10 stocks all fail
            if i == 9 and ok == 0:
                print(f"\n❌ 10 ma dau tien deu that bai - dung lai!")
                print(f"   Nguon {source} co the khong hoat dong.")
                break

        total = time.time() - t0
        print(f"\n{'='*50}")
        print(f"📊 {ok} ✅ / {fail} ❌ / {len(symbols)} tong")
        print(f"📡 Nguon: {source}")
        print(f"⏱️ {total:.0f}s ({total/60:.1f} phut)")
        print(f"{'='*50}")

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

    def save_data(self, df: pd.DataFrame):
        if df.empty:
            print("❌ Khong co data")
            return

        os.makedirs(DATA_DIR, exist_ok=True)
        df.to_csv(RAW_DATA_FILE, index=False)
        symbols_count = df['symbol'].nunique() if 'symbol' in df.columns else 0
        print(f"✅ Saved: {RAW_DATA_FILE} ({len(df)} rows, {symbols_count} ma)")

    def run(self) -> pd.DataFrame:
        print("=" * 60)
        print("📥 BAT DAU LAY DU LIEU - TOP 300 MA")
        print("   Nguon: TCBS (primary) + VCI (fallback)")
        print("=" * 60)

        df = self.fetch_all_data()

        if not df.empty:
            self.save_data(df)

        return df


if __name__ == "__main__":
    fetcher = DataFetcher()
    df = fetcher.run()
    symbols_count = df['symbol'].nunique() if not df.empty and 'symbol' in df.columns else 0
    print(f"\nKet qua: {len(df)} rows, {symbols_count} ma")
