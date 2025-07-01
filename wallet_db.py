import aiosqlite

DB_PATH = "wallets.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS wallets (user_id INTEGER, chain TEXT, address TEXT)"
        )
        await db.execute("""
            CREATE TABLE IF NOT EXISTS last_balances (
                user_id INTEGER,
                chain   TEXT,
                address TEXT,
                balance REAL,
                PRIMARY KEY (user_id, chain, address)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS last_txs (
                user_id   INTEGER,
                chain     TEXT,
                address   TEXT,
                last_hash TEXT,
                PRIMARY KEY (user_id, chain, address)
            )
        """)
        await db.commit()

async def add_wallet(user_id, chain, address):
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO wallets (user_id, chain, address) VALUES (?, ?, ?)",
            (user_id, chain, address)
        )
        await db.commit()

async def remove_wallet(user_id, chain, address):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM wallets WHERE user_id = ? AND chain = ? AND address = ?",
            (user_id, chain, address)
        )
        await db.commit()

async def get_wallets(user_id):
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT chain, address FROM wallets WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

async def get_last_tx(user_id, chain, address):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_hash FROM last_txs WHERE user_id=? AND chain=? AND address=?",
            (user_id, chain, address)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def update_last_tx(user_id, chain, address, last_hash):
    async with aiosqlite.connect(DB_PATH) as db:
        # upsert style:
        await db.execute("""
            INSERT INTO last_txs (user_id, chain, address, last_hash)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id,chain,address) DO UPDATE SET last_hash=excluded.last_hash
        """, (user_id, chain, address, last_hash))
        await db.commit()

async def get_last_balance(user_id: int, chain: str, address: str) -> float | None:
    """Return the last recorded balance, or None if none exists."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT balance FROM last_balances WHERE user_id=? AND chain=? AND address=?",
            (user_id, chain, address)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def update_last_balance(user_id: int, chain: str, address: str, balance: float):
    """
    Insert or update the last_balances table with the new balance.
    Uses ON CONFLICT to upsert.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO last_balances (user_id, chain, address, balance)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, chain, address)
            DO UPDATE SET balance=excluded.balance
        """, (user_id, chain, address, balance))
        await db.commit()

async def get_all_wallets():
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, chain, address FROM wallets")
        return await cursor.fetchall()
    
    await db.commit()

