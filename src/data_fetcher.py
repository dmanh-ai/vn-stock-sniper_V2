"""
VN Stock Sniper - Data Fetcher V3
Sửa lỗi: timeout, danh sách cố định, log chi tiết
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import threading

from src.config import (
    DATA_START_DATE, DATA_SOURCE,
    DATA_DIR, RAW_DATA_FILE
)


class DataFetcher:
    """Lấy dữ liệu chứng khoán Việt Nam"""
    
    # Danh sách mã CỐ ĐỊNH - không gọi API lấy danh sách
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
        self.vnstock = None
        
        try:
            from vnstock import Vnstock
            self.vnstock = Vnstock()
            print("✅ vnstock loaded")
        except Exception as e:
            print(f"⚠️ vnstock error: {e}")
    
    def get_symbols(self) -> list:
        """Danh sách mã CỐ ĐỊNH"""
        symbols = self.VN30_SYMBOLS + self.EXTRA_SYMBOLS
        print(f"📋 {len(symbols)} mã (VN30 + Extra)")
        return symbols
    
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
        except:
            return pd.DataFrame()
    
    def fetch_with_timeout(self, symbol: str, timeout_sec: int = 15) -> pd.DataFrame:
        """Lấy data với timeout - tránh bị treo"""
        result = [pd.DataFrame()]
        
        def fetch():
            try:
                result[0] = self.get_price_history(symbol)
            except:
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
        
        print(f"\n📥 Lấy dữ liệu {len(symbols)} mã...")
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
            
            time.sleep(0.3)
        
        total = time.time() - t0
        print(f"\n{'='*50}")
        print(f"📊 {ok} ✅ / {fail} ❌ / {len(symbols)} tổng")
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
        print("="*60)
        
        df = self.fetch_all_data()
        
        if not df.empty:
            self.save_data(df)
        
        return df


if __name__ == "__main__":
    fetcher = DataFetcher()
    df = fetcher.run()
    print(f"\nKết quả: {len(df)} rows")
