import asyncpg
from typing import List, Dict, Any, Optional
from logger import Logger

class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.pool = None
        self.logger = config.logger

    async def initialize_pool(self):
        """Initialize the database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.db_host,
                port=self.config.db_port,
                database=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password,
                min_size=1,
                max_size=10
            )
            self.logger.passing("Database connection pool initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {e}")
            raise

    async def close_pool(self):
        """Close the database connection pool"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection pool closed")

    async def create_tables(self):
        """Create all necessary tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Create whitelist table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS whitelist (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create blacklist table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS blacklist (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create joinable channels table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS joinable_channels (
                    id SERIAL PRIMARY KEY,
                    channel_name VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create known users table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS known_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE,
                    confidence_score INTEGER,
                    account_age_years INTEGER,
                    account_age_months INTEGER,
                    account_age_days INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create settings table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_username ON whitelist(username)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_username ON blacklist(username)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_channels_name ON joinable_channels(channel_name)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_known_users_username ON known_users(username)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)')

            # Initialize pat counter if it doesn't exist
            await conn.execute('''
                INSERT INTO settings (key, value) VALUES ('pat_counter', '0')
                ON CONFLICT (key) DO NOTHING
            ''')

            self.logger.passing("Database tables created/verified")

    # Whitelist methods
    async def get_whitelist(self) -> List[str]:
        """Get all usernames from whitelist"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT username FROM whitelist ORDER BY username')
            return [row['username'] for row in rows]

    async def add_to_whitelist(self, username: str) -> bool:
        """Add username to whitelist"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('INSERT INTO whitelist (username) VALUES ($1)', username)
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def remove_from_whitelist(self, username: str) -> bool:
        """Remove username from whitelist"""
        async with self.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM whitelist WHERE username = $1', username)
            return result != 'DELETE 0'

    # Blacklist methods
    async def get_blacklist(self) -> List[str]:
        """Get all usernames from blacklist"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT username FROM blacklist ORDER BY username')
            return [row['username'] for row in rows]

    async def add_to_blacklist(self, username: str) -> bool:
        """Add username to blacklist"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('INSERT INTO blacklist (username) VALUES ($1)', username)
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def remove_from_blacklist(self, username: str) -> bool:
        """Remove username from blacklist"""
        async with self.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM blacklist WHERE username = $1', username)
            return result != 'DELETE 0'

    # Joinable channels methods
    async def get_joinable_channels(self) -> List[str]:
        """Get all channel names from joinable_channels"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT channel_name FROM joinable_channels ORDER BY channel_name')
            return [row['channel_name'] for row in rows]

    async def add_joinable_channel(self, channel_name: str) -> bool:
        """Add channel to joinable channels"""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('INSERT INTO joinable_channels (channel_name) VALUES ($1)', channel_name)
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def remove_joinable_channel(self, channel_name: str) -> bool:
        """Remove channel from joinable channels"""
        async with self.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM joinable_channels WHERE channel_name = $1', channel_name)
            return result != 'DELETE 0'

    # Known users methods
    async def get_known_users(self) -> Dict[str, Any]:
        """Get all known users as a dictionary (compatible with existing JSON format)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT username, confidence_score, account_age_years, account_age_months, account_age_days
                FROM known_users ORDER BY username
            ''')
            result = {}
            for row in rows:
                result[row['username']] = {
                    'confidence_score': row['confidence_score'],
                    'account_age_years': row['account_age_years'],
                    'account_age_months': row['account_age_months'],
                    'account_age_days': row['account_age_days']
                }
            return result

    async def add_known_user(self, username: str, confidence_score: int = None,
                           account_age_years: int = None, account_age_months: int = None,
                           account_age_days: int = None) -> bool:
        """Add or update known user"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO known_users (username, confidence_score, account_age_years, account_age_months, account_age_days)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (username) DO UPDATE SET
                    confidence_score = COALESCE($2, known_users.confidence_score),
                    account_age_years = COALESCE($3, known_users.account_age_years),
                    account_age_months = COALESCE($4, known_users.account_age_months),
                    account_age_days = COALESCE($5, known_users.account_age_days),
                    updated_at = CURRENT_TIMESTAMP
            ''', username, confidence_score, account_age_years, account_age_months, account_age_days)
            return True

    async def remove_known_user(self, username: str) -> bool:
        """Remove known user"""
        async with self.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM known_users WHERE username = $1', username)
            return result != 'DELETE 0'

    # Settings methods
    async def get_setting(self, key: str) -> Optional[str]:
        """Get a setting value by key"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT value FROM settings WHERE key = $1', key)
            return row['value'] if row else None

    async def set_setting(self, key: str, value: str) -> bool:
        """Set a setting value"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO settings (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET
                    value = $2,
                    updated_at = CURRENT_TIMESTAMP
            ''', key, value)
            return True

    # Pat counter methods
    async def get_pat_counter(self) -> int:
        """Get current pat counter value"""
        value = await self.get_setting('pat_counter')
        return int(value) if value else 0

    async def increment_pat_counter(self) -> int:
        """Increment pat counter and return new value"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                current = await self.get_pat_counter()
                new_value = current + 1
                await self.set_setting('pat_counter', str(new_value))
                return new_value

    # Helper methods for database integration
    async def is_whitelisted(self, username: str) -> bool:
        """Check if username is in whitelist"""
        whitelist = await self.get_whitelist()
        return username.lower() in [name.lower() for name in whitelist]

    async def is_blacklisted(self, username: str) -> bool:
        """Check if username is in blacklist"""
        blacklist = await self.get_blacklist()
        return username.lower() in [name.lower() for name in blacklist]

    async def is_known_user(self, username: str) -> bool:
        """Check if username is a known user"""
        known_users = await self.get_known_users()
        return username.lower() in [name.lower() for name in known_users.keys()]
