# Ubuntu Setup

Fastest option:

```bash
git clone https://github.com/xelsing1991-maker/vpn_router_redirect.git
cd vpn_router_redirect
chmod +x install_ubuntu.sh
sudo ./install_ubuntu.sh
```

Manual option:

1. Install packages:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

2. Copy the project to the server:

```bash
sudo mkdir -p /opt/botvpnredirect
sudo cp multi_bot_redirect.py app_*.py requirements.txt botvpnredirect.service /opt/botvpnredirect/
sudo touch /opt/botvpnredirect/.env
echo '[]' | sudo tee /opt/botvpnredirect/bot_tokens.json
echo '[]' | sudo tee /opt/botvpnredirect/channels.json
echo '{"bots": {}}' | sudo tee /opt/botvpnredirect/button_stats.json
```

3. Install Python dependencies:

```bash
cd /opt/botvpnredirect
sudo python3 -m venv .venv
sudo .venv/bin/pip install --upgrade pip
sudo .venv/bin/pip install -r requirements.txt
```

4. Install the `systemd` service:

```bash
sudo cp botvpnredirect.service /etc/systemd/system/botvpnredirect.service
sudo systemctl daemon-reload
sudo systemctl enable botvpnredirect
sudo systemctl start botvpnredirect
```

5. Check status and logs:

```bash
sudo systemctl status botvpnredirect
sudo journalctl -u botvpnredirect -f
```

Configure secrets after install:

```bash
sudo nano /opt/botvpnredirect/.env
sudo nano /opt/botvpnredirect/bot_tokens.json
sudo systemctl restart botvpnredirect
```

**Admin Commands**

- `/admin` - open admin panel
- `/stats` - stats for the current bot
- `/add <token>` - add a new bot token
- `/addchannel @username | Channel name` - add a channel

**Admin Panel Features**

- overview of launches and activity
- online users for the last 5 minutes
- list of connected bots
- add bots without editing files
- add and remove channels
- stats for a specific bot
- first bot in `bot_tokens.json` is the primary admin bot

**Notes**

- `button_stats.json` stores visits and activity.
- `channels.json` stores channel buttons.
- `bot_tokens.json` stores Telegram bot tokens.
- `.env` stores admin IDs and public main-bot link settings.
- after adding a new bot through the admin panel, the service restarts automatically.
