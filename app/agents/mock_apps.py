# Embedded JSX and PRD text read better unwrapped.
# ruff: noqa: E501
"""Prebuilt apps the demo LLM "generates" when no model is available.

Each app is a real multi-file Sandpack project that passes QA. Colours live in `/lib/theme.js`, so
the demo can serve race variants (accent colour, light or dark look) and "换成蓝色"-style edits by
rewriting that one file.
"""

import re
from dataclasses import dataclass

COLORS = {
    "蓝": "blue",
    "绿": "emerald",
    "红": "rose",
    "橙": "orange",
    "紫": "violet",
    "粉": "pink",
    "青": "cyan",
    "黄": "amber",
    "灰": "slate",
    "黑": "zinc",
}
DEFAULT_ACCENT = "violet"
LANE_ACCENTS = ("violet", "emerald", "sky")


def theme_js(accent: str, fancy: bool) -> str:
    header = f'export const ACCENT = "{accent}";\nexport const FANCY = {str(fancy).lower()};\n'
    return header + THEME_BODY


THEME_BODY = """
export const theme = {
  page: FANCY
    ? "bg-linear-to-br from-slate-950 via-slate-900 to-slate-950 text-white"
    : "bg-zinc-50 text-zinc-900",
  surface: FANCY ? "bg-white/5 border-white/10 backdrop-blur" : "bg-white border-zinc-200",
  muted: FANCY ? "text-white/60" : "text-zinc-500",
  input: FANCY
    ? "bg-white/10 border-white/20 text-white placeholder:text-white/40"
    : "bg-white border-zinc-300 placeholder:text-zinc-400",
  button: `bg-${ACCENT}-500 hover:bg-${ACCENT}-600 text-white`,
  soft: FANCY ? `bg-${ACCENT}-400/20 text-${ACCENT}-200` : `bg-${ACCENT}-50 text-${ACCENT}-700`,
  text: FANCY ? `text-${ACCENT}-300` : `text-${ACCENT}-600`,
  bar: `bg-${ACCENT}-500`,
};
"""


THEME_RE = re.compile(r'ACCENT = "(\w+)";\s*export const FANCY = (true|false)')

USE_LOCAL_STORAGE = """import { useEffect, useState } from "react";

export function useLocalStorage(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : initial;
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // storage full or disabled: keep working in memory
    }
  }, [key, value]);

  return [value, setValue];
}
"""

KANBAN_APP = """import { useState } from "react";
import { Plus } from "lucide-react";
import Column from "./components/Column";
import { useLocalStorage } from "./lib/useLocalStorage";
import { theme, FANCY } from "./lib/theme";

const COLUMNS = [
  { id: "todo", title: "待办" },
  { id: "doing", title: "进行中" },
  { id: "done", title: "已完成" },
];

const SAMPLE = [
  { id: "1", title: "梳理需求文档", priority: "high", column: "todo" },
  { id: "2", title: "设计首页原型", priority: "medium", column: "doing" },
  { id: "3", title: "搭建项目脚手架", priority: "low", column: "done" },
];

export default function App() {
  const [tasks, setTasks] = useLocalStorage("demo-kanban:tasks", SAMPLE);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("medium");

  function addTask(e) {
    e.preventDefault();
    if (!title.trim()) return;
    setTasks([...tasks, { id: String(Date.now()), title: title.trim(), priority, column: "todo" }]);
    setTitle("");
  }

  function move(id, step) {
    setTasks(
      tasks.map((t) => {
        if (t.id !== id) return t;
        const i = COLUMNS.findIndex((c) => c.id === t.column);
        const next = COLUMNS[Math.min(COLUMNS.length - 1, Math.max(0, i + step))];
        return { ...t, column: next.id };
      }),
    );
  }

  function remove(id) {
    setTasks(tasks.filter((t) => t.id !== id));
  }

  return (
    <div className={`min-h-screen p-4 sm:p-8 ${theme.page}`}>
      <div className="mx-auto max-w-5xl">
        <header className="mb-6">
          <h1 className={`font-bold ${FANCY ? "text-4xl" : "text-2xl"}`}>项目看板</h1>
          <p className={`mt-1 text-sm ${theme.muted}`}>
            共 {tasks.length} 个任务，已完成 {tasks.filter((t) => t.column === "done").length} 个
          </p>
        </header>

        <form onSubmit={addTask} className="mb-6 flex flex-col gap-2 sm:flex-row">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="新任务，例如：完成登录页"
            className={`flex-1 rounded-lg border px-3 py-2 outline-none ${theme.input}`}
          />
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className={`rounded-lg border px-3 py-2 ${theme.input}`}
          >
            <option value="high">高优先级</option>
            <option value="medium">中优先级</option>
            <option value="low">低优先级</option>
          </select>
          <button
            type="submit"
            className={`flex items-center justify-center gap-1 rounded-lg px-4 py-2 font-medium ${theme.button}`}
          >
            <Plus className="size-4" /> 添加
          </button>
        </form>

        <div className="grid gap-4 md:grid-cols-3">
          {COLUMNS.map((col, i) => (
            <Column
              key={col.id}
              title={col.title}
              tasks={tasks.filter((t) => t.column === col.id)}
              canLeft={i > 0}
              canRight={i < COLUMNS.length - 1}
              onMove={move}
              onRemove={remove}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
"""

