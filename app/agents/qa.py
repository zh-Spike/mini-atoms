"""Static checks for a generated Sandpack React project (no LLM involved)."""

import posixpath
import re
from functools import cache
from pathlib import Path

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
# `import Default, { a, b as c } from "x"`; namespace imports are not checked.
IMPORT_CLAUSE_RE = re.compile(
    r"""import\s+(?:([\w$]+)\s*,?\s*)?(?:\{([^}]*)\}\s*)?from\s*['"]([^'"]+)['"]"""
)
LUCIDE_ICONS_FILE = Path(__file__).with_name("lucide_icons.txt")


@cache
def lucide_icons() -> frozenset[str]:
    lines = LUCIDE_ICONS_FILE.read_text().splitlines()
    return frozenset(line for line in lines if line and not line.startswith("#"))


def _is_lucide_icon(name: str) -> bool:
    if name in ("Icon", "createLucideIcon", "icons"):
        return True
    base = name.removeprefix("Lucide").removesuffix("Icon")
    return base in lucide_icons()


def _named(clause: str) -> list[str]:
    return [p.split(" as ")[0].strip() for p in clause.split(",") if p.strip()]


def _exports_name(src: str, name: str) -> bool:
    n = re.escape(name)
    decl = rf"export\s+(?:async\s+)?(?:function\s*\*?|const|let|var|class)\s+{n}\b"
    return bool(re.search(decl, src) or re.search(rf"export\s*\{{[^}}]*\b{n}\b[^}}]*\}}", src))


def _import_issues(path: str, src: str, files: dict[str, str]) -> list[str]:
    """Imported names that do not exist: hallucinated icons, default/named mix-ups."""
    issues: list[str] = []
    for default, named, spec in IMPORT_CLAUSE_RE.findall(src):
        names = _named(named)
        if spec == "lucide-react":
            bad = [n for n in names if not _is_lucide_icon(n)]
            if bad:
                icons = "、".join(bad)
                issues.append(
                    f"{path} 从 lucide-react 引入了不存在的图标 {icons}，请换成真实存在的图标"
                )
            continue
        if not spec.startswith((".", "/")):
            continue
        target = resolve(path, spec, files)
        if target is None:
            continue
        target_src = files[target]
        if default and "export default" not in target_src:
            issues.append(f"{path} 默认导入了 {spec}，但 {target} 没有 default export")
        missing = [n for n in names if n != "default" and not _exports_name(target_src, n)]
        if missing:
            issues.append(f"{path} 从 {spec} 引入的 {'、'.join(missing)} 在 {target} 中没有导出")
    return issues


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
        issues.extend(_import_issues(path, src, files))
    return issues
