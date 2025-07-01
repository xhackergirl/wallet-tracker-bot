import os
from dotenv import load_dotenv
from telethon import TelegramClient, events, Button
from wallet_db import add_wallet, remove_wallet, get_wallets, init_db
from eth_utils import is_valid_eth_address, get_chain_balance, get_chain_erc20
from btc_utils import is_valid_btc_address, get_btc_balance, get_btc_txs
import logging
import asyncio
logging.basicConfig(level=logging.INFO)

load_dotenv()

import os


if __name__ == '__main__':
    print("Bot is running...")
    api_id = 25235449
    if not api_id:
        raise ValueError("TELEGRAM_API_ID is not set in Railway environment variables.")
    API_ID = int(api_id)
    
    API_HASH = os.getenv('TELEGRAM_API_HASH')
    if not API_HASH:
        raise ValueError("TELEGRAM_API_HASH is not set.")

    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
    bot.loop.create_task(monitor_balances())
    bot.run_until_disconnected()



# Temporary storage for chain selection
user_chains = {}

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond(
        "👋 Welcome! What would you like to do?",
        buttons=[
            [Button.inline('➕ Add Wallet', b'add')],
            [Button.inline('📋 List Wallets', b'list')]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b'add'))
async def add_wallet_btn(event):
    await event.respond(
        "Select network:",
        buttons=[
            [Button.inline('ETH (Ethereum)', b'add_eth')],
            [Button.inline('BTC (Bitcoin)', b'add_btc')],
            [Button.inline('BSC (Binance Smart Chain)', b'add_bsc')],
            [Button.inline('Polygon (MATIC)', b'add_poly')]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b'add_eth|add_btc|add_bsc|add_poly'))
async def choose_chain(event):
    chain = event.data.decode().split('_')[1]
    user_chains[event.sender_id] = chain
    await event.respond(f"Send your {chain.upper()} wallet address:")

@bot.on(events.NewMessage)
async def handle_new_message(event):
    user_id = event.sender_id
    if user_id in user_chains:
        chain = user_chains.pop(user_id)
        addr = event.text.strip()
        valid = False
        if chain in ('eth', 'bsc', 'poly'):
            valid = is_valid_eth_address(addr)
        elif chain == 'btc':
            valid = is_valid_btc_address(addr)

        if valid:
            await add_wallet(user_id, chain, addr)
            await event.respond("✅ Wallet added!", buttons=[[Button.inline('📋 List Wallets', b'list')]])
        else:
            await event.respond("❗ Invalid address. Please send a valid one.")

@bot.on(events.CallbackQuery(pattern=b'list'))
async def list_wallets_btn(event):
    user_id = event.sender_id
    wallets = await get_wallets(user_id)  # [(chain, addr), ...]
    if not wallets:
        return await event.respond(
            "You have no wallets tracked.",
            buttons=[[Button.inline('➕ Add Wallet', b'add')]]
        )

    # Build buttons with index instead of full address
    btns = []
    for i, (chain, addr) in enumerate(wallets):
        label = f"{chain.upper()} {addr[:8]}…{addr[-4:]}"
        data  = f"w_{chain}_{i}"   # e.g. "w_eth_0", only ~7 bytes
        
        btns.append([Button.inline(label, data.encode())])
    btns.append([Button.inline('➕ Add Wallet', b'add')])

    await event.respond("Your wallets:", buttons=btns)

@bot.on(events.CallbackQuery(pattern=b'w_'))
async def wallet_actions(event):
    _, chain, idx = event.data.decode().split('_')
    idx = int(idx)
    wallets = await get_wallets(event.sender_id)
    _, addr = wallets[idx]

    buttons = [
        [Button.inline('💰 Show Balance', f"b_{chain}_{idx}".encode())],
        [Button.inline('❌ Remove',       f"r_{chain}_{idx}".encode())],
        [Button.inline('⬅️ Back',         b'list')]
    ]
    await event.respond(f"Actions for `{chain.upper()} {addr}`", 
                        buttons=buttons, parse_mode='markdown')

