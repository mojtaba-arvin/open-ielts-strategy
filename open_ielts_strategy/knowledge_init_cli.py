"""Initialize a private local Knowledge Pack authoring workspace."""
import argparse, json, sys
from .knowledge_authoring import initialize_workspace
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    args=parser.parse_args(argv)
    try: result=initialize_workspace(args.workspace)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())