# Two-minute demo script

1. Show the mission: a Python app behaves locally but not on a second machine or CI runner.
2. Run `envproof capture . --module json --module requests --output baseline.json` in the known-good environment.
3. In the failing environment, run the same command as `current.json`.
4. Run `envproof compare baseline.json current.json --format markdown --output drift-report.md`.
5. Open the report and show how each finding includes the observed evidence, why it may matter, and a suggested next check.
6. Run `python examples/demo_drift.py` to demonstrate a controlled manifest difference without needing two physical machines.
7. End with privacy properties and the limitation: differences are evidence-backed clues, not proof of root cause.

Recording format: 1920×1080 screen capture, terminal font 18–22 px, no personal environment variables or private package indexes visible, output report reviewed before recording. Target 90–120 seconds. No simulated counters, testimonials or fake benchmark claims.
