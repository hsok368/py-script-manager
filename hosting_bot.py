import os
import subprocess
import threading
import time
import sys
from telebot import TeleBot, types
from pathlib import Path

# --- Configuration ---
TOKEN = "8940684766:AAFO4v8oXiCaO-cRLujCOYpKv8kCp2A3v4s"
BASE_DIR = Path("/home/ubuntu/py-script-manager")
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR = BASE_DIR / "logs"
SCRIPTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

bot = TeleBot(TOKEN)
active_processes = {} # {script_name: {"proc": Popen, "start_time": float}}

def get_process_status(name):
    if name not in active_processes:
        return "Stopped 🔴"
    proc = active_processes[name]["proc"]
    if proc.poll() is None:
        return "Running 🟢"
    return f"Error/Exited ⚠️ (Code: {proc.poll()})"

def install_requirements(name, chat_id, message_id):
    bot.edit_message_text(f"⏳ **Installing requirements for {name}...**", chat_id, message_id, parse_mode="Markdown")
    req_file = SCRIPTS_DIR / "requirements.txt"
    if not req_file.exists():
        bot.send_message(chat_id, "❌ `requirements.txt` မတွေ့ပါ။ ကျေးဇူးပြု၍ upload အရင်တင်ပါ။")
        return
    
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        stdout, _ = process.communicate()
        bot.send_message(chat_id, f"✅ **Installation Finished:**\n```\n{stdout[-1000:]}\n```", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"❌ **Installation Error:** {str(e)}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    msg = (
        "🤖 **Universal Python Hosting Dashboard**\n\n"
        "ဒီ Bot ကနေတစ်ဆင့် သင့်ရဲ့ Python scripts တွေကို အလွယ်တကူ Host လုပ်နိုင်ပါတယ်။\n\n"
        "**အဓိက အင်္ဂါရပ်များ:**\n"
        "✅ **Host Anything**: `.py` ဖိုင်ပို့ပြီး host လုပ်ပါ။\n"
        "🛠 **Management**: Start, Stop, Restart ခလုတ်များ။\n"
        "📦 **Auto-Install**: `requirements.txt` ကို တစ်ချက်နှိပ်ရုံနဲ့ install လုပ်ပါ။\n"
        "📜 **Live Logs**: Script ရဲ့ error နဲ့ log များကို ကြည့်ပါ။\n"
        "🗑 **Delete**: အသုံးမလိုတဲ့ script တွေကို ဖျက်ပါ။\n\n"
        "စတင်ရန် `/list` ကို နှိပ်ပါ။"
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.document.file_name.endswith(('.py', '.txt')):
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = SCRIPTS_DIR / message.document.file_name
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        bot.reply_to(message, f"✅ **{message.document.file_name}** ကို လက်ခံရရှိပါပြီ။\n\n`/list` ကိုနှိပ်ပြီး manage လုပ်နိုင်ပါတယ်။")
    else:
        bot.reply_to(message, "❌ `.py` သို့မဟုတ် `requirements.txt` ကိုသာ ပို့ပေးပါ။")

@bot.message_handler(commands=['list'])
def list_scripts(message):
    files = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py')]
    if not files:
        bot.reply_to(message, "📁 Scripts မရှိသေးပါ။ `.py` ဖိုင်တစ်ခု အရင်ပို့ပေးပါ။")
        return

    markup = types.InlineKeyboardMarkup()
    for f in files:
        status_icon = "🟢" if f in active_processes and active_processes[f]["proc"].poll() is None else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_icon} {f}", callback_data=f"manage_{f}"))
    
    bot.send_message(message.chat.id, "📑 **သင့်ရဲ့ Scripts များ:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data.startswith("manage_"):
        name = call.data.replace("manage_", "")
        status = get_process_status(name)
        
        text = f"📄 **Script:** `{name}`\n"
        text += f"📊 **Status:** {status}\n"
        
        markup = types.InlineKeyboardMarkup()
        is_running = name in active_processes and active_processes[name]["proc"].poll() is None
        
        if is_running:
            markup.row(types.InlineKeyboardButton("🛑 Stop", callback_data=f"stop_{name}"),
                       types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart_{name}"))
        else:
            markup.row(types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{name}"))
            
        markup.row(types.InlineKeyboardButton("📦 Install Requirements", callback_data=f"inst_{name}"))
        markup.row(types.InlineKeyboardButton("📜 View Logs", callback_data=f"logs_{name}"),
                   types.InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{name}"))
        markup.row(types.InlineKeyboardButton("⬅️ Back to List", callback_data="back_to_list"))
        
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("start_"):
        name = call.data.replace("start_", "")
        log_path = LOGS_DIR / f"{name}.log"
        log_file = open(log_path, "a")
        
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS_DIR / name)],
            stdout=log_file, stderr=subprocess.STDOUT, text=True, cwd=str(SCRIPTS_DIR)
        )
        active_processes[name] = {"proc": proc, "start_time": time.time()}
        bot.answer_callback_query(call.id, f"🚀 {name} started!")
        callback_query(types.CallbackQuery(call.id, call.from_user, f"manage_{name}", call.chat_instance, call.message))

    elif call.data.startswith("stop_"):
        name = call.data.replace("stop_", "")
        if name in active_processes:
            active_processes[name]["proc"].terminate()
            del active_processes[name]
            bot.answer_callback_query(call.id, f"🛑 {name} stopped!")
        callback_query(types.CallbackQuery(call.id, call.from_user, f"manage_{name}", call.chat_instance, call.message))

    elif call.data.startswith("restart_"):
        name = call.data.replace("restart_", "")
        if name in active_processes:
            active_processes[name]["proc"].terminate()
        time.sleep(1)
        callback_query(types.CallbackQuery(call.id, call.from_user, f"start_{name}", call.chat_instance, call.message))

    elif call.data.startswith("inst_"):
        name = call.data.replace("inst_", "")
        threading.Thread(target=install_requirements, args=(name, chat_id, message_id)).start()

    elif call.data.startswith("logs_"):
        name = call.data.replace("logs_", "")
        log_path = LOGS_DIR / f"{name}.log"
        if log_path.exists():
            with open(log_path, "r") as f:
                logs = f.read()[-1500:] # Last 1500 chars
            bot.send_message(chat_id, f"📜 **Logs for {name}:**\n```\n{logs if logs else '(No logs yet)'}\n```", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "No logs found.")

    elif call.data.startswith("delete_"):
        name = call.data.replace("delete_", "")
        if name in active_processes:
            active_processes[name]["proc"].terminate()
            del active_processes[name]
        (SCRIPTS_DIR / name).unlink(missing_ok=True)
        bot.answer_callback_query(call.id, f"🗑 {name} deleted!")
        list_scripts(call.message)

    elif call.data == "back_to_list":
        list_scripts(call.message)

if __name__ == "__main__":
    print("Hosting Bot is running...")
    bot.polling(none_stop=True)
