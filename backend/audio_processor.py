# Audio signal processing and metadata extraction module
# Computes duration, sample rate, bitrate, loudness (dBFS), and signal-to-noise ratio (SNR) quality score

import os
import math
import subprocess
import numpy as np
import soundfile as sf
import mutagen
import imageio_ffmpeg
from typing import Dict, Any

# Returns the absolute path to the local ffmpeg binary
def get_ffmpeg_binary() -> str:
    # Use imageio_ffmpeg bundled binary as reliable cross-platform engine
    return imageio_ffmpeg.get_ffmpeg_exe()

# Converts any arbitrary audio format (WebM, OGG, M4A, MP3) into a standard 16-bit WAV for signal processing
def convert_to_wav(input_path: str, output_wav_path: str) -> bool:
    ffmpeg_exe = get_ffmpeg_binary()
    # Execute ffmpeg conversion command with standard sample rate
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", input_path,
        "-ac", "1",               # Convert to mono channel for uniform acoustic analysis
        "-ar", "44100",           # Resample to 44.1 kHz standard
        "-f", "wav",
        output_wav_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0

# Extracts comprehensive acoustic parameters from an uploaded or recorded audio file
def extract_audio_properties(file_path: str) -> Dict[str, Any]:
    file_size = os.path.getsize(file_path)
    temp_wav_path = file_path + ".temp.wav"

    duration_sec = 0.0
    sample_rate_hz = 44100
    bitrate_kbps = 128.0
    loudness_db = -24.0
    snr_db = 28.0
    quality_score = 80.0
    quality_label = "Good"

    # Step 1: Extract basic container metadata using mutagen
    try:
        audio_meta = mutagen.File(file_path)
        if audio_meta and audio_meta.info:
            if hasattr(audio_meta.info, "length") and audio_meta.info.length:
                duration_sec = float(audio_meta.info.length)
            if hasattr(audio_meta.info, "sample_rate") and audio_meta.info.sample_rate:
                sample_rate_hz = int(audio_meta.info.sample_rate)
            if hasattr(audio_meta.info, "bitrate") and audio_meta.info.bitrate:
                bitrate_kbps = float(audio_meta.info.bitrate) / 1000.0
    except Exception:
        pass

    # Step 2: Convert to WAV and perform acoustic waveform analysis with numpy and soundfile
    converted = convert_to_wav(file_path, temp_wav_path)
    wav_target = temp_wav_path if converted and os.path.exists(temp_wav_path) else file_path

    try:
        data, sr = sf.read(wav_target)
        if sr > 0:
            sample_rate_hz = sr
        if len(data) > 0:
            # Recompute accurate duration from sample count
            if duration_sec <= 0:
                duration_sec = len(data) / float(sr)

            # Ensure data is 1D float array
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            # Calculate Root Mean Square (RMS) loudness in dBFS
            rms = np.sqrt(np.mean(data ** 2) + 1e-12)
            loudness_db = float(20.0 * np.log10(rms + 1e-9))
            loudness_db = max(-90.0, min(0.0, loudness_db))

            # Estimate Noise Floor and Signal-to-Noise Ratio (SNR)
            frame_size = int(sr * 0.05)
            if len(data) >= frame_size:
                num_frames = len(data) // frame_size
                frames = data[:num_frames * frame_size].reshape((num_frames, frame_size))
                frame_energies = np.mean(frames ** 2, axis=1) + 1e-12

                # Signal energy = 95th percentile of frame energy; Noise floor = 5th percentile
                p95 = np.percentile(frame_energies, 95)
                p05 = np.percentile(frame_energies, 5)

                # Check if energy is dynamic (speech) or constant tone
                if p95 > p05 * 1.5:
                    snr_ratio = p95 / (p05 + 1e-12)
                    snr_db = float(10.0 * np.log10(snr_ratio))
                else:
                    # Constant tone or clean signal: estimate SNR against signal RMS relative to quantization noise
                    snr_db = max(20.0, float(-loudness_db))

                snr_db = max(5.0, min(50.0, snr_db))
                # Map SNR to 0 - 100 Quality Score (where 30dB SNR = 85/100)
                quality_score = float(min(100.0, max(10.0, (snr_db / 35.0) * 100.0)))
    except Exception as e:
        print(f"Warning: Acoustic analysis fallback triggered: {e}")
    finally:
        # Clean up temporary WAV conversion file
        if os.path.exists(temp_wav_path):
            try:
                os.remove(temp_wav_path)
            except Exception:
                pass

    # Calculate fallback bitrate from file size and duration if missing
    if (bitrate_kbps <= 0 or bitrate_kbps == 128.0) and duration_sec > 0:
        bitrate_kbps = (file_size * 8.0) / (duration_sec * 1000.0)

    # Classify quality label based on computed quality score
    if quality_score >= 80:
        quality_label = "Excellent"
    elif quality_score >= 65:
        quality_label = "Good"
    elif quality_score >= 45:
        quality_label = "Fair"
    else:
        quality_label = "Noisy / Low Quality"

    return {
        "file_size_bytes": file_size,
        "duration_seconds": round(duration_sec, 2),
        "sample_rate_hz": int(sample_rate_hz),
        "sample_rate_khz": round(sample_rate_hz / 1000.0, 2),
        "bitrate_kbps": round(bitrate_kbps, 2),
        "loudness_db": round(loudness_db, 2),
        "snr_quality_score": round(quality_score, 1),
        "quality_label": quality_label
    }