KANBAN_COLUMN = """import { ArrowLeft, ArrowRight, Trash2 } from "lucide-react";
import { theme } from "../lib/theme";

const PRIORITY = {
  high: { text: "高", className: "bg-rose-100 text-rose-700" },
  medium: { text: "中", className: "bg-amber-100 text-amber-700" },
  low: { text: "低", className: "bg-emerald-100 text-emerald-700" },
};

export default function Column({ title, tasks, canLeft, canRight, onMove, onRemove }) {
  return (
    <section className={`rounded-xl border p-3 ${theme.surface}`}>
      <h2 className="mb-3 flex items-center justify-between font-semibold">
        {title}
        <span className={`rounded-full px-2 text-xs ${theme.soft}`}>{tasks.length}</span>
      </h2>
      {tasks.length === 0 && <p className={`py-6 text-center text-sm ${theme.muted}`}>暂无任务</p>}
      <ul className="space-y-2">
        {tasks.map((t) => (
          <li key={t.id} className={`rounded-lg border p-3 ${theme.surface}`}>
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm">{t.title}</span>
              <span className={`shrink-0 rounded px-1.5 text-xs ${PRIORITY[t.priority].className}`}>
                {PRIORITY[t.priority].text}
              </span>
            </div>
            <div className={`mt-2 flex justify-end gap-1 ${theme.muted}`}>
              {canLeft && (
                <button onClick={() => onMove(t.id, -1)} title="移到上一列" className="p-1 hover:opacity-70">
                  <ArrowLeft className="size-4" />
                </button>
              )}
              {canRight && (
                <button onClick={() => onMove(t.id, 1)} title="移到下一列" className="p-1 hover:opacity-70">
                  <ArrowRight className="size-4" />
                </button>
              )}
              <button onClick={() => onRemove(t.id)} title="删除" className="p-1 hover:text-rose-500">
                <Trash2 className="size-4" />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
"""

POMODORO_APP = """import { useEffect, useState } from "react";
import { Coffee, Flame, Timer } from "lucide-react";
import TimerDial from "./components/TimerDial";
import { useLocalStorage } from "./lib/useLocalStorage";
import { theme, FANCY } from "./lib/theme";

const today = () => new Date().toISOString().slice(0, 10);

export default function App() {
  const [settings, setSettings] = useLocalStorage("demo-pomodoro:settings", { focus: 25, rest: 5 });
  const [log, setLog] = useLocalStorage("demo-pomodoro:log", {});
  const [mode, setMode] = useState("focus");
  const [left, setLeft] = useState(settings.focus * 60);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!running) return undefined;
    const id = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [running]);

  useEffect(() => {
    if (left > 0 || !running) return;
    setRunning(false);
    if (mode === "focus") {
      setLog({ ...log, [today()]: (log[today()] || 0) + 1 });
      switchMode("rest");
    } else {
      switchMode("focus");
    }
  }, [left, running]);

  function switchMode(next) {
    setMode(next);
    setRunning(false);
    setLeft(settings[next] * 60);
  }

  function updateSetting(key, value) {
    const minutes = Math.min(90, Math.max(1, Number(value) || 1));
    setSettings({ ...settings, [key]: minutes });
    if (mode === key && !running) setLeft(minutes * 60);
  }

  const total = settings[mode] * 60;

  return (
    <div className={`flex min-h-screen items-center justify-center p-4 ${theme.page}`}>
      <div className={`w-full max-w-md rounded-2xl border p-6 ${theme.surface}`}>
        <h1 className={`mb-4 flex items-center gap-2 font-bold ${FANCY ? "text-3xl" : "text-2xl"}`}>
          <Timer className={theme.text} /> 番茄钟
        </h1>

        <div className="mb-6 grid grid-cols-2 gap-2">
          <button
            onClick={() => switchMode("focus")}
            className={`rounded-lg py-2 text-sm ${mode === "focus" ? theme.button : theme.soft}`}
          >
            专注
          </button>
          <button
            onClick={() => switchMode("rest")}
            className={`flex items-center justify-center gap-1 rounded-lg py-2 text-sm ${mode === "rest" ? theme.button : theme.soft}`}
          >
            <Coffee className="size-4" /> 休息
          </button>
        </div>

        <TimerDial
          left={left}
          total={total}
          running={running}
          onToggle={() => setRunning(!running)}
          onReset={() => switchMode(mode)}
        />

        <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
          <label className={theme.muted}>
            专注（分钟）
            <input
              type="number"
              value={settings.focus}
              onChange={(e) => updateSetting("focus", e.target.value)}
              className={`mt-1 w-full rounded-lg border px-3 py-1.5 ${theme.input}`}
            />
          </label>
          <label className={theme.muted}>
            休息（分钟）
            <input
              type="number"
              value={settings.rest}
              onChange={(e) => updateSetting("rest", e.target.value)}
              className={`mt-1 w-full rounded-lg border px-3 py-1.5 ${theme.input}`}
            />
          </label>
        </div>

        <p className={`mt-6 flex items-center justify-center gap-1 text-sm ${theme.muted}`}>
          <Flame className="size-4 text-orange-500" /> 今天已完成 {log[today()] || 0} 个番茄
        </p>
      </div>
    </div>
  );
}
"""

