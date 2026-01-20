"""
TTS Service for OBookLLM

This module provides a text-to-speech service using the CSM (Conversational Speech Model).
It handles model loading, caching, and audio generation for reading notebook responses.
"""
import os
import io
import torch
import torchaudio
from typing import Optional
from dataclasses import dataclass
from huggingface_hub import hf_hub_download

# Disable Triton compilation for compatibility
os.environ["NO_TORCH_COMPILE"] = "1"


@dataclass
class TTSConfig:
    """
    Configuration for the TTS service.
    
    Presets:
    - 'reading' mode (default): Accurate reading with natural pacing
    - 'conversational' mode: More expressive, casual speech with natural hesitations
    """
    speaker: str = "conversational_a"  # Voice style: conversational_a or conversational_b
    max_audio_length_ms: float = 90_000  # Maximum audio length in milliseconds
    # Lower temperature = more accurate/deterministic output
    # Higher temperature = more expressive but may add filler words
    temperature: float = 0.7  # Reduced from 0.9 for more accurate reading
    # Lower topk = more focused vocabulary choices
    # Higher topk = more variety but may stray from text
    topk: int = 30  # Reduced from 50 for more accurate reading
    style: str = "reading"  # 'reading' for accurate, 'conversational' for casual


def get_reading_config(speaker: str = "conversational_a") -> TTSConfig:
    """Get config optimized for accurate reading of text."""
    return TTSConfig(
        speaker=speaker,
        temperature=0.7,
        topk=30,
        style="reading"
    )


def get_conversational_config(speaker: str = "conversational_a") -> TTSConfig:
    """Get config for more expressive, conversational speech."""
    return TTSConfig(
        speaker=speaker,
        temperature=0.9,
        topk=50,
        style="conversational"
    )


