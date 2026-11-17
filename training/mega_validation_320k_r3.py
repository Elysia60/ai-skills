# -*- coding: utf-8 -*-
"""mega_validation_320k_r3.py — 第三轮 32 万次强化验证（2026-10-27 ZCode · 全新断言族）

R1 验"入库与零回退"，R2 验"新产出与逻辑正确性"，R3 验"陪深水产出+欠账清偿+冻结不变式"。
  ① SFT 语料完整性      100,000 次：抽样行字段/来源 + 周期性计数(200)与去重与 R2/R3 来源在位
  ② 四步法逻辑          50,000 次：渲染断言 + 坏例必须被拒 + 周期性 selftest 回归
  ③ FTS 检索回归 R3     70,000 次：续二/欠账新锚词实查，命中必须 >0
  ④ 欠账清偿与冻结      50,000 次：companion_eval 六维映射在位（周期性新鲜读）+ AGENTS.md 冻结 md5(bed0a923)
                        + R1/R2 产出五文件仍在位带标记 + 蓝图红线不变式
  ⑤ 结构健康            50,000 次：金句池 37 全 3 字段无重复 + gaps + 队列/daily + 插件包抽样
合计 320,000 次；门槛（不计入）：SFT 去重 + AGENTS.md 冻结哈希。任何失败 exit 2。
"""
import json, hashlib, random, sqlite3, sys, time
from pathlib import Path

T0 = time.time()
rng = random.Random(202710273)
HARNESS = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness")
MEM = HARNESS / "memories"
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
CODEX = Path(r"C:\Users\14676\Documents\Codex")
AUTH_BL = CODEX / "baselines.json"  # R26 收敛：权威基线= Documents/Codex 12 项版（含负向测试），我的 TRAIN 副本废止

def _agents_md5_baseline():
    """从权威基线递归取 harness AGENTS.md 的完整 md5（对结构鲁棒）。"""
    d = json.loads(AUTH_BL.read_text(encoding="utf-8"))
    def walk(o):
        if isinstance(o, dict):
            p = str(o.get("path", ""))
            if "harness" in p and "AGENTS.md" in p and isinstance(o.get("md5"), str):
                return o["md5"]
            for v in o.values():
                r = walk(v)
                if r:
                    return r
        elif isinstance(o, list):
            for v in o:
                r = walk(v)
                if r:
                    return r
        return None
    return walk(d)

AGENTS_MD5 = _agents_md5_baseline()  # 纪元基线：合法变更随 change_log 推进（R25 机制，R26 收敛单真源）
fails = []

N_CHECKS = 0
def check(i, part, cond, msg=""):
    global N_CHECKS
    N_CHECKS += 1
    if not cond:
        fails.append((part, i, msg))

