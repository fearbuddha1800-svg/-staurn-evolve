---
slug: graphify_export
type: note
graph: gitnexus
---

#!/usr/bin/env python3
"""graphify_export.py — Export GitNexus knowledge graph to Obsidian markdown vault.

Reads the indexed project structure from .gitnexus/meta.json (file hashes + stats)
and the project's Python source files, builds a file/module dependency graph
from import statements, and writes Obsidian-compatible markdown with [[wikilinks]]
under obsidian-vault/.

Usage: python graphify_export.py [project_root] [vault_dir]
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_PROJECT = r"C:\Users\voidk\.hermes\workspace\signal-relay"
DEFAULT_VAULT = r"C:\Users\voidk\.hermes\workspace\signal-relay\obsidian-vault"

# File types to index as notes
INDEX_EXTENSIONS = {".py", ".md", ".json", ".toml", ".yaml", ".yml", ".cfg", ".ini"}

# Directories to skip
SKIP_DIRS = {
    ".git", ".gitnexus", "__pycache__", ".venv", "venv", "node_modules",
    ".mypy_cache", ".pytest_cache", "data", "caches", "backups", "locks",
    "obsidian-vault", "ocr_tmp",
}

# Skip files matching these patterns
SKIP_FILES = {
    ".gitignore", ".dockerignore",
}


def slug_for(path: Path, root: Path) -> str:
    """Obsidian wikilink slug from a file path relative to project root."""
    rel = path.relative_to(root)
    stem = rel.stem
    # Use dotted module path for Python files: package.module
    if path.suffix == ".py":
        parts = list(rel.with_suffix("").parts)
        return ".".join(parts)
    # For other files, use path with slashes replaced by dots
    return ".".join(rel.with_suffix("").parts)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def extract_python_imports(path: Path) -> list[str]:
    """Extract imported module names from a Python file."""
    text = read_text(path)
    if not text:
        return []
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        # Fallback: regex for import lines
        for m in re.finditer(r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))", text, re.MULTILINE):
            mod = m.group(1) or m.group(2)
            if mod:
                imports.append(mod.split(".")[0])
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module.split(".")[0])
    return imports


def collect_files(root: Path) -> dict[str, Path]:
    """Walk project root, return {slug: path} for indexable files."""
    files: dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn in SKIP_FILES or fn.startswith("."):
                continue
            p = Path(dirpath) / fn
            if p.suffix.lower() not in INDEX_EXTENSIONS:
                continue
            slug = slug_for(p, root)
            files[slug] = p
    return files


def write_note(vault_dir: Path, slug: str, content: str, links: list[str]) -> None:
    """Write a single Obsidian note with wikilinks and backlink section."""
    note_path = vault_dir / f"{slug}.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    # Build backlink section from incoming links
    backlinks = ""
    if links:
        backlinks = "\n## Links from\n" + "\n".join(f"- [[{l}]]" for l in sorted(set(links)))

    frontmatter = f"""---
slug: {slug}
type: note
graph: gitnexus
---

"""
    body = frontmatter + content.strip() + "\n" + backlinks + "\n"
    note_path.write_text(body, encoding="utf-8")


def main() -> int:
    project = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_PROJECT)
    vault_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_VAULT)

    if not project.exists():
        print(f"Project root not found: {project}", file=sys.stderr)
        return 1

    print(f"Project: {project}")
    print(f"Vault:   {vault_dir}")

    # Load GitNexus metadata if available
    meta_path = project / ".gitnexus" / "meta.json"
    graph_stats = {}
    if meta_path.exists():
        try:
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)
            stats = meta.get("stats", {})
            graph_stats = {
                "files": stats.get("files", 0),
                "nodes": stats.get("nodes", 0),
                "edges": stats.get("edges", 0),
                "clusters": stats.get("communities", stats.get("clusters", 0)),
                "processes": stats.get("processes", 0),
            }
            print(f"GitNexus stats: {graph_stats}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"Could not read meta.json: {e}", file=sys.stderr)

    # Collect all indexable files
    files = collect_files(project)
    print(f"Indexed {len(files)} files")

    # Build import graph: slug -> list of imported slugs
    import_graph: dict[str, list[str]] = {}
    reverse_links: dict[str, list[str]] = {slug: [] for slug in files}

    for slug, path in files.items():
        if path.suffix == ".py":
            imports = extract_python_imports(path)
            targets: list[str] = []
            for mod in imports:
                # Try to match imported module to a known slug
                if mod in files:
                    targets.append(mod)
                # Also try dotted matches (package.submodule)
                for known in files:
                    if known == mod or known.startswith(mod + "."):
                        if known not in targets:
                            targets.append(known)
            import_graph[slug] = targets
            for t in targets:
                reverse_links.setdefault(t, []).append(slug)

    # Write notes
    vault_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for slug, path in sorted(files.items()):
        content = read_text(path)
        # Truncate very large files for readability
        if len(content) > 50000:
            content = content[:50000] + f"\n\n... (truncated, {len(content)} total bytes) ..."
        links = reverse_links.get(slug, [])
        write_note(vault_dir, slug, content, links)
        written += 1

    # Write index/home note
    index_lines = [
        "# GitNexus Knowledge Graph",
        "",
        f"Exported from: {project}",
        "",
        "## Stats",
    ]
    for k, v in graph_stats.items():
        index_lines.append(f"- {k}: {v}")
    index_lines.extend(
        [
            f"- indexed_files: {len(files)}",
            "",
            "## All Notes",
            "",
        ]
    )
    for slug in sorted(files):
        index_lines.append(f"- [[{slug}]]")

    (vault_dir / "000-Index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    # Write graph map note
    graph_lines = ["# Graph Map", "", "## Module Dependencies", ""]
    for slug in sorted(import_graph):
        targets = import_graph[slug]
        if targets:
            graph_lines.append(f"- [[{slug}]] → " + ", ".join(f"[[{t}]]" for t in targets))
    (vault_dir / "000-Graph-Map.md").write_text("\n".join(graph_lines) + "\n", encoding="utf-8")

    print(f"Wrote {written} notes + index to {vault_dir}")
    print("Graphify export complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

