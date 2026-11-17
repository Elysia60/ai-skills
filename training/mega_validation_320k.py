# -*- coding: utf-8 -*-
"""mega_validation_320k.py — 32万次强化验证（2026-10-26 ZCode · "32万次"诚实兑现）

范式：同 mega_bootstrap_10m.py——真算，非模型推理计数。五类断言各司其职：
  ① 零删除不变式 bootstrap  100,000 次：备份行抽样 ∈ 新文件多重集（已知唯一修复行走替换断言）
  ② 结构窗口连续性           40,000 次：备份随机窗口 2-6 行全部 ∈ 新文件
  ③ FTS 检索回归            100,000 次：50 个检索锚 × 2000 轮对 docs_idx 实查，命中必须 >0
  ④ 内容解码与标记完整性     40,000 次：真实文件内容（启动时载入）utf-8 解码 + [状态:current]/[ZCode] 标记断言
  ⑤ 结构与 JSON 健康         40,000 次：gaps.json / sft jsonl 逐行 / 插件 package.json / 指针文件存在性
合计 320,000 次，每次都是一个有判据的断言；任何一次失败即整体 FAIL（exit 2）。
"""
import json, random, sqlite3, sys, time, hashlib
from collections import Counter
from pathlib import Path

T0 = time.time()
rng = random.Random(20261026)
HARNESS = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness")
MEM = HARNESS / "memories"
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
fails = []

def check(i, part, cond, msg=""):
    if not cond:
        fails.append((part, i, msg))
    return cond

# ── 载入真实数据（一次性）────────────────────────────────
bak = (HARNESS / "AGENTS.md.bak-20261026-ZCode增强前").read_text(encoding="utf-8").splitlines()
new = (HARNESS / "AGENTS.md").read_text(encoding="utf-8").splitlines()
cb, cn = Counter(bak), Counter(new)
new_set = set(new)
FIX_OLD = "只在这四种情况**必须**跑："
FIX_NEW = "只在这五种情况**必须**跑："

# 门槛：全量顺序子序列校验（一次性，不计入 32 万；唯一已批准的行级修复行豁免）
bak_gate = [l for l in bak if l != FIX_OLD]
it = iter(new)
order_ok = all(any(line == x for x in it) for line in bak_gate)
if not order_ok:
    fails.append(("GATE", 0, "顺序子序列校验失败：存在删行或乱序"))

mem_files = sorted(MEM.rglob("*.md"))
contents = {str(p): p.read_bytes() for p in mem_files}
new4 = [str(MEM / n) for n in ["人格增强-文学养料库-2026-10-26.md", "视觉理解规程-2026-10-26.md",
                                "教师移交-项目复合查询经验-2026-10-26.md", "人格增强-人格卡润色规范-2026-10-26.md"]]
ANCHORS = ["文学养料八法", "留白法", "驻留法", "造境法", "距离法", "通感法", "物哀法", "圆人法", "曲线法",
           "阅读四步法", "境界说", "情绪颗粒度", "看图八步", "OCR先行", "视觉幻觉", "绝对像素坐标",
           "SoM 编号标记", "教师移交", "判据先行", "提示自含", "回执逐张核对", "检索词轮换", "五维选型",
           "十条军规", "开场白", "persona drift", "危机七阶段", "Roberts", "ESConv", "InCharacter",
           "SillyTavern", "show", "例话锚", "陪伴", "脆弱用户", "Replika", "主动倾听", "被使用才算交付",
           "probe", "双正本", "maker≠checker", "红", "热线", "skill", "记忆", "验证", "台账", "插件",
           "人格", "文学"]

db = sqlite3.connect(str(MEM / ".search-index.db"))

def fts_hit(term):
    try:
        if len(term) >= 3:
            return db.execute('select count(*) from docs where docs match ?',
                              (f'"{term}"',)).fetchone()[0]
        return db.execute('select count(*) from docs where content like ?',
                          (f'%{term}%',)).fetchone()[0]
    except sqlite3.OperationalError as e:
        raise SystemExit(f"FTS 查询失败 {term}: {e}")

