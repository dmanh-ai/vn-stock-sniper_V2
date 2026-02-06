"""
VN Stock Sniper - Data Fetcher V5
Universe: VN100 (HOSE) + HNX30 (HNX) = ~130 mã
Primary: FiinQuantX (fiinquant.vn) - tận dụng tối đa dữ liệu
Fallback: vnstock
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import threading
import json

from src.config import (
    DATA_START_DATE, DATA_SOURCE,
    DATA_DIR, RAW_DATA_FILE,
    FIINQUANT_USERNAME, FIINQUANT_PASSWORD
)

# File lưu danh sách mã động
SYMBOLS_CACHE_FILE = f"{DATA_DIR}/symbols_cache.json"
FUNDAMENTAL_FILE = f"{DATA_DIR}/fundamental_data.csv"


def get_dynamic_symbols():
    """Lấy danh sách mã VN100 + HNX30 động từ vnstock"""
    try:
        from vnstock import Vnstock
        vs = Vnstock()
        stock = vs.stock(symbol='ACB', source='VCI')

        vn100 = []
        hnx30 = []

        try:
            vn100_data = stock.listing.symbols_by_group('VN100')
            if vn100_data is not None:
                if isinstance(vn100_data, pd.DataFrame):
                    # Tìm column chứa symbol
                    for col in ['symbol', 'ticker', 'code', 'Symbol', 'Ticker']:
                        if col in vn100_data.columns:
                            vn100 = vn100_data[col].tolist()
                            break
                    if not vn100 and len(vn100_data.columns) > 0:
                        vn100 = vn100_data.iloc[:, 0].tolist()
                elif isinstance(vn100_data, list):
                    vn100 = vn100_data
                print(f"   ✅ VN100: {len(vn100)} mã (dynamic)")
        except Exception as e:
            print(f"   ⚠️ VN100 dynamic fetch failed: {e}")

        try:
            hnx30_data = stock.listing.symbols_by_group('HNX30')
            if hnx30_data is not None:
                if isinstance(hnx30_data, pd.DataFrame):
                    for col in ['symbol', 'ticker', 'code', 'Symbol', 'Ticker']:
                        if col in hnx30_data.columns:
                            hnx30 = hnx30_data[col].tolist()
                            break
                    if not hnx30 and len(hnx30_data.columns) > 0:
                        hnx30 = hnx30_data.iloc[:, 0].tolist()
                elif isinstance(hnx30_data, list):
                    hnx30 = hnx30_data
                print(f"   ✅ HNX30: {len(hnx30)} mã (dynamic)")
        except Exception as e:
            print(f"   ⚠️ HNX30 dynamic fetch failed: {e}")

        if vn100 or hnx30:
            # Lưu cache
            cache = {
                'vn100': [str(s) for s in vn100],
                'hnx30': [str(s) for s in hnx30],
                'updated': datetime.now().strftime('%Y-%m-%d %H:%M')
            }
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(SYMBOLS_CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)
            return vn100, hnx30

    except ImportError:
        print("   ⚠️ vnstock chưa cài để lấy danh sách động")
    except Exception as e:
        print(f"   ⚠️ Lỗi lấy danh sách động: {e}")

    return [], []


def load_cached_symbols():
    """Đọc danh sách mã từ cache"""
    try:
        if os.path.exists(SYMBOLS_CACHE_FILE):
            with open(SYMBOLS_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            vn100 = cache.get('vn100', [])
            hnx30 = cache.get('hnx30', [])
            updated = cache.get('updated', '')
            if vn100 or hnx30:
                print(f"   📋 Cache: VN100={len(vn100)}, HNX30={len(hnx30)} (cập nhật: {updated})")
                return vn100, hnx30
    except Exception:
        pass
    return [], []


class FiinQuantFetcher:
    """Lấy dữ liệu từ FiinQuantX - tận dụng tối đa"""

    # Các fields trading data mở rộng
    TRADING_FIELDS = ['open', 'high', 'low', 'close', 'volume', 'value']
    BASIC_FIELDS = ['open', 'high', 'low', 'close', 'volume']

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.client = None
        self._extra_fields_available = None

    def login(self) -> bool:
        """Đăng nhập FiinQuant"""
        try:
            from FiinQuantX import FiinSession
            self.client = FiinSession(
                username=self.username,
                password=self.password
            ).login()
            print("✅ FiinQuant: Đăng nhập thành công")

            # Thử khám phá các method có sẵn
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

    def get_price_history(self, symbol: str, period: int = 500) -> pd.DataFrame:
        """Lấy lịch sử giá 1 mã từ FiinQuant - thử lấy nhiều fields nhất"""
        if not self.client:
            return pd.DataFrame()

        try:
            # Thử lấy với fields mở rộng trước
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
            except Exception:
                # Fallback về basic fields
                if fields != self.BASIC_FIELDS:
                    self._extra_fields_available = False
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
            print(f"   ❌ FiinQuant {symbol}: {e}")
            return pd.DataFrame()

    def _normalize_df(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Chuẩn hóa DataFrame từ FiinQuant"""
        # Map columns
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

        # Đảm bảo có column time
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

        # Columns cần thiết + optional
        required = ['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']
        optional = ['value']

        if all(c in df.columns for c in required):
            keep = required + [c for c in optional if c in df.columns]
            return df[keep]

        print(f"   ⚠️ {symbol}: Thiếu columns. Có: {list(df.columns)}")
        return pd.DataFrame()

    def fetch_fundamental(self, symbols: list) -> pd.DataFrame:
        """Thử lấy dữ liệu cơ bản (PE, PB, EPS...) từ FiinQuant"""
        if not self.client:
            return pd.DataFrame()

        results = []

        # Thử các method có thể có trong FiinQuantX
        for method_name in ['Fetch_Financial_Data', 'Fetch_Ratio_Data',
                            'Fetch_Fundamental_Data', 'Fetch_Market_Data']:
            method = getattr(self.client, method_name, None)
            if method is None:
                continue

            print(f"   📊 Thử {method_name}...")

            for symbol in symbols:
                try:
                    # Thử các cách gọi khác nhau
                    data = None
                    try:
                        data = method(
                            tickers=symbol,
                            fields=['pe', 'pb', 'eps', 'roe', 'roa', 'market_cap',
                                    'dividend_yield', 'debt_to_equity'],
                            period=1,
                            by='quarter',
                        ).get_data()
                    except Exception:
                        try:
                            data = method(
                                tickers=symbol,
                                period=1,
                            ).get_data()
                        except Exception:
                            pass

                    if data is not None and len(data) > 0:
                        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
                        df['symbol'] = symbol
                        results.append(df)

                except Exception:
                    continue

            if results:
                print(f"   ✅ {method_name}: Lấy được {len(results)} mã")
                break

        if results:
            return pd.concat(results, ignore_index=True)
        return pd.DataFrame()


