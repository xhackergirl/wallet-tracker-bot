import aiohttp, os, re
import logging
API_ENDPOINTS = {
    'eth': ("https://api.etherscan.io",  os.getenv('ETHERSCAN_API_KEY')),
    'bsc': ("https://api.bscscan.com",  os.getenv('BSCSCAN_API_KEY')),
    'poly': ("https://api.polygonscan.com",  os.getenv('POLYGONSCAN_API_KEY'))
}

def is_valid_eth_address(addr):
    return bool(re.fullmatch(r'0x[a-fA-F0-9]{40}', addr))

async def get_chain_balance(addr, chain):
    base, key = API_ENDPOINTS[chain]
    url = f"{base}/api?module=account&action=balance&address={addr}&apikey={key}"
    logging.info(f"[{chain}] fetching balance → {url}")
    async with aiohttp.ClientSession() as s:
        resp = await s.get(url)
        data = await resp.json()
        logging.info(f"[{chain}] response: {data}")
        if data.get('status') != '1':
            return None
        return int(data['result']) / 1e18

async def get_chain_erc20(addr, chain):
    base, key = API_ENDPOINTS[chain]
    url = f"{base}/api?module=account&action=tokentx&address={addr}&sort=desc&apikey={key}"
    async with aiohttp.ClientSession() as s:
        data = await (await s.get(url)).json()
        if data.get('status') != '1':
            return []
        agg = {}
        token_info = {}
        for tx in data['result']:
            ct = tx['contractAddress']
            val = int(tx['value'])
            dec = int(tx['tokenDecimal'])
            sym = tx['tokenSymbol']
            dir = 1 if tx['to'].lower() == addr.lower() else -1
            agg[ct] = agg.get(ct, 0) + dir * val
            token_info[ct] = (sym, dec)
        res = []
        for ct, amount in agg.items():
            if amount <= 0:
                continue
            sym, dec = token_info[ct]
            res.append((sym, round(amount / 10**dec, 6)))
        res.sort(key=lambda x: x[1], reverse=True)
        return res[:3]

async def get_chain_erc20_txs(addr, chain, limit=5):
    base, key = API_ENDPOINTS[chain]
    url = f"{base}/api?module=account&action=tokentx&address={addr}&sort=desc&apikey={key}"
    async with aiohttp.ClientSession() as s:
        data = await (await s.get(url)).json()
    if data.get('status') != '1':
        return []
    txs = data['result'][:limit]
    # flatten to simple dicts
    return [
        {'hash': tx['hash'],
         'value': int(tx['value']) / 10**int(tx['tokenDecimal'])}
        for tx in txs
    ]
