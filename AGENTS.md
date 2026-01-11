# Repository Guidelines

## Project Structure & Module Organization
This repo is a small Python CLI with a few top-level modules:
- `interview_processor.py`: core CLI and processing pipeline.
- `watch_interviews.py`, `process_single.py`: entry points for watch/batch helpers.
- `tests/test_interview_processor.py`: pytest suite.
- `prompts/`: prompt text used for insight extraction.
- `dist/` and `foresight_transcribe.egg-info/`: build artifacts; do not edit.

## Build, Test, and Development Commands
- `pip install -e .` installs the package in editable mode.
- `python3 interview_processor.py --watch` runs watch mode locally.
- `python3 interview_processor.py --file path/to/audio.m4a` processes one file.
- `python3 interview_processor.py --batch` processes all pending files.
- `python3 interview_processor.py --test` runs the built-in smoke check.
- `pytest tests/test_interview_processor.py -v` runs the test suite.
- `bash setup.sh` installs local dependencies (Ollama, ffmpeg, models).

## Coding Style & Naming Conventions
- Python 3.9+; follow PEP 8, 4-space indentation, and module-level functions.
- Use `snake_case` for functions/variables, `UpperCamelCase` for classes, and
  `ALL_CAPS` for constants (see `interview_processor.py` config constants).
- Prefer small, single-purpose helpers; keep CLI behavior documented in help text.
- No formatter/linter is enforced; keep changes consistent with existing style.

## Testing Guidelines
- Framework: `pytest` (see `tests/test_interview_processor.py`).
- Name tests as `test_<behavior>`; group by feature in a class or section header.
- If you add CLI flags or output files, add/extend tests to cover them.

## Commit & Pull Request Guidelines
- Commit messages in this repo are short, imperative, and capitalized
  (e.g., `Fix badges`, `Add PyPI packaging`).
- PRs should include a clear description, testing notes, and any relevant
  output samples (transcript/insights) when behavior changes.
- Link related issues if applicable.

## Configuration & Local Paths
- Default config lives in `interview_processor.py` (`WHISPER_MODEL`,
  `OLLAMA_MODEL`, `MIN_FILE_SIZE`, `EXTRACTION_PROMPT`).
- Local workspace folders are created under `~/klavis-interviews/`
  (`raw/`, `transcripts/`, `insights/`, `archive/`, `processing.log`).
