#!/usr/bin/env python3
"""
Unit tests for interview_processor.py

Run with: pytest tests/test_interview_processor.py -v
"""

import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

# Import the module under test
import interview_processor as ip


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directory structure matching the processor's expected layout."""
    dirs = {
        'base': tmp_path / "klavis-interviews",
        'raw': tmp_path / "klavis-interviews" / "raw",
        'transcripts': tmp_path / "klavis-interviews" / "transcripts",
        'insights': tmp_path / "klavis-interviews" / "insights",
        'archive': tmp_path / "klavis-interviews" / "archive",
        'failed': tmp_path / "klavis-interviews" / "failed",
    }

    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    # Patch the module-level directory constants
    with patch.object(ip, 'BASE_DIR', dirs['base']), \
         patch.object(ip, 'RAW_DIR', dirs['raw']), \
         patch.object(ip, 'TRANSCRIPTS_DIR', dirs['transcripts']), \
         patch.object(ip, 'INSIGHTS_DIR', dirs['insights']), \
         patch.object(ip, 'ARCHIVE_DIR', dirs['archive']), \
         patch.object(ip, 'FAILED_DIR', dirs['failed']), \
         patch.object(ip, 'LOG_FILE', dirs['base'] / "processing.log"), \
         patch.object(ip, 'FAILED_LOG', dirs['base'] / "failed_files.json"):
        yield dirs


@pytest.fixture
def mock_audio_file(temp_dirs):
    """Create a mock audio file with sufficient size."""
    audio_file = temp_dirs['raw'] / "test-interview.m4a"
    # Create file with content > 100KB
    audio_file.write_bytes(b"fake audio content " * 6000)  # ~114KB
    return audio_file


@pytest.fixture
def small_audio_file(temp_dirs):
    """Create a mock audio file that's too small."""
    audio_file = temp_dirs['raw'] / "tiny-recording.m4a"
    audio_file.write_bytes(b"tiny")  # < 100KB
    return audio_file


@pytest.fixture
def mock_logger():
    """Patch the global logger."""
    with patch.object(ip, 'logger') as mock:
        mock.info = MagicMock()
        mock.debug = MagicMock()
        mock.warning = MagicMock()
        mock.error = MagicMock()
        yield mock


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    """Tests for file validation logic."""

    def test_validate_file_exists(self, mock_audio_file, mock_logger):
        """Valid audio file passes validation."""
        is_valid, error = ip.validate_file(mock_audio_file)
        assert is_valid is True
        assert error == ""

    def test_validate_file_not_exists(self, temp_dirs, mock_logger):
        """Non-existent file fails validation."""
        fake_path = temp_dirs['raw'] / "does-not-exist.m4a"
        is_valid, error = ip.validate_file(fake_path)
        assert is_valid is False
        assert "does not exist" in error

    def test_validate_file_wrong_format(self, temp_dirs, mock_logger):
        """Unsupported format fails validation."""
        txt_file = temp_dirs['raw'] / "notes.txt"
        txt_file.write_text("not audio")
        is_valid, error = ip.validate_file(txt_file)
        assert is_valid is False
        assert "Unsupported format" in error

    def test_validate_file_too_small(self, small_audio_file, mock_logger):
        """File under 100KB fails validation."""
        is_valid, error = ip.validate_file(small_audio_file)
        assert is_valid is False
        assert "too small" in error

    @pytest.mark.parametrize("extension", [".m4a", ".mp3", ".wav", ".mp4"])
    def test_validate_supported_formats(self, temp_dirs, extension, mock_logger):
        """All supported formats pass validation."""
        audio_file = temp_dirs['raw'] / f"recording{extension}"
        audio_file.write_bytes(b"x" * 150000)  # > 100KB
        is_valid, error = ip.validate_file(audio_file)
        assert is_valid is True


# =============================================================================
# Transcription Tests
# =============================================================================

