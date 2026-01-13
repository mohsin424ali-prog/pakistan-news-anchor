# config.py
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for configuration validation errors"""
    pass

class Config:
    # ========================
    # Application Constants
    # ========================
    CACHE_TIME = 600
    # Increased description length to capture more context
    MAX_DESCRIPTION_LENGTH = 500
    VALID_CATEGORIES = ['general', 'business', 'sports', 'technology']
    MAX_ARTICLES_PER_CATEGORY = 5
    
    # Lowered to 30 to accept short RSS snippets/headlines
    MIN_ARTICLE_LENGTH = 30
    
    CATEGORY_PRIORITY = ['general', 'business', 'sports', 'technology']
    ARTICLE_AGE_LIMIT = 48
    MAX_FEED_ENTRIES = 5
    VIDEO_TIMEOUT = 60
    MAX_RETRY_ATTEMPTS = 3
    REQUEST_TIMEOUT = 20

    # ========================
    # Text Constraints
    # ========================
    TEXT_CONSTRAINTS = {
        'headline': {
            'en': {'max_chars': 90, 'max_lines': 1},
            'ur': {'max_chars': 70, 'max_lines': 1}
        },
        'description': {
            'en': {'min_lines': 3, 'max_lines': 5, 'chars_per_line': 80},
            'ur': {'min_lines': 3, 'max_lines': 5, 'chars_per_line': 60}
        }
    }

    # BEST SOLUTION UPDATE: Increased to 10000 to prevent "Text too long" errors.
    # Edge TTS handles large text well, so 600 was too restrictive.
    MAX_TTS_LENGTH = 10000

    # ========================
    # API Configuration
    # ========================
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    SUMMARIZATION_API = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')
    MAX_CONCURRENT_REQUESTS = 5

    # Headers to mimic a real browser and avoid 403 Forbidden errors
    REQUEST_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # ========================
    # TTS Configuration
    # ========================
    TTS_CONFIG = {
        'en': {
            'engine': 'edge',
            'voice': 'en-GB-RyanNeural',
            'rate': '+15%',
            'pitch': '+0Hz'
        },
        'ur': {
            'engine': 'gtts',
            'lang': 'ur',
            'tld': 'com.pk',
            'slow': False
        }
    }

    # ========================
    # RSS Feed Configuration
    # ========================
    RSS_FEEDS = {
        'general': [
            'https://www.dawn.com/feeds/latest',
            'https://www.thenews.com.pk/rss/1/1',
            'https://www.geo.tv/rss/1/1',
            'https://www.brecorder.com/feed/'
        ],
        'business': [
            'https://profit.pakistantoday.com.pk/feed/',
            'https://www.brecorder.com/feed/',
            'https://tribune.com.pk/business/feed/',
            'https://www.pakistantoday.com.pk/business/feed/',
            'https://www.dawn.com/business/feed'
        ],
        'sports': [
            'https://cricketpakistan.com.pk/rss/news',
            'https://www.geo.tv/rss/sports/1',
            'https://www.thenews.com.pk/rss/1/8',
            'https://www.samaa.tv/sports/feed/',
            'https://tribune.com.pk/sports/feed/'
        ],
        'technology': [
            'https://propakistani.pk/feed/',
            'https://www.techjuice.pk/feed/',
            'https://en.dailypakistan.com.pk/technology/feed/',
            'https://www.suchtv.pk/technology/feed/index.rss',
            'https://www.phoneworld.com.pk/feed/'
        ]
    }

    URDU_RSS_FEEDS = {
        'general': [
            'https://www.bbc.com/urdu/topics/cjgn7n9zzq7t.rss',
            'https://urdu.arynews.tv/feed/',
            'https://www.independenturdu.com/rss',
            'https://www.express.pk/feed',
            'https://jang.com.pk/rss'
        ],
        'business': [
            'https://www.bbc.com/urdu/topics/c340q0p2585t.rss',
            'https://www.urdupoint.com/business.feed',
            'https://www.express.pk/feed',
            'https://urdu.arynews.tv/feed/',
            'https://jang.com.pk/rss'
        ],
        'sports': [
            'https://www.bbc.com/urdu/topics/cg726y985v5t.rss',
            'https://www.urdupoint.com/sports.feed',
            'https://www.express.pk/feed',
            'https://urdu.arynews.tv/feed/',
            'https://jang.com.pk/rss'
        ],
        'technology': [
            'https://www.bbc.com/urdu/topics/ckdxnw9n82dt.rss',
            'https://www.urdupoint.com/technology.feed',
            'https://www.express.pk/feed',
            'https://urdu.arynews.tv/feed/',
            'https://jang.com.pk/rss'
        ]
    }

    # ========================
    # Content Processing
    # ========================
    # Empty list for 'general' to accept ALL general news
    CATEGORY_KEYWORDS = {
        'general': [], 
        'business': ['economy', 'rupee', 'PSX', 'SBP', 'investment', 'trade', 'CPEC'],
        'sports': ['cricket', 'Pakistan Cricket Board', 'PCB', 'PSL', 'pak vs'],
        'technology': ['5G', 'IT', 'technology', 'smartphone', 'AI', 'cybersecurity']
    }

    URDU_SUBCATEGORIES = {
        "general": "عمومی خبریں",
        "business": "کاروبار",
        "sports": "کھیل",
        "technology": "ٹیکنالوجی"
    }

    # ========================
    # Content Moderation
    # ========================
    # Removed keywords that often trigger false positives in news
    PROHIBITED_KEYWORDS = [
        'gambling', 'adult', 'pornography', 'nudity', 'sexual', 'explicit'
    ]

    # ========================
    # File Path Configuration
    # ========================
    BASE_DIR = Path(__file__).parent.resolve()
    AUTO_AVATARS = {
        'en': str(BASE_DIR / 'avatars' / 'auto_anchor_en.png'),
        'ur': str(BASE_DIR / 'avatars' / 'auto_anchor_ur.png')
    }

    # ========================
    # Directory Paths
    # ========================
    @property
    def TEMP_DIR(self) -> Path:
        return self.BASE_DIR / 'temp'

    @property
    def OUTPUT_DIR(self) -> Path:
        return self.BASE_DIR / 'outputs'

    @property
    def AVATAR_DIR(self) -> Path:
        return self.BASE_DIR / 'avatars'

    # ========================
    # Validation Methods
    # ========================
    @classmethod
    def validate_category(cls, category: str) -> bool:
        if category not in cls.VALID_CATEGORIES:
            logger.warning(f"Invalid category: {category}. Valid categories: {cls.VALID_CATEGORIES}")
            return False
        return True

    @classmethod
    def validate_api_keys(cls) -> Dict[str, bool]:
        return {
            'news_api': bool(cls.NEWS_API_KEY),
            'huggingface_api': bool(cls.HUGGINGFACE_API_KEY)
        }

    @classmethod
    def validate_paths(cls) -> List[str]:
        """Validate critical file paths exist"""
        critical_paths = [
            Path("Wav2Lip/checkpoints/wav2lip_gan.pth"),
            Path(cls.AUTO_AVATARS['en']),
            Path(cls.AUTO_AVATARS['ur'])
        ]

        missing = []
        for path in critical_paths:
            if not path.exists():
                missing.append(str(path))
                logger.error(f"Missing critical resource: {path}")

        return missing

    @classmethod
    def validate_text_length(cls, text: str, min_length: int = None, max_length: int = None) -> bool:
        """
        BEST APPROACH VALIDATION:
        Dynamically adjusts limits to prevent unnecessary failures.
        """
        if text is None:
            return False

        # Set defaults if not provided
        if min_length is None:
            min_length = cls.MIN_ARTICLE_LENGTH
            
        # SMART OVERRIDE: 
        # If a caller (like utils.py) passes a strict limit (e.g. 600), but our Config 
        # allows more (4000), we use the larger Config value to prevent errors.
        config_max = cls.MAX_TTS_LENGTH
        if max_length is not None:
            # Use the larger of the two limits to be permissive
            effective_max = max(max_length, config_max)
        else:
            effective_max = config_max

        current_len = len(text.strip())

        if current_len < min_length:
            logger.warning(f"Text too short: {current_len} chars (minimum: {min_length})")
            return False

        if current_len > effective_max:
            logger.warning(f"Text too long: {current_len} chars (maximum: {effective_max})")
            return False
            
        return True

    @classmethod
    def is_content_safe(cls, text: str) -> bool:
        if not text:
            return False

        text_lower = text.lower()
        for keyword in cls.PROHIBITED_KEYWORDS:
            if keyword in text_lower:
                logger.warning(f"Prohibited content detected: {keyword}")
                return False
        return True

    # ========================
    # Directory Initialization
    # ========================
    @classmethod
    def setup_directories(cls) -> None:
        try:
            base_dir = Path(__file__).parent.resolve()
            (base_dir / 'temp').mkdir(exist_ok=True, parents=True)
            (base_dir / 'outputs').mkdir(exist_ok=True, parents=True)
            (base_dir / 'avatars').mkdir(exist_ok=True, parents=True)
            logger.info("Directories initialized successfully")
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")

    @classmethod
    def validate_environment(cls) -> bool:
        try:
            cls.setup_directories()
            missing_files = cls.validate_paths()
            if missing_files:
                logger.error(f"Missing critical files: {missing_files}")
                return False
            
            api_status = cls.validate_api_keys()
            logger.info(f"API Status: {api_status}")
            return True

        except Exception as e:
            logger.error(f"Environment validation failed: {e}")
            return False

# Initialize directories when config is loaded
try:
    Config.setup_directories()
    if not Config.validate_environment():
        logger.warning("Environment validation failed, but continuing...")
except Exception as e:
    logger.error(f"Failed to initialize environment: {e}")