"""
LLM Processor using Groq API
- 100x faster than Hugging Face inference
- Better quality than BART
- Free tier: 14,400 requests/day

Installation: pip install groq
Get API key: https://console.groq.com (free)
"""

import os
from groq import Groq
from typing import Optional, List, Dict
import json

class LLMProcessor:
    """Process news text using Groq's fast LLM inference"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq client
        
        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found. Get one free at https://console.groq.com")
        
        self.client = Groq(api_key=self.api_key)
        
        # Model selection based on task
        self.models = {
            'fast': 'llama-3.1-8b-instant',      # 750 tokens/sec, good quality
            'balanced': 'llama-3.1-70b-versatile', # 300 tokens/sec, best quality
            'cheap': 'llama-3.1-8b-instant'       # Most free tier friendly
        }
    
    def summarize_and_clean(
        self, 
        text: str, 
        language: str = 'en',
        max_length: int = 150,
        add_ssml: bool = True
    ) -> Dict[str, str]:
        """
        Clean, summarize, and optionally add SSML to news text
        
        Args:
            text: Raw news article text
            language: 'en' or 'ur'
            max_length: Maximum words in summary
            add_ssml: Add SSML break tags for natural speech
            
        Returns:
            {
                'cleaned': str,      # Clean text without ads/junk
                'summary': str,      # Concise summary
                'tts_text': str,     # TTS-ready with SSML (if add_ssml=True)
                'headline': str      # Generated headline
            }
        """
        
        # Build prompt based on language
        if language == 'en':
            prompt = self._build_english_prompt(text, max_length, add_ssml)
        elif language == 'ur':
            prompt = self._build_urdu_prompt(text, max_length, add_ssml)
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        try:
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.models['fast'],  # Use fast model for news processing
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert news editor and content processor. Output ONLY valid JSON, no additional text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for consistent formatting
                max_tokens=1000,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            # Parse JSON response
            result = json.loads(response.choices[0].message.content)
            
            # Validate required fields
            required_fields = ['cleaned', 'summary', 'tts_text', 'headline']
            for field in required_fields:
                if field not in result:
                    print(f"⚠️ Missing field '{field}' in LLM response")
                    result[field] = result.get('summary', text[:200])
            
            # Clean SSML if present (remove if malformed)
            if add_ssml and '<speak>' in result['tts_text']:
                result['tts_text'] = self._validate_ssml(result['tts_text'])
            
            print(f"✅ LLM processed: {len(text)} → {len(result['summary'])} chars")
            return result
            
        except Exception as e:
            print(f"❌ LLM processing failed: {e}")
            # Fallback: return basic cleaning
            return self._fallback_processing(text)
    
    def _build_english_prompt(self, text: str, max_length: int, add_ssml: bool) -> str:
        """Build English processing prompt"""
        
        ssml_instructions = ""
        if add_ssml:
            ssml_instructions = """
