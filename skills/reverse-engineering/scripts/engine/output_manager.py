"""
Output Manager
==============
Handles output directory creation, file writing, and manifest generation
for the reverse engineering pipeline.

The output structure is::

    outputs/
    └── {repo_name}/
        ├── {repo_name}_sdd.json
        ├── {repo_name}_dashboard.html
        ├── {repo_name}_report.md
        └── manifest.json          ← lists what was generated, timestamps, sizes

All file-writing operations are tracked internally so that
:meth:`OutputManager.write_manifest` can embed accurate file-size metrics,
and :meth:`OutputManager.summary_lines` can produce a formatted summary for
console output.
"""

import os
import json
import datetime
from pathlib import Path


class OutputManager:
    """Manages output directories and file writing for a single pipeline run.

    Attributes:
        repo_name (str): Repository name used as the output subdirectory.
        base_dir (str): Root outputs directory (default: ``"outputs"``).
        out_dir (Path): Full path to this run's output directory.

    Example::

        om = OutputManager("nopCommerce")
        om.write_json("nopCommerce_sdd.json", sdd_data)
        om.write_text("nopCommerce_report.md", md_content)
        om.write_manifest(files_analyzed=300, classes=132, endpoints=615)
    """

    def __init__(self, repo_name: str, base_dir: str = "."):
        """Initialise the manager and create the output directory if needed.

        Args:
            repo_name (str): Repository name; used as the subdirectory name
                under *base_dir*.
            base_dir (str): Root directory for all pipeline outputs.
                Defaults to ``"."`` (current working directory — outputs land
                in ``{cwd}/{repo_name}/`` next to where the skill is run).
                Pass ``"outputs"`` for the legacy behaviour.
        """
        self.repo_name = repo_name
        self.base_dir  = base_dir
        self.out_dir   = Path(base_dir) / repo_name
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._written: list[dict] = []

    def path_for(self, filename: str) -> Path:
        """Return the full :class:`~pathlib.Path` for a file in this run's output directory.

        Args:
            filename (str): Filename relative to the output directory
                (e.g. ``"manifest.json"``).

        Returns:
            Path: Absolute path to the file (the file is not created).
        """
        return self.out_dir / filename

    def write_json(self, filename: str, data: dict, indent: int = 2) -> Path:
        """Serialise *data* as indented JSON and write to the output directory.

        Args:
            filename (str): Output filename (e.g. ``"repo_sdd.json"``).
            data (dict): Dictionary to serialise.  Non-JSON-serialisable
                values (such as :class:`set`) are converted to lists via
                the ``default=list`` fallback.
            indent (int): JSON indentation level.  Defaults to ``2``.

        Returns:
            Path: Path to the written file.
        """
        out_path = self.out_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=list)
        self._written.append({
            "file": filename,
            "type": "json",
            "size": out_path.stat().st_size,
        })
        return out_path

    def write_text(self, filename: str, content: str) -> Path:
        """Write *content* as a UTF-8 text file to the output directory.

        Args:
            filename (str): Output filename (e.g. ``"repo_report.md"``).
            content (str): Text content to write.

        Returns:
            Path: Path to the written file.
        """
        out_path = self.out_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        self._written.append({
            "file": filename,
            "type": "text",
            "size": out_path.stat().st_size,
        })
        return out_path

    def write_manifest(self, **metrics) -> Path:
        """Write a ``manifest.json`` describing this pipeline run.

        The manifest records the generation timestamp, repository name, output
        directory path, a list of every file written (with size), and any
        arbitrary key-value metrics supplied by the caller.

        Args:
            **metrics: Arbitrary key-value metrics to embed in the manifest
                (e.g. ``files_analyzed=300``, ``classes=132``).

        Returns:
            Path: Path to the manifest file.
        """
        manifest = {
            "generated_at": (
                datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
            ),
            "repo_name": self.repo_name,
            "output_directory": str(self.out_dir),
            "files_written": self._written,
            "metrics": metrics,
        }
        return self.write_json("manifest.json", manifest)

    def summary_lines(self) -> list[str]:
        """Return formatted summary lines for each written file.

        Each line includes the absolute file path and its size in KB,
        suitable for printing to the console after a successful pipeline run.

        Returns:
            list[str]: One string per written file, e.g.
            ``["     * outputs/repo/repo_sdd.json  (142 KB)", ...]``.
        """
        lines = []
        for entry in self._written:
            kb = entry["size"] / 1024
            lines.append(f"     * {self.out_dir / entry['file']}  ({kb:.0f} KB)")
        return lines
