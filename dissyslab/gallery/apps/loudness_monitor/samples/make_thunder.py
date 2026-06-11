#!/usr/bin/env python3
"""Regenerate ``thunderstorm.mp3`` (and ``thunderstorm.wav``).

The ``loudness_monitor`` office ships with a 60-second synthetic
thunderstorm clip so ``dsl run loudness_monitor`` works on a fresh
clone with no recording equipment, no internet, and no portaudio
install. This script is the recipe that produced that clip.

Run it from this folder::

    python make_thunder.py

It writes ``thunderstorm.wav`` and ``thunderstorm.mp3`` next to the
script. Output is deterministic — the same numpy seed produces the
same bytes.

Requirements
------------

    pip install numpy scipy

``ffmpeg`` on PATH if you want the MP3 (the WAV is always written).

Recipe
------

* 60 s total, mono, 16 kHz.
* Quiet background hiss at ~-55 dBFS so even the silent stretches
  carry a tiny non-zero RMS (otherwise the meter logs ``-inf``).
* 6 thunder claps at 4.0, 14.5, 23.8, 33.0, 44.2 and 53.5 seconds
  with peak amplitudes 0.55 / 0.85 / 0.70 / 0.95 / 0.65 / 0.80.
* Each clap is a 3.5 s envelope over (a) low-pass-filtered noise
  for the rumble below 150 Hz and (b) band-pass noise between
  200 Hz and 1200 Hz for the initial crack. 30 ms attack, ~3.5 s
  exponential decay.
* The whole file is normalised to 0.95 peak so the loudest 500 ms
  window measures around -14 dBFS — well above the office's
  default -30 dBFS threshold, so the detector fires confidently.
"""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, lfilter


SR = 16000
DURATION = 60.0
N = int(SR * DURATION)
HERE = Path(__file__).resolve().parent


def thunder_clap(rng, seconds: float = 3.5, peak_amp: float = 0.85):
    """Synthesise one thunder clap as a 1-D float array."""
    n = int(SR * seconds)
    # Rumble: white noise → low-pass at 150 Hz.
    b, a = butter(4, 150 / (SR / 2), "low")
    rumble = lfilter(b, a, rng.standard_normal(n))
    # Crack: band-pass 200–1200 Hz.
    b2, a2 = butter(4, [200 / (SR / 2), 1200 / (SR / 2)], "band")
    crack = lfilter(b2, a2, rng.standard_normal(n))
    sig = 1.0 * rumble + 0.4 * crack
    sig = sig / np.max(np.abs(sig))
    # ADSR envelope: ~30 ms attack to peak, ~3.5 s decay.
    attack_samples = int(SR * 0.030)
    env = np.exp(-np.linspace(0, 5.5, n))
    env[:attack_samples] = (
        np.linspace(0, 1, attack_samples) * env[attack_samples]
    )
    return sig * env * peak_amp


def db(x: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(x * x)))
    return 20.0 * np.log10(max(rms, 1e-10))


def main() -> None:
    rng = np.random.default_rng(42)  # deterministic output

    # ── Background hiss + 6 claps ────────────────────────────────
    audio = rng.standard_normal(N) * 0.002
    clap_times = [4.0, 14.5, 23.8, 33.0, 44.2, 53.5]
    clap_amps = [0.55, 0.85, 0.70, 0.95, 0.65, 0.80]
    for t, amp in zip(clap_times, clap_amps):
        clap = thunder_clap(rng, seconds=3.5, peak_amp=amp)
        start = int(t * SR)
        end = min(start + len(clap), N)
        audio[start:end] += clap[: end - start]

    # ── Normalise to 0.95 peak so MP3 encoding has headroom ──────
    audio = audio / float(np.max(np.abs(audio))) * 0.95

    # ── Quick check of the dB profile ────────────────────────────
    print(f"file mean dBFS:               {db(audio):.1f}")
    print(
        "quiet 1-s window @ 8.5s:      "
        f"{db(audio[int(8.5 * SR):int(9.5 * SR)]):.1f}"
    )
    print(
        "loudest 500 ms @ 33.0s:       "
        f"{db(audio[int(33.0 * SR):int(33.5 * SR)]):.1f}"
    )

    # ── Write WAV ────────────────────────────────────────────────
    wav_path = HERE / "thunderstorm.wav"
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(audio_int16.tobytes())
    print(f"\nWAV written: {wav_path.name}  "
          f"({wav_path.stat().st_size / 1024:.1f} KB)")

    # ── Encode MP3 if ffmpeg is available ───────────────────────
    mp3_path = HERE / "thunderstorm.mp3"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(wav_path),
                "-codec:a", "libmp3lame", "-b:a", "96k",
                str(mp3_path),
            ],
            check=True,
            capture_output=True,
        )
        print(f"MP3 written: {mp3_path.name}  "
              f"({mp3_path.stat().st_size / 1024:.1f} KB)")
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(
            f"\n[make_thunder] ffmpeg not available; skipping MP3. "
            f"WAV is enough for the office: {exc}"
        )


if __name__ == "__main__":
    main()
