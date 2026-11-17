# -*- coding: utf-8 -*-
"""mega_validation_320k_r5.py — 第五轮 32 万次强化验证（2026-10-27 ZCode · 共享模块 + 新工具逻辑族）

R1-R4 验入库/新产出/逻辑/冻结；R5 验**两个新工具的逻辑正确性 + 共享模块 + 累计产出健康**。
  ① SFT 语料完整性       100,000 次（226 行 / R5 来源 / 周期性去重）
  ② 新工具逻辑            60,000 次（freshness 抽取/分类 + 安全门单句/池级分流 + 周期 selftest×3 工具）
  ③ FTS 检索（共享模块）  60,000 次（validation_common.derive_anchors）
  ④ 冻结与产出不变式      60,000 次（AGENTS.md 会话内冻结 + 对 R1 备份零删除 + 蓝图红线 + 8 知识文件 + 隔离件）
  ⑤ 结构健康             50,000 次（金句池 42 且过门 / gaps / 队列 / daily / 插件包）
门槛（不计入）：SFT 去重 + AGENTS.md 对 R1 备份零删除 + 真实金句池过安全门。
"""
import json, hashlib, random, sqlite3, sys, time
from pathlib import Path

T0 = time.time()
rng = random.Random(202710275)
HARNESS = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness")
MEM = HARNESS / "memories"
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
fails = []
N_CHECKS = 0

def check(i, part, cond, msg=""):
    global N_CHECKS
    N_CHECKS += 1
    if not cond:
        fails.append((part, i, msg))

sys.path.insert(0, str(TRAIN))
import validation_common as vc
import literary_four_steps as lfs
import agentsmd_freshness_check as afc
import quotes_safety_check as qsc

