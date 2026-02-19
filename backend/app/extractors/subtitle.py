"""Subtitle extractor - SRT/VTT parsing."""
import re
from pathlib import Path
from typing import Optional

from app.extractors.models import TextSegment, TextSource


def parse_srt(content: str) -> list[TextSegment]:
    """Parse SRT content to TextSegments."""
    segments = []
    # Split by double newline (block separator)
    blocks = re.split(r'\n\s*\n', content.strip())
    time_pattern = re.compile(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})')

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        # First line is index, second is timestamp, rest is text
        match = time_pattern.search(lines[1])
        if not match:
            continue
        g = match.groups()
        start_sec = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
        end_sec = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
        text = ' '.join(line.strip() for line in lines[2:] if line.strip())
        if text:
            segments.append(TextSegment(
                source=TextSource.SUBTITLE,
                start_time=start_sec,
                end_time=end_sec,
                text=text,
                confidence=1.0,
            ))
    return segments


def parse_vtt(content: str) -> list[TextSegment]:
    """Parse WebVTT content to TextSegments."""
    # VTT has similar structure: NOTE/header, then 00:00:00.000 --> 00:00:02.000
    content = re.sub(r'^WEBVTT.*\n', '', content, flags=re.IGNORECASE)
    content = re.sub(r'^.*\d+\n', '', content)  # Remove optional cue identifiers
    # Use same pattern as SRT but allow . or , in timestamp
    return parse_srt(content)


class SubtitleExtractor:
    """Extract text from subtitle files or embedded subtitles."""

    def extract(
        self,
        media_path: str,
        subtitle_path: Optional[str] = None,
    ) -> list[TextSegment]:
        """Extract subtitles from file or video."""
        if subtitle_path:
            return self._parse_file(subtitle_path)
        # Try to find sidecar subtitle (same name, different ext)
        media_dir = Path(media_path).parent
        base = Path(media_path).stem
        for ext in [".srt", ".vtt"]:
            p = media_dir / f"{base}{ext}"
            if p.exists():
                return self._parse_file(str(p))
        # yt-dlp outputs e.g. video.zh-Hans.vtt - glob for any .srt/.vtt in same dir
        for pattern in [f"{base}.*.srt", f"{base}.*.vtt", "*.srt", "*.vtt"]:
            for p in media_dir.glob(pattern):
                if p.suffix.lower() in (".srt", ".vtt"):
                    return self._parse_file(str(p))
        return []

    def _parse_file(self, path: str) -> list[TextSegment]:
        p = Path(path)
        if not p.exists():
            return []
        content = p.read_text(encoding='utf-8', errors='ignore')
        ext = p.suffix.lower()
        if ext == '.srt':
            return parse_srt(content)
        if ext == '.vtt':
            return parse_vtt(content)
        return []
