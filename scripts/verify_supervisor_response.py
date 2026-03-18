import argparse
import json
import pathlib
import py_compile
import re
import sys
import tempfile


FENCE_RE = re.compile(r"```filename:([^\n]+)\n(.*?)```", re.S)


def extract_blocks(response_path: pathlib.Path) -> list[tuple[str, str]]:
    payload = json.loads(response_path.read_text(encoding="utf-8"))
    content = payload.get("content", "")
    return [(name.strip(), body) for name, body in FENCE_RE.findall(content)]


def verify_python_blocks(response_path: pathlib.Path) -> int:
    blocks = extract_blocks(response_path)
    print(f"blocks={len(blocks)}")
    if not blocks:
        print("No filename fences found in supervisor response.", file=sys.stderr)
        return 1

    verify_dir = pathlib.Path(
        tempfile.mkdtemp(
            prefix="verify-supervisor-",
            dir=str(response_path.parent.parent),
        )
    )
    print(f"verify_dir={verify_dir}")

    failures = 0
    for name, body in blocks:
        target = verify_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

        if target.suffix != ".py":
            print(f"SKIP {name} (non-python)")
            continue

        try:
            py_compile.compile(str(target), doraise=True)
            print(f"OK {name}")
        except py_compile.PyCompileError as exc:
            failures += 1
            print(f"FAIL {name}")
            print(exc.msg)

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract filename-fenced supervisor response blocks and compile Python files."
    )
    parser.add_argument("response", type=pathlib.Path, help="Path to response JSON file")
    args = parser.parse_args()
    return verify_python_blocks(args.response)


if __name__ == "__main__":
    raise SystemExit(main())
