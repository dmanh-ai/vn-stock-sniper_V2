"""
VN Stock Sniper - Data Fetcher V8
Universe: Top ~300 mã theo volume (HOSE + HNX)
Source: Entrade (DNSE) REST API - Không cần đăng nhập

Endpoint: https://services.entrade.com.vn/stock-price-service/v2/ohlc
  - Params: symbol, resolution (1D), from (unix), to (unix)
  - Free, public, no auth required
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

# Entrade API
ENTRADE_BASE_URL = "https://services.entrade.com.vn/stock-price-service/v2/ohlc"
REQUEST_DELAY = 0.3  # 300ms giữa mỗi request (tránh bị block)
REQUEST_TIMEOUT = 15  # 15s timeout per request


class EntradeFetcher:
    """Lấy dữ liệu từ Entrade (DNSE) REST API - Free, no auth"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        })
        self._request_count = 0
        self._last_request_time = 0

    def _throttle(self):
        """Rate limiting"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1

    def get_price_history(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """Lấy lịch sử giá OHLCV từ Entrade"""
        self._throttle()

        to_ts = int(time.time())
        from_ts = int((datetime.now() - timedelta(days=days)).timestamp())

        params = {
            'symbol': symbol,
            'resolution': '1D',
            'from': from_ts,
            'to': to_ts,
        }

        try:
            resp = self.session.get(
                ENTRADE_BASE_URL,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            data = resp.json()

            if not data or data.get('s') == 'no_data':
                return pd.DataFrame()

            # Entrade trả về format: {t: [...], o: [...], h: [...], l: [...], c: [...], v: [...]}
            if 't' in data and 'c' in data:
                df = pd.DataFrame({
                    'time': pd.to_datetime(data['t'], unit='s'),
                    'open': data.get('o', data['c']),
                    'high': data.get('h', data['c']),
                    'low': data.get('l', data['c']),
                    'close': data['c'],
                    'volume': data.get('v', [0] * len(data['c'])),
                })
                df['symbol'] = symbol
                return df

            return pd.DataFrame()

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                print(f"   ⏳ Rate limit! Chờ 30s...")
                time.sleep(30)
                return self.get_price_history(symbol, days)
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()


class DataFetcher:
    """Lấy dữ liệu chứng khoán Việt Nam - Top 300 mã - Entrade API"""

    # === DANH SÁCH CỐ ĐỊNH ===
    VN100_SYMBOLS = [
        # VN30
        'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
        'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
        'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE',
        # VNMidCap (70 mã)
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

    # === MÃ BỔ SUNG để đạt ~300 ===
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
        self.fetcher = EntradeFetcher()
        print("✅ Entrade API: Sẵn sàng (no auth required)")

    def get_symbols(self) -> list:
        """Lấy danh sách ~300 mã (HOSE + HNX)"""
        print(f"📋 Lấy danh sách top {TOP_STOCKS_COUNT} mã...")

        all_symbols = list(dict.fromkeys(self.VN100_SYMBOLS + self.HNX30_SYMBOLS))
        print(f"   📋 VN100 + HNX30: {len(all_symbols)} mã (cố định)")

        if len(all_symbols) < TOP_STOCKS_COUNT:
            extra = [s for s in self.EXTRA_HOSE_SYMBOLS + self.EXTRA_HNX_SYMBOLS
                     if s not in all_symbols]
            need = TOP_STOCKS_COUNT - len(all_symbols)
            all_symbols.extend(extra[:need])

        print(f"   📊 Tổng: {len(all_symbols)} mã")
        return all_symbols

    def fetch_all_data(self) -> pd.DataFrame:
        """Lấy dữ liệu tất cả mã từ Entrade"""
        symbols = self.get_symbols()

        print(f"\n📥 Lấy dữ liệu {len(symbols)} mã từ Entrade (DNSE)...")
        print(f"⏰ Rate limit: {REQUEST_DELAY}s/req | Timeout: {REQUEST_TIMEOUT}s/mã\n")

        all_data = []
        ok = 0
        fail = 0
        t0 = time.time()

        for i, symbol in enumerate(symbols):
            elapsed = time.time() - t0
            if elapsed > 1800:
                print(f"\n⚠️ QUÁ 30 PHÚT - Dừng ({ok} mã)")
                break

            df = self.fetcher.get_price_history(symbol)

            if not df.empty:
                all_data.append(df)
                ok += 1
                if (i + 1) % 20 == 0 or (i + 1) == len(symbols):
                    print(f"   [{i+1}/{len(symbols)}] ✅ {ok} mã OK / {fail} fail")
            else:
                fail += 1
                if fail <= 5:
                    print(f"   [{i+1}/{len(symbols)}] ❌ {symbol}")

        total = time.time() - t0
        print(f"\n{'='*50}")
        print(f"📊 {ok} ✅ / {fail} ❌ / {len(symbols)} tổng")
        print(f"📡 Nguồn: Entrade (DNSE)")
        print(f"⏱️ {total:.0f}s ({total/60:.1f} phút)")
        print(f"{'='*50}")

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

    def save_data(self, df: pd.DataFrame):
        """Lưu file"""
        if df.empty:
            print("❌ Không có data")
            return

        os.makedirs(DATA_DIR, exist_ok=True)
        df.to_csv(RAW_DATA_FILE, index=False)
        symbols_count = df['symbol'].nunique() if 'symbol' in df.columns else 0
        print(f"✅ Saved: {RAW_DATA_FILE} ({len(df)} rows, {symbols_count} mã)")

    def run(self) -> pd.DataFrame:
        """Chạy lấy dữ liệu"""
        print("=" * 60)
        print("📥 BẮT ĐẦU LẤY DỮ LIỆU - TOP 300 MÃ (Entrade API)")
        print("=" * 60)

        df = self.fetch_all_data()

        if not df.empty:
            self.save_data(df)

        return df


if __name__ == "__main__":
    fetcher = DataFetcher()
    df = fetcher.run()
    symbols_count = df['symbol'].nunique() if not df.empty and 'symbol' in df.columns else 0
    print(f"\nKết quả: {len(df)} rows, {symbols_count} mã")
