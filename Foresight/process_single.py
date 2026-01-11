#!/usr/bin/env python3
"""
process_single.py - Single audio file processor for interview transcription and analysis.

Processes an audio file through Whisper transcription and Ollama extraction,
producing structured markdown files with insights.

Usage:
    python process_single.py ~/klavis-interviews/raw/interview-123.m4a
"""

import argparse
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path.home() / "klavis-interviews"
RAW_DIR = BASE_DIR / "raw"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
INSIGHTS_DIR = BASE_DIR / "insights"
ARCHIVE_DIR = BASE_DIR / "archive"
LOG_FILE = BASE_DIR / "processing.log"

SUPPORTED_FORMATS = {".m4a", ".wav", ".mp3", ".mp4"}
MIN_FILE_SIZE_KB = 100
WHISPER_MODEL = "medium"
OLLAMA_MODEL = "mistral"

# =============================================================================
# Ollama Extraction Prompt
# =============================================================================

EXTRACTION_PROMPT = """You are analyzing a procurement stakeholder interview transcript. Extract the following in structured markdown format:

## PAIN POINTS
- [List specific problems mentioned with context]

## CURRENT WORKAROUNDS
- [How they handle issues today]

## RISK PATTERNS
- [Recurring failures or vulnerabilities observed]

## OBJECTIONS/CONCERNS
- [Hesitations about potential solutions]

## DECISION CRITERIA
- [What would make them buy/pilot a solution]

## FOLLOW-UP QUESTIONS
- [5-7 specific questions to ask in next conversation]

## KEY QUOTES
- "[Verbatim quotes worth preserving]"

## EXECUTIVE SUMMARY
- [2-3 sentence summary of the conversation]

TRANSCRIPT:
{transcript_text}"""

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    # Ensure base directory exists for log file
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("process_single")
    logger.setLevel(logging.DEBUG)

    # File handler - detailed logging
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Console handler - info and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()

# =============================================================================
# Helper Functions
# =============================================================================

