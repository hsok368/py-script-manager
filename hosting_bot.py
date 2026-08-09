import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import subprocess
import sys
import ast

# သင့် Hosting Bot Token ကို ဤနေရာတွင် ထည့်ပါ
TOKEN = '8940684766:AAFO4v8oXiCaO-cRLujCOYpKv8kCp2A3v4s'
bot = telebot.TeleBot(TOKEN)

user_processes = {}
BASE_DIR = "hosted_bots"

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

def get_user_dir(user_id):
    user_dir = os.path.join(BASE_DIR, str(user_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

# ════════════════════════════════════════════════
#       အလိုအလျောက် Library သွင်းပေးသော စနစ် (Auto-Installer)
# ════════════════════════════════════════════════
def auto_install_deps(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        # Import နာမည်နှင့် Install လုပ်ရမည့် Package နာမည် မတူညီမှုများကို ချိတ်ဆက်ခြင်း
        mapping = {
            'telegram': 'python-telegram-bot',
            'telebot': 'pyTelegramBotAPI',
            'bs4': 'beautifulsoup4',
            'PIL': 'Pillow',
            'cv2': 'opencv-python'
        }
        
        # Python တွင် မူလတည်းက ပါဝင်သော Library များကို ဖယ်ထုတ်ခြင်း
        stdlib = sys.stdlib_module_names if hasattr(sys, 'stdlib_module_names') else {'os', 'sys', 'time', 'asyncio', 'json', 'math', 're', 'random', 'datetime'}
        
        to_install = []
        for lib in imports:
            if lib not in stdlib:
                to_install.append(mapping.get(lib, lib))
        
        if to_install:
            # လိုအပ်သော Library များကို Install လုပ်ခြင်း
            subprocess.run([sys.executable, '-m', 'pip', 'install', *to_install], capture_output=True)
            return to_install
            
    except Exception as e:
        print(f"Auto-install error: {e}")
    return []

# ════════════════════════════════════════════════

def main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("▶️ Start (Auto-Install)", callback_data="start_bot"),
        InlineKeyboardButton("⏹ Stop Bot", callback_data="stop_bot")
    )
    markup.add(
        InlineKeyboardButton("📜 View Logs/Errors", callback_data="view_logs"),
        InlineKeyboardButton("🗑 Delete File", callback_data="delete_file")
    )
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 **Hosting Bot မှ ကြိုဆိုပါတယ်!**\n\n"
        "သင့်ရဲ့ Python code (`.py` file) ကိုသာ ဒီကို ပို့ပေးပါ။\n"
        "လိုအပ်တဲ့ Libraries များကို Bot မှ အလိုအလျောက် ရှာဖွေသွင်းယူပေးပါမည်။"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        user_id = message.from_user.id
        user_dir = get_user_dir(user_id)
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = message.document.file_name
        
        if file_name.endswith('.py'):
            file_path = os.path.join(user_dir, file_name)
            with open(file_path, 'wb') as new_file:
                new_file.write(downloaded_file)
                
            bot.reply_to(message, f"✅ `{file_name}` ဖိုင်ကို လက်ခံရရှိပါပြီ။\nStart နှိပ်ပါက လိုအပ်သည်များကို အလိုအလျောက် သွင်းပေးပါမည်။", 
                         reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ ကျေးဇူးပြု၍ `.py` ဖိုင်ကိုသာ ပို့ပေးပါ။")
            
    except Exception as e:
        bot.reply_to(message, f"❌ အမှားအယွင်းဖြစ်နေပါသည်: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    user_dir = get_user_dir(user_id)
    bot_file = None
    
    if os.path.exists(user_dir):
        for file in os.listdir(user_dir):
            if file.endswith('.py'):
                bot_file = os.path.join(user_dir, file)
                break
            
    log_file = os.path.join(user_dir, "output.log")

    if call.data == "start_bot":
        if bot_file:
            if user_id in user_processes and user_processes[user_id].poll() is None:
                bot.answer_callback_query(call.id, "⚠️ သင့် Bot မှာ လည်ပတ်နေဆဲ ဖြစ်ပါတယ်။", show_alert=True)
            else:
                try:
                    bot.answer_callback_query(call.id, "⏳ လိုအပ်သည်များကို စစ်ဆေး/Install လုပ်နေပါသည်...")
                    bot.send_message(user_id, "⏳ Code ကိုစစ်ဆေးပြီး လိုအပ်သော Libraries များရှိပါက အလိုအလျောက် Install လုပ်နေပါသည်။ ခဏစောင့်ပါ...")
                    
                    # အလိုအလျောက် Install လုပ်မည့် Function ကို ခေါ်ခြင်း
                    installed_libs = auto_install_deps(bot_file)
                    if installed_libs:
                        bot.send_message(user_id, f"📦 **Auto-Installed:** {', '.join(installed_libs)}")
                    
                    # Bot ကို စတင် Run ခြင်း
                    f = open(log_file, "w")
                    process = subprocess.Popen([sys.executable, bot_file], stdout=f, stderr=subprocess.STDOUT)
                    user_processes[user_id] = process
                    bot.send_message(user_id, "✅ သင့် Bot ကို အောင်မြင်စွာ စတင် Run လိုက်ပါပြီ။")
                except Exception as e:
                    bot.send_message(user_id, f"❌ Run ရာတွင် အမှားအယွင်းဖြစ်နေပါသည်: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ Run ရန် .py ဖိုင် မတွေ့ပါ။", show_alert=True)

    elif call.data == "stop_bot":
        if user_id in user_processes and user_processes[user_id].poll() is None:
            user_processes[user_id].terminate() 
            bot.answer_callback_query(call.id, "⏹ Bot ကို ရပ်တန့်လိုက်ပါပြီ။")
            bot.send_message(user_id, "⏹ သင့် Bot ကို ရပ်တန့်လိုက်ပါပြီ။")
        else:
            bot.answer_callback_query(call.id, "⚠️ ရပ်တန့်ရန် Bot လည်ပတ်နေခြင်း မရှိပါ။", show_alert=True)

    elif call.data == "view_logs":
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = f.read()
                if logs:
                    bot.send_message(user_id, f"📜 **Logs / Errors:**\n```python\n{logs[-3500:]}\n```", parse_mode="Markdown")
                else:
                    bot.answer_callback_query(call.id, "Logs များ မရှိသေးပါ။", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Logs ဖိုင် မတွေ့ပါ။", show_alert=True)

    elif call.data == "delete_file":
        if user_id in user_processes and user_processes[user_id].poll() is None:
            user_processes[user_id].terminate()
            
        if os.path.exists(user_dir):
            for file in os.listdir(user_dir):
                os.remove(os.path.join(user_dir, file))
            
        bot.answer_callback_query(call.id, "🗑 ဖိုင်များကို ဖျက်လိုက်ပါပြီ။")
        bot.send_message(user_id, "🗑 သင့်ဖိုင်များကို အောင်မြင်စွာ ဖျက်ပစ်လိုက်ပါပြီ။")

if __name__ == "__main__":
    print("Hosting Bot with Auto-Installer is running...")
    bot.infinity_polling()