class VnStockFetcher:
    """Lấy dữ liệu từ vnstock (fallback)"""

    def __init__(self, source: str = "VCI"):
        self.source = source
        self.vnstock = None

        try:
            from vnstock import Vnstock
            self.vnstock = Vnstock()
            print("✅ vnstock loaded (fallback)")
        except Exception as e:
            print(f"⚠️ vnstock error: {e}")

    def get_price_history(self, symbol: str) -> pd.DataFrame:
        """Lấy giá 1 mã"""
        if not self.vnstock:
            return pd.DataFrame()

        end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.source)
            df = stock.quote.history(start=DATA_START_DATE, end=end_date)

            if df is not None and len(df) > 0:
                df['symbol'] = symbol
                return df
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def get_finance_ratios(self, symbol: str) -> dict:
        """Lấy chỉ số tài chính từ vnstock"""
        if not self.vnstock:
            return {}

        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.source)
            ratios = stock.finance.ratio(period='year')
            if ratios is not None and len(ratios) > 0:
                # Lấy dòng mới nhất
                latest = ratios.iloc[-1].to_dict()
                return latest
        except Exception:
            pass
        return {}


class DataFetcher:
    """Lấy dữ liệu chứng khoán Việt Nam - VN100 + HNX30"""

    # === DANH SÁCH CỐ ĐỊNH (fallback khi không lấy được động) ===
    # VN100: 100 mã lớn nhất trên HOSE (VN30 + VNMidCap)
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

    # HNX30: 30 mã lớn nhất trên HNX
    HNX30_SYMBOLS = [
        'BAB', 'BVS', 'CEO', 'DTD', 'HUT', 'IDC', 'L14', 'MBS', 'NDN', 'NRC',
        'NTP', 'PLC', 'PVB', 'PVI', 'PVS', 'S99', 'SHN', 'SHS', 'TDC', 'THD',
        'TIG', 'TNG', 'TVS', 'VC3', 'VCS', 'VGS', 'VIX', 'VLA', 'VMC', 'VNR',
    ]

    def __init__(self):
        self.source = DATA_SOURCE
        self.fiinquant = None
        self.vnstock_fallback = None

        # Thử kết nối FiinQuant trước
        if FIINQUANT_USERNAME and FIINQUANT_PASSWORD:
            self.fiinquant = FiinQuantFetcher(FIINQUANT_USERNAME, FIINQUANT_PASSWORD)
            if not self.fiinquant.login():
                self.fiinquant = None

        # Nếu không có FiinQuant, dùng vnstock
        if self.fiinquant is None:
            print("📡 Sử dụng vnstock làm nguồn dữ liệu")
            fallback_source = "VCI" if self.source == "FIINQUANT" else self.source
            self.vnstock_fallback = VnStockFetcher(source=fallback_source)

    def get_symbols(self) -> list:
        """Lấy danh sách VN100 + HNX30 (ưu tiên dynamic, fallback cố định)"""
        print("📋 Lấy danh sách mã VN100 + HNX30...")

        # 1. Thử lấy dynamic từ vnstock
        vn100, hnx30 = get_dynamic_symbols()

        # 2. Nếu không được, thử cache
        if not vn100 and not hnx30:
            vn100, hnx30 = load_cached_symbols()

        # 3. Fallback về danh sách cố định
        if not vn100:
            vn100 = self.VN100_SYMBOLS
            print(f"   📋 VN100: {len(vn100)} mã (fallback cố định)")
        if not hnx30:
            hnx30 = self.HNX30_SYMBOLS
            print(f"   📋 HNX30: {len(hnx30)} mã (fallback cố định)")

        # Gộp và loại trùng
        all_symbols = list(dict.fromkeys(vn100 + hnx30))
        print(f"   📊 Tổng: {len(all_symbols)} mã (VN100={len(vn100)} + HNX30={len(hnx30)})")
        return all_symbols

    def fetch_with_timeout(self, symbol: str, timeout_sec: int = 15) -> pd.DataFrame:
        """Lấy data với timeout - tránh bị treo"""
        result = [pd.DataFrame()]

        def fetch():
            try:
                if self.fiinquant:
                    result[0] = self.fiinquant.get_price_history(symbol)
                elif self.vnstock_fallback:
                    result[0] = self.vnstock_fallback.get_price_history(symbol)
            except Exception:
                pass

        thread = threading.Thread(target=fetch)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout_sec)

        if thread.is_alive():
            print(f"   ⏰ {symbol}: TIMEOUT - Bỏ qua")
            return pd.DataFrame()

        return result[0]

    def fetch_all_data(self) -> pd.DataFrame:
        """Lấy dữ liệu tất cả mã VN100 + HNX30"""
        symbols = self.get_symbols()

        source_name = "FiinQuant" if self.fiinquant else "vnstock"
        print(f"\n📥 Lấy dữ liệu {len(symbols)} mã từ {source_name}...")
        print(f"⏰ Timeout: 15s/mã | Max: 25 phút\n")

        all_data = []
        ok = 0
        fail = 0
        t0 = time.time()

        for i, symbol in enumerate(symbols):
            # Safety: max 25 phút (130 mã cần nhiều thời gian hơn)
            elapsed = time.time() - t0
            if elapsed > 1500:
                print(f"\n⚠️ QUÁ 25 PHÚT - Dừng ({ok} mã)")
                break

            df = self.fetch_with_timeout(symbol, timeout_sec=15)

            if not df.empty:
                all_data.append(df)
                ok += 1
                print(f"   [{i+1}/{len(symbols)}] ✅ {symbol} ({len(df)} rows)")
            else:
                fail += 1
                print(f"   [{i+1}/{len(symbols)}] ❌ {symbol}")

                # Nếu quá nhiều lỗi với FiinQuant, chuyển sang vnstock
                if self.fiinquant and fail > 10 and ok == 0:
                    print("\n⚠️ FiinQuant lỗi quá nhiều, chuyển sang vnstock...")
                    self.fiinquant = None
                    self.vnstock_fallback = VnStockFetcher(source="VCI")
                    fail = 0

            time.sleep(0.3)

        total = time.time() - t0
        print(f"\n{'='*50}")
        print(f"📊 {ok} ✅ / {fail} ❌ / {len(symbols)} tổng")
        print(f"📡 Nguồn: {source_name}")
        print(f"⏱️ {total:.0f}s ({total/60:.1f} phút)")
        print(f"{'='*50}")

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

    def fetch_fundamental_data(self, symbols: list = None):
        """Lấy dữ liệu cơ bản (PE, PB, EPS...) và lưu file"""
        if symbols is None:
            symbols = self.get_symbols()

        print(f"\n📊 Lấy dữ liệu cơ bản cho {len(symbols)} mã...")

        fundamental_df = pd.DataFrame()

        # Thử FiinQuant trước
        if self.fiinquant:
            fundamental_df = self.fiinquant.fetch_fundamental(symbols)

        # Nếu FiinQuant không có, thử vnstock
        if fundamental_df.empty and self.vnstock_fallback:
            print("   📡 Thử lấy fundamental từ vnstock...")
            results = []
            for i, symbol in enumerate(symbols[:30]):  # Giới hạn 30 mã để không quá lâu
                try:
                    ratios = self.vnstock_fallback.get_finance_ratios(symbol)
                    if ratios:
                        ratios['symbol'] = symbol
                        results.append(ratios)
                        if (i + 1) % 10 == 0:
                            print(f"   [{i+1}/{min(30, len(symbols))}] Đã lấy {len(results)} mã")
                    time.sleep(0.5)
                except Exception:
                    continue

            if results:
                fundamental_df = pd.DataFrame(results)
                print(f"   ✅ vnstock fundamental: {len(fundamental_df)} mã")

        if not fundamental_df.empty:
            os.makedirs(DATA_DIR, exist_ok=True)
            fundamental_df.to_csv(FUNDAMENTAL_FILE, index=False)
            print(f"   ✅ Saved: {FUNDAMENTAL_FILE}")
        else:
            print("   ⚠️ Không lấy được dữ liệu cơ bản")

        return fundamental_df

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
        print("📥 BẮT ĐẦU LẤY DỮ LIỆU - VN100 + HNX30")
        source_name = "FiinQuant" if self.fiinquant else "vnstock"
        print(f"📡 Nguồn: {source_name}")
        print("=" * 60)

        df = self.fetch_all_data()

        if not df.empty:
            self.save_data(df)

            # Thử lấy thêm fundamental data
            symbols = df['symbol'].unique().tolist() if 'symbol' in df.columns else []
            if symbols:
                self.fetch_fundamental_data(symbols)

        return df


if __name__ == "__main__":
    fetcher = DataFetcher()
    df = fetcher.run()
    symbols_count = df['symbol'].nunique() if not df.empty and 'symbol' in df.columns else 0
    print(f"\nKết quả: {len(df)} rows, {symbols_count} mã")
