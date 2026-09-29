"""Strip the in-figure suptitles from make_figures_sci.py.

The report already prints "Abb. N ..." as a figcaption, so a title baked into
the image duplicates it on the page. This edits the generator in place, once,
and is idempotent.
"""
import pathlib
import re

p = pathlib.Path(__file__).resolve().parent / "make_figures_sci.py"
t = p.read_text(encoding="utf-8")

if "SUP-TITLES STRIPPED" in t:
    print("already stripped")
    raise SystemExit

out, i, n = [], 0, 0
lines = t.split("\n")
while i < len(lines):
    line = lines[i]
    if "fig.suptitle(" in line:
        # consume until the statement ends (balanced parens, ends with a line
        # whose paren depth returns to zero)
        block = [line]
        depth = line.count("(") - line.count(")")
        while depth > 0 and i + 1 < len(lines):
            i += 1
            block.append(lines[i])
            depth += lines[i].count("(") - lines[i].count(")")
        out.append("    # SUP-TITLE REMOVED: the report caption supplies it")
        n += 1
        i += 1
        continue
    out.append(line)
    i += 1

t = "\n".join(out)
t = t.replace('    fig.tight_layout(rect=(0, 0, 1, 0.94))\n    save(fig,',
              '    fig.tight_layout(rect=(0, 0, 1, 1.0))\n    save(fig,')
t = t.replace('    fig.tight_layout(rect=(0, 0.04, 1, 0.95))\n    save(fig,',
              '    fig.tight_layout(rect=(0, 0.04, 1, 1.0))\n    save(fig,')
t = t.replace('        fig.tight_layout(rect=(0, 0, 1, 0.90))\n        save(fig,',
              '        fig.tight_layout(rect=(0, 0, 1, 1.0))\n        save(fig,')
t = t.replace('        fig.tight_layout(rect=(0, 0, 1, 0.92))\n        save(fig,',
              '        fig.tight_layout(rect=(0, 0, 1, 1.0))\n        save(fig,')
t = t.replace('    fig.tight_layout(rect=(0, 0, 1, 0.93))\n    save(fig,',
              '    fig.tight_layout(rect=(0, 0, 1, 1.0))\n    save(fig,')
t = ("# SUP-TITLES STRIPPED -- figures carry no title; the report caption does.\n" + t)

p.write_text(t, encoding="utf-8")
print(f"stripped {n} suptitles")
