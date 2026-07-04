#!/usr/bin/env python3
"""Generate a lightweight code health report for ValidKit.

This scanner is intentionally dependency-free.  It summarizes Python functions,
basic complexity, public API surface, and validation-related hotspots so a
maintainer can quickly decide where to review next.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class FunctionInfo:
    file: str
    name: str
    line: int
    end_line: int
    complexity: int
    args: list[str]
    decorators: list[str]


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.score = 1

    def visit_If(self, node: ast.If) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.score += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.score += 1
        self.generic_visit(node)


def complexity(node: ast.AST) -> int:
    visitor = ComplexityVisitor()
    visitor.visit(node)
    return visitor.score


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return dotted_name(node.func)
    return ""


def iter_functions(path: Path, root: Path) -> list[FunctionInfo]:
    source = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source, filename=str(path))
    parent_classes: dict[int, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    parent_classes[id(child)] = node.name

    functions: list[FunctionInfo] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        cls = parent_classes.get(id(node))
        full_name = f"{cls}.{node.name}" if cls else node.name
        decorators = [dotted_name(item) for item in node.decorator_list]
        functions.append(
            FunctionInfo(
                file=str(path.relative_to(root)),
                name=full_name,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                complexity=complexity(node),
                args=[arg.arg for arg in node.args.args],
                decorators=[item for item in decorators if item],
            )
        )
    return sorted(functions, key=lambda item: (item.file, item.line))


def scan(root: Path) -> dict[str, object]:
    files = sorted(root.rglob("*.py"))
    functions: list[FunctionInfo] = []
    for file in files:
        functions.extend(iter_functions(file, root))

    public = [
        item for item in functions
        if not item.name.split(".")[-1].startswith("_")
    ]
    hotspots = sorted(functions, key=lambda item: item.complexity, reverse=True)[:15]

    return {
        "root": str(root),
        "files": len(files),
        "functions": len(functions),
        "public_functions": len(public),
        "hotspots": [asdict(item) for item in hotspots],
    }


def print_markdown(report: dict[str, object]) -> None:
    print("# ValidKit Code Health Report\n")
    print(f"- Files scanned: {report['files']}")
    print(f"- Functions found: {report['functions']}")
    print(f"- Public functions/methods: {report['public_functions']}\n")
    print("## Complexity Hotspots\n")
    print("| Function | Complexity | Location |")
    print("|---|---:|---|")
    for item in report["hotspots"]:
        print(
            f"| `{item['name']}` | {item['complexity']} | "
            f"`{item['file']}:{item['line']}` |"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan ValidKit Python sources.")
    parser.add_argument("target", nargs="?", default="src/validkit", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = scan(args.target)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_markdown(report)


if __name__ == "__main__":
    main()
