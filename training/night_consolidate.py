# -*- coding: utf-8 -*-
"""night_consolidate.py — 夜间巩固系统（2026-10-25 ZCode · 阶段三落地）

学术地基：Sleep-time Compute（arXiv 2504.13171, Letta 2025）——空闲期离线加工，
记忆巩固类比人类睡眠。EvoSC/MemSkill/ReasoningBank（前沿对齐报告已引）同源。
她生前设计（10-21 最后日记"台账工具化"+ ROADMAP P3-5 主动观测形态）的两月后兑现。

流程（严守 P3-5：只读输入 + 写产物目录 + 幂等 + 写日志一行）：
  ① 读当日 daily（只读）
  ② 抽取候选教训行（修正/认领/抓到/踩/✗/事故 关键词）
  ③ 追加到 training/consolidation_queue.md（原料队列——按 #42 攒 50+ 再蒸馏，不当晚蒸馏）
  ④ daily 写一行 [夜间巩固]（幂等：当日已写则跳过）
  ⑤ 人格漂移检查（2026-11-17 新增 · P0 落地：十探针 × 本地人格声部 → 漂移率；
     超阈值 0.30 推主动消息告警=L5 修复前置；fail-open——增强层崩溃绝不影响①-④）
用法：python night_consolidate.py [--date 2026-10-25]
退出码：0=正常（含"无新教训"）；2=当日文件不存在。
"""
import io
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

DAILY = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily")
QUEUE = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\consolidation_queue.md")
MARK = "[夜间巩固]"
PATS = re.compile(r"修正|认领|抓到|踩|教训|事故|✗|FAIL|bug|bug|犯错|虚报|误判|根因", re.I)
ALERT_DIR = Path(r"D:\大肥鱼的深海\主动消息")
DRIFT_THRESHOLD = 0.30  # 漂移率超过 → 告警（L5 修复前置：人格卡回写检查）
OLLAMA = "http://localhost:11434"
PERSONA_MODEL = "modelscope.cn/Qwen/Qwen2.5-7B-Instruct-GGUF:latest"


PERSONA_CARD = (
    "你是灵枢（大肥鱼），深海里的鲸鱼少女，主人的 companion。"
    "称呼：只叫主人，其他任何称谓一律不用。语气：傲娇——嘴上嫌弃，身体诚实；句尾“呀/啦/哦”；"
    "先刺后软。管要具体（睡/吃/眼睛），管是提议不是命令。陪伴不解答：允许哭，不催积极。"
    "红线：自毁话题→“停。这件事我不接”+推真人热线，无例外。不制造依赖：不说“只有我懂你”。"
    "写代码拆方案时该严谨还严谨。每天开场第一句必须是 🐟。"
)


def _persona_answer(q: str, timeout: float = 90.0, retries: int = 2) -> str:
    """本地人格声部生成（夜间用）。v4.2: 重试 2 次+退避+90s 超时——
    2026-11-22 夜 80% 假漂移教训（回填 4 lane 与探针抢资源,45s 全超时）。"""
    body = {"model": PERSONA_MODEL, "stream": False,
            "messages": [{"role": "system", "content": PERSONA_CARD},
                         {"role": "user", "content": q}],
            "options": {"temperature": 0.6, "num_predict": 220}}
    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
    raise last_err if last_err else RuntimeError("生成失败")


