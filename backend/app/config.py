import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / 'backend' / '.env')

@dataclass
class Settings:
    mode: str = field(default_factory=lambda: os.getenv('APP_MODE', 'live'))
    environment: str = field(default_factory=lambda: os.getenv('APP_ENV', 'development'))
    supabase_url: str = field(default_factory=lambda: os.getenv('SUPABASE_URL', '').rstrip('/'))
    supabase_key: str = field(default_factory=lambda: os.getenv('SUPABASE_PUBLISHABLE_KEY', ''))
    gemini_key: str = field(default_factory=lambda: os.getenv('GEMINI_API_KEY', ''))
    gemini_model: str = field(default_factory=lambda: os.getenv('GEMINI_MODEL', 'gemini-3.5-flash'))
    fallback_model: str = field(default_factory=lambda: os.getenv('GEMINI_FALLBACK_MODEL', 'gemini-3.1-flash-lite'))
    embedding_model: str = field(default_factory=lambda: os.getenv('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001'))
    miro_token: str = field(default_factory=lambda: os.getenv('MIRO_ACCESS_TOKEN', ''))
    miro_users: set[str] = field(default_factory=lambda: set(filter(None, os.getenv('MIRO_ALLOWED_USER_IDS', '').split(','))))
    miro_boards: set[str] = field(default_factory=lambda: set(filter(None, os.getenv('MIRO_ALLOWED_BOARD_IDS', '').split(','))))
    origins: set[str] = field(default_factory=lambda: set(os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001').split(',')))
    data_dir: Path = field(default_factory=lambda: ROOT / '.data' / ('preview' if os.getenv('DEMO_DATA_DIR') == '.data/preview' else ''))

    @property
    def live(self):
        return self.mode == 'live'

    def validate(self):
        if self.mode not in {'live', 'demo'}:
            raise RuntimeError('APP_MODE must be live or demo.')
        if self.environment == 'production' and not self.live:
            raise RuntimeError('Demo mode is disabled in production.')
        if self.live and not all([self.supabase_url.startswith('https://'), self.supabase_key, self.gemini_key]):
            raise RuntimeError('Configure Supabase and Gemini in backend/.env.')
