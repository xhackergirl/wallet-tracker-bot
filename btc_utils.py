import aiohttp, re

def is_valid_btc_address(addr):
    return bool(re.fullmatch(r'([13][A-HJ-NP-Za-km-z1-9]{25,34}|bc1[ac-hj-np-z02-9]{39,59})', addr))

async def get_btc_balance(addr):
    url = f"https://blockchain.info/rawaddr/{addr}"
    async with aiohttp.ClientSession() as s:
        data = await (await s.get(url)).json()
    return data.get('final_balance', 0) / 1e8

async def get_btc_txs(addr):
    url = f"https://blockchain.info/rawaddr/{addr}"
    async with aiohttp.ClientSession() as s:
        data = await (await s.get(url)).json()
    txs = data.get('txs', [])[:3]
    out = []
    for t in txs:
        amt = sum(o['value'] for o in t['out'] if o.get('addr') == addr)
        out.append({'hash': t['hash'], 'value': amt / 1e8})
    return out
