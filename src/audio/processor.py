"""
preprocessor.py

Audio preprocessing module for stutter detection system.
Handles cleaning, enhancement, and segmentation of audio signals.

Key Features:
   - Audio validation and normalization
   - Noise reduction
   - Speech enhancement
   - Audio segmentation
   - Quality checks
   - Silence detection
"""

import numpy as np
from typing import Tuple, Optional, Dict, List
import logging
from scipy import signal
from scipy.signal import butter, filtfilt
import librosa

from src.audio.audio_config import AudioConfig

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """
    Handles all preprocessing operations for audio analysis.

    This class provides methods for cleaning and preparing audio signals
    for stutter detection analysis.

    Attributes:
        config (AudioConfig): Audio configuration settings
        _noise_profile (Optional[np.ndarray]): Stored noise profile for reduction
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize preprocessor with configuration.

        Args:
            config (Optional[AudioConfig]): Audio configuration settings.
                If None, default settings will be used.
        """
        self.config = config or AudioConfig()
        self._noise_profile = None
        logger.info("AudioPreprocessor initialized with enhanced parameters")

    def process_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Main processing pipeline for audio data.

        Args:
            audio_data (np.ndarray): Raw audio signal

        Returns:
            np.ndarray: Processed audio signal
        """
        try:
            # Validate input
            if not self._validate_audio(audio_data):
                raise ValueError("Invalid audio data")

            # Apply processing steps
            audio = self._normalize_audio(audio_data)
            audio = self._reduce_noise(audio)
            audio = self._enhance_speech(audio)

            # Note: We don't remove silence here as it's important for stutter detection
            # Instead, we'll detect silences separately

            logger.info("Audio processing completed successfully")
            return audio

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise

    def _validate_audio(self, audio_data: np.ndarray) -> bool:
        """
        Validate audio data format and quality.

        Args:
            audio_data (np.ndarray): Audio data to validate

        Returns:
            bool: True if valid, False otherwise
        """
        if not isinstance(audio_data, np.ndarray):
            logger.error("Audio data must be numpy array")
            return False

        if len(audio_data.shape) != 1:
            logger.error("Audio must be mono channel")
            return False

        if len(audio_data) == 0:
            logger.error("Audio data is empty")
            return False

        return True

    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Normalize audio volume to consistent level.

        Args:
            audio_data (np.ndarray): Audio signal to normalize

        Returns:
            np.ndarray: Normalized audio signal
        """
        # Peak normalization
        peak = np.abs(audio_data).max()
        if peak > 0:
            normalized = audio_data / peak
        else:
            normalized = audio_data

        return normalized

    def _reduce_noise(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Reduce background noise in audio signal.

        Uses spectral subtraction method for noise reduction.

        Args:
            audio_data (np.ndarray): Audio signal

        Returns:
            np.ndarray: Noise-reduced audio signal
        """
        # Simple noise reduction using spectral gating
        S = librosa.stft(audio_data)
        mag = np.abs(S)
        phase = np.angle(S)

        # Estimate noise floor
        noise_floor = np.mean(mag, axis=1, keepdims=True)
        threshold = 2.0  # Adjust based on needs

        # Apply spectral gate
        mask = mag > threshold * noise_floor
        mag_reduced = mag * mask

        # Reconstruct signal
        S_reduced = mag_reduced * np.exp(1.0j * phase)
        audio_reduced = librosa.istft(S_reduced)

        return audio_reduced

    def _enhance_speech(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Enhance speech frequencies in audio signal.

        Applies bandpass filter to emphasize speech frequencies.

        Args:
            audio_data (np.ndarray): Audio signal

        Returns:
            np.ndarray: Enhanced audio signal
        """
        # Speech enhancement using bandpass filter
        nyquist = self.config.sample_rate / 2
        low_cutoff = 80 / nyquist  # 80 Hz
        high_cutoff = 3000 / nyquist  # 3000 Hz

        b, a = butter(4, [low_cutoff, high_cutoff], btype="band")
        enhanced = filtfilt(b, a, audio_data)

        return enhanced

    def detect_silences(self, audio_data: np.ndarray) -> List[Dict]:
        """
        Detect silent segments in audio.

        This is important for identifying blocks and pauses in speech.

        Args:
            audio_data (np.ndarray): Audio signal

        Returns:
            List[Dict]: List of silence segments with timing information
        """
        # Parameters for silence detection
        frame_length = int(0.025 * self.config.sample_rate)  # 25ms
        hop_length = int(0.010 * self.config.sample_rate)  # 10ms
        threshold_db = -40  # Silence threshold in dB
        min_silence_duration = 0.3  # Minimum silence duration in seconds

        # Get non-silent intervals
        intervals = librosa.effects.split(
            audio_data,
            top_db=-threshold_db,
            frame_length=frame_length,
            hop_length=hop_length,
        )

        # Convert to seconds
        intervals_sec = [
            (start / self.config.sample_rate, end / self.config.sample_rate)
            for start, end in intervals
        ]

        # Find silences between speech segments
        silences = []

        # Add silence at the beginning if needed
        if intervals_sec and intervals_sec[0][0] > 0:
            silences.append(
                {
                    "start": 0,
                    "end": intervals_sec[0][0],
                    "duration": intervals_sec[0][0],
                    "position": "beginning",
                }
            )

        # Add silences between speech segments
        for i in range(len(intervals_sec) - 1):
            silence_start = intervals_sec[i][1]
            silence_end = intervals_sec[i + 1][0]
            duration = silence_end - silence_start

            if duration >= min_silence_duration:
                silences.append(
                    {
                        "start": silence_start,
                        "end": silence_end,
                        "duration": duration,
                        "position": "middle",
                    }
                )

        # Add silence at the end if needed
        if (
            intervals_sec
            and intervals_sec[-1][1] < len(audio_data) / self.config.sample_rate
        ):
            end_time = len(audio_data) / self.config.sample_rate
            silences.append(
                {
                    "start": intervals_sec[-1][1],
                    "end": end_time,
                    "duration": end_time - intervals_sec[-1][1],
                    "position": "end",
                }
            )

        return silences

    def segment_audio(
        self, audio_data: np.ndarray, segment_length_ms: int = 1000
    ) -> List[np.ndarray]:
        """
        Segment audio into smaller chunks for analysis.

        Args:
            audio_data (np.ndarray): Audio signal
            segment_length_ms (int): Length of each segment in milliseconds

        Returns:
            List[np.ndarray]: List of audio segments
        """
        samples_per_segment = self.config.get_duration_samples(segment_length_ms)
        segments = []

        # Split audio into segments
        for start in range(0, len(audio_data), samples_per_segment):
            end = start + samples_per_segment
            if end <= len(audio_data):
                segment = audio_data[start:end]
                segments.append(segment)

        return segments

    def get_audio_quality_metrics(self, audio_data: np.ndarray) -> Dict[str, float]:
        """
        Calculate quality metrics for audio signal.

        Args:
            audio_data (np.ndarray): Audio signal

        Returns:
            Dict[str, float]: Dictionary of quality metrics
        """
        return {
            "snr": self._calculate_snr(audio_data),
            "peak_level": np.max(np.abs(audio_data)),
            "rms_level": np.sqrt(np.mean(audio_data**2)),
        }

    def _calculate_snr(self, audio_data: np.ndarray) -> float:
        """
        Calculate Signal-to-Noise Ratio.

        Args:
            audio_data (np.ndarray): Audio signal

        Returns:
            float: Estimated SNR in dB
        """
        noise_floor = np.mean(
            np.abs(audio_data[:1000])
        )  # Estimate from first 1000 samples
        signal = np.mean(np.abs(audio_data))

        if noise_floor == 0:
            return float("inf")

        snr = 20 * np.log10(signal / noise_floor)
        return snr


# Example usage
if __name__ == "__main__":
    try:
        # Create preprocessor
        preprocessor = AudioPreprocessor()

        # Load test audio (replace with actual audio data)
        test_audio = np.random.randn(16000)  # 1 second of random noise

        # Process audio
        processed_audio = preprocessor.process_audio(test_audio)

        # Get quality metrics
        metrics = preprocessor.get_audio_quality_metrics(processed_audio)
        print("Audio quality metrics:", metrics)

    except Exception as e:
        print(f"Error in preprocessing: {e}")
