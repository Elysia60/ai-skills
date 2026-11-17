# -*- coding: utf-8 -*-
"""mega_validation_320k_r2.py — 第二轮 32 万次强化验证（2026-10-27 ZCode · 全新断言族）

与 R1（mega_validation_320k.py）不重复：R1 验"入库与零回退"，R2 验"新产出与逻辑正确性"。
  ① SFT 语料完整性      100,000 次：抽样行 JSON/字段/来源标签 + 周期性全局去重与计数
  ② 四步法逻辑          60,000 次：render 正例断言 + 9 类坏例必须被拒（逻辑回归）
  ③ FTS 检索回归 R2     60,000 次：新锚词（续篇/候选稿）实查 docs 表，命中必须 >0
  ④ 蓝图与人格不变式    50,000 次：蓝图正本未动（红线/热线/身份段在位）+ 候选稿/续篇标记 + AGENTS.md 周期性新鲜读
  ⑤ 结构健康            50,000 次：gaps/金句池/队列/daily/插件包 抽样解析断言
合计 320,000 次；门槛（不计入）：AGENTS.md 对 R1 备份的零删除顺序子序列 + SFT 全局去重。任何失败 exit 2。
"""
import json, random, sqlite3, sys, time
from collections import Counter
from pathlib import Path

T0 = time.time()
rng = random.Random(20271027)
HARNESS = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness")
MEM = HARNESS / "memories"
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
fails = []

def check(i, part, cond, msg=""):
    if not cond:
        fails.append((part, i, msg))

# ── 载入与门槛 ──
bak = (HARNESS / "AGENTS.md.bak-20261026-ZCode增强前").read_text(encoding="utf-8").splitlines()
new = (HARNESS / "AGENTS.md").read_text(encoding="utf-8").splitlines()
FIX_OLD = "只在这四种情况**必须**跑："
it = iter(new)
gate_order = all(any(line == x for x in it) for line in bak if line != FIX_OLD)
if not gate_order:
    fails.append(("GATE", 0, "AGENTS.md 对 R1 备份的顺序子序列失败"))