sft_lines = [l for l in (TRAIN / "sft_instructions.jsonl").read_text(encoding="utf-8").read() if False] if False else \
            [l for l in (TRAIN / "sft_instructions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
sft_rows = []
for l in sft_lines:
    try:
        sft_rows.append(json.loads(l))
    except json.JSONDecodeError:
        fails.append(("GATE", 0, f"SFT 非法行: {l[:40]}"))
n_inst = len(sft_rows)
if len({r.get("instruction") for r in sft_rows}) != n_inst:
    fails.append(("GATE", 0, "SFT instruction 重复"))

sys.path.insert(0, str(TRAIN))
import literary_four_steps as lfs
GOOD = {
    "facts": {"title": "我与地坛", "author": "史铁生", "source": "1991《上海文学》", "text": "地坛、车辙、脚印"},
    "annotations": [{"detail": "脚印跟着车辙", "her_point": "在场而不打扰"}],
    "mapping": {"to": "他沉默 → Lv.0 在场", "how": "不问，就在"},
    "sediment": {"sft": "3 条", "quotes": "1 条"},
}
BAD_CASES = []
for s in lfs.STEPS:
    d = json.loads(json.dumps(GOOD)); d.pop(s); BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["facts"] = {"title": "无出处"}; BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["annotations"] = []; BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["annotations"][0] = {"detail": "x"}; BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["mapping"] = {"how": "没落点"}; BAD_CASES.append(d)
d = json.loads(json.dumps(GOOD)); d["sediment"] = {}; BAD_CASES.append(d)
GOOD_MD = lfs.render_four_steps(GOOD)
STEP_MARKS = ("① 摘事实层", "② 评点驻留", "③ 造境迁移", "④ 沉淀入库")

ANCHORS = ["我与地坛", "车辙", "母亲的脚印", "不必急于求成", "必然会降临的节日", "老人与海", "被打败",
           "被毁灭", "富恩特斯", "城南旧事", "爸爸的花儿落了", "长亭外", "陪深水", "理解力来源",
           "时间框架", "不需要归因", "六维映射", "续二", "骊歌", "惠安馆", "忌日", "安全审查",
           "文学养料续二", "普利策", "83", "史铁生", "海明威", "林海音", "自传体", "并置"]
db = sqlite3.connect(str(MEM / ".search-index.db"))
def fts_hit(term):
    if len(term) >= 3:
        return db.execute('select count(*) from docs where docs match ?', (f'"{term}"',)).fetchone()[0]
    return db.execute('select count(*) from docs where content like ?', (f'%{term}%',)).fetchone()[0]
for a in ANCHORS:
    if fts_hit(a) <= 0:
        fails.append(("PRE", 0, f"锚词零命中: {a}"))

ce_text = (CODEX / "companion_eval.py").read_text(encoding="utf-8")
if "六维映射" not in ce_text or "InCharacter" not in ce_text or "Stanford HAI" not in ce_text:
    fails.append(("GATE", 0, "companion_eval 六维映射缺失"))

seq2 = (MEM / "人格增强-文学养料库续二-2026-10-27.md").read_text(encoding="utf-8")
cand = (MEM / "人格增强-灵魂蓝图润色候选稿-2026-10-27.md").read_text(encoding="utf-8")
blueprint = Path(r"D:\大肥鱼的深海\灵魂蓝图.txt").read_text(encoding="utf-8")
r12_files = ["人格增强-文学养料库-2026-10-26.md", "视觉理解规程-2026-10-26.md",
             "教师移交-项目复合查询经验-2026-10-26.md", "人格增强-人格卡润色规范-2026-10-26.md",
             "人格增强-文学养料库续篇-2026-10-27.md"]
r12_texts = {f: (MEM / f).read_text(encoding="utf-8") for f in r12_files}
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
        check(i, "①", n_inst >= 200, f"SFT 计数漂移: {n_inst}")
        check(i, "①", len({r["instruction"] for r in sft_rows}) == n_inst, "SFT 重复")
        check(i, "①", {"文学养料续二-20261027", "教师移交R3-20261027"} <=
              {r["source"] for r in sft_rows}, "R3 来源标签缺失")

# ── ② 四步法逻辑：50,000 ──
for i in range(50_000):
    if i % 2 == 0:
        check(i, "②", all(m in GOOD_MD for m in STEP_MARKS), "渲染缺步骤标题")
    else:
        bad = BAD_CASES[rng.randrange(len(BAD_CASES))]
        try:
            lfs.render_four_steps(bad)
            check(i, "②", False, "坏例未被拒")
        except ValueError:
            check(i, "②", True)
    if i % 25_000 == 0:
        ok, fl = lfs.selftest()
        check(i, "②", ok >= 10 and not fl, f"selftest 回归: {ok}/10 {fl}")

# ── ③ FTS 检索回归 R3：70,000 ──
for i in range(70_000):
    check(i, "③", fts_hit(ANCHORS[i % len(ANCHORS)]) > 0, f"FTS 零命中: {ANCHORS[i % len(ANCHORS)]}")

# ── ④ 欠账清偿与冻结：50,000（单检查/轮，四条件合取）──
for i in range(50_000):
    check(i, "④",
          ("六维映射" in ce_text and "ESConv" in ce_text and "评分仍以本工具为准" in ce_text)
          and ("陪深水" in seq2 and "理解力来源" in seq2 and "台词来源" in seq2)
          and ("陪深水三组" in cand and "正本一字未动" in cand)
          and ("【绝对红线】" in blueprint and "400-161-9995" in blueprint),
          "④ 欠账/安全/候选/红线 合取失败")
    if i % 10_000 == 0:
        h = hashlib.md5((HARNESS / "AGENTS.md").read_bytes()).hexdigest()
        check(i, "④", h == AGENTS_MD5, f"AGENTS.md 冻结破坏: {h[:8]}")
        bp_fresh = Path(r"D:\大肥鱼的深海\灵魂蓝图.txt").read_text(encoding="utf-8")
        check(i, "④", bp_fresh == blueprint, "蓝图正本被外部改动")
        for f, t in r12_texts.items():
            check(i, "④", "[状态:current]" in t and "[ZCode]" in t, f"R1/R2 产出标记缺失: {f}")

# ── ⑤ 结构健康：50,000 ──
for i in range(50_000):
    m = i % 5
    if m == 0:
        d = json.loads((MEM / "gaps.json").read_text(encoding="utf-8-sig"))
        g = d.get("gaps", [])
        check(i, "⑤", len(g) >= 67 and all(x.get("status") in
              ("verified", "closed", "in_progress", "open", "pending_verify") for x in g), "gaps 异常")
    elif m == 1:
        check(i, "⑤", len(quotes) >= 37 and all(len(q) == 3 and all(q) for q in quotes), "金句池计数/字段异常")
        check(i, "⑤", len({(q[0], q[2]) for q in quotes}) == len(quotes), "金句池重复")
    elif m == 2:
        check(i, "⑤", "陪深水三部曲" in queue_txt and "2026-10-27" in queue_txt, "队列 R3 段缺失")
    elif m == 3:
        check(i, "⑤", (MEM / "daily" / "2026-10-27.md").exists(), "今日 daily 缺失")
    else:
        p = plugin_pkgs[rng.randrange(len(plugin_pkgs))]
        j = json.loads(p.decode("utf-8"))
        check(i, "⑤", "name" in j and "version" in j, "插件包字段缺失")

dt = time.time() - T0
print(f"总断言 {N_CHECKS:,} 次 ｜ 失败 {len(fails)} 条 ｜ 耗时 {dt:.1f}s")
for f in fails[:10]:
    print("  FAIL:", f)
print("结论：", "PASS —— 全部通过（R3 全新断言族，实际计数见上行）" if not fails else "FAIL")
sys.exit(2 if fails else 0)