class TTSService:
    """
    Text-to-Speech service using Sesame CSM-1B model.
    
    This service generates natural, conversational speech from text.
    The model is loaded lazily on first use to avoid unnecessary memory usage.
    """
    
    _instance: Optional['TTSService'] = None
    _generator = None
    _prompts = None
    _device = None
    _enabled = True
    _initialization_error = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if TTS is available (model can be loaded)."""
        if not cls._enabled:
            return False
        
        # Check for CUDA (required for reasonable performance)
        if not torch.cuda.is_available():
            # Allow CPU but warn about performance
            print("Warning: CUDA not available. TTS will run on CPU (slow).")
        
        return True
    
    @classmethod
    def get_initialization_error(cls) -> Optional[str]:
        """Return any initialization error message."""
        return cls._initialization_error
    
    def _load_model(self):
        """Load the CSM model and voice prompts."""
        if self._generator is not None:
            return
        
        try:
            from .generator import load_csm_1b, Segment
            
            # Select device
            if torch.cuda.is_available():
                self._device = "cuda"
            else:
                self._device = "cpu"
                print("Warning: Running CSM on CPU. This will be slow.")
            
            print(f"Loading CSM-1B TTS model on {self._device}...")
            self._generator = load_csm_1b(self._device)
            print("CSM-1B model loaded successfully.")
            
            # Load voice prompts
            self._load_prompts()
            
        except Exception as e:
            self._enabled = False
            self._initialization_error = str(e)
            print(f"Failed to load TTS model: {e}")
            raise
    
    def _load_prompts(self):
        """Load the voice prompt audio files."""
        from .generator import Segment
        
        # Download prompts from HuggingFace
        prompt_a_path = hf_hub_download(
            repo_id="sesame/csm-1b",
            filename="prompts/conversational_a.wav"
        )
        prompt_b_path = hf_hub_download(
            repo_id="sesame/csm-1b",
            filename="prompts/conversational_b.wav"
        )
        
        # Prompt transcripts for context
        prompt_texts = {
            "conversational_a": (
                "like revising for an exam I'd have to try and like keep up the momentum because I'd "
                "start really early I'd be like okay I'm gonna start revising now and then like "
                "you're revising for ages and then I just like start losing steam I didn't do that "
                "for the exam we had recently to be fair that was a more of a last minute scenario "
                "but like yeah I'm trying to like yeah I noticed this yesterday that like Mondays I "
                "sort of start the day with this not like a panic but like a"
            ),
            "conversational_b": (
                "like a super Mario level. Like it's very like high detail. And like, once you get "
                "into the park, it just like, everything looks like a computer game and they have all "
                "these, like, you know, if, if there's like a, you know, like in a Mario game, they "
                "will have like a question block. And if you like, you know, punch it, a coin will "
                "come out. So like everyone, when they come into the park, they get like this little "
                "bracelet and then you can go punching question blocks around."
            )
        }
        
        def load_audio(path: str) -> torch.Tensor:
            audio_tensor, sample_rate = torchaudio.load(path)
            audio_tensor = audio_tensor.squeeze(0)
            audio_tensor = torchaudio.functional.resample(
                audio_tensor, 
                orig_freq=sample_rate, 
                new_freq=self._generator.sample_rate
            )
            return audio_tensor
        
        self._prompts = {
            "conversational_a": Segment(
                speaker=0,
                text=prompt_texts["conversational_a"],
                audio=load_audio(prompt_a_path)
            ),
            "conversational_b": Segment(
                speaker=1,
                text=prompt_texts["conversational_b"],
                audio=load_audio(prompt_b_path)
            )
        }
    
    def generate_speech(
        self, 
        text: str, 
        config: Optional[TTSConfig] = None
    ) -> tuple[bytes, int]:
        """
        Generate speech audio from text.
        
        Args:
            text: The text to convert to speech
            config: TTS configuration options
        
        Returns:
            Tuple of (wav_bytes, sample_rate)
        """
        if config is None:
            config = TTSConfig()
        
        # Ensure model is loaded
        self._load_model()
        
        # Get the voice prompt
        prompt = self._prompts.get(config.speaker, self._prompts["conversational_a"])
        speaker_id = 0 if config.speaker == "conversational_a" else 1
        
        # Clean text for TTS (remove markdown, etc.)
        style = getattr(config, 'style', 'reading')
        clean_text = self._clean_text_for_tts(text, style=style)
        
        # Generate audio with tuned parameters
        print(f"Generating TTS ({style} mode, temp={config.temperature}, topk={config.topk})")
        print(f"Text: {clean_text[:100]}..." if len(clean_text) > 100 else f"Text: {clean_text}")
        
        audio_tensor = self._generator.generate(
            text=clean_text,
            speaker=speaker_id,
            context=[prompt],
            max_audio_length_ms=config.max_audio_length_ms,
            temperature=config.temperature,
            topk=config.topk,
        )
        
        # Convert to WAV bytes
        wav_buffer = io.BytesIO()
        torchaudio.save(
            wav_buffer, 
            audio_tensor.unsqueeze(0).cpu(), 
            self._generator.sample_rate,
            format="wav"
        )
        wav_buffer.seek(0)
        
        return wav_buffer.read(), self._generator.sample_rate
    
    def _clean_text_for_tts(self, text: str, style: str = "reading") -> str:
        """
        Clean and prepare text for TTS.
        
        For 'reading' style: Text is cleaned and prepared for accurate reading.
        For 'conversational' style: Text is more casually formatted.
        
        Args:
            text: Raw text that may contain markdown
            style: 'reading' or 'conversational'
        
        Returns:
            Clean text suitable for TTS
        """
        import re
        
        # Remove code blocks completely
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`[^`]*`', '', text)
        
        # Remove markdown formatting but keep content
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Italic
        text = re.sub(r'__([^_]+)__', r'\1', text)  # Bold
        text = re.sub(r'_([^_]+)_', r'\1', text)  # Italic
        text = re.sub(r'~~([^~]+)~~', r'\1', text)  # Strikethrough
        
        # Remove headers but keep text
        text = re.sub(r'^#+\s*(.*)$', r'\1.', text, flags=re.MULTILINE)  # Add period after headers
        
        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove images
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
        
        # Remove horizontal rules
        text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
        
        # Convert blockquotes to regular text
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        
        # Convert bullet points to sentences with proper punctuation
        def bullet_to_sentence(match):
            content = match.group(1).strip()
            # Add period if not already ending with punctuation
            if content and content[-1] not in '.!?,:;':
                content += '.'
            return content + ' '
        text = re.sub(r'^\s*[-*+]\s+(.+)$', bullet_to_sentence, text, flags=re.MULTILINE)
        
        # Convert numbered lists to sentences
        def numbered_to_sentence(match):
            content = match.group(1).strip()
            if content and content[-1] not in '.!?,:;':
                content += '.'
            return content + ' '
        text = re.sub(r'^\s*\d+\.\s+(.+)$', numbered_to_sentence, text, flags=re.MULTILINE)
        
        # Remove citation markers like [1], [2], etc.
        text = re.sub(r'\[\d+\]', '', text)
        
        # Clean up URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Normalize newlines to spaces (TTS reads continuously)
        text = re.sub(r'\n+', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()
        
        # Ensure proper sentence endings for natural pacing
        # Add periods after incomplete sentences
        sentences = text.split('. ')
        cleaned_sentences = []
        for s in sentences:
            s = s.strip()
            if s:
                # Ensure sentence ends with punctuation
                if s[-1] not in '.!?':
                    s += '.'
                cleaned_sentences.append(s)
        text = ' '.join(cleaned_sentences)
        
        # Replace multiple periods with single
        text = re.sub(r'\.{2,}', '.', text)
        
        # Limit length (CSM has context limits)
        max_chars = 2000  # Reasonable limit for TTS
        if len(text) > max_chars:
            # Try to cut at sentence boundary
            truncated = text[:max_chars]
            last_period = truncated.rfind('.')
            if last_period > max_chars * 0.7:
                text = truncated[:last_period + 1]
            else:
                text = truncated + "."
        
        return text
    
    def get_sample_rate(self) -> int:
        """Get the audio sample rate."""
        if self._generator is None:
            return 24000  # Default CSM sample rate
        return self._generator.sample_rate


# Global service instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get the global TTS service instance."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service


def generate_tts(text: str, speaker: str = "conversational_a") -> tuple[bytes, int]:
    """
    Convenience function to generate TTS audio.
    
    Args:
        text: Text to convert to speech
        speaker: Voice style ('conversational_a' or 'conversational_b')
    
    Returns:
        Tuple of (wav_bytes, sample_rate)
    """
    service = get_tts_service()
    config = TTSConfig(speaker=speaker)
    return service.generate_speech(text, config)
