import os
from twitchAPI.type import AuthScope
from logger import Logger

class TwitchConfig:
    def __init__(self):
        # Core Twitch API settings - no defaults for security
        self.app_id: str = os.getenv('TWITCH_APP_ID', '')
        self.app_secret: str = os.getenv('TWITCH_APP_SECRET', '')
        if self.app_id == '' or self.app_secret == '':
            raise ValueError('TWITCH_APP_ID and TWITCH_APP_SECRET must be set as environment variables')

        # Twitch settings with defaults
        self.user_name: str = os.getenv('TWITCH_USER', 'streamer_shield')
        self.admin: str = os.getenv('ADMIN_USER', 'caesarlp')

        # Database configuration with defaults
        self.db_host: str = os.getenv('DB_HOST', 'localhost')
        self.db_port: int = int(os.getenv('DB_PORT', '5432'))
        self.db_name: str = os.getenv('DB_NAME', 'streamer_shield')
        self.db_user: str = os.getenv('DB_USER', 'postgres')
        self.db_password: str = os.getenv('DB_PASSWORD', 'password')

        # URLs with defaults
        self.eventsub_url: str = os.getenv('EVENTSUB_URL', 'https://webhook.caes.ar')
        self.shield_url: str = os.getenv('SHIELD_URL', 'http://localhost:38080/api/predict')
        self.auth_url: str = os.getenv('AUTH_URL', 'https://shield.caes.ar/login/confirm')

        # Bot behavior settings with defaults
        self.is_armed: bool = os.getenv('IS_ARMED', 'true').lower() == 'true'
        self.collect_data: bool = os.getenv('COLLECT_DATA', 'true').lower() == 'true'
        self.age_threshold: int = int(os.getenv('AGE_THRESHOLD', '6'))
        self.max_length: int = int(os.getenv('MAX_LENGTH', '31'))

        # Static settings
        self.ban_reason: str = '''You've been banned by StreamerShield, if you think this was an Error, please make an unban request'''
        self.logger: Logger = Logger(console_log=True)
        self.user_scopes: list[AuthScope] = [
            AuthScope.CHAT_READ,
            AuthScope.CHAT_EDIT,
            AuthScope.MODERATOR_READ_CHATTERS,
            AuthScope.MODERATOR_MANAGE_BANNED_USERS,
            AuthScope.MODERATOR_READ_FOLLOWERS
        ]

    def get_database_url(self) -> str:
        """Return the PostgreSQL connection URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
