"""Offline MQL source triage. Passing this check is NOT a compiler verdict."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def strip_comments(source: str) -> str:
    """Remove comments while preserving strings and line numbers."""
    pattern = r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: m[0] if m[0].startswith('"') else
                  "\n" * m[0].count("\n") + " ", source)


def inspect(root: Path, entry: Path) -> dict:
    """Check local includes, input references, and non-MQL orchestration syntax."""
    findings: list[dict] = []
    sources: dict[Path, str] = {}

    def issue(path: Path, code: str, detail: str) -> None:
        findings.append({"file": str(path.relative_to(root)),
                         "code": code, "detail": detail})

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in sources:
            return
        if not path.is_relative_to(root):
            raise ValueError("Source path escapes project root")
        if not path.is_file():
            issue(path, "missing_source", "Source file is absent from this checkout")
            return
        source = strip_comments(path.read_text(encoding="utf-8-sig"))
        sources[path] = source
        for delimiter, include in re.findall(r'#include\s*([<"])([^>"\n]+)[>"]', source):
            relative = Path(include.replace("\\", "/"))
            candidate = (path.parent / relative if delimiter == '"'
                         else root / relative).resolve()
            if not candidate.is_relative_to(root):
                issue(path, "include_escape", include)
            elif candidate.is_file():
                visit(candidate)
            elif include.startswith("HybridMicrostructure") or delimiter == '"':
                issue(path, "missing_include", include)
            # Other angle includes belong to the MT5 standard library, unavailable here.

    visit(entry)
    combined = "\n".join(sources.values())
    inputs = set(re.findall(r'\binput\s+\w+\s+(Inp\w+)\b', combined))
    for path, source in sources.items():
        # Strings are not identifier references or executable code.
        code = re.sub(r'"(?:\\.|[^"\\])*"', '""', source)
        for name in sorted(set(re.findall(r'\bInp\w+\b', code)) - inputs):
            issue(path, "undeclared_input", name)
        if re.search(r'\bdelegate_task\s*\(', code):
            issue(path, "unsupported_agent_api", "delegate_task is not an MQL5 API")
        if re.search(r'^\s*#(?:\||\+)', code, re.MULTILINE):
            issue(path, "invalid_preprocessor", "Uncommented decorative header")
    return {"entry": str(entry.relative_to(root)), "source_files": len(sources),
            "status": "blocked" if findings else "needs_metaeditor_compile",
            "compiled": False, "findings": findings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("entries", nargs="*", default=[
        "Hybrid_Microstructure_EA_V1.0.mq5", "ResearchFramework.mq5"])
    args = parser.parse_args()
    root = args.root.resolve()
    results = [inspect(root, (root / name).resolve()) for name in args.entries]
    print(json.dumps({"kind": "static_triage_only", "results": results}, indent=2))
    return int(any(result["findings"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
