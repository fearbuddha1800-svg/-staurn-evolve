---
slug: agent-reports.scan-inventory
type: note
graph: gitnexus
---

# FULL CHANNEL SWEEP - inventory + cheap triage (SCAN)

_generated 2026-11-03T06:27:31.570000+00:00 · engine: `channel_verify3.py` (read-only) · full data: `scan-inventory.json` · Telegram ran on `telethon-scan.session`, a sqlite-backup copy of the live `telethon.session` (live session never connected, never written)_

## Method

- Inventory: `iter_dialogs(limit=None)` AND `iter_dialogs(limit=None, archived=True)`, deduped by id - main folder AND archive.
- Excluded: bots (entity bot flag / GMGN* / BotFather / @hermes_*), the account's own chats+channels (creator flag, Saved Messages) and the relay's own output channel 'Signal Relay Feed' (`-1004403985547`).
- Triage: last 200 messages per chat, every text through the relay's own `parser.parse_signal` + `ai_filter.looks_like_results` (no MT5, no network writes).
- **complete** = the proven pipeline's keep-filter on this window: non-recap ('tp hit'/'pips' skipped, counted as `recaps`), parse_ok, non-manage, has SL, >=1 TP, numeric entry. `raw` adds the same count WITHOUT the recap screen. `ai-recap` counts `looks_like_results` hits (wider net).
- `sig/day` = complete * 86400 / window-seconds (window floored at 1h). Ranked by complete -> parse rate (parse_ok/is_signal) -> freshness (newest message).

Dialogs inventoried: **134** - excluded **15**, triaged **119** (candidates for deep verification, complete >= 8: **19**).

## Excluded dialogs

| chat | id | type | archived | reason |
|---|---:|---|---|---|
| V01D | 8346808121 | bot | no | bot: @hermes_ttncfvuy66hylfz6_bot |
| Signal Relay Feed | -1004403985547 | channel | no | own: Signal Relay Feed (relay output channel) |
| mofo | 8846383371 | bot | no | bot: @mofocopytradingbot |
| GMGN BSC Bot | 7007671547 | bot | no | bot: @GMGN_bsc_bot |
| 💎GMGN Degen Group - Official | -1002065600367 | bot | no | bot (username pattern): @gmgnai |
| Tyl Trading 📊 | 7313897414 | bot | yes | bot: @Tyltradingbot |
| Tyl vip | 8428734335 | bot | yes | bot: @Tylvipbot |
| Trade | 7421876631 | bot | yes | bot: @TradeTechSecretsBot |
| MAX + | PO AI SIGNAL BOT | 8779167515 | bot | yes | bot: @TradeXMaxPlusBot |
| GMGN.AI | 6887194564 | bot | no | bot: @gmgnaibot |
| GMGN Bot | 8709223511 | bot | no | bot: @GMGNUSBot |
| TrADE X GO + | Ai Signal Bot | 8269031634 | bot | yes | bot: @TradeXGoPlusBot |
| NousHostedHermesBot | 8728920784 | bot | yes | bot: @NousHostedHermesBot |
| Walt (ex. Wallet) | 1985737506 | bot | yes | bot: @Walt (ex. Wallet) |
| BotFather | 93372553 | bot | no | bot: @BotFather |

## Triage table (all swept chats, ranked)

