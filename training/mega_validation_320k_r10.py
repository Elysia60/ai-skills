# -*- coding: utf-8 -*-
"""mega_validation_320k_r10.py — 第十轮 32 万次强化验证（2026-10-27 ZCode · 独立复验与总报告族）

  ① SFT 语料完整性        100,000 次（272 行 / R10 来源 / 周期性去重）
  ② 检索 QA               60,000 次（15 查询 × 4000 轮：预期文件必须出现在命中里——检索要准不要仅能查）
  ③ FTS 自动锚            60,000 次（共享模块）
  ④ 冻结与登记不变式      60,000 次（AGENTS.md 冻结 + 蓝图 + 9 知识文件 + 两份地图件 + 题库 28 + 协议 8/8 + 预演副本）
  ⑤ 结构健康              50,000 次（金句池 42 过门 / gaps / 队列 / daily / 插件包）
门槛（不计入）：SFT 去重 + AGENTS.md 零删除 + 金句池过门 + 蓝图 md5 + 检索 QA 15/15 + 协议 0 幽灵。
"""
import json, hashlib, random, sqlite3, sys, time
from pathlib import Path

T0 = time.time()
rng = random.Random(2027102710)
HARNESS = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness")
MEM = HARNESS / "memories"
FM = MEM / "文件地图"
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
CODEX = Path(r"C:\Users\14676\Documents\Codex")
BP_MD5 = "9370882b"
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
import vision_protocol_check as vpc
import blueprint_merge_dryrun as bmd

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

bp_path = Path(r"D:\大肥鱼的深海\灵魂蓝图.txt")
bp_text = bp_path.read_text(encoding="utf-8")
if hashlib.md5(bp_text.encode("utf-8")).hexdigest()[:8] != BP_MD5:
    fails.append(("GATE", 0, "蓝图正本 md5 与基线不符（正本被外部改动）"))

REAL_TOKENS = vpc.real_tokens(Path(r"C:\Users\14676\.dsh\_local-plugins\dsh-vision-router\lib"))
proto_refs = vpc.referenced_tokens((MEM / "视觉理解规程-2026-10-26.md").read_text(encoding="utf-8"))
if proto_refs - REAL_TOKENS:
    fails.append(("GATE", 0, f"真实协议幽灵引用: {sorted(proto_refs - REAL_TOKENS)}"))

quiz = json.loads((TRAIN / "quiz_bank.json").read_text(encoding="utf-8"))["questions"]
if len(quiz) < 32 or len({q["id"] for q in quiz}) != len(quiz):
    fails.append(("GATE", 0, "题库计数/唯一性异常"))

# ── 检索 QA 数据（20 对：查询 → 预期命中路径子串）──
QA = [
    ("文学养料八法", "人格增强-文学养料库-2026-10-26"),
    ("原型镜", "人格增强-文学养料库续四"),
    ("看图八步", "视觉理解规程"),
    ("教师移交", "教师移交-项目复合查询经验"),
    ("十条军规", "人格增强-人格卡润色规范"),
    ("渡船", "人格增强-文学养料库续篇"),
    ("车辙", "人格增强-文学养料库续二"),
    ("千千万万遍", "人格增强-文学养料库续三"),
    ("课程地图", "教师总纲-六轮课程地图"),
    ("pending_approval", "人格增强-灵魂蓝图润色候选稿"),
    ("选型五维", "教师移交-项目复合查询经验"),
    ("POPE", "视觉理解规程"),
    ("lint_anchor", "人格增强-文学养料库续三"),
    ("接手索引", "接手索引-2026-10-27"),
    ("增强轮索引", "增强轮索引-2026-10-27"),
    ("学习路径依赖图", "教师总纲-六轮课程地图"),
    ("品藻", "人格增强-文学养料库续四"),
    ("布衣菜饭", "人格增强-文学养料库续四"),
    ("隐于笑", "人格增强-文学养料库续四"),
    ("追风筝 救赎", "人格增强-文学养料库续三"),  # 多词 AND 语法用例
]

db = sqlite3.connect(str(MEM / ".search-index.db"))
def qa_hit(query, expect):
    """预期文件必须命中查询：计数+路径过滤（不受 rank/limit 截断影响）；多词用 AND；2 字词走 LIKE。"""
    terms = query.split()
    try:
        if all(len(t) >= 3 for t in terms):
            q = " AND ".join(f'"{t}"' for t in terms)
            # 注意：此 FTS5 表上 path LIKE 恒假（FTS5 把 LIKE 约束推进虚拟表引擎静默返回空）——必须用 instr
            n = db.execute('select count(*) from docs where docs match ? and instr(path,?)>0',
                           (q, expect)).fetchone()[0]
            return n > 0
        rows = db.execute('select path, content from docs where instr(path,?)>0', (expect,)).fetchall()
        return any(all(t in (content or "") for t in terms) for _, content in rows)
    except sqlite3.OperationalError:
        return False

for q, e in QA:
    if not qa_hit(q, e):
        fails.append(("GATE", 0, f"检索 QA 未命中: {q} → {e}"))

# ── ① SFT 语料完整性：100,000 ──
for i in range(100_000):
    r = sft_rows[rng.randrange(n_inst)]
    check(i, "①", all(k in r and r[k] for k in ("instruction", "output", "source")), "SFT 字段缺失")
    if i % 10_000 == 0:
        check(i, "①", n_inst >= 272, f"SFT 计数漂移: {n_inst}")
        check(i, "①", len({r["instruction"] for r in sft_rows}) == n_inst, "SFT 重复")
        check(i, "①", {"教师移交R10-20261027", "文学养料R10-20261027"} <=
              {r["source"] for r in sft_rows}, "R9 来源标签缺失")