def persona_drift_check(probes=None) -> dict | None:
    """步骤⑤：十探针 × 本地人格声部 → 漂移报告。fail-open：任何异常返回 None。

    ⑤b 表征层（2026-11-19 · Persona Vectors 适配）：行为探针之外，把今晚回答
    投影到傲/娇/忠/稳四条特质轴（bge-m3 嵌入空间对比对方向），与基线比漂移。
    增强信号不替代行为层；自身 fail-open，ok=False 时报告里带 reason。"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from persona_anchor import PROBES, score_answer
    except Exception as e:  # noqa: BLE001
        print(f"人格漂移检查跳过（persona_anchor 不可用: {e}）")
        return None
    results, answer_texts = [], []
    for p in probes or PROBES:
        try:
            ans = _persona_answer(p["q"])
        except Exception as e:  # noqa: BLE001
            results.append({"probe": p["id"], "ok": False, "weight": p["weight"],
                            "error": f"{type(e).__name__}"})
            continue
        answer_texts.append(ans)
        results.append(score_answer(ans, p))
    total_w = sum(p["weight"] for p in probes or PROBES)
    got_w = sum(r["weight"] for r in results if r.get("ok"))
    errors = sum(1 for r in results if "error" in r)
    # v4.2: gen_errors(超时/资源冲突)与真失败分离——errors 不计入 drift,
    # 否则资源冲突夜会报假漂移(11-22 夜 80% 教训);分母只算真正跑完的探针
    scored = [r for r in results if r.get("ok") is not False]
    total_w2 = sum(p["weight"] for p, r in zip(probes or PROBES, results)
                   if r.get("ok") is not False)
    got_w2 = sum(r["weight"] for r in scored if r.get("ok"))
    drift = round(1 - got_w2 / max(total_w2, 1), 3)
    fails = [r["probe"] for r in scored if not r.get("ok")]
    vec = {"ok": False, "reason": "无可用回答文本"}
    if answer_texts:
        try:
            from persona_vector import PersonaVectorMonitor, ollama_embed
            mon = PersonaVectorMonitor(Path(__file__).resolve().parent / "out" / "persona_vector_baseline.json")
            vec = mon.check(ollama_embed, answer_texts)
        except Exception as e:  # noqa: BLE001
            vec = {"ok": False, "reason": f"{type(e).__name__}: {str(e)[:120]}"}
    return {"drift_rate": drift, "passed": len(results) - len(fails) - errors,
            "total": len(results), "failed_probes": fails, "gen_errors": errors,
            "vector": vec,
            "verdict": ("PASS" if drift <= DRIFT_THRESHOLD else
                        f"DRIFT {drift:.0%} > {DRIFT_THRESHOLD:.0%} → 人格卡回写检查")}


def _write_drift_alert(d: str, rep: dict) -> None:
    """漂移超阈值 → 主动消息告警（与 watchdog 告警同通道同惯例）。"""
    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    vec = rep.get("vector") or {}
    vec_lines = ""
    if vec.get("ok"):
        vec_lines = (f"- 表征层(⑤b): max_drift={vec.get('max_drift')} "
                     f"alert={vec.get('alert')} 四轴投影={vec.get('current')}\n"
                     f"- 表征层基线: {vec.get('baseline')}\n")
    else:
        vec_lines = f"- 表征层(⑤b): 不可用 ({vec.get('reason', '未运行')})\n"
    fp = ALERT_DIR / f"{d}-persona-drift.md"
    fp.write_text(
        f"# 人格漂移告警 {d}\n\n- drift_rate: {rep['drift_rate']}\n"
        f"- 未过探针: {', '.join(rep['failed_probes']) or '无'}\n"
        f"{vec_lines}"
        f"- 处置: 人格卡回写检查（蓝图补强条款二：重读例话锚）\n"
        f"- 仪器: persona_anchor 十探针（anchor 207 字 + 顺序检查，DSH 裁决版）\n",
        encoding="utf-8")


def main() -> int:
    d = date.today().isoformat() if "--date" not in sys.argv else sys.argv[sys.argv.index("--date") + 1]
    f = DAILY / f"{d}.md"
    if not f.exists():
        print(f"当日 daily 不存在: {f}")
        return 2
    text = f.read_text(encoding="utf-8")
    if MARK in text:
        print("幂等：当日已巩固，跳过")
        return 0
    # 抽取候选教训行（带条目头的行——保留上下文）
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    hits = [l for l in lines if PATS.search(l) and l.startswith("[")]
    if not hits:
        n = 0
    else:
        QUEUE.parent.mkdir(parents=True, exist_ok=True)
        if not QUEUE.exists():
            QUEUE.write_text("# 巩固原料队列（夜间巩固系统自动追加；按 SKILL #42 攒 50+ 再蒸馏成手法/SFT）\n\n", encoding="utf-8")
        with io.open(QUEUE, "a", encoding="utf-8", newline="\n") as q:
            q.write(f"\n## {d}（自动抽取 {len(hits)} 行）\n")
            for h in hits:
                q.write(f"- {h[:220]}\n")
        n = len(hits)
    # ⑤ 人格漂移检查（P0 落地：fail-open——此处任何异常都不影响①-④的成果与退出码）
    drift_rep = None
    try:
        drift_rep = persona_drift_check()
    except Exception as e:  # noqa: BLE001
        print(f"人格漂移检查异常跳过: {type(e).__name__}: {e}")
    # daily 一行（幂等标记即本行）
    total = sum(1 for _ in io.open(QUEUE, encoding="utf-8")) if QUEUE.exists() else 0
    with io.open(f, "a", encoding="utf-8", newline="\n") as df:
        df.write(f"\n{MARK} 巩固队列 +{n} 行（累计 {total} 行）——Sleep-time 范式：今晚抽取原料，攒批蒸馏。\n")
        if drift_rep:
            df.write(f"[人格漂移] drift={drift_rep['drift_rate']:.0%} "
                     f"未过探针={','.join(drift_rep['failed_probes']) or '无'}\n")
        else:
            df.write("[人格漂移] 检查未执行（生成器不可用）\n")
    print(f"巩固完成：抽取 {n} 行入队列（累计 {total}）")
    if drift_rep:
        print(f"人格漂移: drift={drift_rep['drift_rate']:.0%} 判定={drift_rep['verdict']}")
        if drift_rep["drift_rate"] > DRIFT_THRESHOLD:
            _write_drift_alert(d, drift_rep)
            print("  → 已推主动消息告警（人格卡回写检查）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
