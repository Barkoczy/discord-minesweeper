import os
import random
import asyncio
import weakref
import discord
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

TOKEN = os.getenv('TOKEN')
DEFAULT_CHANNEL_ID = os.getenv('DEFAULT_CHANNEL_ID')  # Načítajte ID z .env súboru

# Funkcia na načítanie povolených ID kanálov zo súboru
def load_allowed_channels():
  channels = set()
  if DEFAULT_CHANNEL_ID:
    try:
      channels.add(int(DEFAULT_CHANNEL_ID))
    except ValueError:
      print("Warning: Invalid DEFAULT_CHANNEL_ID in .env file.")
  
  try:
    with open('allowed_channels.txt', 'r') as file:
      channels.update(int(line.strip()) for line in file if line.strip().isdigit())
    if not channels:
      print("Warning: No valid channel IDs found in allowed_channels.txt or .env file.")
  except FileNotFoundError:
    if not channels:
      print("Warning: allowed_channels.txt not found and no valid DEFAULT_CHANNEL_ID. No channels will be allowed.")
  
  return channels
  
# Načítame povolené kanály pri spustení skriptu
ALLOWED_CHANNEL_IDS = load_allowed_channels()

# Použijeme WeakValueDictionary pre automatické odstraňovanie nepoužívaných hier
games = weakref.WeakValueDictionary()

# Minesweeper
class Minesweeper:
  def __init__(self, size=5, mines=5):
    self.size = size
    self.mines = mines
    self.board = bytearray(size * size)
    self.revealed = bytearray(size * size)
    self.game_over = False
    self.last_interaction = asyncio.get_event_loop().time()
    self.place_mines()
    self.calculate_numbers()

  def place_mines(self):
    positions = random.sample(range(self.size * self.size), self.mines)
    for pos in positions:
      self.board[pos] = 255  # 255 reprezentuje mínu

  def calculate_numbers(self):
    for y in range(self.size):
      for x in range(self.size):
        if self.board[y * self.size + x] == 255:
          continue
        count = sum(1 for dy in [-1, 0, 1] for dx in [-1, 0, 1]
          if 0 <= y+dy < self.size and 0 <= x+dx < self.size
          and self.board[(y+dy) * self.size + (x+dx)] == 255)
        self.board[y * self.size + x] = count

  def reveal(self, x, y):
    if not (0 <= x < self.size and 0 <= y < self.size) or self.revealed[y * self.size + x] or self.game_over:
      return False
    self.revealed[y * self.size + x] = 1
    if self.board[y * self.size + x] == 255:
      self.game_over = True
      return True
    if self.board[y * self.size + x] == 0:
      for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
          if 0 <= x+dx < self.size and 0 <= y+dy < self.size:
            self.reveal(x+dx, y+dy)
    if all(self.revealed[i] or self.board[i] == 255 for i in range(self.size * self.size)):
        self.game_over = True
    self.last_interaction = asyncio.get_event_loop().time()
    return False

class GameView(discord.ui.View):
  def __init__(self, game, player_id):
    super().__init__(timeout=None)
    self.game = game
    self.player_id = player_id
    self.update_buttons()

  def update_buttons(self):
    self.clear_items()
    for y in range(self.game.size):
      for x in range(self.game.size):
        button = GameButton(x, y, self.game, self.player_id)
        self.add_item(button)

class GameButton(discord.ui.Button):
  def __init__(self, x, y, game, player_id):
    self.x = x
    self.y = y
    self.game = game
    self.player_id = player_id

    idx = y * game.size + x
    if game.revealed[idx]:
      if game.board[idx] == 255:
        style = discord.ButtonStyle.danger
        label = "💣"
      elif game.board[idx] == 0:
        style = discord.ButtonStyle.secondary
        label = "🟪"
      else:
        style = discord.ButtonStyle.primary
        label = str(game.board[idx])
    else:
      style = discord.ButtonStyle.primary
      label = "🟦"

    super().__init__(style=style, label=label, row=y)

  async def callback(self, interaction: discord.Interaction):
    if interaction.user.id != self.player_id:
      await interaction.response.send_message("You can't interact with this game.", ephemeral=True)
      return

    if self.game.game_over:
      await interaction.response.send_message("The game is already over. Start a new game to play again.", ephemeral=True)
      return

    await interaction.response.defer()

    hit_mine = self.game.reveal(self.x, self.y)

    view = self.view
    view.update_buttons()

    if self.game.game_over:
      content = "You lost the game!" if hit_mine else "Congratulations! You won!"
      del games[self.player_id]
    else:
      content = "Click on the buttons to reveal the blocks except mines."

    embed = discord.Embed(
      title="**Minesweeper**",
      description=content,
      color=discord.Color.red() if hit_mine else discord.Color.green()
    )
    embed.set_author(
      name=interaction.user.display_name,
      icon_url=interaction.user.avatar.url if interaction.user.avatar else None
    )
    await interaction.edit_original_response(embed=embed, view=view)

# Connect
try:
  intents = discord.Intents.default()
  intents.message_content = True
  bot = commands.Bot(command_prefix='!', intents=intents)
except Exception as e:
  print(e)

# Func
def check_channel(ctx):
  channel_id = int(ctx.channel.id)
  allowed_channels = ALLOWED_CHANNEL_IDS
  result = channel_id in allowed_channels
  return result

async def send_game_board(ctx, game):
  view = GameView(game, ctx.author.id)

  embed = discord.Embed(
    title="**Minesweeper**",
    description="Click on the buttons to reveal the blocks except mines.",
    color=discord.Color.blue()
  )
  embed.set_author(
    name=ctx.author.display_name,
    icon_url=ctx.author.avatar.url if ctx.author.avatar else None
  )
  await ctx.send(embed=embed, view=view)

async def clean_old_games():
  while True:
    current_time = asyncio.get_event_loop().time()
    to_remove = [player_id for player_id, game in games.items() 
      if current_time - game.last_interaction > 1800]
    for player_id in to_remove:
      del games[player_id]
    await asyncio.sleep(300)  # Kontrola každých 5 minút

# Commands
@bot.command()
@commands.check(check_channel)
async def play(ctx):
  try:
    game = Minesweeper()
    games[ctx.author.id] = game
    await send_game_board(ctx, game)
  except Exception as e:
    print(e)

@bot.event
async def on_ready():
  print(f'{bot.user} has connected to Discord!')
  print(f'Bot is allowed to operate in {len(ALLOWED_CHANNEL_IDS)} channels.')
  asyncio.create_task(clean_old_games())

# run
bot.run(TOKEN)
