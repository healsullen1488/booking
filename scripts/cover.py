# Замер покрытия сервисного слоя без внешних пакетов (модуль trace).
# Запуск: python scripts/cover.py
import ast
import os
import sys
import trace
import unittest

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
svc = os.path.join(root, "app", "services")


def code_lines(path):
    # строки, где есть выполняемый код (без пустых, комментариев и докстрингов)
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    skip = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            b = n.body
            if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) \
                    and isinstance(b[0].value.value, str):
                for k in range(b[0].lineno, b[0].end_lineno + 1):
                    skip.add(k)
    res = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.stmt) and n.lineno not in skip:
            res.add(n.lineno)
    return res


def run():
    s = unittest.defaultTestLoader.discover(os.path.join(root, "tests", "unit"), top_level_dir=root)
    return unittest.TextTestRunner(verbosity=0).run(s)


tr = trace.Trace(count=1, trace=0)
out = tr.runfunc(run)
hit = {}
for (f, n), c in tr.results().counts.items():
    hit.setdefault(os.path.abspath(f), set()).add(n)

total = 0
done = 0
rows = []
for name in sorted(os.listdir(svc)):
    if not name.endswith(".py") or name == "__init__.py":
        continue
    p = os.path.join(svc, name)
    lines = code_lines(p)
    h = lines & hit.get(p, set())
    miss = sorted(lines - h)
    total += len(lines)
    done += len(h)
    rows.append((name, len(lines), len(h), miss))

print()
print("%-14s %6s %6s %6s  %s" % ("file", "lines", "hit", "%", "missed"))
for name, a, b, miss in rows:
    print("%-14s %6d %6d %5.0f%%  %s" % (name, a, b, 100.0 * b / max(a, 1), miss))
print("%-14s %6d %6d %5.1f%%" % ("TOTAL", total, done, 100.0 * done / total))


# HTML-отчёт: docs/coverage_report.html
import html

parts = ["<!doctype html><meta charset='utf-8'><title>Покрытие сервисного слоя</title>",
         "<style>body{font-family:sans-serif;margin:24px}table{border-collapse:collapse}"
         "td,th{border:1px solid #bbb;padding:4px 10px}pre{margin:0}"
         ".ok{background:#e3f6e3}.no{background:#fbd5d5}.sk{color:#888}</style>",
         "<h1>Покрытие сервисного слоя (app/services)</h1>",
         "<p>Тестов: %d. Покрыто строк: %d из %d (%.1f%%)</p>" % (out.testsRun, done, total, 100.0 * done / total),
         "<table><tr><th>Файл</th><th>Строк</th><th>Покрыто</th><th>%</th></tr>"]
for name, a, b, miss in rows:
    parts.append("<tr><td>%s</td><td>%d</td><td>%d</td><td>%.0f%%</td></tr>" % (name, a, b, 100.0 * b / max(a, 1)))
parts.append("</table>")
for name, a, b, miss in rows:
    p = os.path.join(svc, name)
    lines = code_lines(p)
    parts.append("<h2>%s</h2>" % name)
    for i, line in enumerate(open(p, encoding="utf-8").read().split("\n"), 1):
        cls = "sk"
        if i in lines:
            cls = "ok" if i not in miss else "no"
        parts.append("<pre class='%s'>%4d  %s</pre>" % (cls, i, html.escape(line)))
with open(os.path.join(root, "docs", "coverage_report.html"), "w", encoding="utf-8") as f:
    f.write("\n".join(parts))
print("report: docs/coverage_report.html")
sys.exit(0 if out.wasSuccessful() else 1)
