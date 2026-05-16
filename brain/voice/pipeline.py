import asyncio
from typing import TYPE_CHECKING
from core.logger import get_logger
from voice.stt import Recorder, transcribe
from voice.tts import synthesize

if TYPE_CHECKING:
    from core.ws_server import Client

log = get_logger("voice.pipeline")

# One recorder per client — concurrent PTT sessions are independent
_recorders: dict[str, Recorder] = {}


async def handle_voice_start(client: "Client") -> None:
    """Begin recording for this client."""
    if client.id in _recorders:
        log.warning(f"voice_start received but already recording for {client.id}")
        return

    recorder = Recorder()
    _recorders[client.id] = recorder

    # Recording blocks — run in thread so we don't block the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, recorder.start)
    log.info(f"recording started  client={client.id}")
    await client.send({"type": "visualizer", "mode": "listening"})


async def handle_voice_stop(client: "Client") -> None:
    """Stop recording, transcribe, and send transcript back."""
    recorder = _recorders.pop(client.id, None)
    if recorder is None:
        log.warning(f"voice_stop received but not recording for {client.id}")
        return

    await client.send({"type": "visualizer", "mode": "idle"})

    loop = asyncio.get_event_loop()

    # Stop and get PCM in thread
    pcm = await loop.run_in_executor(None, recorder.stop)

    if pcm.size == 0:
        await client.send({"type": "voice_error", "error": "No audio captured"})
        return

    # Transcribe in thread — CPU-bound
    text = await loop.run_in_executor(None, transcribe, pcm)

    if not text:
        await client.send({"type": "voice_error", "error": "Could not understand audio"})
        return

    log.info(f"transcript ready  client={client.id}  text={text!r}")
    await client.send({"type": "voice_transcript", "text": text})


async def speak(client: "Client", text: str) -> None:
    """
    Synthesize text to speech and send audio to client.
    Called by engine after every assistant response when voice is active.
    """
    if not text.strip():
        return

    loop = asyncio.get_event_loop()
    try:
        b64_audio, sample_rate = await loop.run_in_executor(
            None, synthesize, text
        )
        await client.send({
            "type":        "tts_audio",
            "audio":       b64_audio,
            "sample_rate": sample_rate,
        })
        log.info(f"tts sent  client={client.id}  chars={len(text)}")
    except Exception as e:
        log.warning(f"tts failed  client={client.id}  error={e}")


def cleanup(client_id: str) -> None:
    """Clean up recorder state on disconnect."""
    recorder = _recorders.pop(client_id, None)
    if recorder:
        try:
            recorder.stop()
        except Exception:
            pass