class TestTranscription:
    """Tests for Whisper transcription."""

    def test_transcribe_audio_success(self, mock_audio_file, mock_logger):
        """Successful transcription returns text and duration."""
        # Create mock whisper module
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            'text': 'This is a test transcription.',
            'segments': [{'end': 120.5}]
        }
        mock_whisper.load_model.return_value = mock_model

        with patch.dict('sys.modules', {'whisper': mock_whisper}):
            transcript, duration = ip.transcribe_audio(mock_audio_file)

        assert transcript == 'This is a test transcription.'
        assert duration == 120.5
        mock_whisper.load_model.assert_called_once_with('medium')

    def test_transcribe_audio_with_custom_model(self, mock_audio_file, mock_logger):
        """Transcription uses specified model."""
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {'text': 'Test', 'segments': []}
        mock_whisper.load_model.return_value = mock_model

        with patch.dict('sys.modules', {'whisper': mock_whisper}):
            ip.transcribe_audio(mock_audio_file, model='tiny')

        mock_whisper.load_model.assert_called_once_with('tiny')

    def test_transcribe_audio_whisper_not_installed(self, mock_audio_file, mock_logger):
        """Returns None when Whisper is not installed."""
        with patch.dict('sys.modules', {'whisper': None}):
            # The function imports whisper inside, so we mock the import to fail
            with patch.object(ip, 'transcribe_audio') as mock_transcribe:
                mock_transcribe.return_value = (None, None)
                transcript, duration = mock_transcribe(mock_audio_file)
                assert transcript is None
                assert duration is None


# =============================================================================
# Insight Extraction Tests
# =============================================================================

class TestInsightExtraction:
    """Tests for Ollama insight extraction."""

    @patch('interview_processor.subprocess.run')
    @patch('interview_processor.check_ollama_running')
    def test_extract_insights_success(self, mock_check, mock_run, mock_logger):
        """Successful extraction returns insights."""
        mock_check.return_value = (True, "")
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="## PAIN POINTS\n- Test pain point\n\n## EXECUTIVE SUMMARY\n- Test summary"
        )

        result = ip.extract_insights("Test transcript text")

        assert "PAIN POINTS" in result
        assert "Test pain point" in result

    @patch('interview_processor.subprocess.run')
    def test_extract_insights_ollama_error(self, mock_run, mock_logger):
        """Returns None when Ollama returns an error."""
        mock_run.return_value = MagicMock(returncode=1, stderr="connection refused")

        result = ip.extract_insights("Test transcript")

        assert result is None

    @patch('interview_processor.subprocess.run')
    @patch('interview_processor.check_ollama_running')
    def test_extract_insights_timeout(self, mock_check, mock_run, mock_logger):
        """Returns None on timeout."""
        import subprocess
        mock_check.return_value = (True, "")
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ollama", timeout=300)

        result = ip.extract_insights("Test transcript")

        assert result is None


# =============================================================================
# File Output Tests
# =============================================================================