POMODORO_DIAL = """import { Pause, Play, RotateCcw } from "lucide-react";
import { theme } from "../lib/theme";

function format(seconds) {
  const m = String(Math.floor(seconds / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

export default function TimerDial({ left, total, running, onToggle, onReset }) {
  const progress = total ? (total - left) / total : 0;
  return (
    <div className="flex flex-col items-center">
      <div
        className={`flex size-48 items-center justify-center rounded-full ${theme.text}`}
        style={{
          background: `conic-gradient(currentColor ${progress * 360}deg, rgba(148,163,184,0.2) 0deg)`,
        }}
      >
        <div className={`flex size-40 items-center justify-center rounded-full ${theme.page}`}>
          <span className="font-mono text-4xl font-semibold">{format(left)}</span>
        </div>
      </div>
      <div className="mt-5 flex gap-3">
        <button
          onClick={onToggle}
          className={`flex items-center gap-1 rounded-full px-6 py-2 font-medium ${theme.button}`}
        >
          {running ? <Pause className="size-4" /> : <Play className="size-4" />}
          {running ? "暂停" : "开始"}
        </button>
        <button onClick={onReset} title="重置" className={`rounded-full px-3 py-2 ${theme.soft}`}>
          <RotateCcw className="size-4" />
        </button>
      </div>
    </div>
  );
}
"""

