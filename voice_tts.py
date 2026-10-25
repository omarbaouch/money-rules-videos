"""Text-to-speech for make_short.py and make_long.py.

Voice argument:
  kokoro:<voice>   -> Kokoro TTS (natural voice), e.g. kokoro:af_heart
  /path/model.onnx -> Piper (old robotic voice, fallback)

Kokoro model files go in <repo>/voice/ (run setup_voice.sh first).
"""
import os, subprocess, sys, wave

S = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VOICE = "kokoro:af_heart"
KOKORO_SPEED = float(os.environ.get("KOKORO_SPEED", "1.1"))
_kokoro = None


def _kokoro_model():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        vd = os.path.join(S, "voice")
        _kokoro = Kokoro(os.path.join(vd, "kokoro-v1.0.onnx"), os.path.join(vd, "voices-v1.0.bin"))
    return _kokoro


def tts(text, path, voice=DEFAULT_VOICE, speed=None,
        piper_args=("--length_scale", "0.92", "--sentence_silence", "0.15")):
    """Write speech for `text` to the wav file `path` and return its duration in seconds."""
    if voice.startswith("kokoro:"):
        import numpy as np, soundfile as sf
        name = voice.split(":", 1)[1]
        lang = "en-gb" if name.startswith("b") else "en-us"
        samples, sr = _kokoro_model().create(text, voice=name, speed=speed or KOKORO_SPEED, lang=lang)
        pad = np.zeros(int(sr * 0.12), dtype=samples.dtype)  # short breath after each segment
        samples = np.concatenate([samples, pad])
        sf.write(path, samples, sr, subtype="PCM_16")
        return len(samples) / sr
    subprocess.run([sys.executable, "-m", "piper", "-m", voice, "-f", path, *piper_args],
                   input=text.encode(), check=True, capture_output=True)
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()