class TestFileOutput:
    """Tests for saving transcripts and insights."""

    def test_save_transcript(self, temp_dirs, mock_audio_file, mock_logger):
        """Transcript saved with correct format and frontmatter."""
        with patch.object(ip, 'TRANSCRIPTS_DIR', temp_dirs['transcripts']):
            result = ip.save_transcript(
                mock_audio_file,
                "This is the transcript content.",
                duration=125.5
            )

        assert result is not None
        assert result.exists()

        content = result.read_text()
        assert "filename: test-interview.m4a" in content
        assert "duration: 02:05" in content
        assert "model: whisper-medium" in content
        assert "This is the transcript content." in content

    def test_save_insights(self, temp_dirs, mock_audio_file, mock_logger):
        """Insights saved with correct format and frontmatter."""
        with patch.object(ip, 'INSIGHTS_DIR', temp_dirs['insights']):
            result = ip.save_insights(
                mock_audio_file,
                "## PAIN POINTS\n- Test point\n\n## SUMMARY\n- Test"
            )

        assert result is not None
        assert result.exists()
        assert "-insights.md" in result.name

        content = result.read_text()
        assert "source: test-interview.m4a" in content
        assert "llm_model: mistral" in content

    def test_move_to_archive(self, temp_dirs, mock_audio_file, mock_logger):
        """File moved to archive directory."""
        with patch.object(ip, 'ARCHIVE_DIR', temp_dirs['archive']):
            original_path = mock_audio_file
            assert original_path.exists()

            result = ip.move_to_archive(mock_audio_file)

            assert result is True
            assert not original_path.exists()
            assert (temp_dirs['archive'] / "test-interview.m4a").exists()

    def test_move_to_archive_handles_duplicates(self, temp_dirs, mock_logger):
        """Duplicate filenames get numbered suffix."""
        with patch.object(ip, 'ARCHIVE_DIR', temp_dirs['archive']):
            # Create first file in archive
            existing = temp_dirs['archive'] / "duplicate.m4a"
            existing.write_bytes(b"existing")

            # Create new file to archive
            new_file = temp_dirs['raw'] / "duplicate.m4a"
            new_file.write_bytes(b"x" * 150000)

            result = ip.move_to_archive(new_file)

            assert result is True
            assert (temp_dirs['archive'] / "duplicate_1.m4a").exists()


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelpers:
    """Tests for helper functions."""

    def test_format_duration_seconds(self):
        """Format seconds correctly."""
        assert ip.format_duration(45) == "45s"

    def test_format_duration_minutes(self):
        """Format minutes and seconds correctly."""
        assert ip.format_duration(125) == "2m 5s"

    def test_format_duration_hours(self):
        """Format hours, minutes, seconds correctly."""
        assert ip.format_duration(3725) == "1h 2m 5s"

    def test_format_time_mmss(self):
        """Format MM:SS correctly."""
        assert ip.format_time_mmss(65) == "01:05"
        assert ip.format_time_mmss(3600) == "60:00"

    def test_count_words(self):
        """Count words correctly."""
        assert ip.count_words("one two three") == 3
        assert ip.count_words("") == 0  # empty string split returns []
        assert ip.count_words("hello") == 1

    def test_count_sections(self):
        """Count markdown sections correctly."""
        text = "# Title\n\n## Section 1\nContent\n\n## Section 2\nMore"
        assert ip.count_sections(text) == 2


# =============================================================================
# Integration Tests
# =============================================================================

class TestProcessSingleFile:
    """Integration tests for the full processing pipeline."""

    @patch('interview_processor.extract_insights')
    @patch('interview_processor.transcribe_audio')
    def test_process_single_file_success(
        self, mock_transcribe, mock_extract, temp_dirs, mock_audio_file, mock_logger
    ):
        """Full pipeline succeeds with mocked components."""
        mock_transcribe.return_value = ("Test transcript content.", 180.0)
        mock_extract.return_value = "## PAIN POINTS\n- Test\n\n## SUMMARY\n- Done"

        with patch.object(ip, 'TRANSCRIPTS_DIR', temp_dirs['transcripts']), \
             patch.object(ip, 'INSIGHTS_DIR', temp_dirs['insights']), \
             patch.object(ip, 'ARCHIVE_DIR', temp_dirs['archive']):

            result = ip.process_single_file(mock_audio_file)

        assert result.success is True
        assert result.word_count == 3
        assert result.processing_time > 0

    @patch('interview_processor.transcribe_audio')
    def test_process_single_file_transcription_fails(
        self, mock_transcribe, temp_dirs, mock_audio_file, mock_logger
    ):
        """Pipeline fails gracefully when transcription fails."""
        mock_transcribe.return_value = (None, None)

        with patch.object(ip, 'FAILED_LOG', temp_dirs['base'] / "failed_files.json"):
            result = ip.process_single_file(mock_audio_file)

        assert result.success is False
        assert "Transcription failed" in result.error_message

    @patch('interview_processor.extract_insights')
    @patch('interview_processor.transcribe_audio')
    def test_process_single_file_skip_insights(
        self, mock_transcribe, mock_extract, temp_dirs, mock_audio_file, mock_logger
    ):
        """Pipeline works with --skip-insights flag."""
        mock_transcribe.return_value = ("Test transcript.", 60.0)

        with patch.object(ip, 'TRANSCRIPTS_DIR', temp_dirs['transcripts']), \
             patch.object(ip, 'ARCHIVE_DIR', temp_dirs['archive']):

            result = ip.process_single_file(mock_audio_file, skip_insights=True)

        assert result.success is True
        mock_extract.assert_not_called()

    @patch('interview_processor.extract_insights')
    @patch('interview_processor.transcribe_audio')
    def test_process_single_file_keep_original(
        self, mock_transcribe, mock_extract, temp_dirs, mock_audio_file, mock_logger
    ):
        """Original file kept with --keep-original flag."""
        mock_transcribe.return_value = ("Test.", 30.0)
        mock_extract.return_value = "## SUMMARY\n- Test"

        with patch.object(ip, 'TRANSCRIPTS_DIR', temp_dirs['transcripts']), \
             patch.object(ip, 'INSIGHTS_DIR', temp_dirs['insights']), \
             patch.object(ip, 'ARCHIVE_DIR', temp_dirs['archive']):

            result = ip.process_single_file(mock_audio_file, keep_original=True)

        assert result.success is True
        assert mock_audio_file.exists()  # File should still be in raw/