EXPENSE_APP = """import { useState } from "react";
import { Plus, Trash2, TrendingDown, TrendingUp, Wallet } from "lucide-react";
import CategoryChart from "./components/CategoryChart";
import { useLocalStorage } from "./lib/useLocalStorage";
import { theme, FANCY } from "./lib/theme";

const CATEGORIES = ["餐饮", "交通", "购物", "居住", "娱乐", "其他"];
const month = () => new Date().toISOString().slice(0, 7);

const SAMPLE = [
  { id: "1", type: "income", amount: 12000, category: "其他", note: "工资", date: `${month()}-01` },
  { id: "2", type: "expense", amount: 3200, category: "居住", note: "房租", date: `${month()}-02` },
  { id: "3", type: "expense", amount: 68, category: "餐饮", note: "午饭", date: `${month()}-03` },
  { id: "4", type: "expense", amount: 25, category: "交通", note: "地铁", date: `${month()}-03` },
];

export default function App() {
  const [items, setItems] = useLocalStorage("demo-expense:items", SAMPLE);
  const [form, setForm] = useState({ type: "expense", amount: "", category: "餐饮", note: "" });

  const thisMonth = items.filter((i) => i.date.startsWith(month()));
  const income = thisMonth.filter((i) => i.type === "income").reduce((s, i) => s + i.amount, 0);
  const expense = thisMonth.filter((i) => i.type === "expense").reduce((s, i) => s + i.amount, 0);

  function add(e) {
    e.preventDefault();
    const amount = Number(form.amount);
    if (!amount || amount <= 0) return;
    const date = new Date().toISOString().slice(0, 10);
    setItems([{ ...form, amount, id: String(Date.now()), date }, ...items]);
    setForm({ ...form, amount: "", note: "" });
  }

  return (
    <div className={`min-h-screen p-4 sm:p-8 ${theme.page}`}>
      <div className="mx-auto max-w-3xl space-y-5">
        <h1 className={`flex items-center gap-2 font-bold ${FANCY ? "text-4xl" : "text-2xl"}`}>
          <Wallet className={theme.text} /> 记账本
        </h1>

        <div className="grid grid-cols-3 gap-3">
          <Stat label="本月收入" value={income} icon={<TrendingUp className="size-4 text-emerald-500" />} />
          <Stat label="本月支出" value={expense} icon={<TrendingDown className="size-4 text-rose-500" />} />
          <Stat label="结余" value={income - expense} />
        </div>

        <form onSubmit={add} className={`grid gap-2 rounded-xl border p-4 sm:grid-cols-5 ${theme.surface}`}>
          <select
            value={form.type}
            onChange={(e) => setForm({ ...form, type: e.target.value })}
            className={`rounded-lg border px-2 py-2 ${theme.input}`}
          >
            <option value="expense">支出</option>
            <option value="income">收入</option>
          </select>
          <input
            type="number"
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            placeholder="金额"
            className={`rounded-lg border px-3 py-2 ${theme.input}`}
          />
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className={`rounded-lg border px-2 py-2 ${theme.input}`}
          >
            {CATEGORIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          <input
            value={form.note}
            onChange={(e) => setForm({ ...form, note: e.target.value })}
            placeholder="备注"
            className={`rounded-lg border px-3 py-2 ${theme.input}`}
          />
          <button className={`flex items-center justify-center gap-1 rounded-lg px-3 py-2 ${theme.button}`}>
            <Plus className="size-4" /> 记一笔
          </button>
        </form>

        <CategoryChart items={thisMonth.filter((i) => i.type === "expense")} categories={CATEGORIES} />

        <ul className={`divide-y divide-zinc-500/15 rounded-xl border ${theme.surface}`}>
          {items.length === 0 && <li className={`p-6 text-center text-sm ${theme.muted}`}>还没有记录</li>}
          {items.map((i) => (
            <li key={i.id} className="flex items-center justify-between gap-3 p-3 text-sm">
              <span className={`rounded px-2 py-0.5 text-xs ${theme.soft}`}>{i.category}</span>
              <span className="flex-1 truncate">{i.note || "未备注"}</span>
              <span className={theme.muted}>{i.date}</span>
              <span className={i.type === "income" ? "text-emerald-500" : "text-rose-500"}>
                {i.type === "income" ? "+" : "-"}
                {i.amount.toFixed(2)}
              </span>
              <button
                onClick={() => setItems(items.filter((x) => x.id !== i.id))}
                title="删除"
                className={`${theme.muted} hover:text-rose-500`}
              >
                <Trash2 className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Stat({ label, value, icon }) {
  return (
    <div className={`rounded-xl border p-4 ${theme.surface}`}>
      <p className={`flex items-center gap-1 text-xs ${theme.muted}`}>
        {icon}
        {label}
      </p>
      <p className="mt-1 text-xl font-semibold">¥{value.toFixed(2)}</p>
    </div>
  );
}
"""

EXPENSE_CHART = """import { theme } from "../lib/theme";

export default function CategoryChart({ items, categories }) {
  const totals = categories
    .map((c) => ({ name: c, value: items.filter((i) => i.category === c).reduce((s, i) => s + i.amount, 0) }))
    .filter((c) => c.value > 0)
    .sort((a, b) => b.value - a.value);
  const max = Math.max(1, ...totals.map((t) => t.value));

  return (
    <section className={`rounded-xl border p-4 ${theme.surface}`}>
      <h2 className="mb-3 font-semibold">本月支出分类</h2>
      {totals.length === 0 && <p className={`text-sm ${theme.muted}`}>本月还没有支出</p>}
      <div className="space-y-2">
        {totals.map((t) => (
          <div key={t.name} className="flex items-center gap-3 text-sm">
            <span className="w-10 shrink-0">{t.name}</span>
            <div className="h-3 flex-1 overflow-hidden rounded-full bg-zinc-500/15">
              <div className={`h-full rounded-full ${theme.bar}`} style={{ width: `${(t.value / max) * 100}%` }} />
            </div>
            <span className={`w-20 text-right ${theme.muted}`}>¥{t.value.toFixed(0)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
"""


@dataclass(frozen=True)
class MockApp:
    key: str
    keywords: tuple[str, ...]
    prd: str
    design: str
    files: dict[str, str]
    summary: str


