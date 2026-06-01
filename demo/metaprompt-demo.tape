# metaprompt-demo.tape — renders a LABELED real /metaprompt example to a GIF.
# /metaprompt is model-driven, so this is a faithful replay of a REAL example
# (docs/METAPROMPT-EXAMPLES.md, Example 1), not a live capture. No invented output.
# Render:  vhs demo/metaprompt-demo.tape  ->  demo/metaprompt-demo.gif
Output demo/metaprompt-demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 960
Set Padding 26
Set Theme "Catppuccin Mocha"
Set TypingSpeed 55ms

Hide
Type "source ~/.claude/memory-mcp/.venv/bin/activate && export MP_DEMO_PACE=1.5 && clear"
Enter
Sleep 600ms
Show

Type "python demo/metaprompt_demo.py"
Sleep 700ms
Enter
Sleep 6s