| # | chat | id | type | arch | msgs | complete | raw | is_sig | parse_ok | rate | manage | recaps | ai-recap | media | sig/day | last message (UTC) | err |
|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 51 | @BD_Trading_Bot | -1002002553536 | channel | - | 200 | 0 | 0 | 0 | 0 | - | 0 | 0 | 90 | 0 | 0.00 |  |  |
| 52 | QUOTEX Live SIGNALS 🤖📊 | -1001820088359 | channel | - | 200 | 0 | 0 | 90 | 0 | 0.00 | 0 | 0 | 185 | 0 | 0.00 |  |  |
| 53 | Technical Avi Family | -1001367786629 | channel | - | 200 | 0 | 0 | 31 | 0 | 0.00 | 4 | 0 | 45 | 48 | 0.00 |  |  |
| 54 | Modern Trading 🧿 | -1001486048381 | channel | - | 200 | 0 | 0 | 10 | 0 | 0.00 | 9 | 0 | 62 | 94 | 0.00 |  |  |
| 55 | Quotex_SuperBot | -1001728487830 | channel | - | 200 | 0 | 0 | 0 | 0 | - | 0 | 0 | 77 | 0 | 0.00 |  |  |
| 11 | 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐕𝐕𝐈𝐏 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002647890905 | channel | A | 200 | 19 | 19 | 49 | 48 | 0.98 | 0 | 21 | 76 | 65 | 0.71 |  |  |
| 56 | Trading Binomo Signals Tips | -1001088440481 | channel | - | 200 | 0 | 0 | 19 | 0 | 0.00 | 17 | 0 | 106 | 17 | 0.00 |  |  |
| 57 | The Vault [CHAT] | -1003828962121 | megagroup | A | 40 | 0 | 0 | 9 | 0 | 0.00 | 0 | 0 | 3 | 24 | 0.00 |  |  |
| 58 | Intelligent Trading Signals | -1001346757271 | channel | - | 200 | 0 | 0 | 11 | 0 | 0.00 | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 59 | SignalProvider Contact | 1689672021 | user | - | 3 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 42 | VasilyTrader (Free Forex Signals) | -1001169143349 | channel | - | 200 | 1 | 1 | 73 | 1 | 0.01 | 34 | 3 | 37 | 29 | 0.04 |  |  |
| 60 | PLATINUM .PICKS. | -1002477522071 | channel | A | 200 | 0 | 0 | 1 | 0 | 0.00 | 0 | 0 | 72 | 36 | 0.00 |  |  |
| 61 | Trading Crypto Bitcoin Signals | -1001919848888 | channel | - | 200 | 0 | 0 | 10 | 0 | 0.00 | 9 | 0 | 76 | 32 | 0.00 |  |  |
| 62 | TYL - TRADING 📊🚀 | -1002281357812 | channel | - | 200 | 0 | 0 | 32 | 0 | 0.00 | 0 | 0 | 91 | 90 | 0.00 |  |  |
| 16 | Gold Signals Daily 🔔🏆 | -1003762554260 | channel | - | 200 | 11 | 11 | 62 | 53 | 0.85 | 5 | 45 | 112 | 66 | 0.88 |  |  |
| 63 | 𝒀𝑶𝑶 𝑩𝑰𝑵𝑨𝑹𝒀 𝑻𝑹𝑨𝑫𝑰𝑵𝑮🚦 | -1001721537054 | channel | - | 200 | 0 | 0 | 5 | 0 | 0.00 | 4 | 0 | 79 | 70 | 0.00 |  |  |
| 64 | Whale Sniper | -1001127580919 | channel | - | 200 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 48 | Trading Puzzles | -1001376688947 | channel | - | 200 | 0 | 0 | 90 | 14 | 0.16 | 59 | 4 | 125 | 16 | 0.00 |  |  |
| 29 | 𝑿𝑨𝑼𝑼𝑺𝑫 𝑭𝑹𝑬𝑬 𝑺𝑰𝑮𝑵𝑨𝑳𝑺 | -1002165799093 | channel | - | 200 | 3 | 3 | 44 | 20 | 0.46 | 5 | 129 | 5 | 1 | 0.16 |  |  |
| 13 | SureShot GOLD | -1001588519179 | channel | - | 200 | 17 | 17 | 87 | 17 | 0.20 | 61 | 101 | 105 | 22 | 0.95 |  |  |
| 19 | Gold Scalping - EdgeTrade 👑 | -1001988895125 | channel | - | 200 | 8 | 8 | 49 | 9 | 0.18 | 32 | 20 | 67 | 78 | 1.17 |  |  |
| 65 | MARKET ANALYSIS | -1001256188341 | channel | - | 200 | 0 | 0 | 11 | 0 | 0.00 | 8 | 0 | 22 | 70 | 0.00 |  |  |
| 43 | HIRN SIGNALS v7.8 | -1001248393106 | channel | - | 200 | 0 | 0 | 46 | 41 | 0.89 | 5 | 0 | 146 | 1 | 0.00 |  |  |
| 27 | Xauusd Trading Signals | -1003576321949 | channel | - | 200 | 4 | 4 | 45 | 5 | 0.11 | 39 | 52 | 42 | 70 | 0.58 |  |  |
| 66 | Simple Forex Tools | -1002073061621 | channel | A | 200 | 0 | 0 | 53 | 0 | 0.00 | 45 | 1 | 61 | 111 | 0.00 |  |  |
| 41 | TopTradingSignals(Best Forex & Gold  | -1001196272579 | channel | - | 200 | 1 | 1 | 115 | 32 | 0.28 | 2 | 16 | 67 | 9 | 0.03 |  |  |
| 6 | 𝑋𝐴𝑈𝑈𝑆𝐷 𝑇𝑅𝐴𝐷𝐼𝑁𝐺 𝑀𝐴𝑆𝑇𝐸𝑅 | -1002010239852 | channel | - | 200 | 29 | 29 | 36 | 36 | 1.00 | 0 | 70 | 129 | 28 | 0.69 |  |  |
| 10 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1001601213792 | channel | - | 200 | 20 | 20 | 78 | 75 | 0.96 | 1 | 55 | 89 | 58 | 1.12 |  |  |
| 7 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002620653001 | channel | - | 200 | 24 | 24 | 92 | 91 | 0.99 | 1 | 67 | 99 | 27 | 1.85 |  |  |
| 67 | Arman Shaban Trading © | -1001158704403 | channel | - | 200 | 0 | 0 | 46 | 0 | 0.00 | 24 | 19 | 73 | 0 | 0.00 |  |  |
| 23 | Forex GDP - Free Signals | -1001713690419 | channel | - | 200 | 5 | 5 | 6 | 5 | 0.83 | 1 | 5 | 155 | 34 | 0.92 |  |  |
| 21 | FX PREMIERE VIP GOLD BTC SIGNALS | -1001912261779 | channel | - | 200 | 6 | 6 | 7 | 6 | 0.86 | 1 | 4 | 155 | 34 | 1.17 |  |  |
| 12 | 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 𝐓𝐄𝐀𝐌 | -1003924380674 | channel | - | 200 | 17 | 17 | 20 | 18 | 0.90 | 2 | 41 | 73 | 57 | 2.45 |  |  |
| 15 | 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002520344727 | channel | - | 200 | 15 | 15 | 18 | 15 | 0.83 | 3 | 38 | 68 | 45 | 2.47 |  |  |
| 47 | Gold Trader Alliance 🔔 | -1001708442298 | channel | - | 200 | 0 | 5 | 59 | 14 | 0.24 | 12 | 38 | 68 | 66 | 0.00 |  |  |
| 46 | Easy Forex 👑 OFFICIAL CHANNEL | -1001284268486 | channel | - | 200 | 0 | 13 | 50 | 13 | 0.26 | 10 | 61 | 55 | 78 | 0.00 |  |  |
| 68 | TANMAY TRADING | -1001728134997 | channel | - | 200 | 0 | 0 | 8 | 0 | 0.00 | 8 | 0 | 93 | 107 | 0.00 |  |  |
| 24 | 🎈Nova Scalper Channel™.🎈 | -1001895595355 | channel | - | 200 | 5 | 6 | 40 | 13 | 0.33 | 9 | 50 | 94 | 39 | 0.37 |  |  |
| 69 | TrADE X (POCKET OPTION) | -1002011325214 | channel | A | 200 | 0 | 0 | 48 | 0 | 0.00 | 2 | 0 | 10 | 75 | 0.00 |  |  |
| 70 | MQL5 Algo Trading | -1001904158438 | channel | A | 200 | 0 | 0 | 123 | 0 | 0.00 | 99 | 7 | 33 | 0 | 0.00 |  |  |
| 9 | 𝙱𝚎𝚜𝚝 𝚂𝚒𝚐𝚗𝚊𝚕 𝙵𝚘𝚛𝚎𝚡 | -1002369502254 | channel | - | 200 | 21 | 21 | 115 | 102 | 0.89 | 12 | 91 | 114 | 15 | 0.79 |  |  |
| 71 | TRADING LEGEND F&O | -1001616926726 | channel | - | 200 | 0 | 0 | 7 | 0 | 0.00 | 6 | 1 | 9 | 114 | 0.00 |  |  |
| 25 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐓𝐑𝐀𝐃𝐈𝐍𝐆 𝐌𝐀𝐒𝐓𝐄𝐑𝐒 | -1002698908514 | channel | A | 200 | 4 | 4 | 72 | 65 | 0.90 | 0 | 74 | 110 | 46 | 0.15 |  |  |
| 31 | Smith 1000Pips Gold Channel | -1002041442343 | channel | - | 200 | 3 | 3 | 33 | 6 | 0.18 | 22 | 27 | 21 | 82 | 0.64 |  |  |
| 72 | Pocket Trading Signals | -1001674492582 | channel | - | 200 | 0 | 0 | 8 | 0 | 0.00 | 8 | 0 | 22 | 48 | 0.00 |  |  |
| 14 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐏𝐑𝐎 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002692333123 | channel | - | 200 | 16 | 16 | 67 | 55 | 0.82 | 0 | 36 | 75 | 49 | 0.90 |  |  |
| 4 | Asterra Gold | -1003751867978 | channel | - | 200 | 34 | 34 | 54 | 35 | 0.65 | 14 | 39 | 96 | 6 | 0.79 |  |  |
| 73 | [ 𝐌𝐇𝐁 ] 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002065653037 | channel | - | 200 | 0 | 0 | 5 | 0 | 0.00 | 1 | 0 | 67 | 93 | 0.00 |  |  |
| 74 | Olymptrade signals | -1001867256305 | channel | - | 200 | 0 | 0 | 0 | 0 | - | 0 | 0 | 30 | 0 | 0.00 |  |  |
| 75 | QUOTEX NON MTG BOT | -1002073455294 | channel | - | 200 | 0 | 0 | 11 | 0 | 0.00 | 1 | 1 | 146 | 33 | 0.00 |  |  |
| 76 | ELITE TRADING BANGLADESH ♤ | -1002024723944 | channel | - | 200 | 0 | 0 | 2 | 0 | 0.00 | 0 | 0 | 65 | 1 | 0.00 |  |  |
| 77 | FTO (READ BIO) | -1002759257576 | channel | A | 31 | 0 | 0 | 6 | 0 | 0.00 | 3 | 0 | 0 | 3 | 0.00 |  |  |
| 3 | GOLD FOREX SIGNALS VIP | -1003196282951 | channel | - | 200 | 39 | 39 | 89 | 39 | 0.44 | 13 | 49 | 74 | 25 | 3.40 |  |  |
| 78 | Gentle Binary Trading - GBT | -1001822205958 | channel | - | 200 | 0 | 0 | 5 | 0 | 0.00 | 5 | 0 | 63 | 78 | 0.00 |  |  |
| 37 | ProSignalsFx(Gold And Forex) | -1001485077759 | channel | - | 200 | 2 | 7 | 129 | 30 | 0.23 | 27 | 32 | 161 | 6 | 0.06 |  |  |
| 44 | GOLD Trader Dan | -1001095525244 | channel | - | 200 | 0 | 0 | 18 | 13 | 0.72 | 2 | 19 | 51 | 51 | 0.00 |  |  |
| 79 | Signal8 | -1003629327586 | channel | - | 106 | 0 | 0 | 11 | 0 | 0.00 | 2 | 0 | 13 | 23 | 0.00 |  |  |
| 80 | Quotex Guru🎯 | -1001501043947 | channel | - | 200 | 0 | 0 | 1 | 0 | 0.00 | 1 | 0 | 36 | 73 | 0.00 |  |  |
| 38 | SignalProvider (Free Forex Trading S | -1001469931329 | channel | - | 200 | 2 | 2 | 124 | 14 | 0.11 | 35 | 50 | 59 | 16 | 0.06 |  |  |
| 2 | UnitedSignals (Best Forex Signals) | -1001215049720 | channel | - | 200 | 42 | 42 | 86 | 42 | 0.49 | 24 | 26 | 58 | 9 | 1.51 |  |  |
| 81 | 🚀 𝗤𝘂𝗮𝗻𝘁𝘂𝗺 𝗦𝗶𝗴𝗻𝗮𝗹 🔮 | -1001823538129 | channel | - | 200 | 0 | 0 | 1 | 0 | 0.00 | 1 | 0 | 101 | 45 | 0.00 |  |  |
| 82 | Certified Picks | -1003884507657 | channel | A | 200 | 0 | 0 | 10 | 0 | 0.00 | 6 | 0 | 120 | 0 | 0.00 |  |  |
| 26 | Grow Trading | -1001920020352 | channel | - | 200 | 4 | 4 | 10 | 4 | 0.40 | 5 | 1 | 12 | 56 | 1.15 |  |  |
| 28 | Serezha Calls 😱 | -1002354736142 | channel | - | 200 | 3 | 3 | 56 | 47 | 0.84 | 8 | 7 | 71 | 5 | 0.04 |  |  |
| 40 | 🌸AnabelSignals🌸 Best Free Forex & Go | -1001785197109 | channel | - | 200 | 1 | 1 | 121 | 90 | 0.74 | 1 | 20 | 19 | 15 | 0.03 |  |  |
| 83 | TRADER J FOREX CLUB | -1004446195461 | channel | - | 200 | 0 | 0 | 5 | 0 | 0.00 | 5 | 1 | 25 | 59 | 0.00 |  |  |
| 22 | Scalper Gold Nexus 💰 | -1001540535352 | channel | - | 200 | 6 | 6 | 42 | 8 | 0.19 | 18 | 22 | 55 | 58 | 1.11 |  |  |
| 84 | Lingrid Forex Signals | -1001189068380 | channel | - | 200 | 0 | 0 | 56 | 0 | 0.00 | 15 | 50 | 114 | 63 | 0.00 |  |  |
| 45 | ❗️EliteTradingSignals❗️(Free Gold Fo | -1001662267019 | channel | - | 200 | 0 | 0 | 125 | 52 | 0.42 | 28 | 52 | 86 | 0 | 0.00 |  |  |
| 85 | GoldViewFX | -1001465548315 | channel | - | 200 | 0 | 0 | 17 | 0 | 0.00 | 10 | 10 | 74 | 1 | 0.00 |  |  |
| 86 | Trader J | -1002064087930 | channel | - | 200 | 0 | 0 | 0 | 0 | - | 0 | 0 | 15 | 123 | 0.00 |  |  |
| 1 | Gold Signals VIP (XAUUSD FOREX) | -1001868019139 | channel | - | 200 | 59 | 59 | 138 | 59 | 0.43 | 27 | 5 | 109 | 34 | 1.75 |  |  |
| 39 | Forex GDP - Free Signals | -1001175463265 | channel | - | 200 | 2 | 2 | 72 | 2 | 0.03 | 41 | 0 | 187 | 5 | 0.01 |  |  |
| 50 | R. Linda Trading | -1001746260985 | channel | - | 200 | 0 | 0 | 111 | 1 | 0.01 | 29 | 40 | 173 | 7 | 0.00 |  |  |
| 17 | XAUUSD GOLD SIGNALS | -1003376522019 | megagroup | - | 200 | 9 | 9 | 26 | 26 | 1.00 | 0 | 37 | 57 | 87 | 0.23 |  |  |
| 20 | FOREX GOLD SIGNALS XAUUSD | -1003723702011 | channel | - | 200 | 7 | 7 | 22 | 21 | 0.95 | 1 | 37 | 59 | 90 | 0.18 |  |  |
| 8 | 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002639725270 | channel | A | 200 | 21 | 21 | 38 | 38 | 1.00 | 0 | 57 | 88 | 48 | 0.86 |  |  |
| 49 | OlympTrade English | -1001591220161 | channel | - | 200 | 0 | 0 | 40 | 1 | 0.03 | 18 | 0 | 57 | 76 | 0.00 |  |  |
| 87 | NON MTG LIVE SIGNAL'S (QUOTEX) | -1001879802707 | channel | - | 200 | 0 | 0 | 23 | 0 | 0.00 | 0 | 0 | 124 | 25 | 0.00 |  |  |
| 88 | MyLive Trading | -1001438639695 | channel | - | 200 | 0 | 0 | 11 | 0 | 0.00 | 11 | 0 | 87 | 16 | 0.00 |  |  |
| 89 | 𝗙𝗜𝗥𝗘 𝗧𝗥𝗔𝗗𝗜𝗡𝗚 𝗕𝗗 | -1001936292992 | channel | - | 200 | 0 | 0 | 2 | 0 | 0.00 | 0 | 0 | 94 | 32 | 0.00 |  |  |
| 18 | Christopher Alan Harrison💪 | -1001932578394 | channel | - | 200 | 8 | 8 | 65 | 19 | 0.29 | 2 | 121 | 137 | 0 | 0.10 |  |  |
| 32 | Gold Signals (Free) | -1003022356169 | channel | - | 200 | 2 | 14 | 32 | 14 | 0.44 | 17 | 31 | 22 | 140 | 0.11 |  |  |
| 33 | Gold Xauusd Trader Signals | -1003011435611 | channel | - | 200 | 2 | 14 | 32 | 14 | 0.44 | 17 | 31 | 22 | 140 | 0.11 |  |  |
| 34 | Xauusd Trading Signals (Free) | -1003034749723 | channel | - | 200 | 2 | 14 | 32 | 14 | 0.44 | 17 | 31 | 22 | 140 | 0.11 |  |  |
| 35 | XAUUSD GOLD SIGNALS ®️ | -1003114012204 | channel | - | 200 | 2 | 14 | 32 | 14 | 0.44 | 17 | 31 | 22 | 140 | 0.11 |  |  |
| 36 | Forex Trading Signals (Free) | -1003811991226 | channel | - | 200 | 2 | 14 | 32 | 14 | 0.44 | 17 | 31 | 22 | 140 | 0.11 |  |  |
| 90 | GOLD Copy Trading | -1001335852535 | channel | - | 200 | 0 | 0 | 5 | 0 | 0.00 | 3 | 0 | 99 | 36 | 0.00 |  |  |
| 91 | Maria Wans | 8229947050 | user | - | 2 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 1 | 0.00 |  |  |
| 92 | FundedNext Official Channel | -1001523638497 | channel | A | 200 | 0 | 0 | 23 | 0 | 0.00 | 22 | 0 | 25 | 55 | 0.00 |  |  |
| 5 | XAUHQ 🏛️ | -1001207746934 | channel | - | 200 | 33 | 33 | 64 | 34 | 0.53 | 15 | 79 | 103 | 12 | 0.43 |  |  |
| 93 | Pockets of Rizdom 🧠 | -1001715953952 | channel | A | 200 | 0 | 0 | 109 | 0 | 0.00 | 107 | 0 | 53 | 45 | 0.00 |  |  |
| 94 | TRADING LEGEND QTX | -1001282008556 | channel | - | 200 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 92 | 0.00 |  |  |
| 95 | Telegram | 777000 | user | - | 21 | 0 | 0 | 14 | 0 | 0.00 | 14 | 0 | 0 | 0 | 0.00 |  |  |
| 96 | Ai Trader Dev | 8461635544 | user | A | 5 | 0 | 0 | 1 | 0 | 0.00 | 1 | 0 | 0 | 0 | 0.00 |  |  |
| 97 | Mariyam | 6358316985 | user | - | 3 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 98 | Dan GOLD Trader | 7711680962 | user | A | 13 | 0 | 0 | 0 | 0 | - | 0 | 0 | 3 | 1 | 0.00 |  |  |
| 99 | GTMO SUPPORT | 8580858447 | user | - | 2 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 100 | Algo trades | 8393793788 | user | A | 2 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 1 | 0.00 |  |  |
| 101 | Chad | 8005377854 | user | - | 1 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 102 | Neymar | 6495583513 | user | A | 2 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 103 | GOLD Sniper | 5243618195 | user | - | 7 | 0 | 0 | 0 | 0 | - | 0 | 1 | 4 | 0 | 0.00 |  |  |
| 104 | Hicham Mouhtarif | 6523451099 | user | A | 6 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 1 | 0.00 |  |  |
| 105 | 惠城400服务系美琪💗 | 8012937528 | user | A | 4 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 106 | Diran Rian | 8517444783 | user | A | 4 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 107 | Ahmed Nawaz | 7114916557 | user | A | 6 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 108 | MTB SIGNALS | -1001828310477 | channel | - | 200 | 0 | 0 | 1 | 0 | 0.00 | 0 | 0 | 115 | 39 | 0.00 |  |  |
| 109 | ... | 7676943515 | user | A | 11 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 110 | Robert | 7477180469 | user | A | 3 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 1 | 0.00 |  |  |
| 111 | Noxen | 1238931793 | user | A | 1 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 112 | Maranemuie | 753693177 | user | A | 1 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 113 | Camila | 1400148241 | user | A | 67 | 0 | 0 | 0 | 0 | - | 0 | 0 | 1 | 4 | 0.00 |  |  |
| 114 | danktimmy420🚨📲🔥 | -1004439843313 | channel | A | 0 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 115 | reap🐬 | -1002061860222 | channel | A | 4 | 0 | 0 | 2 | 0 | 0.00 | 2 | 0 | 1 | 2 | 0.00 |  |  |
| 116 | George Williams | 1112262786 | user | A | 1 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 117 | Eric Tim | 7597926140 | user | A | 3 | 0 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 | 0.00 |  |  |
| 118 | Olymp Trade | -1001149412597 | channel | - | 200 | 0 | 0 | 26 | 0 | 0.00 | 25 | 0 | 59 | 35 | 0.00 |  |  |
| 119 | Ly Trader | -1001739881714 | channel | - | 200 | 0 | 0 | 5 | 0 | 0.00 | 4 | 0 | 6 | 67 | 0.00 |  |  |
| 30 | Signals Hub – Crypto • Forex • Stock | -1001023079107 | channel | - | 200 | 3 | 3 | 51 | 16 | 0.31 | 32 | 0 | 85 | 28 | 0.00 |  |  |

## Deep-verify gate (complete >= 8 in the 200-msg window)

| # | chat | id | complete | sig/day | symbols |
|---:|---|---:|---:|---:|---|
| 1 | Gold Signals VIP (XAUUSD FOREX) | -1001868019139 | 59 | 1.75 | XAUUSDx28, XAGUSDx13, BTCUSDx3, XTIUSDx3, EURUSDx3, ETHUSDx3 |
| 2 | UnitedSignals (Best Forex Signals) | -1001215049720 | 42 | 1.51 | XAUUSDx11, EURUSDx5, USDCHFx2, BTCUSDx2, EURJPYx2, EURNZDx2 |
| 3 | GOLD FOREX SIGNALS VIP | -1003196282951 | 39 | 3.40 | XAUUSDx15, EURUSDx4, BTCUSDx4, GBPAUDx3, GBPUSDx3, AUDNZDx2 |
| 4 | Asterra Gold | -1003751867978 | 34 | 0.79 | XAUUSDx32, US30x2 |
| 5 | XAUHQ 🏛️ | -1001207746934 | 33 | 0.43 | XAUUSDx33 |
| 6 | 𝑋𝐴𝑈𝑈𝑆𝐷 𝑇𝑅𝐴𝐷𝐼𝑁𝐺 𝑀𝐴𝑆𝑇𝐸𝑅 | -1002010239852 | 29 | 0.69 | XAUUSDx29 |
| 7 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002620653001 | 24 | 1.85 | XAUUSDx24 |
| 8 | 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002639725270 | 21 | 0.86 | XAUUSDx21 |
| 9 | 𝙱𝚎𝚜𝚝 𝚂𝚒𝚐𝚗𝚊𝚕 𝙵𝚘𝚛𝚎𝚡 | -1002369502254 | 21 | 0.79 | XAUUSDx21 |
| 10 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1001601213792 | 20 | 1.12 | XAUUSDx20 |
| 11 | 𝐏𝐑𝐄𝐌𝐈𝐔𝐌 𝐕𝐕𝐈𝐏 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002647890905 | 19 | 0.71 | XAUUSDx19 |
| 12 | 𝐅𝐗 𝐒𝐈𝐆𝐍𝐀𝐋 𝐓𝐄𝐀𝐌 | -1003924380674 | 17 | 2.45 | XAUUSDx17 |
| 13 | SureShot GOLD | -1001588519179 | 17 | 0.95 | XAUUSDx16, BTCUSDx1 |
| 14 | 𝐗𝐀𝐔𝐔𝐒𝐃 𝐏𝐑𝐎 𝐒𝐈𝐆𝐍𝐀𝐋 | -1002692333123 | 16 | 0.90 | XAUUSDx16 |
| 15 | 𝐆𝐎𝐋𝐃 𝐏𝐑𝐎 𝐓𝐑𝐀𝐃𝐄𝐑 | -1002520344727 | 15 | 2.47 | XAUUSDx15 |
| 16 | Gold Signals Daily 🔔🏆 | -1003762554260 | 11 | 0.88 | XAUUSDx11 |
| 17 | XAUUSD GOLD SIGNALS | -1003376522019 | 9 | 0.23 | XAUUSDx9 |
| 18 | Christopher Alan Harrison💪 | -1001932578394 | 8 | 0.10 | XAUUSDx8 |
| 19 | Gold Scalping - EdgeTrade 👑 | -1001988895125 | 8 | 1.17 | XAUUSDx8 |

Next: `channel_verify3.py verify` runs the V2 exit-geometry verification (per `agent-reports/exit-geometry.md`) on every candidate above.

