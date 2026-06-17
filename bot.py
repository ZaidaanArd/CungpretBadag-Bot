import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import random
import asyncio
import json
import sqlite3

from datetime import datetime, timedelta
import aiohttp
from dotenv import load_dotenv

load_dotenv()

loop_mode = {}
autoplay_mode = {}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

WARNA = {
    "main": 0x5865F2,
    "sukses": 0x57F287,
    "warning": 0xFEE75C,
    "gagal": 0xED4245,
    "info": 0x5865F2,
    "mystic": 0x9B59B6,
    "oranye": 0xE67E22,
    "tosca": 0x1ABC9C,
    "merah": 0xE74C3C,
    "biru": 0x3498DB,
    "music": 0x1DB954,
    "game": 0xE91E63,
    "level": 0x2ECC71,
}

KATA_BIJAK = [
    "Hidup bukan tentang menemukan diri sendiri, tapi tentang menciptakan diri sendiri.",
    "Jangan tunda sampai besok apa yang bisa kamu lakukan hari ini.",
    "Kesuksesan adalah jumlah dari usaha kecil yang diulang hari demi hari.",
    "Satu-satunya cara untuk melakukan pekerjaan hebat adalah dengan mencintai apa yang kamu lakukan.",
    "Percayalah kamu bisa dan kamu sudah setengah jalan.",
    "Jadilah perubahan yang ingin kamu lihat di dunia.",
    "Kegagalan adalah bumbu yang memberi rasa pada kesuksesan.",
    "Hari ini adalah kesempatan untuk membangun masa depan yang kau impikan.",
    "Kecil itu bukan halangan. Konsisten adalah kuncinya.",
    "Jangan bandingkan prosesmu dengan orang lain. Setiap orang punya waktunya sendiri.",
    "Selama ada nafas, masih ada kesempatan untuk memperbaiki diri.",
    "Your limitation—it's only your imagination.",
    "Push yourself because no one else is going to do it for you.",
    "Great things never come from comfort zones.",
    "Dream it. Wish it. Do it.",
    "Talent tanpa kerja keras adalah nothing.",
    "Hidup itu seperti bersepeda. Biar seimbang, kau harus terus bergerak.",
    "Masa depan adalah milik mereka yang percaya pada keindahan mimpi-mimpi mereka.",
    "Sabar itu pahit, tapi buahnya manis.",
    "Jangan pernah menyerah. Keajaiban terjadi pada mereka yang percaya."
]

JAWABAN_8BALL = [
    "Pasti banget! 👍",
    "Iya, menurut saya begitu.",
    "Mungkin... coba lagi nanti.",
    "Tandanya iya, coba tanya lagi.",
    "Lebih baik tidak usah tahu.",
    "Sumber saya bilang iya!",
    "Jangan berharap begitu.",
    "Tidak sekarang.",
    "Sangat tidak mungkin.",
    "Ragu-ragu... coba ulangi.",
    "Saya pikir iya.",
    "100% iya!",
    "Mending tanya yang lain deh.",
    "Sudah jelas! Jawabannya iya.",
    "Tidak. Titik.",
    "Iya, tapi kamu harus usaha dulu."
]

DATA_FILE = "data/levels.json"
DB_PATH = "data/levels.db"
ACTIVITY_LOG = "activity.log"