@bot.on(events.CallbackQuery(pattern=b'b_'))
async def show_balance(event):
    _, chain, idx = event.data.decode().split('_')
    idx = int(idx)
    wallets = await get_wallets(event.sender_id)
    _, addr = wallets[idx]
    # … now fetch balance for addr …

    if chain == 'btc':
        bal = await get_btc_balance(addr)
        await event.respond(f"💰 BTC Balance: `{bal}`", parse_mode='markdown')
    else:
        bal = await get_chain_balance(addr, chain)
        tokens = await get_chain_erc20(addr, chain)
        msg = f"💰 {chain.upper()} Balance: `{bal}`\n"
        if tokens:
            msg += "• Top Tokens:\n"
            for sym, amt in tokens:
                msg += f"   - {sym}: `{amt}`\n"
        else:
            msg += "• No tokens found.\n"
        await event.respond(msg, parse_mode='markdown')

@bot.on(events.CallbackQuery(pattern=b't_'))
async def show_txs(event):
    _, chain, addr = event.data.decode().split('_', 2)
    if chain == 'btc':
        txs = await get_btc_txs(addr)
        msg = "🔄 Last BTC Transactions:\n"
        for t in txs:
            msg += f"- {t['hash']} : {t['value']} BTC\n"
    else:
        txs = await get_chain_erc20(addr, chain)  # simplified: reuse token API for recent txs
        msg = f"🔄 Last {chain.upper()} Transfers:\n"
        for sym, amt in txs:
            msg += f"- {sym}: {amt}\n"
    await event.respond(msg, parse_mode='markdown')

@bot.on(events.CallbackQuery(pattern=b'r_'))
async def remove_wallet_btn(event):
    _, chain, idx = event.data.decode().split('_')
    idx = int(idx)
    wallets = await get_wallets(event.sender_id)
    _, addr = wallets[idx]
    await remove_wallet(event.sender_id, chain, addr)
    await event.respond("🗑️ Wallet removed.", buttons=[[Button.inline('📋 List Wallets', b'list')]])


from wallet_db import get_all_wallets, get_last_tx, update_last_tx, get_last_balance, update_last_balance
from eth_utils import get_chain_erc20_txs      # you’ll write this
from btc_utils import get_btc_txs

async def monitor_txs():
    await init_db()
    while True:
        for user_id, chain, addr in await get_all_wallets():
            # Fetch the 5 most recent txs
            if chain == 'btc':
                txs = await get_btc_txs(addr)
            else:
                txs = await get_chain_erc20_txs(addr, chain)

            if not txs:
                continue

            # Our API returns them newest‐first
            newest_hash = txs[0]['hash']
            last_hash   = await get_last_tx(user_id, chain, addr)

            # If we've never seen any, just record it
            if last_hash is None:
                await update_last_tx(user_id, chain, addr, newest_hash)
                continue

            # Find all txs up to (but not including) last_hash
            new_txs = []
            for tx in txs:
                if tx['hash'] == last_hash:
                    break
                new_txs.append(tx)

            if new_txs:
                # Notify oldest→newest so it reads chronologically
                for tx in reversed(new_txs):
                    text = (
                        f"🔔 *New {chain.upper()} tx* on `{addr}`\n"
                        f"• Hash: `{tx['hash']}`\n"
                        f"• Value: `{tx['value']}` { 'BTC' if chain=='btc' else ''}\n"
                    )
                    await bot.send_message(user_id, text, parse_mode='markdown')
                # Update our bookmark
                await update_last_tx(user_id, chain, addr, newest_hash)

        await asyncio.sleep(30)  # every 5 minutes

async def monitor_balances():
    await init_db()
    while True:
        all_w = await get_all_wallets()
        for user_id, chain, addr in all_w:
            # fetch current
            if chain == 'btc':
                cur = await get_btc_balance(addr)
            else:
                cur = await get_chain_balance(addr, chain)
            if cur is None: continue
            prev = await get_last_balance(user_id, chain, addr) or 0
            if abs(cur - prev) > 1e-9:
                # notify user
                await bot.send_message(
                    user_id,
                    f"🔔 *{chain.upper()}* {addr}\nBalance changed: `{prev}` → `{cur}`",
                    parse_mode='markdown'
                )
                await update_last_balance(user_id, chain, addr, cur)
        await asyncio.sleep(30)  # check every 5 minutes

