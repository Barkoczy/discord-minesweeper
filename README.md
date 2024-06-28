# Discord Minesweeper Bot

I am a Discord bot that can generate a random Minesweeper game that anyone can play!

## How to deploy on server

```bash
conda env create -f environment.yaml
```

```bash
conda activate discord_minesweeper
```

```bash
pip install -r requirements.txt
```

```bash
chmod +x /home/ubuntu/apps/discord-minesweeper/bot.sh
```

```bash
sudo cp discord-minesweeper.service /etc/systemd/system
```

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl enable discord-minesweeper.service
```

```bash
sudo systemctl start discord-minesweeper.service
```

```bash
sudo systemctl status discord-minesweeper.service
```