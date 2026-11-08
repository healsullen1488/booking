# Сохранить OpenAPI-спецификацию: python scripts/export_openapi.py
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)

from app.main import app

path = os.path.join(root, "docs", "openapi.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(app.openapi(), f, ensure_ascii=False, indent=2)
print("saved", path)
