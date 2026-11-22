import json
from pathlib import Path
p=Path("registry/sources.json")
print(json.dumps([x["id"] for x in json.loads(p.read_text())["sources"]]))
