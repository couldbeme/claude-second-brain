# coherence-check.tape — renders the hero Coherence-Yield demo to a GIF.
# REAL output, REAL numbers (CY 0.36 → 1.00) — runs the actual demo, no animation fakery.
# Render:  vhs demo/coherence-check.tape   →   demo/coherence-check.gif
Output demo/coherence-check.gif

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 800
Set Padding 26
Set Theme "Catppuccin Mocha"
Set TypingSpeed 55ms

# --- hidden setup: activate venv + enable GIF pacing so the on-screen command stays clean ---
Hide
Type "source ~/.claude/memory-mcp/.venv/bin/activate && export CY_DEMO_PACE=1.5 && clear"
Enter
Sleep 600ms
Show

# --- recorded: type the command, run it, hold so the 0.36 → 1.00 recovery reads ---
Type "python demo/coherence_check.py"
Sleep 700ms
Enter
Sleep 6s
