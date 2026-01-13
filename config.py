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
    MAX_DESCRIPTION_LENGTH = 300
    VALID_CATEGORIES = ['general', 'business', 'sports', 'technology']
    MAX_ARTICLES_PER_CATEGORY = 5
    MIN_ARTICLE_LENGTH = 100
    CATEGORY_PRIORITY = ['general', 'business', 'sports', 'technology']
    ARTICLE_AGE_LIMIT = 48
    MAX_FEED_ENTRIES = 5
    VIDEO_TIMEOUT = 60
    MAX_RETRY_ATTEMPTS = 3
    REQUEST_TIMEOUT = 15

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

    # Maximum text length for TTS (increased from 600 to 2000)
    MAX_TTS_LENGTH = 2000

    # ========================
    # API Configuration
    # ========================
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    SUMMARIZATION_API = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')
    MAX_CONCURRENT_REQUESTS = 5

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
    CATEGORY_KEYWORDS = {
        'general': ['pakistan', 'national', 'islamabad', 'punjab', 'sindh', 'kpk', 'balochistan'],
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
    PROHIBITED_KEYWORDS = [
        'violence', 'hate', 'terrorism', 'weapon', 'drug', 'gambling',
        'adult', 'pornography', 'nudity', 'sexual', 'explicit'
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
        """Validate if category is supported"""
        if category not in cls.VALID_CATEGORIES:
            logger.warning(f"Invalid category: {category}. Valid categories: {cls.VALID_CATEGORIES}")
            return False
        return True

    @classmethod
    def validate_api_keys(cls) -> Dict[str, bool]:
        """Check which API keys are available"""
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
    def validate_text_length(cls, text: str, min_length: int = 50, max_length: int = None) -> bool:
        """Validate text length for processing"""
        if not text or len(text.strip()) < min_length:
            logger.warning(f"Text too short: {len(text)} characters (minimum: {min_length})")
            return False

        # Use MAX_TTS_LENGTH as default if max_length is not specified
        if max_length is None:
            max_length = cls.MAX_TTS_LENGTH

        if len(text) > max_length:
            logger.warning(f"Text too long: {len(text)} characters (maximum: {max_length})")
            return False
        return True

    @classmethod
    def is_content_safe(cls, text: str) -> bool:
        """Basic content moderation check"""
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
        """Create required directories"""
        try:
            # Create directories using Path directly instead of properties
            base_dir = Path(__file__).parent.resolve()
            (base_dir / 'temp').mkdir(exist_ok=True, parents=True)
            (base_dir / 'outputs').mkdir(exist_ok=True, parents=True)
            (base_dir / 'avatars').mkdir(exist_ok=True, parents=True)
            logger.info("Directories initialized successfully")
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            # Don't raise here, just log the error and continue

    @classmethod
    def validate_environment(cls) -> bool:
        """Validate complete environment setup"""
        try:
            # Check directories
            cls.setup_directories()

            # Check critical files
            missing_files = cls.validate_paths()
            if missing_files:
                logger.error(f"Missing critical files: {missing_files}")
                return False

            # Check API availability
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