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
sys.exit(0 if out.wasSuccessful() else 1)
