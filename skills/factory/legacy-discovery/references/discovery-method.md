# Discovery method

Static, dependency-free scan:
- File extensions → language classification (`_LANG_BY_EXT`).
- Filenames matching common hints (`main`, `app`, `index`, `server`, ...) → entry points.
- VCS/build/vendor directories are skipped to avoid noise.

The scan never executes the target code; it only reads file metadata and names,
so it is safe to run on untrusted repositories.
