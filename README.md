# Telegram Crypto Wallet Tracker Bot

A multi-chain crypto wallet tracker bot for Telegram, supporting Ethereum (ETH), Binance Smart Chain (BSC), Polygon (MATIC), and Bitcoin (BTC).

## Setup

1. Clone or copy the project.
2. Create a `.env` file in the root directory and fill in your keys:
   ```
   TELEGRAM_BOT_TOKEN=...
   ETHERSCAN_API_KEY=...
   BSCSCAN_API_KEY=...
   POLYGONSCAN_API_KEY=...
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```bash
   python main.py
   ```

## Project Structure

- `main.py` — Bot logic, commands, buttons, and event handlers.
- `wallet_db.py` — SQLite persistence for user wallets.
- `eth_utils.py` — Balance and ERC-20/token utilities for ETH, BSC, Polygon.
- `btc_utils.py` — Balance and transaction utilities for Bitcoin.
- `.env.example` — Example environment variables.
- `requirements.txt` — Python dependencies.
