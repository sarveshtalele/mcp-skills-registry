"""
File Loaders
============
Responsible for walking a repository directory tree and reading all
supported source files into memory for downstream parsing.

Supported languages are determined by file extension via
``SUPPORTED_EXTENSIONS``.  Directories listed in ``SKIP_DIRS`` are
pruned from the walk to avoid noise from generated artifacts, virtual
environments, and IDE metadata.
"""

import os

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = [
    ".py", ".java", ".cs", ".ts", ".tsx", ".js", ".jsx",
    ".vb", ".go", ".rb", ".php", ".swift", ".kt", ".cpp", ".h",
]
"""list[str]: File extensions whose contents will be read by :func:`load_repo`.

Each entry must include the leading dot (e.g. ``".py"``).
"""

SKIP_DIRS = {
    "test", "tests", "__pycache__", ".git", "node_modules", "bin", "obj",
    ".vs", "vendor", "dist", "build", "coverage", "migrations", "wwwroot",
    "packages", ".idea", ".vscode", "target", "out", ".gradle",
}
"""set[str]: Directory names (case-insensitive) to exclude from the walk.

This prevents reading generated artifacts, dependency caches, IDE files,
and compiled output that would pollute the analysis.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_repo(repo_path, extensions=None):
    """Walk *repo_path* and return file records for every supported source file.

    The function recursively descends into subdirectories, pruning any whose
    lower-cased name appears in :data:`SKIP_DIRS` or contains a skip-dir
    substring.  For each qualifying file it reads the content as UTF-8,
    replacing undecodable bytes with the replacement character so that binary
    blobs do not crash the loader.

    Args:
        repo_path (str): Absolute or relative path to the root of the cloned
            repository.
        extensions (list[str] | None): Whitelist of file extensions to read.
            When ``None`` (default) :data:`SUPPORTED_EXTENSIONS` is used.

    Returns:
        list[dict]: Each element is a ``{"path": str, "content": str}`` dict
        where *path* is the absolute filesystem path and *content* is the raw
        UTF-8 text of the file.

    Raises:
        Nothing — read errors are caught and a warning is printed instead so
        that a single unreadable file does not abort the whole run.
    """
    if extensions is None:
        extensions = SUPPORTED_EXTENSIONS

    files_data = []
    for root, dirs, files in os.walk(repo_path):
        # Prune the directory list in-place to avoid descending into skipped dirs.
        dirs[:] = [
            d for d in dirs
            if d.lower() not in SKIP_DIRS
            and not any(skip in d.lower() for skip in SKIP_DIRS)
        ]

        for fname in files:
            if any(fname.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, fname)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        files_data.append({"path": full_path, "content": f.read()})
                except Exception as e:
                    print(f"  [WARN] Could not read {full_path}: {e}")

    return files_data
