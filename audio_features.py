import numpy as np
import librosa
import io
import soundfile as sf
from functools import lru_cache


TARGET_SR = 8000
MAX_ANALYSIS_SEC = 30


def extract_audio_features(audio_bytes: bytes, transcript: str):
    """
    Fast + safe audio feature extraction
    """
    try:
        # Decode WAV bytes correctly
        with sf.SoundFile(io.BytesIO(audio_bytes)) as f:
            y = f.read(dtype="float32")
            sr = f.samplerate
    except Exception as e:
        raise RuntimeError(f"Audio decode failed: {e}")

    return _extract_features(y, sr, transcript)


@lru_cache(maxsize=32)
def _extract_features_cached(y_hash, sr, transcript):
    # This function is only called via wrapper
    return None


def _extract_features(y, sr, transcript):
    # ---------------- Resample ----------------
    if sr != TARGET_SR:
        y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
        sr = TARGET_SR

    # ---------------- Trim ----------------
    max_len = sr * MAX_ANALYSIS_SEC
    if len(y) > max_len:
        y = y[:max_len]

    duration = len(y) / sr
    if duration <= 0:
        return None

    # ---------------- Speaking rate ----------------
    word_count = len(transcript.split())
    speaking_rate = (word_count / duration) * 60 if duration > 0 else 0

    # ---------------- Energy (RMS) ----------------
    rms = librosa.feature.rms(
        y=y,
        frame_length=512,
        hop_length=256
    )[0]
    energy = float(np.mean(rms))

    # ---------------- Silence ----------------
    silence_threshold = 0.02
    silence_ratio = float(np.mean(rms < silence_threshold))
    total_silence = silence_ratio * duration

    # ---------------- FAST Pitch (piptrack) ----------------
    S = np.abs(librosa.stft(y, n_fft=512, hop_length=256))
    pitches, magnitudes = librosa.piptrack(S=S, sr=sr)

    # Flatten arrays
    pitches = pitches.flatten()
    magnitudes = magnitudes.flatten()

    # Keep only valid human pitch range
    valid = (
        (pitches > 80) &
        (pitches < 300) &
        (magnitudes > np.percentile(magnitudes, 75))
    )

    pitch_vals = pitches[valid]

    # SAFE pitch std
    pitch_std = float(np.std(pitch_vals)) if len(pitch_vals) > 10 else 0.0

    # ---------------- Normalization ----------------
    def clamp(v): return max(0, min(100, v))

    rate_score = clamp(100 - abs(speaking_rate - 130))
    energy_score = clamp((energy / 0.04) * 100)
    pitch_score = clamp(100 - pitch_std * 2.5)
    pause_score = clamp(100 - silence_ratio * 120)

    audio_confidence = (
        0.4 * pitch_score +
        0.35 * energy_score +
        0.25 * rate_score
    )

    fluency_score = (
        0.6 * pause_score +
        0.4 * rate_score
    )

    return {
        "speaking_rate_wpm": round(speaking_rate, 1),
        "total_silence_sec": round(total_silence, 2),
        "silence_ratio": round(silence_ratio, 3),
        "pitch_std": round(pitch_std, 2),
        "energy": round(energy, 4),
        "audio_confidence": round(audio_confidence, 2),
        "fluency_score": round(fluency_score, 2),
    }
