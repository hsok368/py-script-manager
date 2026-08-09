import os
import subprocess
import threading
import time
import sys
import psutil
from telebot import TeleBot, types
from pathlib import Path
from datetime import datetime

# --- Configuration ---
TOKEN = "8940684766:AAFO4v8oXiCaO-cRLujCOYpKv8kCp2A3v4s"
BASE_DIR = Path("/home/ubuntu/py-script-manager")
SCRIPTS_DIR = BASE_DIR / "scripts"
LOGS_DIR = BASE_DIR / "logs"
SCRIPTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

bot = TeleBot(TOKEN, parse_mode="HTML")
active_processes = {} # {script_name: {"proc": Popen, "start_time": float}}

# --- Helpers ---

def get_sys_info():
    return {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "uptime": str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split('.')[0]
    }

def get_status_icon(name):
    if name not in active_processes:
        return "🔴 Stopped"
    proc = active_processes[name]["proc"]
    if proc.poll() is None:
        return "🟢 Running"
    return "⚠️ Error/Exited"

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📁 My Scripts"),
        types.KeyboardButton("📊 System Status"),
        types.KeyboardButton("📦 Install Requirements"),
        types.KeyboardButton("❓ Help & Info")
    )
    return markup

# --- Handlers ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "<b>🚀 Welcome to Python Hosting Pro</b>\n"
        "───────────────────────\n"
        "Professional Python script hosting dashboard via Telegram.\n\n"
        "<b>✨ Features:</b>\n"
        "• High-Performance Hosting\n"
        • Real-time Log Streaming\n"
        "• Dynamic Dependency Management\n"
        "• System Resource Monitoring\n\n"
        "<i>Send a .py file to get started!</i>"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📁 My Scripts")
