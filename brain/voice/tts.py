import io
import base64
import wave
import numpy as np
from core.logger import get_logger

log = get_logger("voice.tts")

SAMPLE_RATE = 24000   # Kokoro outputs 24kHz
VOICE       = "af_heart"  # warm, natural voice

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from kokoro_onnx import Kokoro
        log.info("loading Kokoro TTS model...")
        _pipeline = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
        log.info("Kokoro ready")
    return _pipeline


def synthesize(text: str) -> tuple[str, int]:
    """
    Convert text to speech.
    Returns (base64_wav_string, sample_rate).
    Raises RuntimeError if TTS is unavailable.
    """
    if not text.strip():
        raise ValueError("empty text")

    pipeline = _get_pipeline()

    # Kokoro returns a generator of (samples, sample_rate, _) tuples
    chunks: list[np.ndarray] = []
    for samples, sr, _ in pipeline.create(text, voice=VOICE, speed=1.0, lang="en-us"):
        chunks.append(samples)

    if not chunks:
        raise RuntimeError("Kokoro returned no audio")

    audio = np.concatenate(chunks)

    # Encode to WAV in memory
    wav_bytes = _to_wav(audio, SAMPLE_RATE)
    b64 = base64.b64encode(wav_bytes).decode("utf-8")
    log.debug(f"tts synthesized  chars={len(text)}  wav_bytes={len(wav_bytes)}")
    return b64, SAMPLE_RATE


def _to_wav(audio: np.ndarray, sample_rate: int) -> bytes:
    """Convert float32 audio to 16-bit WAV bytes."""
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()
