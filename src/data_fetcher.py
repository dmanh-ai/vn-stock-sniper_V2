"""
VN Stock Sniper - Data Fetcher V4
Primary: FiinQuantX (fiinquant.vn)
Fallback: vnstock
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import threading

from src.config import (
    DATA_START_DATE, DATA_SOURCE,
    DATA_DIR, RAW_DATA_FILE,
    FIINQUANT_USERNAME, FIINQUANT_PASSWORD
)


class FiinQuantFetcher:
    """Lấy dữ liệu từ FiinQuantX"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.client = None

    def login(self) -> bool:
        """Đăng nhập FiinQuant"""
        try:
            from FiinQuantX import FiinSession
            self.client = FiinSession(
                username=self.username,
                password=self.password
            ).login()
            print("✅ FiinQuant: Đăng nhập thành công")
            return True
        except ImportError:
            print("❌ FiinQuantX chưa cài đặt. Cài bằng:")
            print("   pip install --extra-index-url https://fiinquant.github.io/fiinquantx/simple fiinquantx")
            return False
        except Exception as e:
            print(f"❌ FiinQuant: Lỗi đăng nhập - {e}")
            return False

    def get_symbols(self) -> list:
        """Lấy danh sách mã từ FiinQuant hoặc dùng danh sách cố định"""
        # Dùng danh sách cố định VN30 + Extra
        return DataFetcher.VN30_SYMBOLS + DataFetcher.EXTRA_SYMBOLS

    def get_price_history(self, symbol: str, period: int = 500) -> pd.DataFrame:
        """Lấy lịch sử giá 1 mã từ FiinQuant"""
        if not self.client:
            return pd.DataFrame()

        try:
            data = self.client.Fetch_Trading_Data(
                tickers=symbol,
                fields=['open', 'high', 'low', 'close', 'volume'],
                adjusted=True,
                period=period,
                realtime=False,
                by='1d',
            ).get_data()

            if data is not None and len(data) > 0:
                df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)

                # Chuẩn hóa columns
                col_map = {}
                for col in df.columns:
                    cl = col.lower().strip()
                    if 'time' in cl or 'date' in cl:
                        col_map[col] = 'time'
                    elif cl in ['open', 'high', 'low', 'close', 'volume']:
                        col_map[col] = cl

                if col_map:
                    df = df.rename(columns=col_map)

                # Đảm bảo có column time
                if 'time' not in df.columns:
                    # Nếu index là datetime
                    if isinstance(df.index, pd.DatetimeIndex):
                        df['time'] = df.index
                        df = df.reset_index(drop=True)
                    else:
                        # Thử tìm column datetime
                        for col in df.columns:
                            try:
                                df['time'] = pd.to_datetime(df[col])
                                break
                            except (ValueError, TypeError):
                                continue

                df['symbol'] = symbol

                # Đảm bảo có đủ columns cần thiết
                required = ['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']
                if all(c in df.columns for c in required):
                    return df[required]

                print(f"   ⚠️ {symbol}: Thiếu columns. Có: {list(df.columns)}")
                return pd.DataFrame()

            return pd.DataFrame()

        except Exception as e:
            print(f"   ❌ FiinQuant {symbol}: {e}")
            return pd.DataFrame()

    def fetch_batch(self, symbols: list, period: int = 500) -> pd.DataFrame:
        """Lấy dữ liệu nhiều mã cùng lúc"""
        # Thử gửi nhiều mã 1 lần (FiinQuant hỗ trợ)
        if not self.client:
            return pd.DataFrame()

        try:
            tickers_str = ','.join(symbols) if len(symbols) <= 10 else None

            if tickers_str:
                data = self.client.Fetch_Trading_Data(
                    tickers=tickers_str,
                    fields=['open', 'high', 'low', 'close', 'volume'],
                    adjusted=True,
                    period=period,
                    realtime=False,
                    by='1d',
                ).get_data()

                if data is not None and len(data) > 0:
                    df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
                    return df

        except Exception:
            pass

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