def log_activity(pesan):
    try:
        with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {pesan}\n")
    except:
        pass

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS levels (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL DEFAULT 'Unknown',
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS afk (
            guild_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT 'Tidak ada alasan',
            since INTEGER NOT NULL,
            PRIMARY KEY (guild_id, user_id)
        )
    """)
    conn.commit()

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                old_data = json.load(f)
            if old_data:
                total = 0
                for guild_id, users in old_data.items():
                    for user_id, info in users.items():
                        conn.execute(
                            "INSERT OR REPLACE INTO levels (guild_id, user_id, xp, name) VALUES (?, ?, ?, ?)",
                            (guild_id, user_id, info.get("xp", 0), info.get("name", "Unknown"))
                        )
                        total += 1
                conn.commit()
                os.replace(DATA_FILE, DATA_FILE + ".bak")
                print(f"✅ Migrated {total} users from JSON to SQLite")
        except Exception as e:
            print(f"⚠️ JSON migration failed: {e}")
    conn.close()

def get_xp_for_level(level):
    return 5 * (level ** 2) + 50 * level + 100

def get_level_from_xp(xp):
    level = 0
    while True:
        needed = get_xp_for_level(level)
        if xp >= needed:
            xp -= needed
            level += 1
        else:
            break
    return level, xp

# ──────────────────────────────────────────────────────────
# MUSIC PLAYER
# ──────────────────────────────────────────────────────────

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

ffmpeg_options = {
    "options": "-vn -bufsize 64k -b:a 128k",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
}

import logging
logging.getLogger("yt_dlp").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

ydl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "ignoreerrors": True,
    "extract_flat": False,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

music_queues = {}
music_nowplaying = {}

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title", "Unknown")
        self.url = data.get("webpage_url", "")
        self.duration = data.get("duration", 0)
        self.thumbnail = data.get("thumbnail", "")
        self.uploader = data.get("uploader", "Unknown")

    @classmethod
    async def from_query(cls, query, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        try:
            data = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        except Exception:
            return None

        if data is None:
            return None

        if "entries" in data:
            data = data["entries"][0]
            if data is None:
                return None

        audio_url = data["url"]
        title = data.get("title", "Unknown")
        return cls(
            discord.FFmpegPCMAudio(audio_url, **ffmpeg_options),
            data=data,
        ), title

def get_music_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    return music_queues[guild_id]

async def play_next(ctx, guild_id):
    queue = get_music_queue(guild_id)

    if loop_mode.get(guild_id) and guild_id in music_nowplaying:
        last = music_nowplaying[guild_id]
        if "url" in last:
            result = await YTDLSource.from_query(last["url"])
            if result:
                player, _ = result
                queue.insert(0, {"player": player, "title": last["title"], "requester": last["requester"], "url": last["url"]})

    if autoplay_mode.get(guild_id) and not queue and guild_id in music_nowplaying:
        last = music_nowplaying[guild_id]
        auto_q = f"{last['title']} audio"
        result = await YTDLSource.from_query(auto_q)
        if result:
            player, title = result
            queue.append({"player": player, "title": title, "requester": bot.user, "url": ""})

    if queue:
        item = queue.pop(0)
        player = item["player"]
        title = item["title"]
        requester = item["requester"]

        ctx.voice_client.play(
            player,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx, guild_id), bot.loop
            ),
        )
        music_nowplaying[guild_id] = {"title": title, "requester": requester, "url": item.get("url", "")}

        embed = discord.Embed(
            title=f"🎵 **Now Playing**",
            description=f"**{title}**",
            color=WARNA["music"],
        )
        if hasattr(player, "thumbnail") and player.thumbnail:
            embed.set_thumbnail(url=player.thumbnail)
        embed.add_field(name="Diminta oleh", value=requester.mention, inline=True)
        embed.add_field(name="Antrian", value=f"{len(queue)} lagu", inline=True)
        await ctx.send(embed=embed, delete_after=10)
    else:
        music_nowplaying.pop(guild_id, None)
        await ctx.voice_client.disconnect()

@bot.command(aliases=["p", "nyanyi"])
async def play(ctx, *, query):
    """Putar lagu dari YouTube. Contoh: !play naruto opening | blue bird"""
    if not YTDLP_AVAILABLE:
        return await ctx.send(embed=discord.Embed(title="❌ yt-dlp belum terinstall!", color=WARNA["gagal"]))

    if not ctx.author.voice:
        return await ctx.send(embed=discord.Embed(title="❌ Kamu harus di voice channel dulu!", color=WARNA["gagal"]))

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    queries = [q.strip() for q in query.split("|")]
    if len(queries) > 10:
        return await ctx.send(embed=discord.Embed(title="❌ Maksimal 10 lagu sekaligus!", color=WARNA["gagal"]))

    msg = await ctx.send(embed=discord.Embed(title=f"🔍 **Mencari {len(queries)} lagu...**", color=WARNA["music"]))

    results = []
    for i, q in enumerate(queries):
        result = await YTDLSource.from_query(q)
        if result:
            player, title = result
            audio_url = result[0].data.get("url", "") if hasattr(result[0], "data") else ""
            results.append({"player": result[0], "title": title, "requester": ctx.author, "url": audio_url})
        await msg.edit(embed=discord.Embed(
            title=f"🔍 **Mencari... ({i+1}/{len(queries)})**",
            description=f"✅ **{result[1]}**" if result else f"❌ {q}",
            color=WARNA["music"]
        ))

    if not results:
        return await msg.edit(embed=discord.Embed(title="❌ Semua lagu gagal ditemukan!", color=WARNA["gagal"]))

    queue = get_music_queue(ctx.guild.id)
    item = results.pop(0)

    if ctx.voice_client.is_playing():
        queue.insert(0, item)
        memulai = f"📃 **{item['title']}** — ditambahkan ke antrian (posisi 1)"
    else:
        log_activity(f"MUSIC PLAY {ctx.author} memutar: {item['title']} di {ctx.guild}")
        ctx.voice_client.play(
            item["player"],
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx, ctx.guild.id), bot.loop
            ),
        )
        music_nowplaying[ctx.guild.id] = {"title": item["title"], "requester": item["requester"], "url": item.get("url", "")}
        memulai = f"▶️ **{item['title']}** — sekarang diputar"

    for item in results:
        queue.append(item)

    total_queries = len(queries)
    total_success = len(results) + 1
    total_failed = total_queries - total_success
    embed = discord.Embed(
        title="✅ **Selesai!**",
        description=(
            f"{memulai}\n"
            f"📃 **{len(results)}** lagu di antrian\n"
            f"{'❌ **' + str(total_failed) + '** gagal' if total_failed else '✅ Semua berhasil'}"
        ),
        color=WARNA["sukses"]
    )
    await msg.edit(embed=embed)

@bot.command()
async def pause(ctx):
    """Pause lagu yang sedang diputar."""
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        return await ctx.send(embed=discord.Embed(title="❌ Tidak ada lagu yang diputar!", color=WARNA["gagal"]))
    ctx.voice_client.pause()
    await ctx.send(embed=discord.Embed(title="⏸️ **Paused**", color=WARNA["music"]))

@bot.command()
async def resume(ctx):
    """Resume lagu yang di-pause."""
    if not ctx.voice_client or not ctx.voice_client.is_paused():
        return await ctx.send(embed=discord.Embed(title="❌ Lagunya gak di-pause!", color=WARNA["gagal"]))
    ctx.voice_client.resume()
    await ctx.send(embed=discord.Embed(title="▶️ **Resumed**", color=WARNA["music"]))

@bot.command(aliases=["next", "s"])
async def skip(ctx):
    """Skip ke lagu berikutnya."""
    if not ctx.voice_client or not (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
        return await ctx.send(embed=discord.Embed(title="❌ Gak ada lagu yang bisa di-skip!", color=WARNA["gagal"]))
    log_activity(f"MUSIC SKIP {ctx.author} di {ctx.guild}")
    ctx.voice_client.stop()
    await ctx.send(embed=discord.Embed(title="⏭️ **Skipped**", color=WARNA["music"]))

@bot.command()
async def stop(ctx):
    """Stop music & clear queue."""
    if not ctx.voice_client:
        return await ctx.send(embed=discord.Embed(title="❌ Bot gak di voice channel!", color=WARNA["gagal"]))
    log_activity(f"MUSIC STOP {ctx.author} di {ctx.guild}")
    music_queues.pop(ctx.guild.id, None)
    music_nowplaying.pop(ctx.guild.id, None)
    loop_mode.pop(ctx.guild.id, None)
    autoplay_mode.pop(ctx.guild.id, None)
    ctx.voice_client.stop()
    await ctx.voice_client.disconnect()
    await ctx.send(embed=discord.Embed(title="⏹️ **Stopped** • Antrian dibersihkan", color=WARNA["music"]))

@bot.command(aliases=["q", "antrian"])
async def queue(ctx):
    """Lihat antrian lagu."""
    queue_list = get_music_queue(ctx.guild.id)
    now = music_nowplaying.get(ctx.guild.id)

    embed = discord.Embed(title="🎶 **Music Queue**", color=WARNA["music"])

    if now:
        embed.add_field(name="▶️ **Sedang Diputar**", value=f"**{now['title']}**\nDiminta oleh {now['requester'].mention}", inline=False)

    if not queue_list:
        embed.description = "Antrian kosong. Tambah lagu dengan `!play`!"
    else:
        daftar = ""
        for i, item in enumerate(queue_list[:10], 1):
            daftar += f"`{i}.` **{item['title']}** — {item['requester'].mention}\n"
        if len(queue_list) > 10:
            daftar += f"\n...dan {len(queue_list) - 10} lagu lainnya"
        embed.add_field(name=f"📃 **Antrian ({len(queue_list)})**", value=daftar, inline=False)

    await ctx.send(embed=embed)

@bot.command(aliases=["np", "lagu"])
async def nowplaying(ctx):
    """Lihat lagu yang sedang diputar."""
    now = music_nowplaying.get(ctx.guild.id)
    if not now:
        return await ctx.send(embed=discord.Embed(title="❌ Tidak ada lagu yang diputar!", color=WARNA["gagal"]))
    embed = discord.Embed(
        title="🎵 **Now Playing**",
        description=f"**{now['title']}**",
        color=WARNA["music"],
    )
    embed.set_footer(text=f"Diminta oleh {now['requester'].name}", icon_url=now['requester'].display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=["v", "vol"])
async def volume(ctx, vol: int):
    """Atur volume (0-100). Contoh: !volume 50"""
    if not ctx.voice_client:
        return await ctx.send(embed=discord.Embed(title="❌ Bot gak di voice channel!", color=WARNA["gagal"]))
    if vol < 0 or vol > 100:
        return await ctx.send(embed=discord.Embed(title="❌ Volume harus 0-100!", color=WARNA["gagal"]))
    if not ctx.voice_client.source:
        return await ctx.send(embed=discord.Embed(title="❌ Gak ada lagu yang diputar!", color=WARNA["gagal"]))
    ctx.voice_client.source.volume = vol / 100
    await ctx.send(embed=discord.Embed(title=f"🔊 **Volume: {vol}%**", color=WARNA["music"]))

@bot.command(aliases=["join", "masuk"])
async def joinvc(ctx):
    """Suruh bot join voice channel kamu."""
    if not ctx.author.voice:
        return await ctx.send(embed=discord.Embed(title="❌ Kamu harus di voice channel!", color=WARNA["gagal"]))
    if ctx.voice_client:
        if ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)
            await ctx.send(embed=discord.Embed(title=f"📌 **Pindah ke** {ctx.author.voice.channel.mention}", color=WARNA["music"]))
        else:
            await ctx.send(embed=discord.Embed(title="ℹ️ Udah di voice channel yang sama!", color=WARNA["music"]))
    else:
        await ctx.author.voice.channel.connect()
        log_activity(f"VOICE JOIN {ctx.author} di {ctx.guild} ke {ctx.author.voice.channel}")
        await ctx.send(embed=discord.Embed(title=f"📌 **Joined** {ctx.author.voice.channel.mention}", color=WARNA["music"]))

@bot.command(aliases=["leave", "keluar"])
async def leavevc(ctx):
    """Suruh bot keluar dari voice channel."""
    if not ctx.voice_client:
        return await ctx.send(embed=discord.Embed(title="❌ Bot gak di voice channel!", color=WARNA["gagal"]))
    music_queues.pop(ctx.guild.id, None)
    music_nowplaying.pop(ctx.guild.id, None)
    loop_mode.pop(ctx.guild.id, None)
    autoplay_mode.pop(ctx.guild.id, None)
    log_activity(f"VOICE LEAVE {ctx.author} di {ctx.guild}")
    await ctx.voice_client.disconnect()
    await ctx.send(embed=discord.Embed(title="👋 **Bye!** Keluar dari voice channel", color=WARNA["music"]))

@bot.command()
async def shuffle(ctx):
    """Acak antrian lagu."""
    queue = get_music_queue(ctx.guild.id)
    if len(queue) < 2:
        return await ctx.send(embed=discord.Embed(title="❌ Minimal 2 lagu di antrian buat diacak!", color=WARNA["gagal"]))
    random.shuffle(queue)
    await ctx.send(embed=discord.Embed(title="🔀 **Antrian Diacak!**", description=f"{len(queue)} lagu telah diacak", color=WARNA["music"]))

@bot.command()
async def loop(ctx):
    """Toggle loop lagu (ulang terus)."""
    status = loop_mode.get(ctx.guild.id, False)
    loop_mode[ctx.guild.id] = not status
    await ctx.send(embed=discord.Embed(
        title="🔁 **Loop**",
        description=f"Loop **{'ON' if not status else 'OFF'}**",
        color=WARNA["sukses"] if not status else WARNA["gagal"]
    ))

@bot.command()
async def autoplay(ctx):
    """Toggle autoplay (putar lagu mirip otomatis)."""
    status = autoplay_mode.get(ctx.guild.id, False)
    autoplay_mode[ctx.guild.id] = not status
    await ctx.send(embed=discord.Embed(
        title="♾️ **Autoplay**",
        description=f"Autoplay **{'ON' if not status else 'OFF'}**\n{'Lagu mirip akan diputar otomatis saat antrian habis' if not status else ''}",
        color=WARNA["sukses"] if not status else WARNA["gagal"]
    ))

@bot.command(aliases=["lirik"])
async def lyrics(ctx, *, query=None):
    """Cari lirik lagu. Contoh: !lyrics naruto blue bird"""
    if not query:
        now = music_nowplaying.get(ctx.guild.id)
        if not now:
            return await ctx.send(embed=discord.Embed(title="❌ Lagi gak ada lagu yang diputar! Ketik `!lyrics <judul>`", color=WARNA["gagal"]))
        query = now["title"]

    await ctx.send(embed=discord.Embed(title="🔍 **Mencari lirik...**", color=WARNA["music"]))

    if " - " in query:
        artist, title = query.split(" - ", 1)
    else:
        artist = ""
        title = query

    async def cari_lyrics(artist, title):
        if artist:
            url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
            async with aiohttp.ClientSession() as s:
                async with s.get(url) as r:
                    if r.status == 200:
                        d = await r.json()
                        return d.get("lyrics", ""), title, artist, None
        url = f"https://api.lyrics.ovh/v1/Unknown/{title}"
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status == 200:
                    d = await r.json()
                    return d.get("lyrics", ""), title, "Unknown", None
        return None, None, None, None

    try:
        lirik, judul, artist, thumb = await cari_lyrics(artist, title)
        if not lirik:
            return await ctx.send(embed=discord.Embed(title="❌ Lirik tidak ditemukan!", color=WARNA["gagal"]))

        if len(lirik) > 4000:
            chunks = [lirik[i:i+4000] for i in range(0, len(lirik), 4000)]
            for j, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=f"📜 **{judul}** — {artist}",
                    description=chunk,
                    color=WARNA["music"]
                )
                embed.set_footer(text=f"Halaman {j+1}/{len(chunks)}")
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title=f"📜 **{judul}** — {artist}",
                description=lirik,
                color=WARNA["music"]
            )
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=discord.Embed(title="❌ Gagal mencari lirik!", description=f"```{e}```", color=WARNA["gagal"]))

# ──────────────────────────────────────────────────────────
# MINI GAMES
# ──────────────────────────────────────────────────────────

class TicTacToeButton(Button):
    def __init__(self, row, col, game_view):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=row)
        self.row_idx = row
        self.col_idx = col
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        game = self.game_view
        if interaction.user.id != game.current_turn:
            return await interaction.response.send_message("Bukan giliran kamu!", ephemeral=True)
        if game.board[self.row_idx][self.col_idx] is not None:
            return await interaction.response.send_message("Kotak sudah terisi!", ephemeral=True)

        game.board[self.row_idx][self.col_idx] = game.symbols[str(interaction.user.id)]
        self.label = game.symbols[str(interaction.user.id)]
        self.disabled = True
        if game.symbols[str(interaction.user.id)] == "❌":
            self.style = discord.ButtonStyle.danger
        else:
            self.style = discord.ButtonStyle.success

        winner = game.check_winner()
        if winner:
            for button in game.children:
                button.disabled = True
            if winner == "seri":
                embed = discord.Embed(title="🤝 **Seri!**", color=WARNA["warning"])
            else:
                user_id = game.player_ids[winner]
                user = bot.get_user(user_id)
                embed = discord.Embed(
                    title=f"🎉 **{winner} Menang!**" if user is None else f"🎉 **{user.name} Menang!**",
                    color=WARNA["sukses"]
                )
            await interaction.response.edit_message(embed=embed, view=self.game_view)
            self.game_view.stop_game()
            return

        game.switch_turn()
        current_user = game.player1 if game.current_turn == game.player1.id else game.player2
        embed = discord.Embed(
            title="🎮 **TicTacToe**",
            description=f"Giliran: **{current_user.mention}** ({game.symbols[str(game.current_turn)]})",
            color=WARNA["game"]
        )
        await interaction.response.edit_message(embed=embed, view=self.game_view)

class TicTacToeView(View):
    def __init__(self, player1, player2):
        super().__init__(timeout=120)
        self.player1 = player1
        self.player2 = player2
        self.board = [[None]*3 for _ in range(3)]
        self.symbols = {str(player1.id): "❌", str(player2.id): "⭕"}
        self.player_ids = {"❌": player1.id, "⭕": player2.id}
        self.current_turn = player1.id
        self.active = True

        for r in range(3):
            for c in range(3):
                self.add_item(TicTacToeButton(r, c, self))

    def check_winner(self):
        for row in self.board:
            if row[0] and row[0] == row[1] == row[2]:
                return row[0]
        for c in range(3):
            if self.board[0][c] and self.board[0][c] == self.board[1][c] == self.board[2][c]:
                return self.board[0][c]
        if self.board[0][0] and self.board[0][0] == self.board[1][1] == self.board[2][2]:
            return self.board[0][0]
        if self.board[0][2] and self.board[0][2] == self.board[1][1] == self.board[2][0]:
            return self.board[0][2]
        if all(all(cell is not None for cell in row) for row in self.board):
            return "seri"
        return None

    def switch_turn(self):
        self.current_turn = self.player2.id if self.current_turn == self.player1.id else self.player1.id

    def stop_game(self):
        self.active = False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

@bot.command(aliases=["ttt", "tictactoe"])
async def tic(ctx, *, opponent: discord.Member):
    """Main TicTacToe lawan teman. Contoh: !tic @user"""
    if opponent.id == ctx.author.id:
        return await ctx.send(embed=discord.Embed(title="❌ Gak bisa main sama diri sendiri!", color=WARNA["gagal"]))
    if opponent.bot:
        return await ctx.send(embed=discord.Embed(title="❌ Gak bisa main sama bot!", color=WARNA["gagal"]))

    view = TicTacToeView(ctx.author, opponent)
    embed = discord.Embed(
        title="🎮 **TicTacToe**",
        description=f"Giliran: **{ctx.author.mention}** (❌)",
        color=WARNA["game"]
    )
    embed.set_footer(text=f"{ctx.author.name} (❌) vs {opponent.name} (⭕)")
    await ctx.send(embed=embed, view=view)

class RPSButton(Button):
    def __init__(self, label, emoji, game_view):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, emoji=emoji, row=0)
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        game = self.game_view
        if interaction.user.id not in (game.player1.id, game.player2.id):
            return await interaction.response.send_message("Bukan permainan kamu!", ephemeral=True)

        user_id = str(interaction.user.id)

        if user_id in game.choices:
            return await interaction.response.send_message("Kamu sudah milih!", ephemeral=True)

        game.choices[user_id] = self.label.lower()
        await interaction.response.defer()

        if len(game.choices) == 2:
            p1_choice = game.choices[str(game.player1.id)]
            p2_choice = game.choices[str(game.player2.id)]

            rules = {"gunting": "kertas", "kertas": "batu", "batu": "gunting"}
            if p1_choice == p2_choice:
                hasil = "🤝 **Seri!**"
                warna = WARNA["warning"]
            elif rules.get(p1_choice) == p2_choice:
                hasil = f"🎉 **{game.player1.mention} Menang!** {p1_choice} > {p2_choice}"
                warna = WARNA["sukses"]
            else:
                hasil = f"🎉 **{game.player2.mention} Menang!** {p2_choice} > {p1_choice}"
                warna = WARNA["sukses"]

            embed = discord.Embed(
                title="✂️ **Hasil RPS!**",
                description=(
                    f"{game.player1.mention}: {p1_choice} {game.emoji_map[p1_choice]}\n"
                    f"{game.player2.mention}: {p2_choice} {game.emoji_map[p2_choice]}\n\n"
                    f"**{hasil}**"
                ),
                color=warna
            )
            for child in self.view.children:
                child.disabled = True
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            embed = discord.Embed(
                title="✂️ **Rock Paper Scissors**",
                description=f"Menunggu {game.player2.mention} memilih...",
                color=WARNA["game"]
            )
            await interaction.message.edit(embed=embed)

class RPSView(View):
    def __init__(self, player1, player2):
        super().__init__(timeout=60)
        self.player1 = player1
        self.player2 = player2
        self.choices = {}
        self.emoji_map = {"batu": "🪨", "kertas": "📄", "gunting": "✂️"}

        self.add_item(RPSButton("Batu", "🪨", self))
        self.add_item(RPSButton("Kertas", "📄", self))
        self.add_item(RPSButton("Gunting", "✂️", self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

@bot.command(aliases=["suit"])
async def rps(ctx, *, opponent: discord.Member):
    """Main suit lawan teman. Contoh: !rps @user"""
    if opponent.id == ctx.author.id:
        return await ctx.send(embed=discord.Embed(title="❌ Gak bisa main sama diri sendiri!", color=WARNA["gagal"]))
    if opponent.bot:
        return await ctx.send(embed=discord.Embed(title="❌ Gak bisa main sama bot!", color=WARNA["gagal"]))

    view = RPSView(ctx.author, opponent)
    embed = discord.Embed(
        title="✂️ **Rock Paper Scissors**",
        description=f"{ctx.author.mention} pilih yuk!",
        color=WARNA["game"]
    )
    embed.set_footer(text="Klik tombol di bawah buat milih")
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=["guess", "tebak"])
async def tebakangka(ctx):
    """Tebak angka 1-100. Bot kasih clue."""
    angka = random.randint(1, 100)
    percobaan = 0

    embed = discord.Embed(
        title="🔢 **Tebak Angka!**",
        description="Aku milih angka 1-100. Tebak pake `!tebak <angka>`\n\n**Kirim tebakanmu di chat!**",
        color=WARNA["game"]
    )
    embed.set_footer(text=f"Dimulai oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

    def cek(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

    while True:
        try:
            msg = await bot.wait_for("message", check=cek, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send(embed=discord.Embed(
                title="⏰ **Waktu Habis!**",
                description=f"Angka yang bener adalah **{angka}**",
                color=WARNA["gagal"]
            ))

        tebak = int(msg.content)
        percobaan += 1

        if tebak == angka:
            embed = discord.Embed(
                title="🎉 **BENAR!**",
                description=f"Kamu berhasil nebak **{angka}** dalam **{percobaan}** percobaan!",
                color=WARNA["sukses"]
            )
            await ctx.send(embed=embed)
            return
        elif tebak < angka:
            await ctx.send(f"⬆️ **Lebih gede** dari {tebak} (percobaan ke-{percobaan})", delete_after=5)
        else:
            await ctx.send(f"⬇️ **Lebih kecil** dari {tebak} (percobaan ke-{percobaan})", delete_after=5)

# ──────────────────────────────────────────────────────────
# LEVELING / XP SYSTEM
# ──────────────────────────────────────────────────────────

xp_cooldowns = {}

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    await bot.process_commands(message)

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    # ── AFK System ──
    conn = sqlite3.connect(DB_PATH)
    try:
        afk_prefixes = tuple(f"{bot.command_prefix}{cmd}" for cmd in ["afk", "away"])
        if not message.content.startswith(afk_prefixes):
            removed = conn.execute(
                "DELETE FROM afk WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            ).rowcount
            conn.commit()
            if removed:
                await message.channel.send(embed=discord.Embed(
                    title="👋 **Selamat Datang Kembali!**",
                    description="Status AFK kamu telah dihapus.",
                    color=WARNA["sukses"]
                ), delete_after=5)

        for mentioned in message.mentions:
            if mentioned.bot:
                continue
            row = conn.execute(
                "SELECT reason, since FROM afk WHERE guild_id = ? AND user_id = ?",
                (guild_id, str(mentioned.id))
            ).fetchone()
            if row:
                reason, since_ts = row
                since = datetime.fromtimestamp(since_ts)
                elapsed = datetime.now() - since
                menit = int(elapsed.total_seconds() // 60)
                if menit < 1:
                    durasi = "beberapa detik"
                elif menit < 60:
                    durasi = f"{menit} menit"
                else:
                    jam = menit // 60
                    menit_sisa = menit % 60
                    durasi = f"{jam} jam {menit_sisa} menit"

                embed = discord.Embed(
                    title="💤 **AFK**",
                    description=f"**{mentioned.display_name}** sedang AFK\n{reason}",
                    color=WARNA["warning"]
                )
                embed.set_footer(text=f"Sudah {durasi} yang lalu")
                await message.channel.send(embed=embed, delete_after=8)
    finally:
        conn.close()

    # ── XP System ──
    now = datetime.now()
    cooldown_key = f"{guild_id}:{user_id}"
    if cooldown_key in xp_cooldowns:
        if now - xp_cooldowns[cooldown_key] < timedelta(seconds=60):
            return

    xp_cooldowns[cooldown_key] = now

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ).fetchone()

        xp = row[0] if row else 0

        old_level, _ = get_level_from_xp(xp)
        xp += random.randint(5, 15)

        if xp > 999999:
            xp = 0

        conn.execute(
            "INSERT OR REPLACE INTO levels (guild_id, user_id, xp, name) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, xp, message.author.name)
        )
        conn.commit()

        new_level, _ = get_level_from_xp(xp)

        if new_level > old_level:
            embed = discord.Embed(
                title="🎉 **LEVEL UP!**",
                description=f"{message.author.mention} naik ke **Level {new_level}**!",
                color=WARNA["level"]
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            await message.channel.send(embed=embed)
    finally:
        conn.close()

@bot.command(aliases=["level", "xp", "lvl"])
async def rank(ctx, *, member: discord.Member = None):
    """Cek level & XP kamu atau member lain."""
    member = member or ctx.author
    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT xp FROM levels WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ).fetchone()

        if row is None:
            return await ctx.send(embed=discord.Embed(
                title=f"ℹ️ {member.display_name}",
                description="Belum punya XP nih. Coba chat dikit!",
                color=WARNA["level"]
            ))

        total_xp = row[0]
        level, sisa_xp = get_level_from_xp(total_xp)
        needed = get_xp_for_level(level)

        all_users = conn.execute(
            "SELECT user_id FROM levels WHERE guild_id = ? ORDER BY xp DESC",
            (guild_id,)
        ).fetchall()
        rank_pos = next((i+1 for i, (uid,) in enumerate(all_users) if uid == user_id), 0)

        bar = "█" * int((sisa_xp / needed) * 10) + "░" * (10 - int((sisa_xp / needed) * 10))

        embed = discord.Embed(
            title=f"📊 **{member.display_name}**",
            color=WARNA["level"]
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🏆 Level", value=level, inline=True)
        embed.add_field(name="📈 XP", value=f"{total_xp:,}", inline=True)
        embed.add_field(name="#️⃣ Peringkat", value=f"#{rank_pos}", inline=True)
        embed.add_field(name="XP Progress", value=f"{bar}\n`{sisa_xp:,} / {needed:,} XP`", inline=False)
        embed.set_footer(text="Chat di server buat dapet XP! (cooldown 60 detik)")
        await ctx.send(embed=embed)
    finally:
        conn.close()

@bot.command(aliases=["lb", "top"])
async def leaderboard(ctx):
    """Top 10 leaderboard XP di server ini."""
    guild_id = str(ctx.guild.id)

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT user_id, xp, name FROM levels WHERE guild_id = ? ORDER BY xp DESC LIMIT 10",
            (guild_id,)
        ).fetchall()

        if not rows:
            return await ctx.send(embed=discord.Embed(title="ℹ️ Belum ada data XP di server ini!", color=WARNA["level"]))

        embed = discord.Embed(
            title=f"🏆 **Leaderboard {ctx.guild.name}**",
            color=WARNA["level"]
        )

        medal = ["🥇", "🥈", "🥉"]
        daftar = ""
        for i, (uid, xp, name) in enumerate(rows):
            level, _ = get_level_from_xp(xp)
            member = ctx.guild.get_member(int(uid))
            display_name = member.display_name if member else name
            icon = medal[i] if i < 3 else f"`{i+1}.`"
            daftar += f"{icon} **{display_name}** • Level {level} ({xp:,} XP)\n"

        embed.description = daftar
        await ctx.send(embed=embed)
    finally:
        conn.close()

# ──────────────────────────────────────────────────────────
# AFK SYSTEM
# ──────────────────────────────────────────────────────────

@bot.command(aliases=["away"])
async def afk(ctx, *, alasan=None):
    """Set status AFK. Contoh: !afk lagi makan"""
    alasan = alasan or "Tidak ada alasan"
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO afk (guild_id, user_id, reason, since) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, alasan, int(datetime.now().timestamp()))
        )
        conn.commit()
    finally:
        conn.close()

    embed = discord.Embed(
        title="💤 **AFK Mode ON**",
        description=f"Alasan: {alasan}",
        color=WARNA["warning"]
    )
    embed.set_footer(text="Ketik pesan untuk menghilangkan status AFK")
    await ctx.send(embed=embed)

# ──────────────────────────────────────────────────────────
# AI CHAT (Groq - Llama 3)
# ──────────────────────────────────────────────────────────

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = None
if GROQ_API_KEY and GROQ_AVAILABLE and GROQ_API_KEY != "isi_api_key_kamu_disini":
    groq_client = Groq(api_key=GROQ_API_KEY)

ai_conversations = {}
AI_MAX_HISTORY = 30

@bot.command(aliases=["ai", "tanya"])
async def ask(ctx, *, prompt):
    """Tanya AI (Llama 3 via Groq). Contoh: !ask apa itu black hole?"""
    if not GROQ_AVAILABLE:
        return await ctx.send(embed=discord.Embed(
            title="❌ groq belum terinstall!",
            description="Jalankan: `pip install groq`",
            color=WARNA["gagal"]
        ))
    if groq_client is None:
        return await ctx.send(embed=discord.Embed(
            title="❌ API Key belum diatur!",
            description="Isi `GROQ_API_KEY` di file `.env`\nDapatkan API key gratis di: https://console.groq.com",
            color=WARNA["gagal"]
        ))

    async with ctx.typing():
        try:
            user_id = str(ctx.author.id)

            if user_id not in ai_conversations:
                ai_conversations[user_id] = []

            messages = [{"role": "system", "content": "Kamu adalah asisten AI yang ramah dan membantu. Jawab dalam Bahasa Indonesia. Jawab dengan singkat, jelas, dan informatif."}]
            for msg in ai_conversations[user_id][-AI_MAX_HISTORY:]:
                messages.append(msg)
            messages.append({"role": "user", "content": prompt})

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=2048,
            )

            reply = response.choices[0].message.content

            ai_conversations[user_id].append({"role": "user", "content": prompt})
            ai_conversations[user_id].append({"role": "assistant", "content": reply})

            if len(ai_conversations[user_id]) > AI_MAX_HISTORY * 2:
                ai_conversations[user_id] = ai_conversations[user_id][-AI_MAX_HISTORY * 2:]

            teks = reply[:4000]
            embed = discord.Embed(
                description=teks,
                color=WARNA["info"]
            )
            embed.set_author(name="🤖 AI Chat", icon_url=bot.user.display_avatar.url)
            embed.set_footer(text=f"{ctx.author.name} • Ketik !resetask untuk reset riwayat")

            if len(reply) > 4000:
                embed.description = teks + "\n\n*...pesan terpotong (max 4000 karakter)*"

            await ctx.send(embed=embed)

        except Exception as e:
            err_msg = str(e)[:500]
            await ctx.send(embed=discord.Embed(
                title="❌ AI Error",
                description=f"```{err_msg}```",
                color=WARNA["gagal"]
            ))

@bot.command(aliases=["resetai", "clearai"])
async def resetask(ctx):
    """Reset riwayat percakapan dengan AI."""
    ai_conversations.pop(str(ctx.author.id), None)
    await ctx.send(embed=discord.Embed(
        title="🔄 **Riwayat Direset**",
        description="Percakapan dengan AI dimulai dari awal.",
        color=WARNA["sukses"]
    ))

# ──────────────────────────────────────────────────────────
# ORIGINAL COMMANDS (updated help)
# ──────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"!help • {len(bot.guilds)} server"
        )
    )
    log_activity(f"ONLINE {bot.user} ({len(bot.guilds)} server)")
    print(f"[ONLINE] {bot.user} sudah online! ({len(bot.guilds)} server)")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="⚠️ Kurang Argumen!",
            description=f"**Cara pakai:** `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`",
            color=WARNA["warning"]
        )
        embed.set_footer(text=f"Ketik !help {ctx.command.name} untuk info lengkap")
        await ctx.send(embed=embed, delete_after=8)
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="❌ Argumen Tidak Valid!",
            description=str(error),
            color=WARNA["gagal"]
        )
        await ctx.send(embed=embed, delete_after=8)
    else:
        log_activity(f"ERROR {ctx.author}: !{ctx.command.name} - {error}")
        embed = discord.Embed(
            title="❌ Terjadi Error!",
            description=f"```{error}```",
            color=WARNA["gagal"]
        )
        await ctx.send(embed=embed, delete_after=10)
        raise error

@bot.command()
async def help(ctx, command_specific=None):
    """Menampilkan menu bantuan."""
    if command_specific:
        cmd = bot.get_command(command_specific)
        if not cmd:
            embed = discord.Embed(
                title="❌ Command Tidak Ditemukan",
                description=f"Command `{command_specific}` gak ada. Coba `!help` untuk lihat semua command.",
                color=WARNA["gagal"]
            )
            return await ctx.send(embed=embed, delete_after=8)

        embed = discord.Embed(
            title=f"📖 !{cmd.name}",
            description=cmd.help or "Tidak ada deskripsi.",
            color=WARNA["info"]
        )
        embed.add_field(name="Cara Pakai", value=f"`!{cmd.name} {cmd.signature}`", inline=False)
        aliases = cmd.aliases
        if aliases:
            embed.add_field(name="Alias", value=", ".join(f"`{a}`" for a in aliases), inline=False)
        embed.set_footer(text=f"Ketik !help untuk daftar semua command")
        return await ctx.send(embed=embed)

    embed = discord.Embed(
        title="🤖 **Botnya Jai**",
        description="Hai! Aku Botnya Jai, siap bantu kamu sehari-hari. Pilih kategori di bawah ya!",
        color=WARNA["main"]
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)

    kategori = {
        "🎵 **Music**": ["play", "pause", "resume", "skip", "stop", "shuffle", "loop", "autoplay", "queue", "nowplaying", "volume", "lyrics", "joinvc", "leavevc"],
        "🎮 **Games**": ["tic", "rps", "tebakangka", "ping", "8ball", "roll", "coinflip", "choose"],
        "📊 **Leveling**": ["rank", "leaderboard"],
        "🤖 **AI**": ["ask", "resetask"],
        "ℹ️ **Info**": ["userinfo", "serverinfo", "avatar", "help"],
        "🛠️ **Utility**": ["say", "poll", "hitungmundur", "halo", "kata", "afk"],
    }

    for nama, cmds in kategori.items():
        daftar = ""
        for cmd_name in cmds:
            cmd = bot.get_command(cmd_name)
            if cmd:
                daftar += f"`!{cmd_name}` — {cmd.help or '-'}\n"
        embed.add_field(name=nama, value=daftar, inline=False)

    embed.set_footer(
        text=f"Diminta oleh {ctx.author.name} • {datetime.now().strftime('%H:%M')}",
        icon_url=ctx.author.display_avatar.url
    )
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    """Cek kecepatan bot."""
    msg = await ctx.send(embed=discord.Embed(title="🏓 Pinging...", color=WARNA["info"]))
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 **Pong!**",
        description=f"📶 **{latency}ms**",
        color=WARNA["sukses"]
    )
    embed.set_footer(text=f"Lebih cepet dari lu mikir 😏")
    await msg.edit(embed=embed)

@bot.command()
async def halo(ctx):
    """Sapa bot, bot sapa balik!"""
    member_count = ctx.guild.member_count if ctx.guild else 1
    embed = discord.Embed(
        title="👋 Halo gaiss!",
        description=(
            f"Halo juga **{ctx.author.name}**! Senang banget ketemu kamu~ 🥳\n\n"
            f"🎉 Kamu anggota ke-**{member_count}** di server ini!"
        ),
        color=WARNA["warning"]
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=["dadu"])
async def roll(ctx, dice="1d6"):
    """Lempar dadu. Contoh: !roll 2d6"""
    try:
        jumlah, sisi = dice.lower().split("d")
        jumlah = int(jumlah)
        sisi = int(sisi)
        if jumlah < 1 or jumlah > 100:
            return await ctx.send(embed=discord.Embed(title="❌ Jumlah dadu maks 100!", color=WARNA["gagal"]))
        if sisi < 2 or sisi > 1000:
            return await ctx.send(embed=discord.Embed(title="❌ Sisi dadu 2-1000!", color=WARNA["gagal"]))
    except:
        return await ctx.send(embed=discord.Embed(title="❌ Format salah! Contoh: `!roll 2d6`", color=WARNA["gagal"]))

    hasil = [random.randint(1, sisi) for _ in range(jumlah)]
    total = sum(hasil)

    embed = discord.Embed(
        title="🎲 **Hasil Dadu!**",
        color=WARNA["oranye"]
    )
    embed.add_field(name="Lemparan", value=", ".join(map(str, hasil)), inline=False)
    if jumlah > 1:
        embed.add_field(name="Total", value=str(total), inline=True)
    embed.add_field(name="Dadu", value=f"{jumlah}d{sisi}", inline=True)
    embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=["bola8", "mintaramal"])
async def eightball(ctx, *, pertanyaan):
    """Tanya magic 8-ball! Contoh: !8ball apakah aku ganteng?"""
    jawaban = random.choice(JAWABAN_8BALL)
    embed = discord.Embed(
        title="🔮 **Magic 8-Ball**",
        color=WARNA["mystic"]
    )
    embed.add_field(name="❓ Pertanyaan", value=pertanyaan, inline=False)
    embed.add_field(name="✨ Jawaban", value=jawaban, inline=False)
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3113/3113022.png")
    embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=["pilih", "pick"])
async def choose(ctx, *, opsi):
    """Pilih salah satu opsi. Contoh: !choose makan | tidur | main"""
    pilihan = [o.strip() for o in opsi.split("|")]
    if len(pilihan) < 2:
        return await ctx.send(embed=discord.Embed(title="❌ Minimal 2 opsi! Pakai `|` sebagai pemisah.", color=WARNA["gagal"]))
    hasil = random.choice(pilihan)
    embed = discord.Embed(
        title="🤔 **Bingung? Biar aku yang pilih!**",
        color=WARNA["tosca"]
    )
    embed.add_field(name="Opsi", value="\n".join(f"{i+1}. {p}" for i, p in enumerate(pilihan)), inline=False)
    embed.add_field(name="✅ Aku pilih", value=f"**{hasil}**", inline=False)
    embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, *, member: discord.Member = None):
    """Lihat avatar member. Contoh: !avatar @user"""
    member = member or ctx.author
    embed = discord.Embed(
        title=f"🖼️ Avatar {member.display_name}",
        color=member.color if member.color.value != 0 else WARNA["biru"]
    )
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=f"Klik kanan > save image | Diminta oleh {ctx.author.name}")
    await ctx.send(embed=embed)

@bot.command(aliases=["info", "whois"])
async def userinfo(ctx, *, member: discord.Member = None):
    """Lihat info detail member. Contoh: !userinfo @user"""
    member = member or ctx.author

    roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
    roles_str = ", ".join(roles) if roles else "Tidak ada role"

    embed = discord.Embed(
        title=f"👤 **{member.display_name}**",
        color=member.color if member.color.value != 0 else WARNA["biru"],
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🔹 Nama Global", value=member.name, inline=True)
    embed.add_field(name="🆔 ID", value=member.id, inline=True)
    embed.add_field(name="📆 Akun Dibuat", value=member.created_at.strftime("%d %b %Y"), inline=True)
    embed.add_field(name="📥 Join Server", value=member.joined_at.strftime("%d %b %Y"), inline=True)
    embed.add_field(name="🎭 Status", value=str(member.status).title(), inline=True)
    embed.add_field(name=f"📜 Roles ({len(roles)})", value=roles_str, inline=False)
    embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=["server", "guildinfo"])
async def serverinfo(ctx):
    """Lihat info detail server."""
    guild = ctx.guild
    if not guild:
        return await ctx.send(embed=discord.Embed(title="❌ Ini bukan server!", color=WARNA["gagal"]))

    boosts = guild.premium_subscription_count
    boost_tier = guild.premium_tier

    embed = discord.Embed(
        title=f"🏰 **{guild.name}**",
        color=WARNA["merah"]
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="🆔 ID Server", value=guild.id, inline=True)
    pemilik = guild.owner.mention if guild.owner else f"<@{guild.owner_id}>"
    embed.add_field(name="👑 Owner", value=pemilik, inline=True)
    embed.add_field(name="📅 Dibuat", value=guild.created_at.strftime("%d %b %Y"), inline=True)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="💬 Channels", value=f"{len(guild.text_channels)} Text | {len(guild.voice_channels)} Voice", inline=True)
    embed.add_field(name="🚀 Boost", value=f"Tier {boost_tier} ({boosts} boost)", inline=True)
    embed.add_field(name="😎 Emoji", value=len(guild.emojis), inline=True)
    embed.add_field(name="📜 Roles", value=len(guild.roles), inline=True)
    if guild.banner:
        embed.set_image(url=guild.banner.url)
    embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def say(ctx, *, pesan):
    """Bot ngomong pake embed. Contoh: !say Hai semua!"""
    embed = discord.Embed(
        description=pesan,
        color=ctx.author.color if ctx.author.color.value != 0 else WARNA["info"]
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def poll(ctx, *, arg):
    """Buat polling. Contoh: !poll Film apa yang bagus? | A | B | C"""
    parts = [p.strip() for p in arg.split("|")]
    if len(parts) < 2:
        return await ctx.send(embed=discord.Embed(title="❌ Pakai format: `!poll pertanyaan | opsi1 | opsi2`", color=WARNA["gagal"]))

    pertanyaan = parts[0]
    opsi = parts[1:]
    if len(opsi) > 10:
        return await ctx.send(embed=discord.Embed(title="❌ Maksimal 10 opsi!", color=WARNA["gagal"]))
    if len(opsi) < 2:
        return await ctx.send(embed=discord.Embed(title="❌ Minimal 2 opsi!", color=WARNA["gagal"]))

    emoji_angka = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]

    deskripsi = "\n\n".join(f"{emoji_angka[i]} {opsi[i]}" for i in range(len(opsi)))
    embed = discord.Embed(
        title=f"📊 **{pertanyaan}**",
        description=deskripsi,
        color=WARNA["sukses"]
    )
    embed.set_footer(text=f"Poll oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    msg = await ctx.send(embed=embed)

    for i in range(len(opsi)):
        await msg.add_reaction(emoji_angka[i])

@bot.command(aliases=["quotes", "katabijak"])
async def kata(ctx):
    """Dapatkan kata bijak random."""
    quote = random.choice(KATA_BIJAK)
    embed = discord.Embed(
        description=f"*“{quote}”*",
        color=WARNA["mystic"]
    )
    embed.set_author(name="💡 Kata Bijak Hari Ini")
    embed.set_footer(text=f"Untuk {ctx.author.name} • semangat terus ya! 💪", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=["cointoss", "toss"])
async def coinflip(ctx):
    """Lempar koin. Hasil: Head atau Tail."""
    hasil = random.choice(["**Kepala (Head)** 🪙", "**Ekor (Tail)** 🪙"])
    embed = discord.Embed(
        title="🪙 **Lempar Koin!**",
        description=f"Hasilnya: {hasil}",
        color=WARNA["warning"]
    )
    embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=["timer", "countdown"])
async def hitungmundur(ctx, detik: int):
    """Hitung mundur. Contoh: !hitungmundur 10"""
    if detik < 1 or detik > 300:
        return await ctx.send(embed=discord.Embed(title="❌ Maksimal 300 detik (5 menit)!", color=WARNA["gagal"]))

    embed = discord.Embed(
        title=f"⏳ **Hitung Mundur: {detik} detik**",
        color=WARNA["merah"]
    )
    msg = await ctx.send(embed=embed)

    for sisa in range(detik, 0, -1):
        embed = discord.Embed(
            title=f"⏳ **Hitung Mundur: {sisa} detik**",
            color=WARNA["oranye"] if sisa > 5 else WARNA["merah"]
        )
        await msg.edit(embed=embed)
        await asyncio.sleep(1)

    embed = discord.Embed(
        title="⏰ **WAKTU HABIS!** 🔔",
        description=f"{ctx.author.mention} hitung mundur selesai!",
        color=WARNA["sukses"]
    )
    embed.set_footer(text=f"Diminta oleh {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await msg.edit(embed=embed)

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ Token tidak ditemukan! Buat file .env dan isi DISCORD_TOKEN=token_kamu")
    exit(1)

init_db()
bot.run(TOKEN)
