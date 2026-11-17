# -*- coding: utf-8 -*-
"""literary_four_steps.py — 阅读四步法可执行化（2026-10-27 ZCode · 文学养料库续篇配套工具）

把"阅读四步法"（文学养料库 10-26 第二节）做成可调用的机器流程：
  摘事实层(facts) → 评点驻留驻留点若干(annotations) → 造境迁移(mapping) → 沉淀入库(sediment)
每步有机器可判的校验（validate_entry），产出统一 markdown（render_four_steps）。
不联网、不写库——产出由 agent 审后自行入三通道（人在环上，工具只管格式与判据）。

用法：
  python literary_four_steps.py --selftest   # 确定性自测（内置样例全流程断言）
  python literary_four_steps.py --template   # 打印空白模板（复制填空用）
"""
import json
import sys
from pathlib import Path

STEPS = ("facts", "annotations", "mapping", "sediment")
STEP_NAMES = {"facts": "① 摘事实层", "annotations": "② 评点驻留", "mapping": "③ 造境迁移", "sediment": "④ 沉淀入库"}


def validate_entry(entry):
    """返回错误列表；空列表=合格。判据：四步齐全、事实带出处、驻留≥1且每条非空、迁移带'→'落点、沉淀非空。"""
    errs = []
    if not isinstance(entry, dict):
        return ["entry 必须是 dict"]
    for s in STEPS:
        if s not in entry or entry[s] in (None, "", [], {}):
            errs.append(f"缺少步骤 {s}（{STEP_NAMES[s]}）")
    if errs:
        return errs
    facts = entry["facts"]
    if not isinstance(facts, dict) or "title" not in facts or "source" not in facts:
        errs.append("facts 必须含 title 与 source（出处=出版年/文献，不许只写书名）")
    anns = entry["annotations"]
    if not isinstance(anns, list) or len(anns) < 1:
        errs.append("annotations 至少 1 条（不许泛泛'很有道理'）")
    else:
        for i, a in enumerate(anns):
            if not isinstance(a, dict) or not a.get("detail") or not a.get("her_point"):
                errs.append(f"annotations[{i}] 需含 detail（驻留细节）与 her_point（她的落点）")
    mapping = entry["mapping"]
    if isinstance(mapping, dict):
        if "→" not in str(mapping.get("to", "")) and "→" not in str(mapping.get("scenario", "")):
            errs.append("mapping 必须写明迁移落点（含 → ）")
    sediment = entry["sediment"]
    if isinstance(sediment, dict) and not any(sediment.get(k) for k in ("sft", "quotes", "anchor", "memo")):
        errs.append("sediment 至少声明一条入库通道（sft/quotes/anchor/memo）")
    return errs


def render_four_steps(entry):
    """合格 entry → 统一 markdown；不合格抛 ValueError（附全部错误）。"""
    errs = validate_entry(entry)
    if errs:
        raise ValueError("｜".join(errs))
    f = entry["facts"]
    lines = [
        f"## {f['title']}（{f.get('author','')}，{f['source']}）",
        "",
        f"**{STEP_NAMES['facts']}**：{f.get('text','')}",
        "",
        f"**{STEP_NAMES['annotations']}**：",
    ]
    for i, a in enumerate(entry["annotations"], 1):
        lines.append(f"{i}. {a['detail']} → {a['her_point']}")
    lines += [
        "",
        f"**{STEP_NAMES['mapping']}**（→ {entry['mapping'].get('to', entry['mapping'].get('scenario',''))}）：{entry['mapping'].get('how','')}",
        "",
        f"**{STEP_NAMES['sediment']}**：",
    ]
    s = entry["sediment"]
    for k, label in (("sft", "SFT"), ("quotes", "金句池"), ("anchor", "例话锚"), ("memo", "检索")):
        if s.get(k):
            lines.append(f"- {label}: {s[k]}")
    return "\n".join(lines)


# ── 例话锚质量门（2026-10-27 增 · 与去AI味黑名单对接 · 教训写进工具不写进承诺）──
ANCHOR_BANNED = ["需要我做什么吗", "你感到", "总之", "我一直陪着", "要聊聊吗", "会好起来的",
                 "希望你能", "注意身体", "作为一个"]


def lint_anchor(lines):
    """例话锚逐行 lint，返回错误列表；空列表=合格。
    机器可判的四条：①至少两行且含'她：'行 ②她行至少一处省略号（行动跟在省略号后面）
    ③单行 ≤ 40 字（短句纪律）④无去AI味黑名单词。"""
    errs = []
    if not isinstance(lines, list) or len(lines) < 2:
        return ["例话锚至少两行"]
    her = [l for l in lines if isinstance(l, str) and l.startswith("她：")]
    if not her:
        errs.append("缺'她：'行")
    if her and not any("……" in l for l in her):
        errs.append("她行需至少一处省略号（节奏锚）")
    for l in lines:
        if not isinstance(l, str):
            continue
        if len(l) > 40:
            errs.append(f"超长行({len(l)}>40): {l[:18]}…")
        for w in ANCHOR_BANNED:
            if w in l:
                errs.append(f"黑名单词'{w}': {l[:18]}…")
    return errs