- Add natural SSML breaks for news broadcast:
  * <break time="300ms"/> after introductory phrases
  * <break time="500ms"/> between major sentences
  * Wrap everything in <speak></speak> tags
  * Use ONLY straight quotes ("), not curly quotes
"""
        
        return f"""Process this news article and return ONLY a JSON object with these exact fields:

ARTICLE TEXT:
{text}

Return JSON with:
1. "cleaned": Remove ads, spam, "Read more", social media prompts, etc. Keep only news content.
2. "summary": Concise {max_length}-word summary suitable for news broadcast. Focus on: Who, What, When, Where, Why.
3. "headline": Engaging 8-12 word headline
4. "tts_text": News broadcast script{' with SSML breaks' if add_ssml else ''} (should sound natural when spoken)
{ssml_instructions}

Example JSON output:
{{
  "cleaned": "Pakistan's cricket team won against India...",
  "summary": "Pakistan defeated India by 5 wickets in the Asia Cup final...",
  "headline": "Pakistan Clinches Asia Cup Victory Over India",
  "tts_text": "<speak>Pakistan defeated India, <break time='300ms'/>winning the Asia Cup final by 5 wickets. <break time='500ms'/>The match was held in Dubai...</speak>"
}}

Output ONLY the JSON, no other text."""

    def _build_urdu_prompt(self, text: str, max_length: int, add_ssml: bool) -> str:
        """Build Urdu processing prompt"""
        
        return f"""Process this Urdu news article and return ONLY a JSON object:

ARTICLE TEXT (URDU):
{text}

Return JSON with:
1. "cleaned": اشتہارات اور spam ہٹائیں، صرف خبر رکھیں
2. "summary": {max_length} الفاظ میں خلاصہ
3. "headline": 8-12 الفاظ میں سرخی
4. "tts_text": نیوز براڈکاسٹ کے لیے متن (NO SSML for Urdu - gTTS doesn't support it)

Example JSON output:
{{
  "cleaned": "پاکستان کی کرکٹ ٹیم نے بھارت کو شکست دی...",
  "summary": "پاکستان نے ایشیا کپ فائنل میں بھارت کو 5 وکٹ سے شکست دی...",
  "headline": "پاکستان نے ایشیا کپ جیت لیا",
  "tts_text": "پاکستان نے بھارت کو شکست دے کر ایشیا کپ جیت لیا..."
}}

Output ONLY the JSON, no other text."""

    def _validate_ssml(self, text: str) -> str:
        """Validate and clean SSML"""
        try:
            # Ensure proper wrapping
            if not text.strip().startswith('<speak>'):
                text = '<speak>' + text
            if not text.strip().endswith('</speak>'):
                text = text + '</speak>'
            
            # Convert curly quotes to straight
            text = text.replace('"', '"').replace('"', '"')
            text = text.replace(''', "'").replace(''', "'")
            
            # Ensure self-closing break tags
            import re
            text = re.sub(r'<break([^/>]+)>', r'<break\1/>', text)
            
            return text
        except Exception as e:
            print(f"⚠️ SSML validation failed: {e}")
            # Strip all SSML if validation fails
            return re.sub(r'<[^>]+>', '', text)
    
    def _fallback_processing(self, text: str) -> Dict[str, str]:
        """Fallback when LLM fails - basic text processing"""
        # Simple cleaning
        import re
        cleaned = re.sub(r'(Read more|Click here|Subscribe|Follow us).*', '', text, flags=re.IGNORECASE)
        cleaned = cleaned.strip()[:500]
        
        # Simple summary (first 2 sentences)
        sentences = re.split(r'[.!?]+', cleaned)
        summary = '. '.join(sentences[:2]) + '.'
        
        return {
            'cleaned': cleaned,
            'summary': summary,
            'tts_text': summary,
            'headline': sentences[0][:80] if sentences else "News Update"
        }
    
    def batch_process(self, articles: List[Dict]) -> List[Dict]:
        """
        Process multiple articles efficiently
        
        Args:
            articles: List of {'text': str, 'language': str} dicts
            
        Returns:
            List of processed articles with LLM fields added
        """
        results = []
        
        for idx, article in enumerate(articles):
            print(f"Processing article {idx + 1}/{len(articles)}...")
            
            try:
                processed = self.summarize_and_clean(
                    text=article['text'],
                    language=article.get('language', 'en'),
                    add_ssml=article.get('language', 'en') == 'en'  # SSML only for English
                )
                
                # Merge with original article
                results.append({**article, **processed})
                
            except Exception as e:
                print(f"❌ Failed to process article {idx + 1}: {e}")
                # Use fallback
                results.append({
                    **article,
                    **self._fallback_processing(article['text'])
                })
        
        return results


# ============================================================================
# ALTERNATIVE PROVIDERS (in case Groq doesn't work)
# ============================================================================

class TogetherAIProcessor(LLMProcessor):
    """Alternative: Together.ai - Good quality, free credits"""
    
    def __init__(self, api_key: Optional[str] = None):
        import together
        
        self.api_key = api_key or os.environ.get('TOGETHER_API_KEY')
        together.api_key = self.api_key
        
        self.models = {
            'fast': 'meta-llama/Llama-3-8b-chat-hf',
            'balanced': 'meta-llama/Llama-3-70b-chat-hf',
        }
    
    # Override client methods to use Together.ai API
    # (Implementation similar to Groq but using together.Complete.create)


class CerebrasProcessor(LLMProcessor):
    """Alternative: Cerebras - Fastest inference (2000+ tokens/sec)"""
    
    def __init__(self, api_key: Optional[str] = None):
        from cerebras.cloud.sdk import Cerebras
        
        self.api_key = api_key or os.environ.get('CEREBRAS_API_KEY')
        self.client = Cerebras(api_key=self.api_key)
        
        self.models = {
            'fast': 'llama3.1-8b',
            'balanced': 'llama3.1-70b',
        }
    
    # (Implementation similar to Groq)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Example 1: Basic usage
    processor = LLMProcessor()  # Uses GROQ_API_KEY from env
    
    sample_text = """
    KARACHI: Pakistan's cricket team secured a thrilling victory against India
    in the Asia Cup final on Monday. The team won by 5 wickets with 2 overs
    remaining. Mohammad Rizwan was declared player of the match for his 
    unbeaten 87 runs. [READ MORE] [SUBSCRIBE TO OUR CHANNEL] Click here for
    live updates.
    """
    
    result = processor.summarize_and_clean(
        text=sample_text,
        language='en',
        max_length=50,
        add_ssml=True
    )
    
    print("\n" + "="*80)
    print("PROCESSING RESULT:")
    print("="*80)
    print(f"Headline: {result['headline']}")
    print(f"\nCleaned: {result['cleaned']}")
    print(f"\nSummary: {result['summary']}")
    print(f"\nTTS Text: {result['tts_text']}")
    
    # Example 2: Batch processing
    articles = [
        {'text': sample_text, 'language': 'en'},
        # ... more articles
    ]
    
    batch_results = processor.batch_process(articles)
    print(f"\n✅ Processed {len(batch_results)} articles")