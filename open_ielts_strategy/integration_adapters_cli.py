"""Report installed capability adapters without loading provider code."""
import argparse, json
from .integration_adapters import CAPABILITIES, discover_adapters

def inspect_adapters():
    grouped = {name: [] for name in sorted(CAPABILITIES)}
    for item in discover_adapters():
        grouped[item.capability].append({"name": item.name, "version": item.version})
    return {"group": "open_ielts_strategy.adapters",
            "capabilities": {key: {"status": "available" if value else "unavailable", "adapters": value}
                             for key, value in grouped.items()},
            "provider_code_loaded": False}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(json.dumps(inspect_adapters(), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
