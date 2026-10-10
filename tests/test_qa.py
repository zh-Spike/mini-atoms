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


def test_reserved_file() -> None:
    files = {**GOOD, "/index.js": "x"}
    assert any("/index.js" in i for i in check_project(files))