class DataFetcher:
    """Lấy dữ liệu chứng khoán Việt Nam - Hỗ trợ FiinQuant + vnstock"""

    # Danh sách mã CỐ ĐỊNH
    VN30_SYMBOLS = [
        'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
        'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
        'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE',
    ]

    EXTRA_SYMBOLS = [
        'VCI', 'DGW', 'PNJ', 'REE', 'GMD', 'VND', 'HCM', 'DCM', 'DPM', 'PVD',
        'PVS', 'BSR', 'TCH', 'KDH', 'NVL', 'DXG', 'HDG', 'DIG', 'KBC', 'GEX',
        'HSG', 'NKG', 'FRT', 'VHC', 'ANV', 'ASM', 'HAH', 'VTP', 'PAN', 'KDC',
        'PC1', 'TNG', 'SCS', 'VCG', 'CTD', 'FCN', 'PHR', 'MSH', 'IDI', 'DBC',
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

        # Nếu không có FiinQuant hoặc source khác, dùng vnstock
        if self.fiinquant is None:
            print("📡 Sử dụng vnstock làm nguồn dữ liệu")
            fallback_source = "VCI" if self.source == "FIINQUANT" else self.source
            self.vnstock_fallback = VnStockFetcher(source=fallback_source)

    def get_symbols(self) -> list:
        """Danh sách mã CỐ ĐỊNH"""
        symbols = self.VN30_SYMBOLS + self.EXTRA_SYMBOLS
        print(f"📋 {len(symbols)} mã (VN30 + Extra)")
        return symbols

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
        """Lấy dữ liệu tất cả mã"""
        symbols = self.get_symbols()

        source_name = "FiinQuant" if self.fiinquant else "vnstock"
        print(f"\n📥 Lấy dữ liệu {len(symbols)} mã từ {source_name}...")
        print(f"⏰ Timeout: 15s/mã | Max: 20 phút\n")

        all_data = []
        ok = 0
        fail = 0
        t0 = time.time()

        for i, symbol in enumerate(symbols):
            # Safety: max 20 phút
            elapsed = time.time() - t0
            if elapsed > 1200:
                print(f"\n⚠️ QUÁ 20 PHÚT - Dừng ({ok} mã)")
                break

            df = self.fetch_with_timeout(symbol, timeout_sec=15)

            if not df.empty:
                all_data.append(df)
                ok += 1
                print(f"   [{i+1}/{len(symbols)}] ✅ {symbol} ({len(df)} rows)")
            else:
                fail += 1
                print(f"   [{i+1}/{len(symbols)}] ❌ {symbol}")

                # Nếu FiinQuant thất bại, thử vnstock cho mã này
                if self.fiinquant and self.vnstock_fallback is None:
                    pass  # Không fallback nếu chưa init vnstock
                elif self.fiinquant and fail <= 5:
                    pass  # Cho phép vài lỗi trước khi switch

                # Nếu quá nhiều lỗi với FiinQuant, chuyển sang vnstock
                if self.fiinquant and fail > 10 and ok == 0:
                    print("\n⚠️ FiinQuant lỗi quá nhiều, chuyển sang vnstock...")
                    self.fiinquant = None
                    self.vnstock_fallback = VnStockFetcher(source="VCI")
                    # Reset counters
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

    def save_data(self, df: pd.DataFrame):
        """Lưu file"""
        if df.empty:
            print("❌ Không có data")
            return

        os.makedirs(DATA_DIR, exist_ok=True)
        df.to_csv(RAW_DATA_FILE, index=False)
        print(f"✅ Saved: {RAW_DATA_FILE} ({len(df)} rows)")

    def run(self) -> pd.DataFrame:
        """Chạy lấy dữ liệu"""
        print("="*60)
        print("📥 BẮT ĐẦU LẤY DỮ LIỆU")
        source_name = "FiinQuant" if self.fiinquant else "vnstock"
        print(f"📡 Nguồn: {source_name}")
        print("="*60)

        df = self.fetch_all_data()

        if not df.empty:
            self.save_data(df)

        return df


if __name__ == "__main__":
    fetcher = DataFetcher()
    df = fetcher.run()
    print(f"\nKết quả: {len(df)} rows")
