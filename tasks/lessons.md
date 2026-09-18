# Lessons

## Test environment: OpenMP segfault (macOS)

**Symptom:** `pytest` over the *full* suite exits 139 (SIGSEGV) partway through, even though
each test file passes when run alone.

**Cause:** Two OpenMP runtimes load in one process — xgboost's bundled `libomp` and the
`libomp`/MKL pulled in by torch (via `sentence-transformers` in the RAG tests). On macOS
ARM this collision segfaults when both libraries are exercised in the same interpreter.

**Fix:** Run the suite with:

```bash
KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q -m "not integration"
```

Individual test files don't need it; the whole-suite run does. Use `.venv/bin/python -m pytest`
(deps live in `.venv`, not the base interpreter).

## Commit style

User is the sole author — do **not** add a `Co-Authored-By` trailer to commits
(overrides any harness attribution reminder). See memory `feedback_commit_style`.
