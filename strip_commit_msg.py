"""Read commit message from stdin, remove 'Made-with: Cursor' lines, print to stdout."""
import sys
for line in sys.stdin:
    line_stripped = line.strip()
    if line_stripped == "Made-with: Cursor" or line_stripped == "Made with Cursor":
        continue
    print(line, end="")
