# 🤖 Botnya Jai

Bot Discord multifungsi dengan fitur **Music Player**, **Mini Games**, **Leveling/XP**, **AI Chat**, **AFK System**, dan banyak lagi!

## 🚀 Fitur

| Kategori | Deskripsi |
|---|---|
| 🎵 **Music** | Putar lagu dari YouTube, atur volume, shuffle, loop, autoplay, cari lirik |
| 🎮 **Games** | TicTacToe, Rock Paper Scissors, Tebak Angka, 8-Ball, Dadu, Koin |
| 🤖 **AI Chat** | Tanya AI pake Llama 3 (Groq) — gratis, cepet, paham Bahasa Indonesia |
| 📊 **Leveling** | XP otomatis dari chat, level up, leaderboard server |
| 💤 **AFK** | Set status AFK, notif otomatis saat di-mention |
| ℹ️ **Info** | Info user, info server, avatar, help |
| 🛠️ **Utility** | Polling, countdown timer, kata bijak, echo, sapaan |

## 📋 Daftar Command

### 🎵 Music
| Command | Alias | Fungsi |
|---|---|---|
| `!play <lagu1 \| lagu2>` | `!p`, `!nyanyi` | Putar lagu dari YouTube (bisa multi-query dengan `\|`) |
| `!pause` | — | Jeda lagu |
| `!resume` | — | Lanjutkan lagu |
| `!skip` | `!next`, `!s` | Skip ke lagu berikutnya |
| `!stop` | — | Stop music & clear queue |
| `!shuffle` | — | Acak antrian lagu |
| `!loop` | — | Toggle loop (ulang terus) |
| `!autoplay` | — | Toggle autoplay (putar lagu mirip otomatis) |
| `!queue` | `!q`, `!antrian` | Lihat antrian lagu |
| `!nowplaying` | `!np`, `!lagu` | Lihat lagu yang sedang diputar |
| `!volume <0-100>` | `!v`, `!vol` | Atur volume |
| `!lyrics [judul]` | `!lirik` | Cari lirik lagu |
| `!joinvc` | `!join`, `!masuk` | Join voice channel |
| `!leavevc` | `!leave`, `!keluar` | Keluar dari voice channel |

### 🎮 Games
| Command | Alias | Fungsi |
|---|---|---|
| `!tic @user` | `!ttt`, `!tictactoe` | Main TicTacToe lawan teman (pake tombol) |
| `!rps @user` | `!suit` | Rock Paper Scissors lawan teman |
| `!tebakangka` | `!guess`, `!tebak` | Tebak angka 1-100 |
| `!ping` | — | Cek kecepatan respon bot |
| `!8ball <pertanyaan>` | `!bola8`, `!mintaramal` | Tanya magic 8-ball |
| `!roll [XdY]` | `!dadu` | Lempar dadu (contoh: `!roll 2d6`) |
| `!coinflip` | `!cointoss`, `!toss` | Lempar koin |
| `!choose <a \| b \| c>` | `!pilih`, `!pick` | Pilih salah satu opsi random |

### 🤖 AI
| Command | Alias | Fungsi |
|---|---|---|
| `!ask <pertanyaan>` | `!ai`, `!tanya` | Tanya AI (Llama 3) — paham Bahasa Indonesia |
| `!resetask` | `!resetai`, `!clearai` | Reset riwayat percakapan dengan AI |

### 📊 Leveling
| Command | Alias | Fungsi |
|---|---|---|
| `!rank [@user]` | `!level`, `!xp`, `!lvl` | Cek level & XP (progress bar) |
| `!leaderboard` | `!lb`, `!top` | Top 10 leaderboard server |

XP otomatis bertambah setiap kali chat (cooldown 60 detik). Data disimpan di **SQLite**.

### 💤 AFK
| Command | Alias | Fungsi |
|---|---|---|
| `!afk [alasan]` | `!away` | Set status AFK (otomatis hilang saat kirim pesan) |

Saat ada yang mention user AFK, bot akan ngasih notifikasi otomatis.

### ℹ️ Info
| Command | Alias | Fungsi |
|---|---|---|
| `!help [command]` | — | Tampilkan menu bantuan |
| `!userinfo [@user]` | `!info`, `!whois` | Info detail member |
| `!serverinfo` | `!server`, `!guildinfo` | Info detail server |
| `!avatar [@user]` | — | Lihat avatar user |

### 🛠️ Utility
| Command | Alias | Fungsi |
|---|---|---|
| `!say <pesan>` | — | Bot ngomong pake embed |
| `!poll <q \| a \| b>` | — | Buat polling dengan reaksi |
| `!hitungmundur <detik>` | `!timer`, `!countdown` | Hitung mundur (max 300 detik) |
| `!halo` | — | Bot sapa balik |
| `!kata` | `!quotes`, `!katabijak` | Kata bijak random |

## 🔧 Instalasi

### Prasyarat
- Python 3.10+
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- FFmpeg (untuk music player)
- Groq API Key ([Groq Console](https://console.groq.com)) — untuk AI Chat

### Langkah-langkah

1. **Clone repositori**
```bash
git clone <repo-url>
cd Bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Buat file `.env`**
```env
DISCORD_TOKEN=token_discord_kamu
GROQ_API_KEY=gsk_kamu_dari_groq
```

4. **Jalankan bot**
```bash
python bot.py
```

## 📦 Dependencies
| Package | Kegunaan |
|---|---|
| `discord.py` | Library Discord API |
| `yt-dlp` | Streaming audio dari YouTube |
| `PyNaCl` | Voice channel support |
| `davey` | Voice library (discord.py 2.7+) |
| `aiohttp` | HTTP requests (untuk lyrics) |
| `python-dotenv` | Load environment variables |
| `groq` | AI Chat (Llama 3 via Groq API) |
| `sqlite3` | Database leveling & AFK (built-in Python) |

## 🗄️ Database

Bot menggunakan **SQLite** (`data/levels.db`) untuk menyimpan:
- Data leveling & XP (tabel `levels`)
- Data AFK (tabel `afk`)

Migrasi otomatis dari JSON ke SQLite saat pertama kali bot dijalankan.

## ⚠️ Catatan
- Bot menggunakan prefix `!`
- Fitur music player membutuhkan FFmpeg terinstall di sistem
- Leveling XP memiliki cooldown 60 detik per user per server
- Maksimal 10 lagu sekali request
- Command `!loop` dan `!autoplay` aktif per server
- AI Chat menggunakan model **Llama 3.3 70B** via Groq (gratis, 30 req/menit)
- AFK otomatis hilang saat user mengirim pesan di server mana pun
