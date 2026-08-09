# 🚀 Universal Python Script Manager Dashboard

A professional web-based dashboard and Telegram Bot to host, manage, and monitor any Python script.

## ✨ Features
- **Universal Dashboard**: Host and manage multiple Python scripts from one place.
- **Process Management**: Start, Stop, Restart scripts with a single click.
- **Live Logs**: Real-time log streaming via WebSockets.
- **Edit System**: Modify script content directly from the browser.
- **Error Reporting**: Immediate visual feedback on script status and errors.
- **Dynamic Installation**: Install dependencies from `requirements.txt` via the UI.
- **Telegram Integration**: Manage your scripts on the go using the integrated Telegram Bot.
- **System Monitoring**: Real-time CPU, RAM, and Disk usage stats.

## 🛠 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/bawh395/py-script-manager.git
   cd py-script-manager
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Telegram Bot (Optional):**
   Edit `scripts/telegram_bot.py` and replace the `TOKEN` variable with your bot token.

4. **Run the Dashboard:**
   ```bash
   python app.py
   ```

5. **Access the Dashboard:**
   Open `http://localhost:5000` in your browser.

## 📁 Directory Structure
- `/scripts`: Place your Python scripts here.
- `/templates`: HTML templates for the dashboard.
- `/static`: CSS and JavaScript files.
- `/logs`: Log files for each script.
- `/uploads`: Temporary directory for uploaded files.

## 🤖 Telegram Bot Commands
- `/list` - List all scripts and their status.
- `/status` - Show system resource usage.
- `/start_script <name>` - Start a specific script.
- `/stop_script <name>` - Stop a specific script.

## 📝 License
MIT License. Feel free to use and modify!
