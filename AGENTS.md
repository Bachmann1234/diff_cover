# AGENTS.md

Welcome! This document provides an architectural map, subsystem breakdown, data-flow guide, and codebase conventions for agents working on `diff_cover`.

---

## 1. Project Overview & Capabilities

`diff_cover` provides two primary CLI tools designed to inspect modified code within Git diffs:
1. **`diff-cover`** (`diff_cover.diff_cover_tool`): Compares lines modified in a diff against code coverage reports (supports Cobertura, Clover, JaCoCo XML, and LCOV).
2. **`diff-quality`** (`diff_cover.diff_quality_tool`): Compares lines modified in a diff against violations reported by code quality / linter tools (supports 15+ built-in drivers or custom pluggy plugins).

Both tools support:
- Filtering against git diffs (committed vs uncommitted, staged vs unstaged, untracked files, custom base branch, `...` vs `..` range notation, diff files).
- Multi-format report outputs: Terminal/console, HTML (with pygments syntax highlighting), Markdown, JSON, and GitHub Actions workflow annotations.
- Failure thresholds via `--fail-under <SCORE>`, exiting with status code `1` if coverage/quality is below the specified target or `0` on success.
- Project configuration via TOML (`pyproject.toml` or standalone config files under `[tool.diff_cover]` and `[tool.diff_quality]`).

---

## 2. Directory Structure & Key Components

```
diff_cover/
├── command_runner.py          # Subprocess runner, exit code checking, ExecutableNotFoundError
├── config_parser.py           # TOML parser reading [tool.diff_cover] & [tool.diff_quality]
├── diff_cover_tool.py         # Entry point & CLI parsing for `diff-cover`
├── diff_quality_tool.py       # Entry point & CLI parsing for `diff-quality`
├── diff_reporter.py           # Git diff parser (GitDiffReporter, BaseDiffReporter)
├── git_diff.py                # Wrapper around `git diff` and diff files (GitDiffTool, GitDiffFileTool)
├── git_path.py                # Path normalization & conversion between git root and cwd (GitPathTool)
├── hookspecs.py               # Pluggy hook specification for 3rd-party quality plugins
├── report_generator.py        # Report generators (HTML, Console, Markdown, JSON, GitHub Annotations)
├── snippets.py                # Source snippet extraction & syntax highlighting with Pygments
├── util.py                    # Path helpers (to_unix_path), unescaping filenames, open_file helper
├── templates/                 # Jinja2 templates for all report output formats
│   ├── console_coverage_report.txt
│   ├── console_quality_report.txt
│   ├── html_coverage_report.html
│   ├── html_quality_report.html
│   ├── markdown_coverage_report.md
│   ├── markdown_quality_report.md
│   ├── github_coverage_annotations.txt
│   └── snippet_content.*
└── violationsreporters/       # Coverage and quality report parsers & driver implementations
    ├── base.py                # BaseViolationReporter, QualityDriver, RegexBasedDriver, Violation namedtuple
    ├── clover.py              # CloverFileIndex: two-tier fast indexing for Clover XML
    ├── java_violations_reporter.py # Java drivers (Checkstyle XML, Findbugs, PMD)
    └── violations_reporter.py # XmlCoverageReporter (Cobertura/Clover/JaCoCo), LcovCoverageReporter,
                               # and Python/JS/C++ drivers (Pylint, Flake8, Ruff, Mypy, ESLint, etc.)

tests/                         # Comprehensive pytest test suite
├── conftest.py                # Global fixtures (e.g. GitPathTool reset fixture)
├── helpers.py                 # Test helpers: mock diff generator, fixture loader
└── fixtures/                  # Coverage reports, sample diffs, and dummy source files
```

---

## 3. Architecture & Data Flow

### 3.1. `diff-cover` Pipeline

```
[CLI / Config]
      │
      ▼
parse_coverage_args() ──► GitPathTool.set_cwd()
      │
      ▼
GitDiffTool / GitDiffFileTool ──► execute `git diff` (or read diff file)
      │
      ▼
GitDiffReporter ──► parse unified diff hunks into {src_path: [changed_line_numbers]}
      │
      ▼
XmlCoverageReporter / LcovCoverageReporter ──► parse coverage XML/LCOV
      │
      ▼
DiffViolations ──► Set intersection: (diff_lines ∩ measured_lines ∩ violation_lines)
      │
      ▼
ReportGenerator (Html / Markdown / String / Json / GitHubAnnotations)
      │
      ▼
Write bytes to output stream / file & evaluate `--fail-under`
```