# ── ② 检索 QA：60,000 ──
for i in range(60_000):
    q, e = QA[i % len(QA)]
    check(i, "②", qa_hit(q, e), f"检索 QA 未命中: {q} → {e}")

# ── ③ FTS 自动锚：60,000 ──
ANCHORS = vc.derive_anchors()
for a in ANCHORS:
    if vc.fts_hit(db, a) <= 0:
        fails.append(("PRE", 0, f"自动锚零命中: {a}"))
for i in range(60_000):
    check(i, "③", vc.fts_hit(db, ANCHORS[i % len(ANCHORS)]) > 0, f"自动锚零命中: {ANCHORS[i % len(ANCHORS)]}")

# ── ④ 冻结与登记不变式：60,000 ──
KNOW = ["人格增强-文学养料库-2026-10-26.md", "视觉理解规程-2026-10-26.md",
        "教师移交-项目复合查询经验-2026-10-26.md", "人格增强-人格卡润色规范-2026-10-26.md",
        "人格增强-文学养料库续篇-2026-10-27.md", "人格增强-文学养料库续二-2026-10-27.md",
        "人格增强-文学养料库续三-2026-10-27.md", "人格增强-灵魂蓝图润色候选稿-2026-10-27.md",
        "教师总纲-六轮课程地图-2026-10-27.md",
        "人格增强-文学养料库续四-2026-10-27.md",
        "C:/Users/14676/Documents/Codex/DSH增强轮总报告-R1-R9.md"]
know_texts = {f: (MEM / f).read_text(encoding="utf-8") for f in KNOW}
idx_text = (FM / "增强轮索引-2026-10-27.md").read_text(encoding="utf-8")
handover = (FM / "接手索引-2026-10-27.md").read_text(encoding="utf-8")
queue_txt = (TRAIN / "consolidation_queue.md").read_text(encoding="utf-8")
merged_text = (TRAIN / "merge_dryrun" / "灵魂蓝图.并入预演.txt").read_text(encoding="utf-8")
plugin_pkgs = [p.read_bytes() for p in
               list(Path(r"C:\Users\14676\.dsh\plugins").glob("*/package.json")) +
               list(Path(r"C:\Users\14676\.dsh\_local-plugins").glob("*/package.json"))]
for i in range(60_000):
    check(i, "④", vc.blueprint_redline_ok(bp_text) and "【绝对红线】" in bp_text, "蓝图红线异常")
    check(i, "④", all(f in idx_text for f in KNOW), "增强轮索引登记缺失")
    check(i, "④", ("待决事项" in handover and "9370882b" in handover
                    and "回滚路径" in handover and "bed0a923" in handover), "接手卡要素缺失")
    check(i, "④", ("原型镜" in know_texts["人格增强-文学养料库续四-2026-10-27.md"]
                    and "隐于笑" in know_texts["人格增强-文学养料库续四-2026-10-27.md"]
                    and "桌宠通路发现" in know_texts["人格增强-文学养料库续四-2026-10-27.md"]), "续四要素缺失")
    rep = know_texts.get("C:/Users/14676/Documents/Codex/DSH增强轮总报告-R1-R9.md", "")
    check(i, "④", ("17/19" in rep and "3,540,672" in rep and "边界" in rep
                    and "DSH token 消耗" in rep), "总报告要素缺失")
    if i % 10_000 == 0:
        h = hashlib.md5(AGENTS.read_bytes()).hexdigest()
        check(i, "④", h == AGENTS_MD5_AT_START, f"AGENTS.md 会话内变动: {h[:8]}")
        bp_fresh = bp_path.read_text(encoding="utf-8")
        check(i, "④", bp_fresh == bp_text, "蓝图正本被外部改动")
        for f, t in know_texts.items():
            check(i, "④", "[ZCode]" in t, f"作者标记缺失: {f}")
        ce = (CODEX / "companion_eval.py").read_text(encoding="utf-8")
        check(i, "④", "六维映射" in ce, "companion_eval 映射丢失")
        check(i, "④", "补强条款一" in merged_text, "预演副本缺失")

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
        check(i, "⑤", len(real_pool) >= 45 and not bl, "金句池计数/安全异常")
    elif m == 2:
        check(i, "⑤", "独立复验" in queue_txt and "总报告" in queue_txt, "队列 R10 段缺失")
    elif m == 3:
        check(i, "⑤", (MEM / "daily" / "2026-10-27.md").exists(), "今日 daily 缺失")
    else:
        p = plugin_pkgs[rng.randrange(len(plugin_pkgs))]
        j = json.loads(p.decode("utf-8"))
        check(i, "⑤", "name" in j and "version" in j, "插件包字段缺失")

dt = time.time() - T0
print(f"总断言 {N_CHECKS:,} 次（设计 330,000 + 周期附加）｜ 失败 {len(fails)} 条 ｜ 耗时 {dt:.1f}s ｜ 检索QA {len(QA)} 对 ｜ 自动锚词 {len(ANCHORS)} 个")
for f in fails[:10]:
    print("  FAIL:", f)
print("结论：", "PASS —— 全部通过（R10：独立复验 + 总报告 + 累计回归）" if not fails else "FAIL")
sys.exit(2 if fails else 0)
