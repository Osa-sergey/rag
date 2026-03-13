"""GigaAM-based audio transcriber with Silero VAD for long-form audio.

Converts Telegram OGG/Opus voice messages to WAV via ffmpeg,
then transcribes using GigaAM (supports MPS / Apple Silicon).
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class Transcriber:
    """Speech-to-text using GigaAM models.

    Supports short-form (≤25s) and long-form (via Silero VAD) audio.
    """

    def __init__(
        self,
        model_name: str = "v3_e2e_rnnt",
        use_vad: bool = True,
        vad_threshold: float = 0.5,
        max_short_duration: float = 25.0,
    ) -> None:
        import gigaam

        self._gigaam = gigaam
        self._model_name = model_name
        self._use_vad = use_vad
        self._vad_threshold = vad_threshold
        self._max_short_duration = max_short_duration

        logger.info("Loading GigaAM model '%s'...", model_name)
        self._model = gigaam.load_model(model_name)
        logger.info("GigaAM model loaded successfully")

        # Pre-load Silero VAD if needed
        self._vad_model = None
        if use_vad:
            self._load_silero_vad()

    def transcribe(self, audio_path: str | Path) -> str:
        """Transcribe audio file (OGG or WAV).

        Automatically converts OGG to WAV and selects short/long-form mode.
        """
        audio_path = Path(audio_path)

        # Convert OGG → WAV if needed
        if audio_path.suffix.lower() in (".ogg", ".oga", ".opus"):
            wav_path = self._convert_to_wav(audio_path)
        else:
            wav_path = str(audio_path)

        # Determine duration and pick transcription mode
        duration = self._get_audio_duration(wav_path)
        logger.info("Audio duration: %.1f seconds", duration)

        if duration <= self._max_short_duration:
            return self._transcribe_short(wav_path)
        else:
            return self._transcribe_long(wav_path)

    # ── Short-form transcription ──────────────────────────────

    def _transcribe_short(self, wav_path: str) -> str:
        """Direct transcription for audio ≤ 25 seconds."""
        text = self._model.transcribe(wav_path)
        logger.info("Short-form result: '%s'", text[:100])
        return text

    # ── Long-form transcription with Silero VAD ───────────────

    def _transcribe_long(self, wav_path: str) -> str:
        """Segment audio with Silero VAD and transcribe each segment."""
        import torch
        import torchaudio

        logger.info("Long-form transcription with Silero VAD")

        # Read audio
        waveform, sample_rate = torchaudio.load(wav_path)

        # Resample to 16kHz if needed (Silero VAD expects 16kHz)
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
            sample_rate = 16000

        # Mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Get VAD segments
        segments = self._get_vad_segments(waveform.squeeze(), sample_rate)
        logger.info("VAD detected %d speech segments", len(segments))

        # Transcribe each segment
        transcriptions = []
        for i, (start_sample, end_sample) in enumerate(segments):
            segment = waveform[:, start_sample:end_sample]

            # Save segment to temp WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                segment_path = f.name

            try:
                torchaudio.save(segment_path, segment, sample_rate)
                text = self._model.transcribe(segment_path)
                if text.strip():
                    transcriptions.append(text.strip())
                    logger.debug("Segment %d: '%s'", i, text[:80])
            finally:
                os.unlink(segment_path)

        result = " ".join(transcriptions)
        logger.info("Long-form result (%d segments): '%s'", len(transcriptions), result[:100])
        return result

    def _get_vad_segments(
        self, waveform, sample_rate: int
    ) -> list[tuple[int, int]]:
        """Run Silero VAD to get speech segment boundaries (in samples)."""
        import torch

        # Reset VAD state
        self._vad_model.reset_states()

        # Process in 512-sample chunks (Silero VAD requirement at 16kHz)
        window_size = 512
        speeches = []
        current_speech_start = None

        for i in range(0, len(waveform), window_size):
            chunk = waveform[i : i + window_size]
            if len(chunk) < window_size:
                chunk = torch.nn.functional.pad(chunk, (0, window_size - len(chunk)))

            prob = self._vad_model(chunk, sample_rate).item()

            if prob >= self._vad_threshold:
                if current_speech_start is None:
                    current_speech_start = i
            else:
                if current_speech_start is not None:
                    speeches.append((current_speech_start, i))
                    current_speech_start = None

        # Close final segment
        if current_speech_start is not None:
            speeches.append((current_speech_start, len(waveform)))

        # Merge close segments (gap < 0.3s)
        merged = self._merge_segments(speeches, sample_rate, gap_threshold=0.3)
        return merged

    @staticmethod
    def _merge_segments(
        segments: list[tuple[int, int]],
        sample_rate: int,
        gap_threshold: float = 0.3,
    ) -> list[tuple[int, int]]:
        """Merge speech segments that are close together."""
        if not segments:
            return []

        gap_samples = int(gap_threshold * sample_rate)
        merged = [segments[0]]

        for start, end in segments[1:]:
            prev_end = merged[-1][1]
            if start - prev_end <= gap_samples:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))

        return merged

    # ── Audio utilities ───────────────────────────────────────

    @staticmethod
    def _convert_to_wav(ogg_path: Path) -> str:
        """Convert OGG/Opus to 16kHz mono WAV via ffmpeg."""
        wav_path = str(ogg_path.with_suffix(".wav"))
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(ogg_path),
            "-ar", "16000",
            "-ac", "1",
            "-f", "wav",
            wav_path,
        ]
        logger.debug("Converting: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

        logger.info("Converted %s → %s", ogg_path.name, wav_path)
        return wav_path

    @staticmethod
    def _get_audio_duration(wav_path: str) -> float:
        """Get audio duration in seconds via ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            wav_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.warning("ffprobe failed, assuming short audio")
            return 10.0
        return float(result.stdout.strip())

    def _load_silero_vad(self) -> None:
        """Load Silero VAD model from torch.hub."""
        import torch

        logger.info("Loading Silero VAD model...")
        self._vad_model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )
        logger.info("Silero VAD loaded")
