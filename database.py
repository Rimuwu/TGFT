import aiosqlite
from typing import List, Optional
import random

class Database:
    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = db_path
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS giveaway_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_name TEXT,
                    user_id TEXT,
                    username TEXT,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(key_name, user_id)
                )
            ''')
            
            await db.commit()
    
    async def add_to_giveaway(self, key_name: str, user_id: str, username: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    'INSERT INTO giveaway_participants (key_name, user_id, username) VALUES (?, ?, ?)',
                    (key_name, user_id, username)
                )
                await db.commit()
                return True
            except:
                return False
    
    async def get_giveaway_participants(self, key_name: str) -> List[tuple]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT user_id, username FROM giveaway_participants WHERE key_name = ? ORDER BY joined_at',
                (key_name,)
            )
            return await cursor.fetchall()
    
    async def pick_random_winner(self, key_name: str) -> Optional[tuple]:
        participants = await self.get_giveaway_participants(key_name)
        if not participants:
            return None
        return random.choice(participants)
    
    async def clear_giveaway(self, key_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM giveaway_participants WHERE key_name = ?', (key_name,))
            await db.commit()
    
    async def get_participants_count(self, key_name: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM giveaway_participants WHERE key_name = ?', (key_name,))
            result = await cursor.fetchone()
            return result[0] if result else 0