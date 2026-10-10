from app.agents.qa import check_project, used_packages

GOOD = {
    "/App.js": 'import { Plus } from "lucide-react";\nimport List from "./components/List";\n'
    "export default function App() { return <List />; }\n",
    "/components/List.js": 'import { fmt } from "../lib/fmt";\nexport default () => null;\n',
    "/lib/fmt.js": "export const fmt = (x) => x;\n",
}


def test_good_project_passes() -> None:
    assert check_project(GOOD) == []
    assert used_packages(GOOD) == {"lucide-react"}


def test_missing_entry() -> None:
    assert any("/App.js" in i for i in check_project({"/x.js": "export default 1;"}))


def test_broken_import_and_bad_package() -> None:
    files = {
        "/App.js": 'import axios from "axios";\nimport X from "./Missing";\nexport default X;\n'
    }
    issues = check_project(files)
    assert any("axios" in i for i in issues)
    assert any("./Missing" in i for i in issues)


def test_hallucinated_lucide_icon() -> None:
    files = {
        **GOOD,
        "/App.js": 'import { Timer, TimerIcon, LucideCoffee, Tomato as T } from "lucide-react";\n'
        "export default function App() { return null; }\n",
    }
    issues = check_project(files)
    assert issues == ["/App.js 从 lucide-react 引入了不存在的图标 Tomato，请换成真实存在的图标"]


def test_default_and_named_export_mismatch() -> None:
    files = {
        "/App.js": 'import List from "./List";\nimport { fmt, parse } from "./fmt";\n'
        "export default function App() { return <List />; }\n",
        "/List.js": "export function List() { return null; }\n",
        "/fmt.js": "export const fmt = (x) => x;\nconst parse = 1;\nexport { parse as other };\n",
    }
    issues = check_project(files)
    assert any("默认导入了 ./List" in i for i in issues)
    assert not any("fmt、" in i or i.endswith("fmt 在 /fmt.js 中没有导出") for i in issues)
    files["/fmt.js"] = "export const fmt = 1;\nexport { parse };\nconst parse = 2;\n"
    files["/List.js"] = "export default function List() { return null; }\n"
    assert check_project(files) == []


def test_reserved_file() -> None:
    files = {**GOOD, "/index.js": "x"}
    assert any("/index.js" in i for i in check_project(files))