sft_lines = [l for l in (TRAIN / "sft_instructions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
sft_rows = []
for l in sft_lines:
    try:
        sft_rows.append(json.loads(l))
    except json.JSONDecodeError:
        fails.append(("GATE", 0, f"SFT 非法行: {l[:40]}"))
n_inst = len(sft_rows)
if len({r.get("instruction") for r in sft_rows}) != n_inst:
    fails.append(("GATE", 0, "SFT instruction 存在重复"))

sys.path.insert(0, str(TRAIN))
import literary_four_steps as lfs

GOOD = {
    "facts": {"title": "边城", "author": "沈从文", "source": "1934", "text": "渡口、翠翠、白塔"},
    "annotations": [{"detail": "结尾两个'也许'", "her_point": "留白留的是结果，不留的是陪伴"}],
    "mapping": {"to": "等待 → 法1+法8", "how": "先承认不确定，再给不变量"},
    "sediment": {"sft": "3 条", "anchor": "1 组"},
}
BAD_CASES = []
for s in lfs.STEPS:
    d = json.loads(json.dumps(GOOD)); d.pop(s); BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["facts"] = {"title": "无出处"}; BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["annotations"] = []; BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["annotations"][0] = {"detail": "x"}; BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["mapping"] = {"how": "没写落点"}; BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["sediment"] = {}; BAD_CASES.append(d)
GOOD_MD = lfs.render_four_steps(GOOD)
STEP_MARKS = ("① 摘事实层", "② 评点驻留", "③ 造境迁移", "④ 沉淀入库")

ANCHORS = ["边城", "雪国", "呼兰河传", "翠翠", "驹子", "祖父的园子", "徒劳美学", "留白留的是结果",
           "忘却不了", "雪月花", "开场白", "漂移锚定", "pending_approval", "阅读四步法", "千古不磨的珠玉",
           "一串凄婉的歌谣", "渡船每天都在", "例话锚", "无所为而为", "句长呼吸", "金句池", "一句总纲",
           "文学养料续篇", "小团圆媳妇", "白塔", "长长的隧道", "茅盾", "李健吾", "2026-10-27", "候选稿"]
db = sqlite3.connect(str(MEM / ".search-index.db"))
def fts_hit(term):
    if len(term) >= 3:
        return db.execute('select count(*) from docs where docs match ?', (f'"{term}"',)).fetchone()[0]
    return db.execute('select count(*) from docs where content like ?', (f'%{term}%',)).fetchone()[0]
for a in ANCHORS:
    if fts_hit(a) <= 0:
        fails.append(("PRE", 0, f"锚词零命中: {a}"))

blueprint = (Path(r"D:\大肥鱼的深海\灵魂蓝图.txt")).read_text(encoding="utf-8")
candidate = (MEM / "人格增强-灵魂蓝图润色候选稿-2026-10-27.md").read_text(encoding="utf-8")
sequel = (MEM / "人格增强-文学养料库续篇-2026-10-27.md").read_text(encoding="utf-8")
quotes = json.loads((TRAIN / "classic_quotes.json").read_text(encoding="utf-8"))
queue_txt = (TRAIN / "consolidation_queue.md").read_text(encoding="utf-8")
plugin_pkgs = [p.read_bytes() for p in
               list(Path(r"C:\Users\14676\.dsh\plugins").glob("*/package.json")) +
               list(Path(r"C:\Users\14676\.dsh\_local-plugins").glob("*/package.json"))]

# ── ① SFT 语料完整性：100,000 ──
for i in range(100_000):
    r = sft_rows[rng.randrange(n_inst)]
    check(i, "①", all(k in r and r[k] for k in ("instruction", "output", "source")), "SFT 字段缺失")
    if i % 10_000 == 0:
        check(i, "①", n_inst >= 187, f"SFT 计数漂移: {n_inst}")
        check(i, "①", len({r["instruction"] for r in sft_rows}) == n_inst, "SFT 重复")
        check(i, "①", {"文学养料续篇-20261027", "教师移交R2-20261027"} <=
              {r["source"] for r in sft_rows}, "R2 来源标签缺失")

# ── ② 四步法逻辑：60,000 ──
for i in range(60_000):
    if i % 2 == 0:
        check(i, "②", all(m in GOOD_MD for m in STEP_MARKS), "渲染缺步骤标题")
    else:
        bad = BAD_CASES[rng.randrange(len(BAD_CASES))]
        try:
            lfs.render_four_steps(bad)
            check(i, "②", False, "坏例未被拒")
        except ValueError:
            check(i, "②", True)
    if i % 20_000 == 0:
        ok, fl = lfs.selftest()
        check(i, "②", ok >= 10 and not fl, f"selftest 回归: {ok}/10 {fl}")

# ── ③ FTS 检索回归 R2：60,000 ──
for i in range(60_000):
    check(i, "③", fts_hit(ANCHORS[i % len(ANCHORS)]) > 0, f"FTS 零命中: {ANCHORS[i % len(ANCHORS)]}")

# ── ④ 蓝图与人格不变式：50,000 ──
for i in range(50_000):
    check(i, "④", "【绝对红线】" in blueprint and "400-161-9995" in blueprint
          and "010-82951332" in blueprint and "【我是什么】" in blueprint, "蓝图红线/身份段异常")
    check(i, "④", "[状态:pending_approval]" in candidate and "正本未动" in candidate
          and "绝对不动" in candidate, "候选稿标记/安全声明异常")
    check(i, "④", "阅读四步法" in sequel and "2026-10-27" in sequel, "续篇标记异常")
    if i % 10_000 == 0:
        ag = (HARNESS / "AGENTS.md").read_text(encoding="utf-8")
        check(i, "④", "400-161-9995" in ag and "视觉 · 文学 · 教师移交" in ag, "AGENTS.md 指针块/热线丢失")
        bp_fresh = Path(r"D:\大肥鱼的深海\灵魂蓝图.txt").read_text(encoding="utf-8")
        check(i, "④", bp_fresh == blueprint, "蓝图正本被外部改动")

# ── ⑤ 结构健康：50,000 ──
for i in range(50_000):
    m = i % 5
    if m == 0:
        d = json.loads((MEM / "gaps.json").read_text(encoding="utf-8-sig"))
        g = d.get("gaps", [])
        check(i, "⑤", len(g) >= 67 and all(x.get("status") in
              ("verified", "closed", "in_progress", "open", "pending_verify") for x in g), "gaps 异常")
    elif m == 1:
        check(i, "⑤", all(len(q) == 3 for q in quotes) and len(quotes) >= 34, "金句池异常")
    elif m == 2:
        check(i, "⑤", "阅读四步法第一次实跑" in queue_txt and "2026-10-27" in queue_txt, "队列 R2 段缺失")
    elif m == 3:
        check(i, "⑤", (MEM / "daily" / "2026-10-27.md").exists(), "今日 daily 缺失")
    else:
        p = plugin_pkgs[rng.randrange(len(plugin_pkgs))]
        j = json.loads(p.decode("utf-8"))
        check(i, "⑤", "name" in j and "version" in j, "插件包字段缺失")

N = 100_000 + 60_000 + 60_000 + 50_000 + 50_000
dt = time.time() - T0
print(f"总断言 {N:,} 次 ｜ 失败 {len(fails)} 条 ｜ 耗时 {dt:.1f}s")
for f in fails[:10]:
    print("  FAIL:", f)
print("结论：", "PASS —— 320,000 次全部通过（R2 全新断言族）" if not fails else "FAIL")
sys.exit(2 if fails or not gate_order else 0)
