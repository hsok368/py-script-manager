import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import subprocess
import signal

# သင့် Bot Token ကို ဤနေရာတွင် ထည့်ပါ
TOKEN = '8940684766:AAFO4v8oXiCaO-cRLujCOYpKv8kCp2A3v4s'
bot = telebot.TeleBot(TOKEN)

# User တွေရဲ့ လည်ပတ်နေတဲ့ Process တွေကို သိမ်းထားမယ့် နေရာ (Dictionary)
user_processes = {}
# User တွေရဲ့ ဖိုင်တွေ သိမ်းဖို့ အဓိက Folder
BASE_DIR = "hosted_bots"

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# User အလိုက် Folder တည်ဆောက်ပေးတဲ့ Function
def get_user_dir(user_id):
    user_dir = os.path.join(BASE_DIR, str(user_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

# ခလုတ်များ (Inline Keyboard) ဖန်တီးပေးတဲ့ Function
def main_menu_keyboard():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("▶️ Start Bot", callback_data="start_bot"),
        InlineKeyboardButton("⏹ Stop Bot", callback_data="stop_bot")
    )
    markup.add(
        InlineKeyboardButton("📜 View Logs/Errors", callback_data="view_logs"),
        InlineKeyboardButton("🗑 Delete File", callback_data="delete_file")
    )
    markup.add(
        InlineKeyboardButton("📦 Install Requirements", callback_data="install_req")
    )
    return markup

# /start ကို နှိပ်တဲ့အခါ
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 **Hosting Bot မှ ကြိုဆိုပါတယ်!**\n\n"
        "1️⃣ သင့်ရဲ့ Python code (`.py` file) ကို ဒီကို ပို့ပေးပါ။\n"
        "2️⃣ လိုအပ်တဲ့ libraries တွေရှိရင် `requirements.txt` ကိုပါ ပို့ပေးပါ။\n\n"
        "အောက်ပါခလုတ်များဖြင့် သင့် Bot ကို အလွယ်တကူ ထိန်းချုပ်နိုင်ပါတယ်။"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

# ဖိုင်များ (Documents) လက်ခံတဲ့အခါ
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        user_id = message.from_user.id
        user_dir = get_user_dir(user_id)
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = message.document.file_name
        
        if file_name.endswith('.py') or file_name == 'requirements.txt':
            file_path = os.path.join(user_dir, file_name)
            
            with open(file_path, 'wb') as new_file:
                new_file.write(downloaded_file)
                
            bot.reply_to(message, f"✅ `{file_name}` ဖိုင်ကို အောင်မြင်စွာ သိမ်းဆည်းပြီးပါပြီ။\nအောက်ပါခလုတ်များဖြင့် ထိန်းချုပ်ပါ။", 
                         reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ ကျေးဇူးပြု၍ `.py` ဖိုင် သို့မဟုတ် `requirements.txt` ကိုသာ ပို့ပေးပါ။")
            
    except Exception as e:
        bot.reply_to(message, f"❌ ဖိုင်သိမ်းဆည်းရာတွင် အမှားအယွင်းဖြစ်နေပါသည်: {e}")

# ခလုတ်တွေကို နှိပ်တဲ့အခါ အလုပ်လုပ်မယ့် အပိုင်း (Callback Queries)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    user_dir = get_user_dir(user_id)
    bot_file = None
    
    # ယူဆချက်အနေနဲ့ အရင်ဆုံးရောက်လာတဲ့ .py ကို အဓိက Run မယ့်ဖိုင်လို့ သတ်မှတ်ပါမယ်
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
                    # Logs နဲ့ Error တွေကို log file ထဲ သိမ်းမယ်
                    f = open(log_file, "w")
                    process = subprocess.Popen(['python3', bot_file], stdout=f, stderr=subprocess.STDOUT)
                    user_processes[user_id] = process
                    bot.answer_callback_query(call.id, "▶️ Bot ကို စတင်လိုက်ပါပြီ။")
                    bot.send_message(user_id, "✅ သင့် Bot ကို အောင်မြင်စွာ Run လိုက်ပါပြီ။ Logs များကို စစ်ဆေးနိုင်ပါတယ်။")
                except Exception as e:
                    bot.send_message(user_id, f"❌ Run ရာတွင် အမှားအယွင်းဖြစ်နေပါသည်: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ Run ရန် .py ဖိုင် မတွေ့ပါ။", show_alert=True)

    elif call.data == "stop_bot":
        if user_id in user_processes and user_processes[user_id].poll() is None:
            user_processes[user_id].terminate() # သို့မဟုတ် .kill()
            bot.answer_callback_query(call.id, "⏹ Bot ကို ရပ်တန့်လိုက်ပါပြီ။")
            bot.send_message(user_id, "⏹ သင့် Bot ကို ရပ်တန့်လိုက်ပါပြီ။")
        else:
            bot.answer_callback_query(call.id, "⚠️ ရပ်တန့်ရန် Bot လည်ပတ်နေခြင်း မရှိပါ။", show_alert=True)

    elif call.data == "view_logs":
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = f.read()
                if logs:
                    # Message အရမ်းရှည်ရင် နောက်ဆုံး စာလုံးရေ 4000 ကိုပဲ ပြမယ်
                    bot.send_message(user_id, f"📜 **Logs / Errors:**\n```python\n{logs[-4000:]}\n```", parse_mode="Markdown")
                else:
                    bot.answer_callback_query(call.id, "Logs များ မရှိသေးပါ။", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "Logs ဖိုင် မတွေ့ပါ။", show_alert=True)

    elif call.data == "delete_file":
        # အရင်ဆုံး Process ကို ရပ်ပါမယ်
        if user_id in user_processes and user_processes[user_id].poll() is None:
            user_processes[user_id].terminate()
            
        # ဖိုင်တွေအကုန်ဖျက်ပါမယ်
        if os.path.exists(user_dir):
            for file in os.listdir(user_dir):
                os.remove(os.path.join(user_dir, file))
            
        bot.answer_callback_query(call.id, "🗑 ဖိုင်များကို ဖျက်လိုက်ပါပြီ။")
        bot.send_message(user_id, "🗑 သင့်ဖိုင်များကို အောင်မြင်စွာ ဖျက်ပစ်လိုက်ပါပြီ။")

    elif call.data == "install_req":
        req_file = os.path.join(user_dir, 'requirements.txt')
        if os.path.exists(req_file):
            bot.send_message(user_id, "⏳ Libraries များကို Install လုပ်နေပါသည်။ ခဏစောင့်ပါ...")
            try:
                # pip install ကို လှမ်း Run ခြင်း
                result = subprocess.run(['pip3', 'install', '-r', req_file], capture_output=True, text=True)
                if result.returncode == 0:
                    bot.send_message(user_id, "✅ လိုအပ်သော Libraries များ Install လုပ်ခြင်း အောင်မြင်ပါသည်။")
                else:
                    bot.send_message(user_id, f"❌ Install လုပ်ရာတွင် Error ဖြစ်နေပါသည်:\n```\n{result.stderr}\n```", parse_mode="Markdown")
            except Exception as e:
                bot.send_message(user_id, f"❌ အမှားအယွင်းဖြစ်နေပါသည်: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ requirements.txt ဖိုင် မတွေ့ပါ။", show_alert=True)

# Bot ကို 24 နာရီ လည်ပတ်စေခြင်း
if __name__ == "__main__":
    print("Hosting Bot is running...")
    bot.infinity_polling()
