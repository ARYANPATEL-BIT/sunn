import io
import subprocess

import imageio_ffmpeg
import soundfile


def to_wav(src_path, dst_path, rate=16000):
    """Convert any upload (webm/ogg/mp4 from MediaRecorder) to mono 16-bit PCM WAV. 16 kHz is
    the rate the Prisma docs say it resamples to. bitexact keeps ffmpeg's version string out of
    the file, so the same recording always hashes the same."""
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", src_path,
         "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", "-map_metadata", "-1",
         "-fflags", "+bitexact", "-flags:a", "+bitexact", dst_path],
        check=True,
    )


def seconds(audio):
    """Duration of a wav given as a path or as bytes, or None if it can't be read."""
    try:
        return soundfile.info(io.BytesIO(audio) if isinstance(audio, bytes) else audio).duration
    except RuntimeError:
        return None