### 3.2. `diff-quality` Pipeline

```
[CLI / Config]
      │
      ▼
parse_quality_args() ──► GitPathTool.set_cwd()
      │
      ▼
Resolve driver (QUALITY_DRIVERS or pluggy hook `diff_cover_report_quality`)
      │
      ├── (A) If pre-generated reports provided: driver.parse_reports(file_handles)
      └── (B) If live check: driver.installed() ──► execute driver.command on changed files
      │
      ▼
QualityReporter ──► maps violations to Unix paths relative to git root
      │
      ▼
GitDiffReporter ──► filters violations to lines changed in the diff
      │
      ▼
QualityReportGenerator ──► renders results & checks `--fail-under`
```

---

## 4. Deep-Dive into Core Subsystems

### 4.1. Git & Diff Processing (`git_diff.py`, `diff_reporter.py`, `git_path.py`)

- **`GitDiffTool`**:
  - Executes git diff commands using `-U0` (unified diff with 0 lines of context) to precisely isolate modified lines.
  - Generates diffs for committed changes (`diff_committed`), staged changes (`diff_staged`), unstaged changes (`diff_unstaged`), and untracked files (`untracked`).
  - Supports `--diff-range-notation`: `...` (symmetric difference, merge-base) or `..` (tip-to-tip comparison).
  - Handles `--ignore-whitespace` via `--ignore-all-space` and `--ignore-blank-lines`.
- **`GitDiffFileTool`**:
  - Subclass of `GitDiffTool` for reading diffs from a file directly instead of shelling out to git.
- **`GitDiffReporter`**:
  - Parses unified diff hunks (`@@ -start,len +start,len @@`). Tracks additions (`+`), deletions (`-`), and calculates the final line numbers for modified source files.
  - Applies file include/exclude patterns and validates supported file extensions.
  - Returns `{src_path: [line_numbers]}` with unique, sorted line numbers.
- **`GitPathTool`**:
  - Crucial bridge between git diff paths and filesystem paths.
  - Normalizes paths relative to current working directory (`relative_path`) and git repository root (`absolute_path`).
  - **Important invariant**: `_cwd` and `_root` are stored as class variables.

### 4.2. Coverage & Violation Reporters (`violationsreporters/`)

- **`Violation` namedtuple**: `Violation(line: int, message: str)`.
- **`BaseViolationReporter`**: Abstract base defining:
  - `violations(src_path) -> List[Violation]`
  - `measured_lines(src_path) -> Optional[Set[int]]` (returning `None` signals all changed lines in the file are measured).
  - `name() -> str`
- **`XmlCoverageReporter`**:
  - Inspects XML root elements to dynamically classify report type: Cobertura, Clover, or JaCoCo.
  - Resolves source paths using `sources/source` elements and handles `src_roots` (for Java projects).
  - Supports `branch_coverage=True` by extracting condition-coverage attributes (e.g. `50% (1/2)` in Cobertura) and treating partially covered branches as violations.
  - Supports `expand_coverage_report=True` to append missing lines based on hits of adjacent lines.
- **`CloverFileIndex` (`clover.py`)**:
  - Optimizes Clover XML parsing by indexing `<file>` nodes into `_by_relative_path` and `_by_last_segment` maps. Avoids quadratic $O(N \times M)$ tree scans on large test suites.
- **`LcovCoverageReporter`**:
  - Parses LCOV format records: `SF` (source file), `DA` (line hit counts), `BRDA` (branch data), and `end_of_record`.
- **`QualityDriver` & `RegexBasedDriver` (`base.py`)**:
  - `RegexBasedDriver`: Implements regex parsing on linter output (e.g. `path:line: message`).
  - `QualityReporter`: Wraps a driver; either parses pre-generated report files or invokes the linter CLI across modified files in batches.
- **Plugin Architecture**:
  - Pluggy hookspec: `@hookspec def diff_cover_report_quality(reports, options)` in `diff_cover.hookspecs`.
  - External packages register plugins via setuptools entry point `diff_cover`.

### 4.3. Reporting & Snippet Generation (`report_generator.py`, `snippets.py`)

- **`DiffViolations`**:
  - Computes the intersection between lines modified in the diff, lines measured by test coverage / linters, and lines flagged as violations.
- **`BaseReportGenerator`**:
  - Calculates metrics: `percent_covered(src_path)`, `total_percent_covered()`, `total_num_lines()`, `total_num_violations()`.