APPS = [
    MockApp(
        "pomodoro",
        ("番茄", "专注", "计时", "倒计时", "timer"),
        "## 产品目标\n帮助用户用番茄工作法保持专注。\n\n## 核心功能\n- 开始 / 暂停 / 重置倒计时\n"
        "- 在专注和休息之间切换，时长可自定义\n- 一个番茄结束后自动进入休息\n- 统计今天完成的番茄数\n\n"
        "## 页面与交互\n单页：模式切换、圆形进度表盘、时长设置、今日统计。\n\n"
        "## 数据\nlocalStorage 保存时长设置和每天的番茄数。",
        "## 技术方案\nReact 函数组件 + Hooks，Tailwind 样式，lucide-react 图标，"
        "自定义 hook 持久化到 localStorage。\n\n## 文件结构\n- /App.js：计时状态和设置\n"
        "- /components/TimerDial.js：圆形进度和控制按钮\n- /lib/useLocalStorage.js：持久化 hook\n"
        "- /lib/theme.js：主题色\n\n## 状态与数据流\nApp 持有 mode、left、running；"
        "设置和统计通过 useLocalStorage 读写。",
        {"/App.js": POMODORO_APP, "/components/TimerDial.js": POMODORO_DIAL},
        "完成了番茄钟：支持自定义专注和休息时长、圆形进度表盘，并记录今天完成的番茄数。",
    ),
    MockApp(
        "expense",
        ("记账", "收支", "花销", "账单", "预算", "消费"),
        "## 产品目标\n轻量记录日常收支，看清钱花在哪。\n\n## 核心功能\n- 记录收入或支出（金额、分类、备注）\n"
        "- 本月收入、支出、结余汇总\n- 按分类展示本月支出占比\n- 删除记录\n\n"
        "## 页面与交互\n单页：顶部汇总卡片、记账表单、分类条形图、流水列表。\n\n"
        "## 数据\nlocalStorage 保存全部流水。",
        "## 技术方案\nReact 函数组件 + Hooks，Tailwind 样式，lucide-react 图标，"
        "自定义 hook 持久化到 localStorage。\n\n## 文件结构\n- /App.js：流水状态、表单、汇总\n"
        "- /components/CategoryChart.js：分类条形图\n- /lib/useLocalStorage.js：持久化 hook\n"
        "- /lib/theme.js：主题色\n\n## 状态与数据流\nitems 数组存在 App，汇总和图表都由它派生。",
        {"/App.js": EXPENSE_APP, "/components/CategoryChart.js": EXPENSE_CHART},
        "完成了记账本：可以记录收支，查看本月汇总和分类支出条形图，数据保存在本地。",
    ),
    MockApp(
        "kanban",
        ("看板", "任务", "待办", "todo", "项目"),
        "## 产品目标\n用看板管理个人或小团队的任务进度。\n\n## 核心功能\n- 新建任务并设置优先级\n"
        "- 待办 / 进行中 / 已完成三列\n- 任务在列之间左右移动\n- 删除任务，显示完成数量\n\n"
        "## 页面与交互\n单页：顶部统计、新建任务表单、三列看板。\n\n"
        "## 数据\nlocalStorage 保存全部任务。",
        "## 技术方案\nReact 函数组件 + Hooks，Tailwind 样式，lucide-react 图标，"
        "自定义 hook 持久化到 localStorage。\n\n## 文件结构\n- /App.js：任务状态和新建表单\n"
        "- /components/Column.js：单列和任务卡片\n- /lib/useLocalStorage.js：持久化 hook\n"
        "- /lib/theme.js：主题色\n\n## 状态与数据流\ntasks 数组存在 App，每个任务带 column 字段，"
        "移动即修改 column。",
        {"/App.js": KANBAN_APP, "/components/Column.js": KANBAN_COLUMN},
        "完成了任务看板：支持新建带优先级的任务，在三列之间移动和删除，数据保存在本地。",
    ),
]
DEFAULT_APP = APPS[-1]


def pick_app(text: str) -> MockApp:
    lowered = text.lower()
    for app in APPS:
        if any(k in lowered for k in app.keywords):
            return app
    return DEFAULT_APP


def app_files(app: MockApp, accent: str, fancy: bool) -> dict[str, str]:
    return {
        **app.files,
        "/lib/useLocalStorage.js": USE_LOCAL_STORAGE,
        "/lib/theme.js": theme_js(accent, fancy),
    }


def requested_accent(text: str) -> str | None:
    for word, accent in COLORS.items():
        if word in text:
            return accent
    return None


def current_theme(files_text: str) -> tuple[str, bool]:
    m = THEME_RE.search(files_text)
    if not m:
        return DEFAULT_ACCENT, False
    return m.group(1), m.group(2) == "true"
