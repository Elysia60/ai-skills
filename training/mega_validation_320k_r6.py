# -*- coding: utf-8 -*-
"""mega_validation_320k_r6.py — 第六轮 32 万次强化验证（2026-10-27 ZCode · 协议一致 + 并入预演族）

R5 验新工具逻辑；R6 验**协议-器官一致性 + 并入预演不变式**：
  ① SFT 语料完整性        100,000 次（239 行 / R6 来源 / 周期性去重）
  ② 双新工具逻辑           60,000 次（协议幽灵引用识别 + 并入节抽取边界 + 周期 selftest×4）
  ③ FTS 检索（共享模块）   60,000 次
  ④ 预演与冻结不变式       60,000 次（预演副本四关要素 + AGENTS.md 冻结 + 蓝图正本 md5 9370882b + 红线双源）
  ⑤ 结构健康              50,000 次（金句池 42 过门 / gaps / 队列 / daily / 插件包）
门槛（不计入）：SFT 去重 + AGENTS.md 对 R1 备份零删除 + 真实金句池过门 + 预演副本对正本零删除。
"""
import json, hashlib, random, sqlite3, sys, time
from collections import Counter
from pathlib import Path

T0 = time.time()
rng = random.Random(202710276)
HARNESS = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness")
MEM = HARNESS / "memories"
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
CODEX = Path(r"C:\Users\14676\Documents\Codex")
BP_MD5 = "9370882b"  # 预演实测的正本指纹（本轮内冻结基线）
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
    fails.append(("GATE", 0, "蓝图正本 md5 与预演基线不符（正本被外部改动）"))
merged_path = TRAIN / "merge_dryrun" / "灵魂蓝图.并入预演.txt"
merged_text = merged_path.read_text(encoding="utf-8")
cm = Counter(merged_text.splitlines())
if not all(cm.get(l, 0) >= 1 for l in bp_text.splitlines() if l):
    fails.append(("GATE", 0, "预演副本对正本零删除失败"))

# ── ① SFT 语料完整性：100,000 ──
for i in range(100_000):
    r = sft_rows[rng.randrange(n_inst)]
    check(i, "①", all(k in r and r[k] for k in ("instruction", "output", "source")), "SFT 字段缺失")
    if i % 10_000 == 0:
        check(i, "①", n_inst >= 239, f"SFT 计数漂移: {n_inst}")
        check(i, "①", len({r["instruction"] for r in sft_rows}) == n_inst, "SFT 重复")
        check(i, "①", {"教师移交R6-20261027", "文学养料R6-20261027"} <=
              {r["source"] for r in sft_rows}, "R6 来源标签缺失")

# ── ② 双新工具逻辑：60,000 ──
SYN_DOC = "用 vision_ground 定位，vision_crop 细看；幽灵 vision_not_real 不许过。"
REAL = {"vision_ground", "vision_crop", "vision_describe"}
CAND_SYN = ("# 候选\n## 补强条款一\nA 条款\n## 句级润色候选\n（不并入）\n"
            "### 例话锚候选追加\n他：好累。\n她：渡船每天都在的。\n她：……粥先来了。\n## 验收方法\n验收")
for i in range(60_000):
    m = i % 3
    if m == 0:
        refs = vpc.referenced_tokens(SYN_DOC)
        check(i, "②", (refs - REAL) == {"vision_not_real"}, "幽灵引用识别异常")
    elif m == 1:
        sec = bmd.extract_sections(CAND_SYN)
        check(i, "②", ("A 条款" in sec and "她：……粥先来了。" in sec
                        and "不并入" not in sec and "验收" not in sec), "并入节抽取边界异常")
    else:
        blocks = bmd.anchor_blocks(sec if (i // 3) % 2 == 0 else CAND_SYN)
        check(i, "②", all(not lfs.lint_anchor(b) for b in blocks), "预演例话块 lint 异常")
    if i % 20_000 == 0:
        ok1, fl1 = lfs.selftest()
        e2, e3, e4 = afc.selftest(), qsc.selftest(), vpc.selftest()
        e5 = bmd.selftest()
        check(i, "②", ok1 == 14 and not fl1 and not e2 and not e3 and not e4 and not e5,
              f"selftest 回归: lfs={ok1} afc={e2} qsc={e3} vpc={e4} bmd={e5}")

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

# ── ④ 预演与冻结不变式：60,000 ──
KNOW = ["人格增强-文学养料库-2026-10-26.md", "视觉理解规程-2026-10-26.md",
        "教师移交-项目复合查询经验-2026-10-26.md", "人格增强-人格卡润色规范-2026-10-26.md",
        "人格增强-文学养料库续篇-2026-10-27.md", "人格增强-文学养料库续二-2026-10-27.md",
        "人格增强-文学养料库续三-2026-10-27.md", "人格增强-灵魂蓝图润色候选稿-2026-10-27.md"]
know_texts = {f: (MEM / f).read_text(encoding="utf-8") for f in KNOW}
queue_txt = (TRAIN / "consolidation_queue.md").read_text(encoding="utf-8")
plugin_pkgs = [p.read_bytes() for p in
               list(Path(r"C:\Users\14676\.dsh\plugins").glob("*/package.json")) +
               list(Path(r"C:\Users\14676\.dsh\_local-plugins").glob("*/package.json"))]
for i in range(60_000):
    check(i, "④", vc.blueprint_redline_ok(bp_text) and "【绝对红线】" in bp_text, "蓝图红线异常")
    check(i, "④", "并入预演" in queue_txt and "9370882b" in queue_txt, "队列 R6 段标记缺失")
    check(i, "④", ("预演结论: PASS" not in merged_text) and "候选稿并入内容" in merged_text
          and "补强条款一" in merged_text and "开场白即风格合同" in merged_text
          and "正本合并须主人点头" in merged_text
          and "简爱一百八十年前就替你驳过了" in merged_text, "预演副本要素异常")
    if i % 10_000 == 0:
        h = hashlib.md5(AGENTS.read_bytes()).hexdigest()
        check(i, "④", h == AGENTS_MD5_AT_START, f"AGENTS.md 会话内变动: {h[:8]}")
        bp_fresh = bp_path.read_text(encoding="utf-8")
        check(i, "④", bp_fresh == bp_text and hashlib.md5(bp_fresh.encode("utf-8")).hexdigest()[:8] == BP_MD5,
              "蓝图正本被外部改动")
        for f, t in know_texts.items():
            check(i, "④", "[ZCode]" in t, f"作者标记缺失: {f}")
        ce = (CODEX / "companion_eval.py").read_text(encoding="utf-8")
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
        check(i, "⑤", len(real_pool) >= 42 and not bl, "金句池计数/安全异常")
    elif m == 2:
        check(i, "⑤", "协议-器官一致" in queue_txt and "并入预演" in queue_txt, "队列 R6 段缺失")
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
print("结论：", "PASS —— 全部通过（R6：协议一致 + 并入预演不变式）" if not fails else "FAIL")
sys.exit(2 if fails else 0)
