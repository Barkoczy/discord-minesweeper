#!/bin/bash

# Aktivuje prostredie Miniconda
source ~/miniconda3/bin/activate discord_minesweeper

# Definuj cestu k adresáru, kde sú uložené súbory
dir=/home/ubuntu/apps/discord-minesweeper

# Spustenie Python skriptu app.py
python3 "$dir/app.py"

# Deaktivuje prostredie po skončení
conda deactivate