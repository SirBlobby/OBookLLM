"""
Watermarking module for CSM TTS
This module handles adding imperceptible watermarks to AI-generated audio.
"""
import torch
import torchaudio

# Public watermark key for CSM 1B (not secure, for identification purposes)
# If using in production, generate your own private key and keep it secret
CSM_1B_GH_WATERMARK = [212, 211, 146, 56, 201]


def load_watermarker(device: str = "cuda"):
    """
    Load the SilentCipher watermarking model.
    
    Args:
        device: Device to load the model on ('cuda' or 'cpu')
    
    Returns:
        The watermarking model
    """
    try:
        import silentcipher
        model = silentcipher.get_model(
            model_type="44.1k",
            device=device,
        )
        return model
    except ImportError:
        print("Warning: silentcipher not installed. Watermarking will be disabled.")
        return None
    except Exception as e:
        print(f"Warning: Failed to load watermarker: {e}. Watermarking will be disabled.")
        return None


@torch.inference_mode()
def watermark(
    watermarker,
    audio_array: torch.Tensor,
    sample_rate: int,
    watermark_key: list[int],
) -> tuple[torch.Tensor, int]:
    """
    Apply an imperceptible watermark to audio.
    
    Args:
        watermarker: The watermarking model
        audio_array: Audio tensor to watermark
        sample_rate: Sample rate of the audio
        watermark_key: List of integers for the watermark
    
    Returns:
        Tuple of (watermarked_audio, output_sample_rate)
    """
    if watermarker is None:
        # Return original audio if watermarker is not available
        return audio_array, sample_rate
    
    audio_array_44khz = torchaudio.functional.resample(audio_array, orig_freq=sample_rate, new_freq=44100)
    encoded, _ = watermarker.encode_wav(audio_array_44khz, 44100, watermark_key, calc_sdr=False, message_sdr=36)

    output_sample_rate = min(44100, sample_rate)
    encoded = torchaudio.functional.resample(encoded, orig_freq=44100, new_freq=output_sample_rate)
    return encoded, output_sample_rate


@torch.inference_mode()
def verify(
    watermarker,
    watermarked_audio: torch.Tensor,
    sample_rate: int,
    watermark_key: list[int],
) -> bool:
    """
    Verify if audio contains the expected watermark.
    
    Args:
        watermarker: The watermarking model
        watermarked_audio: Audio tensor to check
        sample_rate: Sample rate of the audio
        watermark_key: Expected watermark key
    
    Returns:
        True if the audio contains the expected watermark
    """
    if watermarker is None:
        return False
    
    watermarked_audio_44khz = torchaudio.functional.resample(watermarked_audio, orig_freq=sample_rate, new_freq=44100)
    result = watermarker.decode_wav(watermarked_audio_44khz, 44100, phase_shift_decoding=True)

    is_watermarked = result["status"]
    if is_watermarked:
        is_csm_watermarked = result["messages"][0] == watermark_key
    else:
        is_csm_watermarked = False

    return is_watermarked and is_csm_watermarked


def load_audio(audio_path: str) -> tuple[torch.Tensor, int]:
    """Load audio from a file path."""
    audio_array, sample_rate = torchaudio.load(audio_path)
    audio_array = audio_array.mean(dim=0)
    return audio_array, int(sample_rate)
