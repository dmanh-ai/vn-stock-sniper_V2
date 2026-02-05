"""
VN Stock Sniper - Telegram Bot
Gửi báo cáo và nhận lệnh quản lý portfolio
"""

import asyncio
import json
import os
from datetime import datetime

try:
    from telegram import Update, Bot
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ python-telegram-bot chưa được cài đặt")

from src.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PORTFOLIO_FILE, DATA_DIR


class TelegramBot:
    """Bot Telegram để gửi báo cáo và quản lý portfolio"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.portfolio_file = PORTFOLIO_FILE
        
        # Tạo thư mục data nếu chưa có
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Khởi tạo portfolio nếu chưa có
        if not os.path.exists(self.portfolio_file):
            self.save_portfolio({"positions": [], "cash_percent": 100})
    
    def load_portfolio(self) -> dict:
        """Đọc portfolio"""
        if os.path.exists(self.portfolio_file):
            with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"positions": [], "cash_percent": 100}
    
    def save_portfolio(self, portfolio: dict):
        """Lưu portfolio"""
        with open(self.portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, indent=2, ensure_ascii=False)
    
    async def send_message(self, text: str, parse_mode: str = None):
        """Gửi tin nhắn đến Telegram"""
        if not self.token or not self.chat_id:
            print("⚠️ Telegram chưa được cấu hình")
            return False
        
        try:
            bot = Bot(token=self.token)
            
            # Chia nhỏ tin nhắn nếu quá dài (Telegram giới hạn 4096 ký tự)
            max_length = 4000
            
            if len(text) <= max_length:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
            else:
                # Chia thành nhiều phần
                parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                for i, part in enumerate(parts):
                    if i > 0:
                        part = f"(tiếp theo...)\n\n{part}"
                    await bot.send_message(
                        chat_id=self.chat_id,
                        text=part,
                        parse_mode=parse_mode
                    )
                    await asyncio.sleep(0.5)
            
            print("✅ Đã gửi Telegram thành công")
            return True
            
        except Exception as e:
            print(f"❌ Lỗi gửi Telegram: {e}")
            return False
    
    def send_message_sync(self, text: str, parse_mode: str = None):
        """Gửi tin nhắn (đồng bộ)"""
        return asyncio.run(self.send_message(text, parse_mode))
    
    def send_report(self, report: str):
        """Gửi báo cáo"""
        today = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        header = f"""
════════════════════════════════
📊 VN STOCK SNIPER + AI
📅 {today}
════════════════════════════════

"""
        full_message = header + report
        return self.send_message_sync(full_message)
    
    # === COMMAND HANDLERS (cho bot chạy liên tục) ===
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /start"""
        welcome = """
🤖 VN Stock Sniper Bot

Các lệnh có thể dùng:

📊 Xem thông tin:
/portfolio - Xem danh mục hiện tại
/help - Xem hướng dẫn

💰 Quản lý danh mục:
/buy <mã> <số lượng> <giá>
/sell <mã> <số lượng>
/cash <phần trăm>

Ví dụ:
/buy VCI 1000 37000
/sell MWG 500
/cash 30
"""
        await update.message.reply_text(welcome)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /help"""
        help_text = """
📚 HƯỚNG DẪN SỬ DỤNG

1️⃣ MUA CỔ PHIẾU:
/buy <mã> <số CP> <giá mua>
Ví dụ: /buy VCI 1000 37000

2️⃣ BÁN CỔ PHIẾU:
/sell <mã> <số CP>
Ví dụ: /sell MWG 500
(Bán hết: /sell MWG all)

3️⃣ CẬP NHẬT TIỀN MẶT:
/cash <phần trăm>
Ví dụ: /cash 30 (30% tiền mặt)

4️⃣ XEM DANH MỤC:
/portfolio

5️⃣ XÓA TOÀN BỘ:
/clear

Bot sẽ tự động gửi báo cáo mỗi sáng lúc 7:30 AM.
"""
        await update.message.reply_text(help_text)
    
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /portfolio - xem danh mục"""
        portfolio = self.load_portfolio()
        positions = portfolio.get('positions', [])
        cash = portfolio.get('cash_percent', 100)
        
        if not positions:
            msg = f"""
💼 DANH MỤC HIỆN TẠI

💵 Tiền mặt: {cash}%
📊 Cổ phiếu: Chưa có vị thế nào

Dùng /buy <mã> <số CP> <giá> để thêm.
"""
        else:
            msg = f"""
💼 DANH MỤC HIỆN TẠI

💵 Tiền mặt: {cash}%

📊 CÁC VỊ THẾ:
"""
            for pos in positions:
                msg += f"""
• {pos['symbol']}
  Số CP: {pos['quantity']:,}
  Giá mua: {pos['entry_price']:,}
  Ngày: {pos.get('entry_date', 'N/A')}
"""
        
        await update.message.reply_text(msg)
    
    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /buy - mua cổ phiếu"""
        try:
            args = context.args
            if len(args) < 3:
                await update.message.reply_text("❌ Sai cú pháp!\nDùng: /buy <mã> <số CP> <giá>\nVí dụ: /buy VCI 1000 37000")
                return
            
            symbol = args[0].upper()
            quantity = int(args[1])
            price = float(args[2])
            
            portfolio = self.load_portfolio()
            positions = portfolio.get('positions', [])
            
            # Kiểm tra đã có vị thế chưa
            existing = None
            for i, pos in enumerate(positions):
                if pos['symbol'] == symbol:
                    existing = i
                    break
            
            today = datetime.now().strftime("%d/%m/%Y")
            
            if existing is not None:
                # Cập nhật vị thế (tính giá trung bình)
                old_qty = positions[existing]['quantity']
                old_price = positions[existing]['entry_price']
                
                new_qty = old_qty + quantity
                new_price = (old_qty * old_price + quantity * price) / new_qty
                
                positions[existing]['quantity'] = new_qty
                positions[existing]['entry_price'] = round(new_price, 0)
                positions[existing]['last_update'] = today
                
                msg = f"""