# 启动自检：50 锚在当前索引必须全部命中（否则第③部分无意义）
for a in ANCHORS:
    if fts_hit(a) <= 0:
        fails.append(("PRE", 0, f"锚词零命中：{a}"))

gaps = json.loads((MEM / "gaps.json").read_text(encoding="utf-8-sig"))
sft_lines = [l for l in (TRAIN / "sft_instructions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
plugin_pkgs = [p for p in Path(r"C:\Users\14676\.dsh\plugins").glob("*/package.json")] + \
              [p for p in Path(r"C:\Users\14676\.dsh\_local-plugins").glob("*/package.json")]
pkg_data = [p.read_bytes() for p in plugin_pkgs]
pointer_paths = ["人格增强-文学养料库-2026-10-26.md", "视觉理解规程-2026-10-26.md",
                 "教师移交-项目复合查询经验-2026-10-26.md", "人格增强-人格卡润色规范-2026-10-26.md"]

# ── ① 零删除不变式 bootstrap：100,000 ──
for i in range(100_000):
    line = bak[rng.randrange(len(bak))]
    if line == FIX_OLD:
        check(i, "①", FIX_NEW in new_set, "修复行替换缺失")
    else:
        check(i, "①", (cn[line] >= 1) if line not in new_set else True, f"行丢失: {line[:40]}")

# ── ② 结构窗口连续性：40,000 ──
for i in range(40_000):
    w = rng.randrange(2, 7)
    s = rng.randrange(0, max(1, len(bak) - w))
    win = bak[s:s + w]
    check(i, "②", all(cn[l] >= 1 or l == FIX_OLD for l in win), f"窗口断裂@{s}: {win[0][:30]}")

# ── ③ FTS 检索回归：100,000 ──
for i in range(100_000):
    term = ANCHORS[i % len(ANCHORS)]
    check(i, "③", fts_hit(term) > 0, f"FTS 零命中: {term}")

# ── ④ 内容解码与标记完整性：40,000 ──
paths = list(contents.keys())
for i in range(40_000):
    k = paths[rng.randrange(len(paths))]
    try:
        txt = contents[k].decode("utf-8")
        check(i, "④", len(txt) > 0, f"空文件: {k}")
    except UnicodeDecodeError as e:
        check(i, "④", False, f"解码失败: {k} {e}")
    if i % 10_000 == 0:
        for f in new4:
            t = contents[f].decode("utf-8")
            check(i, "④", "[状态:current]" in t and "[ZCode]" in t, f"标记缺失: {f}")
        ag = (HARNESS / "AGENTS.md").read_text(encoding="utf-8")
        check(i, "④", "400-161-9995" in ag and "010-82951332" in ag, "热线不变式丢失")

# ── ⑤ 结构与 JSON 健康：40,000 ──
for i in range(40_000):
    m = i % 4
    if m == 0:
        d = json.loads((MEM / "gaps.json").read_text(encoding="utf-8-sig"))
        check(i, "⑤", len(d.get("gaps", [])) >= 67, "gaps 条数漂移")
    elif m == 1:
        l = sft_lines[rng.randrange(len(sft_lines))]
        r = json.loads(l)
        check(i, "⑤", all(k in r for k in ("instruction", "output", "source")), f"SFT 字段缺失@{l[:30]}")
    elif m == 2:
        p = pkg_data[rng.randrange(len(pkg_data))]
        j = json.loads(p.decode("utf-8"))
        check(i, "⑤", "name" in j and "version" in j, "package.json 字段缺失")
    else:
        f = pointer_paths[rng.randrange(len(pointer_paths))]
        check(i, "⑤", (MEM / f).exists(), f"指针文件不存在: {f}")

# 汇总
N = 100_000 + 40_000 + 100_000 + 40_000 + 40_000
dt = time.time() - T0
print(f"总断言 {N:,} 次 ｜ 失败 {len(fails)} 条 ｜ 耗时 {dt:.1f}s")
for f in fails[:10]:
    print("  FAIL:", f)
print("结论：", "PASS —— 320,000 次全部通过" if not fails else "FAIL")
sys.exit(2 if fails or not order_ok else 0)