def cmd_list_scripts(message):
    files = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py')]
    if not files:
        bot.reply_to(message, "<b>📁 No scripts found.</b>\nPlease upload a <code>.py</code> file first.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in files:
        status = get_status_icon(f)
        markup.add(types.InlineKeyboardButton(f"{status} | {f}", callback_data=f"manage_{f}"))
    
    bot.send_message(message.chat.id, "<b>📂 Script Manager Dashboard</b>\nSelect a script to manage its state:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 System Status")
def cmd_sys_status(message):
    info = get_sys_info()
    status_text = (
        "<b>📊 Server Resource Status</b>\n"
        "───────────────────────\n"
        f"<b>🖥 CPU Usage:</b> <code>{info['cpu']}%</code>\n"
        f"<b>💾 RAM Usage:</b> <code>{info['ram']}%</code>\n"
        f"<b>💽 Disk Space:</b> <code>{info['disk']}%</code>\n"
        f"<b>⏱ Uptime:</b> <code>{info['uptime']}</code>\n"
        "───────────────────────\n"
        "<i>Status updated in real-time.</i>"
    )
    bot.send_message(message.chat.id, status_text)

@bot.message_handler(func=lambda m: m.text == "📦 Install Requirements")
def cmd_install_req(message):
    req_file = SCRIPTS_DIR / "requirements.txt"
    if not req_file.exists():
        bot.reply_to(message, "❌ <b>requirements.txt not found.</b>\nPlease upload your requirements file first.")
        return
    
    msg = bot.reply_to(message, "⏳ <b>Starting dynamic installation...</b>")
    
    def run_install():
        try:
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            stdout, _ = process.communicate()
            bot.edit_message_text(f"✅ <b>Installation Complete!</b>\n<pre>{stdout[-1500:]}</pre>", message.chat.id, msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ <b>Installation Failed:</b> {str(e)}", message.chat.id, msg.message_id)

    threading.Thread(target=run_install).start()

@bot.message_handler(func=lambda m: m.text == "❓ Help & Info")
def cmd_help(message):
    help_text = (
        "<b>💡 Pro Hosting Bot Guide</b>\n"
        "───────────────────────\n"
        "<b>1. Upload:</b> Send any <code>.py</code> file to the bot.\n"
        "<b>2. Manage:</b> Use 📁 <b>My Scripts</b> to Start/Stop/Delete.\n"
        "<b>3. Logs:</b> Check 📜 <b>View Logs</b> for debugging.\n"
        "<b>4. Deps:</b> Upload <code>requirements.txt</code> and click 📦 <b>Install</b>.\n"
        "───────────────────────\n"
        "<i>Powered by Python Hosting Pro</i>"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.document.file_name.endswith(('.py', '.txt')):
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_path = SCRIPTS_DIR / message.document.file_name
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        bot.reply_to(message, f"✅ <b>File Received:</b> <code>{message.document.file_name}</code>\nManagement is now available in the dashboard.")
    else:
        bot.reply_to(message, "❌ <b>Unsupported Format.</b>\nPlease send only <code>.py</code> or <code>.txt</code> files.")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    if call.data.startswith("manage_"):
        name = call.data.replace("manage_", "")
        status = get_status_icon(name)
        
        text = (
            f"<b>🛠 Script Management:</b> <code>{name}</code>\n"
            "───────────────────────\n"
            f"<b>Current Status:</b> {status}\n"
            "───────────────────────"
        )
        
        markup = types.InlineKeyboardMarkup()
        is_running = name in active_processes and active_processes[name]["proc"].poll() is None
        
        if is_running:
            markup.row(types.InlineKeyboardButton("🛑 Stop", callback_data=f"stop_{name}"),
                       types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart_{name}"))
        else:
            markup.row(types.InlineKeyboardButton("▶️ Start Script", callback_data=f"start_{name}"))
            
        markup.row(types.InlineKeyboardButton("📜 View Live Logs", callback_data=f"logs_{name}"))
        markup.row(types.InlineKeyboardButton("🗑 Delete Permanent", callback_data=f"delete_{name}"))
        markup.row(types.InlineKeyboardButton("⬅️ Back to List", callback_data="back_to_list"))
        
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup)

    elif call.data.startswith("start_"):
        name = call.data.replace("start_", "")
        log_path = LOGS_DIR / f"{name}.log"
        log_file = open(log_path, "a")
        
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPTS_DIR / name)],
            stdout=log_file, stderr=subprocess.STDOUT, text=True, cwd=str(SCRIPTS_DIR)
        )
        active_processes[name] = {"proc": proc, "start_time": time.time()}
        bot.answer_callback_query(call.id, f"🚀 {name} is now online!")
        handle_query(types.CallbackQuery(call.id, call.from_user, f"manage_{name}", call.chat_instance, call.message))

    elif call.data.startswith("stop_"):
        name = call.data.replace("stop_", "")
        if name in active_processes:
            active_processes[name]["proc"].terminate()
            del active_processes[name]
            bot.answer_callback_query(call.id, f"🛑 {name} has been stopped.")
        handle_query(types.CallbackQuery(call.id, call.from_user, f"manage_{name}", call.chat_instance, call.message))

    elif call.data.startswith("restart_"):
        name = call.data.replace("restart_", "")
        if name in active_processes:
            active_processes[name]["proc"].terminate()
        time.sleep(1)
        handle_query(types.CallbackQuery(call.id, call.from_user, f"start_{name}", call.chat_instance, call.message))

    elif call.data.startswith("logs_"):
        name = call.data.replace("logs_", "")
        log_path = LOGS_DIR / f"{name}.log"
        if log_path.exists():
            with open(log_path, "r") as f:
                logs = f.read()[-2000:]
            bot.send_message(chat_id, f"<b>📜 Logs for {name}:</b>\n<pre>{logs if logs else '(No output yet)'}</pre>")
        else:
            bot.answer_callback_query(call.id, "No logs available.")

    elif call.data.startswith("delete_"):
        name = call.data.replace("delete_", "")
        if name in active_processes:
            active_processes[name]["proc"].terminate()
            del active_processes[name]
        (SCRIPTS_DIR / name).unlink(missing_ok=True)
        bot.answer_callback_query(call.id, f"🗑 {name} deleted.")
        cmd_list_scripts(call.message)

    elif call.data == "back_to_list":
        files = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py')]
        markup = types.InlineKeyboardMarkup(row_width=1)
        for f in files:
            status = get_status_icon(f)
            markup.add(types.InlineKeyboardButton(f"{status} | {f}", callback_data=f"manage_{f}"))
        bot.edit_message_text("<b>📂 Script Manager Dashboard</b>\nSelect a script to manage its state:", chat_id, msg_id, reply_markup=markup)

if __name__ == "__main__":
    print("Python Hosting Pro is starting...")
    bot.infinity_polling()
