# AI-Powered Pakistani News Anchor

> **Platform:** Hugging Face Spaces
> **Technologies:** Streamlit, LLM APIs, Wav2Lip, OpenCV, TTS, RSS feed aggregation
> **Languages:** Python, JavaScript, HTML/CSS

## Overview

Developed an innovative AI news anchor system that automatically transforms Pakistani news articles into professional video presentations. The system aggregates news from multiple RSS feeds in both English and Urdu, processes content using advanced LLMs for cleaning and summarization, generates natural-sounding synthetic voice narration with multiple TTS engines, and creates AI-powered video presentations with lip-synced avatars using Wav2Lip technology.

## Key Features

### 🌐 Multi-Language Support
- **English News:** Edge TTS with SSML support for natural speech
- **Urdu News:** gTTS with character filtering for proper pronunciation
- **Pakistani News Focus:** Keyword filtering for relevant local content

### 🤖 AI-Powered Processing
- **LLM Integration:** Groq API for fast, high-quality content enhancement
- **Lip-Syncing:** Wav2Lip for realistic mouth movements synchronized to audio
- **Content Filtering:** Pakistani news keyword filtering for relevance

### ⚡ Performance Optimization
- **Async Processing:** Background task execution to prevent UI blocking
- **Caching:** RSS feed caching with 10-minute TTL
- **Streaming UI:** Real-time progress updates during video generation

### 🎨 User Experience
- **Responsive Design:** Mobile-friendly interface
- **Debug Mode:** Text processing pipeline visualization
- **Progress Tracking:** Real-time video generation status
- **Download Options:** Generated videos available for download

## Technical Stack

### Frontend
- **Streamlit:** Web framework for the user interface
- **HTML/CSS/JavaScript:** Custom styling and interactive elements

### AI/ML Components
- **Wav2Lip:** Lip-syncing model for video generation
- **OpenCV:** Computer vision for video processing
- **Hugging Face Transformers:** Machine learning models
- **Groq API:** LLM processing for content enhancement

### Text-to-Speech
- **Edge TTS:** High-quality English voice synthesis
- **gTTS:** Urdu voice synthesis with proper pronunciation

### News Processing
- **RSS Feed Parsing:** Multiple news sources aggregation
- **NewsAPI:** Additional news content retrieval
- **Newspaper3k:** Article content extraction and cleaning

### Infrastructure
- **Asyncio:** Background task processing
- **Docker:** Containerized deployment
- **Hugging Face Spaces:** Production hosting

## Achievements

- ✅ Successfully integrated multiple AI technologies into a cohesive system
- ✅ Implemented real-time video generation with lip-syncing capabilities
- ✅ Created a user-friendly interface for news content creation
- ✅ Optimized performance with caching and async processing
- ✅ Demonstrated expertise in multimodal AI applications and media processing

## Quick Start

### Prerequisites
- Python 3.8+
- Git
- Docker (optional for deployment)

### Installation
```bash
# Clone the repository
git clone https://github.com/mohsin424ali-prog/pakistan-news-anchor.git
cd pakistan-news-anchor

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application
```bash
# Development mode
streamlit run app.py

# Production mode (Docker)
docker build -t pakistan-news-anchor .
docker run -p 8501:8501 pakistan-news-anchor
```

## Usage

1. **Access the Web Interface:** Open `http://localhost:8501` in your browser
2. **Select News Source:** Choose English or Urdu news
3. **Configure Settings:** Adjust TTS voice, video quality, and processing options
4. **Generate Video:** Click "Generate News Video" to start processing
5. **Download Result:** Save the generated video to your device

## API Reference

### Core Functions

#### News Processing
```python
# English news processing
from english_news import process_english_news
articles = process_english_news(rss_feeds, llm_processor)

# Urdu news processing
from urdu_news import process_urdu_news
articles = process_urdu_news(rss_feeds, llm_processor)
```

#### TTS Generation
```python
# Generate English TTS
from tts import generate_english_tts
audio_file = generate_english_tts(text, voice_settings)

# Generate Urdu TTS
from tts import generate_urdu_tts
audio_file = generate_urdu_tts(text, voice_settings)
```

#### Video Generation
```python
# Create video with lip-syncing
from video import generate_news_video
video_file = generate_news_video(audio_file, avatar_image, text_content)
```

## Configuration

### Environment Variables
```bash
# News API Keys
NEWSAPI_KEY=your_newsapi_key
RSS_FEEDS=https://example.com/rss.xml

# LLM API Keys
GROQ_API_KEY=your_groq_key
TOGETHER_API_KEY=your_together_key

# TTS Settings
EDGE_TTS_API_KEY=your_edge_tts_key

# Video Processing
WAV2LIP_MODEL_PATH=path/to/wav2lip/model
```

### Configuration File
See `config.py` for detailed configuration options including:
- RSS feed URLs
- API endpoints and keys
- Processing parameters
- File paths and directories

## Contributing

We welcome contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Project Repository:** https://github.com/mohsin424ali-prog/pakistan-news-anchor
- **Issues and Questions:** Use GitHub Issues
- **Discussions:** Join our GitHub Discussions

## Related Projects

- **Wav2Lip:** https://github.com/Rudrabha/Wav2Lip
- **Streamlit:** https://github.com/streamlit/streamlit
- **Groq API:** https://github.com/GroqInc/groq-python-sdk

---

**Built with ❤️ for Pakistani news content creation**