"""
Telegram Bot Manager
====================
Allows managing your Python scripts via Telegram.
Commands: /start, /list, /status, /start_script <name>, /stop_script <name>
"""

import os
import requests
import time
from telebot import TeleBot, types

# Configuration
API_BASE = "http://localhost:5000/api"
TOKEN = "8940684766:AAFO4v8oXiCaO-cRLujCOYpKv8kCp2A3v4s" # Provided by user

bot = TeleBot(TOKEN)

def get_scripts():
    try:
        r = requests.get(f"{API_BASE}/scripts")
        return r.json()
    except:
        return []

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🤖 *Universal Script Manager Bot*\n\n"
        "Commands:\n"
        "/list - List all scripts\n"
        "/status - Show system status\n"
        "/help - Show this message"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['list'])
def list_scripts(message):
    scripts = get_scripts()
    if not scripts:
        bot.reply_to(message, "No scripts found.")
        return

    markup = types.InlineKeyboardMarkup()
    for s in scripts:
        status_icon = "🟢" if s['status'] == 'running' else "🔴" if s['status'] == 'stopped' else "⚠️"
        btn_text = f"{status_icon} {s['name']}"
        callback_data = f"view_{s['name']}"
        markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=callback_data))
    
    bot.send_message(message.chat.id, "Select a script to manage:", reply_markup=markup)

@bot.message_handler(commands=['status'])
def sys_status(message):
    try:
        r = requests.get(f"{API_BASE}/system")
        data = r.json()
        text = (
            "📊 *System Status*\n\n"
            f"🖥 CPU: {data['cpu']}%\n"
            f"💾 RAM: {data['ram']}%\n"
            f"💽 Disk: {data['disk']}%\n"
            f"⏱ Uptime: {data['uptime']}s"
        )
        bot.reply_to(message, text, parse_mode="Markdown")
    except:
        bot.reply_to(message, "Error fetching system status. Is the dashboard running?")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    data = call.data
    
    if data.startswith("view_"):
        name = data.replace("view_", "")
        scripts = get_scripts()
        script = next((s for s in scripts if s['name'] == name), None)
        
        if not script:
            bot.answer_callback_query(call.id, "Script not found.")
            return

        status_icon = "🟢" if script['status'] == 'running' else "🔴" if script['status'] == 'stopped' else "⚠️"
        text = (
            f"📄 *Script:* `{name}`\n"
            f"📊 *Status:* {script['status'].upper()} {status_icon}\n"
            f"🆔 *PID:* `{script['pid'] or 'N/A'}`\n"
            f"🕒 *Started:* `{script['started_at'] or 'N/A'}`"
        )
        
        markup = types.InlineKeyboardMarkup()
        if script['status'] == 'running':
            markup.add(types.InlineKeyboardButton("🛑 Stop", callback_data=f"stop_{name}"))
        else:
            markup.add(types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{name}"))
        
        markup.add(types.InlineKeyboardButton("🔄 Restart", callback_data=f"restart_{name}"))
        markup.add(types.InlineKeyboardButton("⬅️ Back to List", callback_data="back_list"))
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "back_list":
        scripts = get_scripts()
        markup = types.InlineKeyboardMarkup()
        for s in scripts:
            status_icon = "🟢" if s['status'] == 'running' else "🔴" if s['status'] == 'stopped' else "⚠️"
            markup.add(types.InlineKeyboardButton(text=f"{status_icon} {s['name']}", callback_data=f"view_{s['name']}"))
        bot.edit_message_text("Select a script to manage:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif data.startswith(("start_", "stop_", "restart_")):
        action, name = data.split("_", 1)
        try:
            r = requests.post(f"{API_BASE}/{action}/{name}")
            res = r.json()
            bot.answer_callback_query(call.id, res.get("message", res.get("error", "Action sent")))
            # Refresh view
            callback_query(types.CallbackQuery(call.id, call.from_user, f"view_{name}", call.chat_instance, call.message))
        except:
            bot.answer_callback_query(call.id, "Connection error.")

if __name__ == "__main__":
    print("Telegram Bot Manager started...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