✅ ĐÃ CẬP NHẬT VỊ THẾ

📈 {symbol}
Số CP cũ: {old_qty:,}
Mua thêm: {quantity:,} @ {price:,}
Tổng: {new_qty:,} CP
Giá TB: {new_price:,.0f}
"""
            else:
                # Thêm vị thế mới
                new_position = {
                    "symbol": symbol,
                    "quantity": quantity,
                    "entry_price": price,
                    "entry_date": today,
                    "last_update": today
                }
                positions.append(new_position)
                
                msg = f"""
✅ ĐÃ THÊM VỊ THẾ MỚI

📈 {symbol}
Số CP: {quantity:,}
Giá mua: {price:,}
Ngày: {today}
"""
            
            portfolio['positions'] = positions
            self.save_portfolio(portfolio)
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}\nDùng: /buy <mã> <số CP> <giá>")
    
    async def cmd_sell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /sell - bán cổ phiếu"""
        try:
            args = context.args
            if len(args) < 2:
                await update.message.reply_text("❌ Sai cú pháp!\nDùng: /sell <mã> <số CP>\nVí dụ: /sell MWG 500\nBán hết: /sell MWG all")
                return
            
            symbol = args[0].upper()
            sell_qty = args[1].lower()
            
            portfolio = self.load_portfolio()
            positions = portfolio.get('positions', [])
            
            # Tìm vị thế
            pos_index = None
            for i, pos in enumerate(positions):
                if pos['symbol'] == symbol:
                    pos_index = i
                    break
            
            if pos_index is None:
                await update.message.reply_text(f"❌ Không tìm thấy vị thế {symbol}")
                return
            
            current_qty = positions[pos_index]['quantity']
            
            if sell_qty == 'all':
                sell_qty = current_qty
            else:
                sell_qty = int(sell_qty)
            
            if sell_qty > current_qty:
                await update.message.reply_text(f"❌ Không đủ CP! Hiện có: {current_qty:,}")
                return
            
            if sell_qty == current_qty:
                # Xóa vị thế
                removed = positions.pop(pos_index)
                msg = f"""
✅ ĐÃ ĐÓNG VỊ THẾ

📉 {symbol}
Đã bán: {sell_qty:,} CP
Giá vốn: {removed['entry_price']:,}
"""
            else:
                # Giảm vị thế
                positions[pos_index]['quantity'] = current_qty - sell_qty
                positions[pos_index]['last_update'] = datetime.now().strftime("%d/%m/%Y")
                
                msg = f"""
✅ ĐÃ BÁN MỘT PHẦN

📉 {symbol}
Đã bán: {sell_qty:,} CP
Còn lại: {current_qty - sell_qty:,} CP
"""
            
            portfolio['positions'] = positions
            self.save_portfolio(portfolio)
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}")
    
    async def cmd_cash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /cash - cập nhật % tiền mặt"""
        try:
            args = context.args
            if len(args) < 1:
                await update.message.reply_text("❌ Sai cú pháp!\nDùng: /cash <phần trăm>\nVí dụ: /cash 30")
                return
            
            cash_percent = float(args[0])
            
            if cash_percent < 0 or cash_percent > 100:
                await update.message.reply_text("❌ Phần trăm phải từ 0-100!")
                return
            
            portfolio = self.load_portfolio()
            portfolio['cash_percent'] = cash_percent
            self.save_portfolio(portfolio)
            
            await update.message.reply_text(f"✅ Đã cập nhật tiền mặt: {cash_percent}%")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi: {e}")
    
    async def cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Lệnh /clear - xóa toàn bộ portfolio"""
        self.save_portfolio({"positions": [], "cash_percent": 100})
        await update.message.reply_text("✅ Đã xóa toàn bộ danh mục!")
    
    def run_bot(self):
        """Chạy bot (chế độ lắng nghe lệnh)"""
        if not TELEGRAM_AVAILABLE:
            print("❌ python-telegram-bot chưa được cài đặt")
            return
        
        if not self.token:
            print("❌ TELEGRAM_TOKEN chưa được cấu hình")
            return
        
        print("🤖 Đang khởi động Telegram Bot...")
        
        app = Application.builder().token(self.token).build()
        
        # Thêm handlers
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
        app.add_handler(CommandHandler("buy", self.cmd_buy))
        app.add_handler(CommandHandler("sell", self.cmd_sell))
        app.add_handler(CommandHandler("cash", self.cmd_cash))
        app.add_handler(CommandHandler("clear", self.cmd_clear))
        
        print("✅ Bot đã sẵn sàng!")
        
        # Chạy bot
        app.run_polling(allowed_updates=Update.ALL_TYPES)


# Test
if __name__ == "__main__":
    bot = TelegramBot()
    
    # Test gửi tin nhắn
    bot.send_message_sync("🤖 Test VN Stock Sniper Bot!")