def timestamp() -> str:
    """Return formatted timestamp for display."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_progress(emoji: str, message: str) -> None:
    """Log a progress message with timestamp and emoji."""
    logger.info(f"[{timestamp()}] {emoji} {message}")


def create_directories() -> None:
    """Create all required directories if they don't exist."""
    for directory in [RAW_DIR, TRANSCRIPTS_DIR, INSIGHTS_DIR, ARCHIVE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")


def format_duration(seconds: float) -> str:
    """Format duration in seconds to MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


# =============================================================================
# Validation Functions
# =============================================================================

def validate_file(file_path: Path) -> Tuple[bool, str]:
    """
    Validate the input audio file.

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file exists
    if not file_path.exists():
        return False, f"File does not exist: {file_path}"

    # Check file format
    if file_path.suffix.lower() not in SUPPORTED_FORMATS:
        return False, (
            f"Unsupported format: {file_path.suffix}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )

    # Check file size (> 100KB)
    file_size_kb = file_path.stat().st_size / 1024
    if file_size_kb < MIN_FILE_SIZE_KB:
        return False, (
            f"File too small ({file_size_kb:.1f}KB). "
            f"Minimum size: {MIN_FILE_SIZE_KB}KB. Skipping test recordings."
        )

    return True, ""


# =============================================================================
# Transcription Functions
# =============================================================================

def get_audio_duration(file_path: Path) -> Optional[float]:
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-show_entries",
                "format=duration", "-of", "json", str(file_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
        logger.warning(f"Could not determine audio duration: {e}")
        return None


def transcribe_audio(file_path: Path) -> Tuple[Optional[str], Optional[float]]:
    """
    Transcribe audio file using Whisper.

    Returns:
        Tuple of (transcript_text, duration_seconds) or (None, None) on failure
    """
    try:
        import whisper
    except ImportError:
        logger.error("Whisper not installed. Install with: pip install openai-whisper")
        return None, None

    log_progress("🎙️ ", "Transcribing... (this may take 2-3 minutes)")
    logger.debug(f"Loading Whisper model: {WHISPER_MODEL}")

    try:
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(str(file_path))

        transcript = result.get("text", "").strip()

        # Try to get duration from Whisper result or fallback to ffprobe
        duration = None
        if "segments" in result and result["segments"]:
            last_segment = result["segments"][-1]
            duration = last_segment.get("end")

        if duration is None:
            duration = get_audio_duration(file_path)

        logger.debug(f"Transcription complete. Length: {len(transcript)} chars")
        return transcript, duration

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return None, None


# =============================================================================
# Ollama Functions
# =============================================================================

def check_ollama_running() -> bool:
    """Check if Ollama is running and accessible."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def extract_insights(transcript: str) -> Optional[str]:
    """
    Send transcript to Ollama for insight extraction.

    Returns:
        Extracted insights as markdown string, or None on failure
    """
    if not check_ollama_running():
        logger.error(
            "Ollama is not running. Start it with:\n"
            "  ollama serve\n"
            "Then ensure the model is available:\n"
            f"  ollama pull {OLLAMA_MODEL}"
        )
        print(
            "\n❌ Ollama is not running. Please start it:\n"
            "   1. Open a new terminal\n"
            "   2. Run: ollama serve\n"
            f"   3. Then: ollama pull {OLLAMA_MODEL}\n"
        )
        return None

    log_progress("🧠", "Extracting insights...")
    logger.debug(f"Sending to Ollama model: {OLLAMA_MODEL}")

    prompt = EXTRACTION_PROMPT.format(transcript_text=transcript)

    try:
        result = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL, prompt],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for extraction
        )

        if result.returncode != 0:
            logger.error(f"Ollama returned error: {result.stderr}")
            return None

        insights = result.stdout.strip()
        logger.debug(f"Extraction complete. Length: {len(insights)} chars")
        return insights

    except subprocess.TimeoutExpired:
        logger.error("Ollama extraction timed out after 5 minutes")
        return None
    except Exception as e:
        logger.error(f"Ollama extraction failed: {e}")
        return None


# =============================================================================
# File Output Functions
# =============================================================================

def save_transcript(
    file_path: Path,
    transcript: str,
    duration: Optional[float]
) -> Optional[Path]:
    """
    Save transcript to markdown file with YAML frontmatter.

    Returns:
        Path to saved file, or None on failure
    """
    filename = file_path.stem
    output_path = TRANSCRIPTS_DIR / f"{filename}.md"

    duration_str = format_duration(duration) if duration else "Unknown"
    processed_date = datetime.now().isoformat()

    content = f"""---
filename: {file_path.name}
processed_date: {processed_date}
duration: {duration_str}
model: whisper-{WHISPER_MODEL}
---

# Transcript: {filename}

{transcript}
"""

    try:
        output_path.write_text(content, encoding="utf-8")
        log_progress("✅", "Transcript saved")
        logger.debug(f"Transcript saved to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to save transcript: {e}")
        return None


def save_insights(file_path: Path, insights: str) -> Optional[Path]:
    """
    Save insights to markdown file with YAML frontmatter.

    Returns:
        Path to saved file, or None on failure
    """
    filename = file_path.stem
    output_path = INSIGHTS_DIR / f"{filename}-insights.md"

    processed_date = datetime.now().isoformat()

    content = f"""---
source: {file_path.name}
processed_date: {processed_date}
llm_model: {OLLAMA_MODEL}
---

# Interview Insights: {filename}

{insights}
"""

    try:
        output_path.write_text(content, encoding="utf-8")
        log_progress("✅", "Insights saved")
        logger.debug(f"Insights saved to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to save insights: {e}")
        return None


def archive_file(file_path: Path) -> bool:
    """
    Move processed file to archive directory.

    Returns:
        True on success, False on failure
    """
    archive_path = ARCHIVE_DIR / file_path.name

    try:
        shutil.move(str(file_path), str(archive_path))
        log_progress("📦", "Moved to archive")
        logger.debug(f"Archived to: {archive_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to archive file: {e}")
        return False


# =============================================================================
# Main Processing Function
# =============================================================================

def process_file(file_path: Path) -> bool:
    """
    Process a single audio file through the full pipeline.

    Returns:
        True if fully successful, False if any step failed
    """
    log_progress("📁", f"Processing: {file_path.name}")
    logger.debug(f"Full path: {file_path}")

    # Step 1: Validate file
    is_valid, error_msg = validate_file(file_path)
    if not is_valid:
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        return False

    # Step 2: Transcribe with Whisper
    transcript, duration = transcribe_audio(file_path)
    if transcript is None:
        logger.error("Transcription failed - aborting")
        print("❌ Transcription failed. Check log for details.")
        return False

    # Step 3: Save transcript
    transcript_path = save_transcript(file_path, transcript, duration)
    if transcript_path is None:
        logger.error("Failed to save transcript - aborting")
        return False

    # Step 4: Extract insights with Ollama
    insights = extract_insights(transcript)
    if insights is None:
        logger.warning(
            "Insight extraction failed. Transcript saved but file not archived."
        )
        print("⚠️  Insight extraction failed. Transcript saved, file NOT archived.")
        return False

    # Step 5: Save insights
    insights_path = save_insights(file_path, insights)
    if insights_path is None:
        logger.warning("Failed to save insights. File not archived.")
        return False

    # Step 6: Archive original file
    if not archive_file(file_path):
        logger.warning("Failed to archive file, but processing complete.")

    log_progress("✨", "Complete!")
    return True


# =============================================================================
# CLI Entry Point
# =============================================================================

def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Process a single audio file for transcription and insight extraction.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python process_single.py ~/klavis-interviews/raw/interview-123.m4a
  python process_single.py ./my-recording.mp3

Supported formats: .m4a, .wav, .mp3, .mp4
        """
    )
    parser.add_argument(
        "audio_file",
        type=Path,
        help="Path to the audio file to process"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug output"
    )

    args = parser.parse_args()

    # Enable verbose console output if requested
    if args.verbose:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(logging.DEBUG)

    # Create required directories
    create_directories()

    # Resolve to absolute path
    file_path = args.audio_file.expanduser().resolve()

    # Process the file
    success = process_file(file_path)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
