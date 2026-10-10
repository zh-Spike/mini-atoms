"""Static checks for a generated Sandpack React project (no LLM involved)."""

import posixpath
import re

ENTRY = "/App.js"
ALLOWED_PACKAGES = {
    "react",
    "react-dom",
    "lucide-react",
    "recharts",
    "date-fns",
    "clsx",
}
RESERVED = {"/index.js", "/public/index.html", "/package.json"}
IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w*{}\s,]+\s+from\s+)?|import\s*\(\s*|require\s*\(\s*)['"]([^'"]+)['"]"""
)
RESOLVE_SUFFIXES = ("", ".js", ".jsx", "/index.js", "/index.jsx")


def package_name(spec: str) -> str:
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") else parts[0]


def resolve(from_path: str, spec: str, files: dict[str, str]) -> str | None:
    base = posixpath.normpath(posixpath.join(posixpath.dirname(from_path), spec))
    for suffix in RESOLVE_SUFFIXES:
        if base + suffix in files:
            return base + suffix
    return None


def used_packages(files: dict[str, str]) -> set[str]:
    pkgs: set[str] = set()
    for path, src in files.items():
        if not path.endswith((".js", ".jsx")):
            continue
        for spec in IMPORT_RE.findall(src):
            if not spec.startswith((".", "/")):
                pkgs.add(package_name(spec))
    return pkgs


def check_project(files: dict[str, str]) -> list[str]:
    issues: list[str] = []
    if ENTRY not in files:
        issues.append(f"缺少入口文件 {ENTRY}（必须 default export 一个 React 组件）")
    elif "export default" not in files[ENTRY]:
        issues.append(f"{ENTRY} 没有 default export")
    for path, src in files.items():
        if path in RESERVED:
            issues.append(f"{path} 由运行环境提供，不要生成")
        if not src.strip():
            issues.append(f"{path} 是空文件")
        if not path.endswith((".js", ".jsx")):
            continue
        for spec in IMPORT_RE.findall(src):
            if spec.startswith((".", "/")):
                if resolve(path, spec, files) is None:
                    issues.append(f"{path} 引用了不存在的文件 {spec}")
            elif package_name(spec) not in ALLOWED_PACKAGES:
                issues.append(f"{path} 使用了不允许的依赖 {spec}")
    return issues
