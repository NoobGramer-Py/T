import io
import threading
import numpy as np
import sounddevice as sd
import wave
from core.logger import get_logger

log = get_logger("voice.stt")

SAMPLE_RATE = 16000  # Whisper expects 16kHz
CHANNELS    = 1
DTYPE       = "int16"

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        log.info("loading Whisper tiny.en model...")
        _model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        log.info("Whisper ready")
    return _model


class Recorder:
    """
    Records audio in a background thread while active.
    Call start() to begin, stop() to end and get PCM frames.
    """

    def __init__(self) -> None:
        self._frames:  list[np.ndarray] = []
        self._lock     = threading.Lock()
        self._stream:  sd.InputStream | None = None
        self._active   = False

    def start(self) -> None:
        if self._active:
            return
        self._frames = []
        self._active = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()
        log.debug("recorder started")

    def stop(self) -> np.ndarray:
        """Stop recording. Returns concatenated PCM int16 array."""
        self._active = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        log.debug(f"recorder stopped  frames={len(self._frames)}")
        if not self._frames:
            return np.array([], dtype=np.int16)
        return np.concatenate(self._frames, axis=0).flatten()

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        if status:
            log.warning(f"sounddevice status: {status}")
        if self._active:
            with self._lock:
                self._frames.append(indata.copy())


def transcribe(pcm: np.ndarray) -> str:
    """
    Transcribe int16 PCM audio to text using Whisper.
    Returns empty string if audio is too short or silent.
    """
    if pcm.size < SAMPLE_RATE * 0.3:  # less than 300ms — ignore
        return ""

    # Whisper needs float32 in [-1, 1]
    audio_f32 = pcm.astype(np.float32) / 32768.0

    model = _get_model()
    segments, _ = model.transcribe(
        audio_f32,
        language="en",
        vad_filter=True,        # skip silence
        vad_parameters={"min_silence_duration_ms": 500},
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    log.info(f"transcribed: {text!r}")
    return text


def pcm_to_wav_bytes(pcm: np.ndarray) -> bytes:
    """Convert int16 PCM array to WAV bytes for debugging/logging."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()
