# Contributing to AI-Powered Pakistani News Anchor

We welcome contributions from the community! This document outlines the process for contributing to this AI-powered news anchor project.

## Development Guidelines

### Code Style
- **Python:** Follow PEP 8 style guidelines
- **Streamlit:** Use consistent component structure
- **Comments:** Add docstrings for all functions and classes
- **Naming:** Use descriptive variable and function names

### Git Workflow
1. **Fork** the repository
2. **Create a branch** for your feature or bug fix
3. **Make changes** with descriptive commit messages
4. **Test thoroughly** before submitting
5. **Submit a pull request** with clear description

### Branch Naming
- **Features:** `feature/description`
- **Bug Fixes:** `fix/description`
- **Documentation:** `docs/description`
- **Testing:** `test/description`

## Pull Request Process

### Before Submitting
1. Ensure all tests pass
2. Update documentation if needed
3. Check code style with linters
4. Test on multiple platforms if applicable

### Pull Request Requirements
- **Description:** Clear explanation of changes
- **Testing:** Include test cases for new functionality
- **Documentation:** Update relevant documentation
- **Breaking Changes:** Clearly mark any breaking changes

### Review Process
1. Maintainers will review your PR
2. Address any feedback or requested changes
3. PR will be merged once approved

## Issue Reporting

### Bug Reports
1. **Describe the issue** clearly
2. **Steps to reproduce** the problem
3. **Expected vs Actual behavior**
4. **Environment details** (OS, Python version, etc.)
5. **Error logs** or screenshots if applicable

### Feature Requests
1. **Describe the feature** you want
2. **Explain the use case** and benefits
3. **Provide examples** if possible
4. **Discuss alternatives** you considered

### Security Issues
If you discover a security vulnerability, please email the maintainers directly instead of opening a public issue.

## Development Environment Setup

### Prerequisites
- Python 3.8+
- Git
- Docker (optional)

### Installation
```bash
# Clone the repository
git clone https://github.com/mohsin424ali-prog/pakistan-news-anchor.git
cd pakistan-news-anchor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Environment Variables
Create a `.env` file with your API keys:
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

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_components.py

# Run with coverage
pytest --cov=app --cov=english_news --cov=urdu_news
```

## Code Organization

### Core Components
- **`app.py`:** Main Streamlit application
- **`config.py`:** Configuration management
- **`ui.py`:** User interface components
- **`async_processor.py`:** Background task processing
- **`cache_manager.py`:** Caching system

### Language Processing
- **`english_news.py`:** English news processing
- **`urdu_news.py`:** Urdu news processing

### Media Processing
- **`tts.py`:** Text-to-speech generation
- **`video.py`:** Video generation with lip-syncing
- **`utils.py`:** Utility functions

### AI Integration
- **`llm_processor.py`:** LLM content enhancement
- **`Wav2Lip/`:** Lip-syncing library

## Documentation

### Updating Documentation
- Update README.md for user-facing changes
- Add API documentation for new functions
- Update CONTRIBUTING.md for process changes
- Add troubleshooting guides for common issues

### Code Documentation
- Use docstrings for all functions and classes
- Include parameter descriptions and return values
- Add examples where helpful
- Document any complex algorithms or processes

## Testing Requirements

### Unit Tests
- Test all new functions
- Include edge cases and error conditions
- Test with mock data when appropriate

### Integration Tests
- Test component interactions
- Test end-to-end workflows
- Test with real API keys in CI/CD

### Performance Tests
- Test with large news articles
- Test video generation performance
- Test caching effectiveness

## Release Process

### Versioning
We use Semantic Versioning (SemVer):
- **MAJOR:** Breaking changes
- **MINOR:** New features
- **PATCH:** Bug fixes

### Release Checklist
1. Update version number in `config.py`
2. Update `CHANGELOG.md`
3. Test all functionality
4. Update documentation
5. Tag the release
6. Create GitHub release

## Community Standards

### Communication
- Be respectful and constructive
- Use clear and concise language
- Provide context and examples
- Be patient and understanding

### Code Quality
- Write clean, maintainable code
- Follow established patterns
- Add appropriate error handling
- Consider performance implications

### Project Vision
This project aims to:
- Provide high-quality AI-powered news content
- Support both English and Urdu languages
- Demonstrate advanced AI/ML integration
- Create accessible news consumption tools

## Getting Help

### Resources
- **Documentation:** Check the README and docs/
- **Issues:** Search existing issues first
- **Discussions:** Use GitHub Discussions for questions
- **Community:** Join our Discord/Slack (if available)

### Contact Maintainers
For urgent matters or sensitive issues, contact the project maintainers directly via email.

---

Thank you for contributing to the AI-Powered Pakistani News Anchor project! Your contributions help make this project better for everyone.

**> Built with ❤️ for Pakistani news content creation**