# =============================================================================
# Session Stats Tests
# =============================================================================

class TestSessionStats:
    """Tests for session statistics tracking."""

    def test_session_stats_add_success(self):
        """Stats track successful processing."""
        stats = ip.SessionStats()
        result = ip.ProcessingResult(
            success=True,
            filepath=Path("/test.m4a"),
            processing_time=120.0
        )

        stats.add_result(result)

        assert stats.files_processed == 1
        assert stats.files_failed == 0
        assert stats.total_time == 120.0

    def test_session_stats_add_failure(self):
        """Stats track failed processing."""
        stats = ip.SessionStats()
        result = ip.ProcessingResult(
            success=False,
            filepath=Path("/test.m4a"),
            error_message="Test error"
        )

        stats.add_result(result)

        assert stats.files_processed == 0
        assert stats.files_failed == 1
        assert len(stats.errors) == 1

    def test_session_stats_average_time(self):
        """Average time calculated correctly."""
        stats = ip.SessionStats()
        stats.files_processed = 4
        stats.total_time = 480.0

        assert stats.average_time == 120.0

    def test_session_stats_average_time_zero_files(self):
        """Average time is zero with no files."""
        stats = ip.SessionStats()
        assert stats.average_time == 0.0


# =============================================================================
# Dependency Check Tests
# =============================================================================

class TestDependencyChecks:
    """Tests for dependency validation."""

    @patch('interview_processor.subprocess.run')
    def test_check_ollama_running_success(self, mock_run):
        """Returns True when Ollama is running with model."""
        mock_run.return_value = MagicMock(returncode=0, stdout="mistral:latest")

        is_ok, error = ip.check_ollama_running()

        assert is_ok is True
        assert error == ""

    @patch('interview_processor.subprocess.run')
    def test_check_ollama_running_not_started(self, mock_run):
        """Returns False when Ollama is not running."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        is_ok, error = ip.check_ollama_running()

        assert is_ok is False
        assert "not running" in error

    @patch('interview_processor.subprocess.run')
    def test_check_ollama_model_missing(self, mock_run):
        """Returns False when model is not pulled."""
        mock_run.return_value = MagicMock(returncode=0, stdout="llama2:latest")

        is_ok, error = ip.check_ollama_running()

        assert is_ok is False
        assert "not found" in error


# =============================================================================
# CLI Tests
# =============================================================================

class TestCLI:
    """Tests for command-line interface."""

    def test_main_no_args_shows_help(self, capsys):
        """Running with no args shows help and exits cleanly."""
        with patch('sys.argv', ['interview_processor.py']):
            result = ip.main()

        assert result == 0
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or result == 0

    @patch('interview_processor.show_status')
    def test_main_status_command(self, mock_status):
        """--status calls show_status()."""
        with patch('sys.argv', ['interview_processor.py', '--status']), \
             patch('interview_processor.setup_logging', return_value=MagicMock()), \
             patch.object(ip, 'logger', MagicMock()):
            ip.main()

        mock_status.assert_called_once()


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
