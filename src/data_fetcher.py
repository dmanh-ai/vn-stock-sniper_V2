"""
VN Stock Sniper - Data Fetcher (Fixed)
Lấy dữ liệu giá cổ phiếu từ vnstock - ĐÃ SỬA LỖI API
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os

try:
    from vnstock import Vnstock
    VNSTOCK_AVAILABLE = True
except ImportError:
    VNSTOCK_AVAILABLE = False
    print("⚠️ vnstock chưa được cài đặt")

from src.config import (
    TOP_STOCKS_COUNT, DATA_START_DATE, DATA_SOURCE,
    DATA_DIR, RAW_DATA_FILE
)


class DataFetcher:
    """Lấy dữ liệu chứng khoán Việt Nam"""
    
    def __init__(self):
        self.source = DATA_SOURCE
        if VNSTOCK_AVAILABLE:
            self.vnstock = Vnstock()
        else:
            self.vnstock = None
        
    def get_all_symbols(self) -> list:
        """Lấy danh sách tất cả mã cổ phiếu"""
        if not self.vnstock:
            return []
        
        try:
            # Cách mới để lấy danh sách symbols
            stock = self.vnstock.stock(symbol='VN30F1M', source=self.source)
            
            # Thử nhiều cách khác nhau
            try:
                # Cách 1: listing.all_symbols()
                symbols_df = stock.listing.all_symbols()
                if symbols_df is not None and len(symbols_df) > 0:
                    if 'symbol' in symbols_df.columns:
                        symbols = symbols_df['symbol'].dropna().tolist()
                    elif 'ticker' in symbols_df.columns:
                        symbols = symbols_df['ticker'].dropna().tolist()
                    else:
                        symbols = symbols_df.iloc[:, 0].dropna().tolist()
                    
                    # Lọc chỉ lấy mã hợp lệ (3 ký tự)
                    symbols = [s for s in symbols if s and isinstance(s, str) and len(s) == 3]
                    print(f"✅ Lấy được {len(symbols)} mã cổ phiếu (cách 1)")
                    return symbols
            except Exception as e1:
                print(f"⚠️ Cách 1 thất bại: {e1}")
            
            try:
                # Cách 2: Dùng danh sách mã cố định
                default_symbols = [
                    # VN30
                    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
                    'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
                    'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE',
                    # Thêm các mã phổ biến khác
                    'VCI', 'DGW', 'PNJ', 'REE', 'GMD', 'VND', 'HCM', 'DCM', 'DPM', 'PVD',
                    'PVS', 'BSR', 'ORS', 'EVF', 'TCH', 'KDH', 'NVL', 'PDR', 'DXG', 'HDG',
                    'HAG', 'HNG', 'DIG', 'IJC', 'KBC', 'VGC', 'GEX', 'HSG', 'NKG', 'TLG',
                    'FRT', 'VHC', 'ANV', 'IDI', 'ASM', 'DBC', 'HAH', 'VTP', 'ACV', 'HVN',
                    'VEA', 'PAN', 'KDC', 'VSH', 'PC1', 'PHR', 'GIL', 'TNG', 'MSH', 'TCM',
                    'SCS', 'VCG', 'CTD', 'HBC', 'FCN', 'LCG', 'C4G', 'VOS', 'HHS', 'CEO'
                ]
                print(f"✅ Sử dụng danh sách mã mặc định: {len(default_symbols)} mã")
                return default_symbols
            except Exception as e2:
                print(f"⚠️ Cách 2 thất bại: {e2}")
            
            return []
            
        except Exception as e:
            print(f"❌ Lỗi lấy danh sách mã: {e}")
            # Fallback: trả về danh sách mã mặc định
            return self._get_default_symbols()
    
    def _get_default_symbols(self) -> list:
        """Danh sách mã mặc định khi không lấy được từ API"""
        return [
            # VN30
            'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
            'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
            'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE',
            # Thêm các mã phổ biến
            'VCI', 'DGW', 'PNJ', 'REE', 'GMD', 'VND', 'HCM', 'DCM', 'DPM', 'PVD',
            'PVS', 'BSR', 'ORS', 'EVF', 'TCH', 'KDH', 'NVL', 'PDR', 'DXG', 'HDG'
        ]
    
    def get_price_history(self, symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Lấy lịch sử giá 1 mã"""
        if not self.vnstock:
            return pd.DataFrame()
        
        if start_date is None:
            start_date = DATA_START_DATE
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.source)
            df = stock.quote.history(start=start_date, end=end_date)
            
            if df is not None and len(df) > 0:
                df['symbol'] = symbol
                return df
            return pd.DataFrame()
            
        except Exception as e:
            # Không in lỗi chi tiết để tránh spam log
            return pd.DataFrame()
    
    def fetch_all_data(self, symbols: list = None) -> pd.DataFrame:
        """Lấy dữ liệu tất cả các mã"""
        if symbols is None:
            symbols = self.get_all_symbols()
        
        if not symbols:
            print("❌ Không có mã nào để lấy dữ liệu")
            return pd.DataFrame()
        
        print(f"\n📥 Đang lấy dữ liệu {len(symbols)} mã...")
        
        all_data = []
        success_count = 0
        
        for i, symbol in enumerate(symbols):
            try:
                df = self.get_price_history(symbol)
                
                if not df.empty:
                    all_data.append(df)
                    success_count += 1
                
                # Progress
                if (i + 1) % 10 == 0:
                    progress = (i + 1) / len(symbols) * 100
                    print(f"   [{i+1}/{len(symbols)}] {progress:.1f}% - Đã lấy {success_count} mã")
                
                time.sleep(0.3)  # Tránh bị block
                
            except Exception as e:
                continue
        
        print(f"\n✅ Lấy xong {success_count}/{len(symbols)} mã")
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            return combined
        
        return pd.DataFrame()
    
    def save_data(self, df: pd.DataFrame, filepath: str = None):
        """Lưu dữ liệu ra file"""
        if filepath is None:
            filepath = RAW_DATA_FILE
            
        if df.empty:
            print("❌ Không có dữ liệu để lưu")
            return
        
        # Tạo thư mục nếu chưa có
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        
        # Lưu CSV
        df.to_csv(filepath, index=False)
        print(f"✅ Đã lưu: {filepath} ({len(df)} dòng)")
    
    def load_data(self, filepath: str = None) -> pd.DataFrame:
        """Đọc dữ liệu từ file"""
        if filepath is None:
            filepath = RAW_DATA_FILE
            
        if not os.path.exists(filepath):
            print(f"❌ File không tồn tại: {filepath}")
            return pd.DataFrame()
        
        df = pd.read_csv(filepath)
        print(f"✅ Đã đọc: {filepath} ({len(df)} dòng)")
        return df
    
    def run(self) -> pd.DataFrame:
        """Chạy lấy dữ liệu và lưu file"""
        print("="*60)
        print("📥 BẮT ĐẦU LẤY DỮ LIỆU")
        print("="*60)
        
        # Lấy danh sách mã
        symbols = self.get_all_symbols()
        
        if not symbols:
            print("❌ Không lấy được danh sách mã, sử dụng danh sách mặc định")
            symbols = self._get_default_symbols()
        
        # Lấy dữ liệu
        df = self.fetch_all_data(symbols)
        
        # Lưu file
        if not df.empty:
            self.save_data(df)
        
        return df


# Test
if __name__ == "__main__":
    fetcher = DataFetcher()
    df = fetcher.run()
    print(f"\nKết quả: {len(df)} dòng dữ liệu")
