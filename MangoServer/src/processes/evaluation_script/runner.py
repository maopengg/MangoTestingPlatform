"""Isolated interpreter entry point; no platform credentials or ORM are loaded."""

import json
from pathlib import Path
import runpy


def main():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024, 2 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except ImportError:
        pass
    data = json.loads(Path("input.json").read_text(encoding="utf-8"))
    script = runpy.run_path("target.py", init_globals={"__mango_evaluation_inputs__": data["input"]})
    result = script["main"](data["input"], data["context"])
    if not isinstance(result, dict):
        raise TypeError("main must return a JSON object")
    output = json.dumps(result, ensure_ascii=False, allow_nan=False)
    Path("output.json").write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