- **`TemplateReportGenerator`**:
  - Renders Jinja2 templates with `TEMPLATE_ENV` configured with gettext i18n support.
  - Combines adjacent violation lines for compact display (e.g. `[1, 2, 3, 5]` -> `["1-3", "5"]`).
  - All report generators write raw encoded bytes (`output_file.write(content.encode("utf-8"))`).
- **`Snippet` (`snippets.py`)**:
  - Extracts code surrounding violation lines with context (`NUM_CONTEXT_LINES = 4`).
  - Splits snippets when gap exceeds `MAX_GAP_IN_SNIPPET = 4`.
  - Formats with Pygments for syntax-highlighted HTML, terminal colors, or Markdown code blocks.
  - Supports `--show-covered` to highlight covered diff lines (green) alongside violations (red).
  - Robust multi-encoding fallback: tries UTF-8, checks `chardet` with confidence threshold, and falls back to `cp1252`.

### 4.4. Configuration System (`config_parser.py`)

- Loads configuration from TOML files (`pyproject.toml` or custom path).
- Sections supported: `[tool.diff_cover]` and `[tool.diff_quality]`.
- Precedence: Defaults < Config File < CLI Flags.
- `_normalize_patterns`: Normalizes `include` and `exclude` inputs so both strings and arrays are consistently handled as lists.

---

## 5. Testing Patterns & Practices

The test suite lives under `tests/` and uses `pytest`:

### 5.1. Test Isolation & `GitPathTool`
- `GitPathTool` maintains class-level state (`_cwd`, `_root`).
- `tests/conftest.py` has an `autouse=True` fixture `reset_git_path_tool` that resets these class variables before and after every test. If creating tests that set custom working directories, this fixture ensures isolation.

### 5.2. Test Fixtures & Helpers (`tests/helpers.py`)
- **`fixture_path(rel_path)` / `load_fixture(rel_path)`**: Loads files from `tests/fixtures/`.
- **`git_diff_output(diff_dict, deleted_files=None)`**: Synthesizes realistic git diff outputs for unit tests without needing a real git repo.
- **`pytest-datadir`**: For tests that need dedicated data files, create a folder matching the test module name (e.g. `tests/test_clover_violations_reporter/test.xml`) and inject `datadir`.
- **Mocking Git & Commands**: Check `tests/test_integration.py` for examples of mocking `subprocess.Popen` via `patch_git_command` to test end-to-end CLI execution safely.

### 5.3. Documentation
- **AGENTS.md**: Each time you change something in the codebase / test / lint setup check if you need to update the `AGENTS.md` and/or `README.md`.

---

## 6. Development Workflows & Commands

All development dependencies and scripts are managed with **Poetry**:

### Running Tests
```bash
# Run the entire test suite
poetry run pytest

# Run a specific test file
poetry run pytest tests/test_diff_cover_tool.py

# Run a specific test matching an expression
poetry run pytest tests/test_diff_cover_tool.py -k test_show_covered

# Run tests in parallel with coverage (as in CI)
poetry run pytest -n auto --cov-context test --cov --cov-report=xml tests
```

### Code Formatting
```bash
# Format codebase with Black
poetry run black diff_cover tests

# Sort imports with isort
# Note: On Windows, prefix with $env:PYTHONUTF8=1 in PowerShell to avoid charmap encoding errors
poetry run isort diff_cover tests
```

---

## 7. Key Invariants & Gotchas for Implementers

1. **Path Separators (`/` vs `\`)**:
   - `git diff` always emits forward slashes (`/`), while Windows filesystems use backslashes (`\`).
   - Always use `diff_cover.util.to_unix_path()` or `GitPathTool` when handling, storing, or comparing file paths.
2. **Byte-Oriented Output**:
   - Report generators (`generate_report`, `generate_css`) expect output streams that accept raw `bytes` (e.g., `sys.stdout.buffer`, `io.BytesIO`, or files opened with mode `"wb"`). Always use `diff_cover.util.open_file(path, "wb")`.
3. **Subprocess & Missing Tools**:
   - External quality tools might not be installed on the user's system. Always handle `ExecutableNotFoundError` gracefully and provide clear error messages.
4. **Backward Compatibility in CLI Options**:
   - Legacy options like `--html-report`, `--json-report`, `--markdown-report` are handled via `handle_old_format()` and translated to `--format <type>:<path>`. Maintain support for both representations when updating CLI arguments.
5. **Set-Based Arithmetic in Reporters**:
   - `measured_lines` returning `None` indicates that every line in the file was analyzed (common for linters). If `measured_lines` is an empty set `set()`, it indicates the file was completely unmeasured. Ensure this distinction is preserved.