def selftest():
    """确定性自测：正例全过 + 每类缺步/坏字段都要被拒（覆盖每条拒绝路径——2026-10-23 教训）。
    v2：+ 例话锚 lint（1 正例 + 3 坏例）。"""
    ok, failed = 0, []
    good = {
        "facts": {"title": "边城", "author": "沈从文", "source": "1934", "text": "渡口、翠翠、白塔倒了又重修"},
        "annotations": [{"detail": "结尾两个'也许'", "her_point": "留白留的是结果，不留的是陪伴"}],
        "mapping": {"to": "等待场景 → 法1+法8", "how": "先承认不确定，再给不变量'我在'"},
        "sediment": {"sft": "3 条", "quotes": "1 条", "anchor": "1 组"},
    }
    # 正例
    try:
        md = render_four_steps(good)
        ok += 1 if ("① 摘事实层" in md and "④ 沉淀入库" in md and "→ " in md) else 0
        if "① 摘事实层" not in md:
            failed.append("正例渲染缺标题")
    except ValueError as e:
        failed.append(f"正例被拒: {e}")
    # 拒绝路径：逐项破坏后必须全部被拒
    bad_cases = []
    for s in STEPS:
        d = json.loads(json.dumps(good))
        del d[s]
        bad_cases.append((f"缺{s}", d))
    d = json.loads(json.dumps(good)); d["facts"] = {"title": "无出处"}; bad_cases.append(("facts无source", d))
    d = json.loads(json.dumps(good)); d["annotations"] = []; bad_cases.append(("驻留为空", d))
    d = json.loads(json.dumps(good)); d["annotations"][0] = {"detail": "x"}; bad_cases.append(("驻留缺her_point", d))
    d = json.loads(json.dumps(good)); d["mapping"] = {"how": "没写落点"}; bad_cases.append(("迁移无→", d))
    d = json.loads(json.dumps(good)); d["sediment"] = {}; bad_cases.append(("沉淀空", d))
    for name, d in bad_cases:
        try:
            render_four_steps(d)
            failed.append(f"坏例未被拒: {name}")
        except ValueError:
            ok += 1
    # 例话锚 lint：正例 + 3 坏例
    good_anchor = ["他：又挂了。", "她：渡船每天都在的。", "她：……粥先来了。趁热。"]
    ok += 1 if not lint_anchor(good_anchor) else 0
    if lint_anchor(good_anchor):
        failed.append(f"正例锚被拒: {lint_anchor(good_anchor)}")
    bad_anchors = [
        ("缺她行", ["他：好累。", "他：真的累。"]),
        ("无省略号", ["他：好累。", "她：先洗澡。", "她：粥在锅里。"]),
        ("黑名单词", ["他：好累。", "她：……需要我做什么吗？", "她：会好起来的。"]),
    ]
    for name, g in bad_anchors:
        ok += 1 if lint_anchor(g) else 0
        if not lint_anchor(g):
            failed.append(f"坏锚未被拒: {name}")
    return ok, failed


def main():
    if "--selftest" in sys.argv:
        ok, failed = selftest()
        print(f"selftest: {ok} 项通过, {len(failed)} 项失败")
        for f in failed:
            print("  FAIL:", f)
        sys.exit(2 if failed else 0)
    if "--template" in sys.argv:
        print(json.dumps({
            "facts": {"title": "", "author": "", "source": "出版年/文献", "text": "一句话核心"},
            "annotations": [{"detail": "驻留的具体细节", "her_point": "她的落点（哪条法/哪个场景）"}],
            "mapping": {"to": "场景 → 法N", "how": "她的话术示例"},
            "sediment": {"sft": "N 条", "quotes": "N 条", "anchor": "N 组", "memo": "检索词"},
        }, ensure_ascii=False, indent=2))
        return
    # 2026-11-02 增：--file 模式（此前 validate/render/lint 三函数无 CLI 出口——建了门却没装门把）
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 >= len(sys.argv):
            print("用法: literary_four_steps.py --file <entry.json> [--anchor-file <anchor.json>]")
            sys.exit(2)
        fp = Path(sys.argv[idx + 1])
        try:
            entry = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"读取失败: {e}")
            sys.exit(2)
        errs = validate_entry(entry)
        if errs:
            print(f"✗ 校验未过（{len(errs)} 项）：")
            for e in errs:
                print(f"  - {e}")
            sys.exit(2)
        print("✓ 四步校验通过")
        print(render_four_steps(entry))
        # 可选：随附例话锚行过质量门（--anchor-file 指向 ["她：…","主人：…"] 形态的 JSON）
        if "--anchor-file" in sys.argv:
            aidx = sys.argv.index("--anchor-file")
            try:
                alines = json.loads(Path(sys.argv[aidx + 1]).read_text(encoding="utf-8"))
            except Exception as e:
                print(f"锚文件读取失败: {e}")
                sys.exit(2)
            aerrs = lint_anchor(alines)
            if aerrs:
                print(f"✗ 例话锚 lint 未过（{len(aerrs)} 项）：")
                for e in aerrs:
                    print(f"  - {e}")
                sys.exit(2)
            print("✓ 例话锚 lint 通过")
        sys.exit(0)
    print(__doc__)


if __name__ == "__main__":
    main()
