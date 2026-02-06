"""
VN Stock Sniper - Data Fetcher V6
Universe: Top ~300 mã theo volume (HOSE + HNX)
Source: FiinQuantX ONLY (fiinquant.vn)

Rate limits FiinQuantX (free):
  - 90 requests/phút, 80 requests/giây
  - Max 33 mã/lần (lịch sử), period tối đa 1 năm
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import threading
import json
import re

from src.config import (
    DATA_START_DATE, DATA_SOURCE,
    DATA_DIR, RAW_DATA_FILE,
    FIINQUANT_USERNAME, FIINQUANT_PASSWORD
)

# File lưu danh sách mã động
SYMBOLS_CACHE_FILE = f"{DATA_DIR}/symbols_cache.json"

# Rate limit settings
FIINQUANT_BATCH_SIZE = 33       # Max mã/request theo FiinQuant
FIINQUANT_DELAY = 0.8           # Giây giữa mỗi request (~75 req/phút, dưới limit 90)
FIINQUANT_RATE_LIMIT_WAIT = 65  # Chờ 65 giây khi bị rate limit


def is_rate_limit_error(error_msg: str) -> bool:
    """Kiểm tra lỗi có phải rate limit không"""
    keywords = ['rate limit', 'too many', '429', 'giới hạn', 'limit exceeded',
                'maximum api request', 'wait to retry']
    msg = str(error_msg).lower()
    return any(k in msg for k in keywords)


def load_cached_symbols():
    """Đọc danh sách mã từ cache"""
    try:
        if os.path.exists(SYMBOLS_CACHE_FILE):
            with open(SYMBOLS_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            # Support both old and new cache format
            if 'all_symbols' in cache:
                symbols = cache['all_symbols']
                updated = cache.get('updated', '')
                print(f"   📋 Cache: {len(symbols)} mã (cập nhật: {updated})")
                return symbols
            vn100 = cache.get('vn100', [])
            hnx30 = cache.get('hnx30', [])
            updated = cache.get('updated', '')
            if vn100 or hnx30:
                print(f"   📋 Cache: VN100={len(vn100)}, HNX30={len(hnx30)} (cập nhật: {updated})")
                return list(dict.fromkeys(vn100 + hnx30))
    except Exception:
        pass
    return []


class FiinQuantFetcher:
    """Lấy dữ liệu từ FiinQuantX - tận dụng tối đa, xử lý rate limit"""

    TRADING_FIELDS = ['open', 'high', 'low', 'close', 'volume', 'value']
    BASIC_FIELDS = ['open', 'high', 'low', 'close', 'volume']

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.client = None
        self._extra_fields_available = None
        self._request_count = 0
        self._last_request_time = 0

    def login(self) -> bool:
        """Đăng nhập FiinQuant"""
        try:
            from FiinQuantX import FiinSession
            self.client = FiinSession(
                username=self.username,
                password=self.password
            ).login()
            print("✅ FiinQuant: Đăng nhập thành công")
            self._discover_methods()
            return True
        except ImportError:
            print("❌ FiinQuantX chưa cài đặt. Cài bằng:")
            print("   pip install --extra-index-url https://fiinquant.github.io/fiinquantx/simple fiinquantx")
            return False
        except Exception as e:
            print(f"❌ FiinQuant: Lỗi đăng nhập - {e}")
            return False

    def _discover_methods(self):
        """Khám phá các method có sẵn trong FiinQuantX client"""
        if not self.client:
            return
        methods = [m for m in dir(self.client) if not m.startswith('_')]
        fetch_methods = [m for m in methods if 'fetch' in m.lower() or 'get' in m.lower()]
        if fetch_methods:
            print(f"   📡 FiinQuant methods: {', '.join(fetch_methods)}")

    def _throttle(self):
        """Rate limiting: đảm bảo không vượt quá 90 req/phút"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < FIINQUANT_DELAY:
            time.sleep(FIINQUANT_DELAY - elapsed)
        self._last_request_time = time.time()
        self._request_count += 1

    def _handle_rate_limit(self, error_msg: str) -> bool:
        """Xử lý rate limit: chờ rồi retry. Return True nếu nên retry."""
        if is_rate_limit_error(error_msg):
            wait_time = FIINQUANT_RATE_LIMIT_WAIT
            match = re.search(r'(\d+)\s*(?:giây|second|sec)', str(error_msg).lower())
            if match:
                wait_time = int(match.group(1)) + 5

            print(f"   ⏳ Rate limit! Chờ {wait_time}s...")
            time.sleep(wait_time)
            return True
        return False

    def get_price_history(self, symbol: str, period: int = 250) -> pd.DataFrame:
        """Lấy lịch sử giá 1 mã từ FiinQuant (period max 250 cho free tier ~1 năm)"""
        if not self.client:
            return pd.DataFrame()

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                self._throttle()
                fields = self.TRADING_FIELDS if self._extra_fields_available is not False else self.BASIC_FIELDS

                try:
                    data = self.client.Fetch_Trading_Data(
                        tickers=symbol,
                        fields=fields,
                        adjusted=True,
                        period=period,
                        realtime=False,
                        by='1d',
                    ).get_data()
                except Exception as e:
                    if self._handle_rate_limit(str(e)) and attempt < max_retries:
                        continue
                    if fields != self.BASIC_FIELDS:
                        self._extra_fields_available = False
                        self._throttle()
                        data = self.client.Fetch_Trading_Data(
                            tickers=symbol,
                            fields=self.BASIC_FIELDS,
                            adjusted=True,
                            period=period,
                            realtime=False,
                            by='1d',
                        ).get_data()
                    else:
                        raise

                if self._extra_fields_available is None and data is not None:
                    self._extra_fields_available = True

                if data is not None and len(data) > 0:
                    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
                    return self._normalize_df(df, symbol)

                return pd.DataFrame()

            except Exception as e:
                if self._handle_rate_limit(str(e)) and attempt < max_retries:
                    continue
                if attempt == max_retries:
                    print(f"   ❌ FiinQuant {symbol}: {e}")
                return pd.DataFrame()

        return pd.DataFrame()

    def _normalize_df(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Chuẩn hóa DataFrame từ FiinQuant"""
        col_map = {}
        for col in df.columns:
            cl = col.lower().strip()
            if 'time' in cl or 'date' in cl:
                col_map[col] = 'time'
            elif cl in ['open', 'high', 'low', 'close', 'volume', 'value']:
                col_map[col] = cl
            elif 'ticker' in cl or 'symbol' in cl:
                col_map[col] = 'ticker_col'

        if col_map:
            df = df.rename(columns=col_map)

        if 'time' not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex):
                df['time'] = df.index
                df = df.reset_index(drop=True)
            else:
                for col in df.columns:
                    try:
                        df['time'] = pd.to_datetime(df[col])
                        break
                    except (ValueError, TypeError):
                        continue

        df['symbol'] = symbol

        required = ['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']
        optional = ['value']

        if all(c in df.columns for c in required):
            keep = required + [c for c in optional if c in df.columns]
            return df[keep]

        print(f"   ⚠️ {symbol}: Thiếu columns. Có: {list(df.columns)}")
        return pd.DataFrame()


class DataFetcher:
    """Lấy dữ liệu chứng khoán Việt Nam - Top 300 mã - FiinQuant ONLY"""

    # === DANH SÁCH CỐ ĐỊNH (fallback khi không lấy được động) ===
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

    # === MÃ BỔ SUNG để đạt ~300 (HOSE + HNX thanh khoản cao) ===
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
        self.source = DATA_SOURCE
        self.fiinquant = None

        # FiinQuant ONLY - không fallback vnstock
        if FIINQUANT_USERNAME and FIINQUANT_PASSWORD:
            self.fiinquant = FiinQuantFetcher(FIINQUANT_USERNAME, FIINQUANT_PASSWORD)
            if not self.fiinquant.login():
                self.fiinquant = None
                print("❌ FiinQuant login thất bại. Không có nguồn dữ liệu!")
        else:
            print("❌ Thiếu FIINQUANT_USERNAME / FIINQUANT_PASSWORD trong .env")
            print("   Vui lòng cấu hình FiinQuant credentials.")

    def get_symbols(self) -> list:
        """Lấy danh sách ~300 mã (HOSE + HNX)"""
        from src.config import TOP_STOCKS_COUNT
        print(f"📋 Lấy danh sách top {TOP_STOCKS_COUNT} mã...")

        # Bước 1: Thử đọc từ cache
        cached = load_cached_symbols()
        if len(cached) >= 100:
            if len(cached) >= TOP_STOCKS_COUNT:
                return cached[:TOP_STOCKS_COUNT]

        # Bước 2: Dùng danh sách cố định
        all_symbols = list(dict.fromkeys(self.VN100_SYMBOLS + self.HNX30_SYMBOLS))
        print(f"   📋 VN100 + HNX30: {len(all_symbols)} mã (cố định)")

        # Bước 3: Bổ sung thêm mã để đạt ~300
        if len(all_symbols) < TOP_STOCKS_COUNT:
            extra = [s for s in self.EXTRA_HOSE_SYMBOLS + self.EXTRA_HNX_SYMBOLS
                     if s not in all_symbols]
            need = TOP_STOCKS_COUNT - len(all_symbols)
            all_symbols.extend(extra[:need])

        print(f"   📊 Tổng: {len(all_symbols)} mã")
        return all_symbols

    def fetch_with_timeout(self, symbol: str, timeout_sec: int = 30) -> pd.DataFrame:
        """Lấy data với timeout"""
        if not self.fiinquant:
            return pd.DataFrame()

        result = [pd.DataFrame()]

        def fetch():
            try:
                result[0] = self.fiinquant.get_price_history(symbol)
            except Exception:
                pass

        thread = threading.Thread(target=fetch)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout_sec)

        if thread.is_alive():
            print(f"   ⏰ {symbol}: TIMEOUT")
            return pd.DataFrame()

        return result[0]

    def fetch_all_data(self) -> pd.DataFrame:
        """Lấy dữ liệu tất cả mã - FiinQuant ONLY"""
        if not self.fiinquant:
            print("❌ Không có FiinQuant connection. Dừng.")
            return pd.DataFrame()

        symbols = self.get_symbols()

        print(f"\n📥 Lấy dữ liệu {len(symbols)} mã từ FiinQuant...")
        print(f"⏰ Rate limit: {FIINQUANT_DELAY}s/req | Timeout: 30s/mã\n")

        all_data = []
        ok = 0
        fail = 0
        t0 = time.time()

        for i, symbol in enumerate(symbols):
            # Safety: max 30 phút
            elapsed = time.time() - t0
            if elapsed > 1800:
                print(f"\n⚠️ QUÁ 30 PHÚT - Dừng ({ok} mã)")
                break

            df = self.fetch_with_timeout(symbol, timeout_sec=30)

            if not df.empty:
                all_data.append(df)
                ok += 1
                print(f"   [{i+1}/{len(symbols)}] ✅ {symbol} ({len(df)} rows)")
            else:
                fail += 1
                print(f"   [{i+1}/{len(symbols)}] ❌ {symbol}")

        total = time.time() - t0
        print(f"\n{'='*50}")
        print(f"📊 {ok} ✅ / {fail} ❌ / {len(symbols)} tổng")
        print(f"📡 Nguồn: FiinQuant")
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
        print("📥 BẮT ĐẦU LẤY DỮ LIỆU - TOP 300 MÃ (FiinQuant ONLY)")
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