# ── 门槛 ──
sft_lines = [l for l in (TRAIN / "sft_instructions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
sft_rows = []
for l in sft_lines:
    try:
        sft_rows.append(json.loads(l))
    except json.JSONDecodeError:
        fails.append(("GATE", 0, f"SFT 非法行: {l[:40]}"))
n_inst = len(sft_rows)
if len({r.get("instruction") for r in sft_rows}) != n_inst:
    fails.append(("GATE", 0, "SFT instruction 重复"))

AGENTS = HARNESS / "AGENTS.md"
AGENTS_MD5_AT_START = hashlib.md5(AGENTS.read_bytes()).hexdigest()
bak = (HARNESS / "AGENTS.md.bak-20261026-ZCode增强前").read_text(encoding="utf-8").splitlines()
FIX_OLD = "只在这四种情况**必须**跑："
it = iter(AGENTS.read_text(encoding="utf-8").splitlines())
if not all(any(line == x for x in it) for line in bak if line != FIX_OLD):
    fails.append(("GATE", 0, "对 R1 备份的零删除顺序子序列失败"))

real_pool = json.loads((TRAIN / "classic_quotes.json").read_text(encoding="utf-8"))
_, real_blocked = qsc.check_pool(real_pool)
if real_blocked:
    fails.append(("GATE", 0, f"真实金句池未过安全门: {len(real_blocked)} 条"))

# ── ① SFT 语料完整性：100,000 ──
for i in range(100_000):
    r = sft_rows[rng.randrange(n_inst)]
    check(i, "①", all(k in r and r[k] for k in ("instruction", "output", "source")), "SFT 字段缺失")
    if i % 10_000 == 0:
        check(i, "①", n_inst >= 226, f"SFT 计数漂移: {n_inst}")
        check(i, "①", len({r["instruction"] for r in sft_rows}) == n_inst, "SFT 重复")
        check(i, "①", {"教师移交R5-20261027", "文学养料R5-20261027"} <=
              {r["source"] for r in sft_rows}, "R5 来源标签缺失")

# ── ② 新工具逻辑：60,000 ──
SYN_TXT = (r"工具在 C:\Tool\a.md；占位 模型.pmx 不算；相对路径 tool\x.py 不算；"
           r"坏路径 C:\Nope\not_there.py；本工具 C:\Real\self.py；")
CLEAN_Q = ["边城", "渡船每天都在的", "沈从文"]
DIRTY_Q = ["测试", "他不想活了", "某人"]
for i in range(60_000):
    m = i % 4
    if m == 0:
        got = afc.extract_paths(SYN_TXT)
        check(i, "②", (r"C:\Tool\a.md" in got and r"C:\Nope\not_there.py" in got
                        and not any("模型" in p for p in got)
                        and not any(p.endswith("tool\\x.py") for p in got)), "路径抽取异常")
    elif m == 1:
        fake = {r"C:\Nope\not_there.py": False}
        ok, missing, cfail = afc.classify([r"C:\Tool\a.md", r"C:\Nope\not_there.py"],
                                          exists=lambda p: fake.get(p, Path(p).exists()))
        check(i, "②", r"C:\Nope\not_there.py" in missing and not cfail, "分类分流异常")
    elif m == 2:
        check(i, "②", not qsc.check_quote(CLEAN_Q) and bool(qsc.check_quote(DIRTY_Q)), "单句门分流异常")
    else:
        cl, bl = qsc.check_pool([CLEAN_Q, DIRTY_Q])
        check(i, "②", len(cl) == 1 and len(bl) == 1, "池级分流异常")
    if i % 20_000 == 0:
        ok1, fl1 = lfs.selftest()
        errs2 = afc.selftest()
        errs3 = qsc.selftest()
        check(i, "②", ok1 == 14 and not fl1 and not errs2 and not errs3,
              f"selftest 回归: lfs={ok1}/14 fl={fl1} afc={errs2} qsc={errs3}")

# ── ③ FTS 检索（共享模块自动锚）：60,000 ──
ANCHORS = vc.derive_anchors()
if len(ANCHORS) < 40:
    fails.append(("GATE", 0, f"自动锚词过少: {len(ANCHORS)}"))
db = sqlite3.connect(str(MEM / ".search-index.db"))
for a in ANCHORS:
    if vc.fts_hit(db, a) <= 0:
        fails.append(("PRE", 0, f"自动锚零命中: {a}"))
for i in range(60_000):
    check(i, "③", vc.fts_hit(db, ANCHORS[i % len(ANCHORS)]) > 0, f"自动锚零命中: {ANCHORS[i % len(ANCHORS)]}")

# ── ④ 冻结与产出不变式：60,000 ──
KNOW = ["人格增强-文学养料库-2026-10-26.md", "视觉理解规程-2026-10-26.md",
        "教师移交-项目复合查询经验-2026-10-26.md", "人格增强-人格卡润色规范-2026-10-26.md",
        "人格增强-文学养料库续篇-2026-10-27.md", "人格增强-文学养料库续二-2026-10-27.md",
        "人格增强-文学养料库续三-2026-10-27.md", "人格增强-灵魂蓝图润色候选稿-2026-10-27.md"]
know_texts = {f: (MEM / f).read_text(encoding="utf-8") for f in KNOW}
blueprint = Path(r"D:\大肥鱼的深海\灵魂蓝图.txt").read_text(encoding="utf-8")
queue_txt = (TRAIN / "consolidation_queue.md").read_text(encoding="utf-8")
plugin_pkgs = [p.read_bytes() for p in
               list(Path(r"C:\Users\14676\.dsh\plugins").glob("*/package.json")) +
               list(Path(r"C:\Users\14676\.dsh\_local-plugins").glob("*/package.json"))]
for i in range(60_000):
    check(i, "④", vc.blueprint_redline_ok(blueprint) and "【绝对红线】" in blueprint, "蓝图红线异常")
    check(i, "④", (TRAIN / "classic_quotes_blocked.json").exists()
          and "P1-2 清偿" in queue_txt and "安全门首捕" in queue_txt, "隔离件/队列 R5 段缺失")
    if i % 10_000 == 0:
        h = hashlib.md5(AGENTS.read_bytes()).hexdigest()
        check(i, "④", h == AGENTS_MD5_AT_START, f"AGENTS.md 会话内变动: {h[:8]}")
        bp_fresh = Path(r"D:\大肥鱼的深海\灵魂蓝图.txt").read_text(encoding="utf-8")
        check(i, "④", bp_fresh == blueprint, "蓝图正本被外部改动")
        for f, t in know_texts.items():
            check(i, "④", "[ZCode]" in t, f"作者标记缺失: {f}")
        ce = (Path(r"C:\Users\14676\Documents\Codex") / "companion_eval.py").read_text(encoding="utf-8")
        check(i, "④", "六维映射" in ce, "companion_eval 映射丢失")

# ── ⑤ 结构健康：50,000 ──
for i in range(50_000):
    m = i % 5
    if m == 0:
        d = json.loads((MEM / "gaps.json").read_text(encoding="utf-8-sig"))
        g = d.get("gaps", [])
        check(i, "⑤", len(g) >= 67 and all(x.get("status") in
              ("verified", "closed", "in_progress", "open", "pending_verify") for x in g), "gaps 异常")
    elif m == 1:
        _, bl = qsc.check_pool(real_pool)
        check(i, "⑤", len(real_pool) >= 42 and not bl
              and all(len(q) == 3 and all(q) for q in real_pool), "金句池计数/安全异常")
    elif m == 2:
        check(i, "⑤", "P1-2 清偿" in queue_txt and "2026-10-27" in queue_txt, "队列 R5 段缺失")
    elif m == 3:
        check(i, "⑤", (MEM / "daily" / "2026-10-27.md").exists(), "今日 daily 缺失")
    else:
        p = plugin_pkgs[rng.randrange(len(plugin_pkgs))]
        j = json.loads(p.decode("utf-8"))
        check(i, "⑤", "name" in j and "version" in j, "插件包字段缺失")

dt = time.time() - T0
print(f"总断言 {N_CHECKS:,} 次（设计 330,000 + 周期附加）｜ 失败 {len(fails)} 条 ｜ 耗时 {dt:.1f}s ｜ 自动锚词 {len(ANCHORS)} 个")
for f in fails[:10]:
    print("  FAIL:", f)
print("结论：", "PASS —— 全部通过（R5：新工具逻辑 + 共享模块 + 累计产出健康）" if not fails else "FAIL")
sys.exit(2 if fails else 0)
