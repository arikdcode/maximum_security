#!/bin/bash
set -e

echo "" > zdump/context.txt

ctx_paths=(
    # scripts/build_win_bundle.sh
    # scripts/rebuild_and_run.sh
    # scripts/setup_on_linux.sh
    # scripts/test_on_linux.sh
    # main.sh
    scripts/win_build_and_launch.sh
    windows/run_on_windows.ps1
    app_src/main.py
    app_src/mod_launcher.py
)

for path in "${ctx_paths[@]}"; do
    echo "---- $path ----" >> zdump/context.txt
    cat "$path" >> zdump/context.txt
    echo "" >> zdump/context.txt
    echo "" >> zdump/context.txt
done

# Send "tree" output to context as well
echo "---- Directory tree ----" >> zdump/context.txt
tree -a -I 'zdump|__pycache__|*.pyc|*.pyo|.git' >> zdump/context.txt || echo "(tree command failed)" >> zdump/context.txt
echo "" >> zdump/context.txt
echo "" >> zdump/context.txt

# Copy context to clipboard if possible with (xclip -selection clipboard zdump/context.txt)
if command -v xclip &> /dev/null; then
    xclip -selection clipboard zdump/context.txt
    echo "Context copied to clipboard."
else
    echo "xclip not found; context not copied to clipboard."
fi