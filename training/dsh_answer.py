# -*- coding: utf-8 -*-
"""dsh_answer.py — 检索增强 + 生成后校验答题器（2026-10-25 ZCode）

背景（DSH 侧复验）：qwen-dsh-v1 裸答 = 格式对齐但内容错（编号错位/训练集内幻觉）。
根因：知识靠权重"背"，小数据背不住。
组合拳：
  ① 检索注入 v2（评估轮升级）：mem-search FTS 全库（daily/gaps/深海/研究层），
     不再只扫 53 条手法——N13 闸门 4/5 诚实拒绝的根因是检索面太窄
  ② 模型生成：qwen-dsh-v1（风格已对齐）只负责组织语言
  ③ 生成后校验：输出中的编号回查台账核对，不符即标 [编号存疑]
用法：python dsh_answer.py "问题"
"""
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

SKILL = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\pending-skills\ledger-lessons\SKILL.md")
DB = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\.search-index.db")
MODEL = "modelscope.cn/Qwen/Qwen2.5-7B-Instruct-GGUF:latest"
ADAPTER = "C:/Users/14676/.zcode/workspace/default/ai-skills/training/out/qwen-dsh-v5-lora"
USE_ADAPTER = True  # qwen-dsh-v5 风格层（2026-11-14 曾切 v7：评测证据 F8→F6 在案，但 detached 部署连续两次挂死于加载~85%处，回滚 v5 已知良好态；v7 待查明挂因后重试——见 切换判定-v5vs7-20261114.md）


def load_methods() -> list:
    """解析 SKILL.md 手法：[(编号, 全文)]"""
    text = SKILL.read_text(encoding="utf-8").split("## 出师自测")[0]
    out = []
    for m in re.finditer(r"^(\d+)\. \*\*(.+?)\*\*[：:]?(.*)$", text, re.M):
        out.append((m.group(1), f"{m.group(2)}。{m.group(3)}".strip()))
    return out


# 检索配置（2026-10-25 千次随机搜索定稿：Bergstra&Bengio 2012；20 题金标 18/20 持平基线
# 但 k=4 上下文减半——护栏滚动：N13 端到端不退才保留此配置）
RETRIEVE_CFG = {"k": 4, "daily": 1.34, "gaps": 0.67, "deepsea": 1.37, "skill": 1.35}


def retrieve(query: str, k: int = None) -> list:
    k = k or RETRIEVE_CFG["k"]
    """检索 v2.1（评估轮修正）：中文连续串滑窗切块是垃圾块（"会话日志损坏是/怎么修好的"
    永不命中）——改为 ASCII 词整取 + 中文 2 字滑窗，命中数按唯一词计。"""
    import sqlite3
    conn = sqlite3.connect(str(DB))
    terms = set()
    for run in re.findall(r"[A-Za-z0-9_.-]+|[\u4e00-\u9fff]+", query):
        if re.match(r"^[A-Za-z0-9_.-]+$", run):
            if len(run) >= 2:
                terms.add(run)
        else:  # 中文串 → 3 字滑窗（trigram 索引最短 3 字，2 字永不命中——首跑教训）
            terms.update(run[i:i + 3] for i in range(len(run) - 2))
    hits = {}
    for t in terms:
        try:
            rows = conn.execute("SELECT path, content FROM docs WHERE docs MATCH ?", (f'"{t}"',)).fetchall()
        except sqlite3.OperationalError:
            continue
        for path, content in rows:
            pos = content.lower().find(t.lower())
            if pos < 0:
                continue
            excerpt = content[max(0, pos - 60):pos + 150].replace("\n", " ").strip()
            if path not in hits:
                hits[path] = [0, ""]
            hits[path][0] += 1
            if len(hits[path][1]) < 200:
                hits[path][1] = (hits[path][1] + " … " + excerpt)[:420]
    conn.close()
    # 来源类型加权（2026-10-25 治元内容污染）：gaps.json 的 evidence 会原文转述"错误答案"
    # （如 N13 描述 ICU 混淆），词频压过 daily 里的正解记录——模型忠实复述批评文而非正解。
    # 权重：daily/深海正本（事实记录）0 + 1.0 奖励；gaps.json 降权 0.5；其余 1.0。
    def src_weight(path: str) -> float:
        p = path.replace("\\", "/").lower()
        if "/daily/" in p or "时间线" in p or "日记" in p:
            return RETRIEVE_CFG["daily"]
        if "gaps.json" in p:
            return RETRIEVE_CFG["gaps"]
        if "灵魂蓝图" in p or "记忆锚点" in p or "每日.txt" in p:
            return RETRIEVE_CFG["deepsea"]
        if "skill.md" in p:
            return RETRIEVE_CFG["skill"]
        return 1.0
    scored = sorted(hits.items(), key=lambda kv: (-kv[1][0] * src_weight(kv[0])))[:k]
    return [(score, path.replace("\\", "/").split("/")[-1], excerpt) for path, (score, excerpt) in scored]


_model_cache = None

def _load_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel
    tok = AutoTokenizer.from_pretrained("D:/AI训练基座/qwen25-7b-instruct-hf")
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    m = AutoModelForCausalLM.from_pretrained("D:/AI训练基座/qwen25-7b-instruct-hf", quantization_config=bnb, device_map="auto")
    m = PeftModel.from_pretrained(m, ADAPTER)
    m.eval()
    _model_cache = (tok, m)
    return _model_cache


V5_SERVER = "http://127.0.0.1:9622/answer"

def generate_via_server(prompt: str, timeout: float = 60.0):
    """9622 常驻服务优先（2026-11-14 接线——补上 dsh_v5_server 文档声明却一直缺失的回退链）。
    服务端的 im_start 模板与 generate() 逐字一致，传入完整 RAG prompt 即等价；
    任何失败（未启动/加载中 503/超时）→ 返回 None 走原进程内路径——fail-open，不引入新故障面。"""
    try:
        req = urllib.request.Request(
            V5_SERVER, data=json.dumps({"q": prompt}).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")).get("answer")
    except Exception:  # noqa: BLE001 — 增强层失败回退原路径
        return None

def generate(prompt: str) -> str:
    import torch
    tok, model = _load_model()
    msg = "<|im_start|>user" + chr(10) + prompt + "<|im_end|>" + chr(10) + "<|im_start|>assistant" + chr(10)
    inputs = tok(msg, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=220, do_sample=False)
    return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

def verify_refs(answer: str) -> str:
    """生成后校验 v2（DSH 侧口试题二行动项）：编号存在性 + 编号-内容匹配——
    "编号存在 ≠ 编号正确"。撒谎的是没拦住它的那道闸。"""
    methods_list = load_methods()
    methods = {num: full for num, full in methods_list}

    def check(m):
        num = m.group(1)
        if num not in methods:
            return m.group(0) + "[编号不存在]"
        context = answer[max(0, m.start() - 20):m.start()]
        # 全子串集合（贪婪滑窗会跨词边界）——2~4 字全部子串
        ctx_terms = {context[i:i + L]
                     for L in (2, 3, 4)
                     for i in range(max(0, len(context) - L + 1))
                     if re.match(r"^[\u4e00-\u9fff\w]+$", context[i:i + L])}
        if not ctx_terms:
            return m.group(0)
        if any(t in methods[num] for t in ctx_terms):
            return m.group(0)
        best_m, best_score = None, 0
        for mn, full in methods_list:
            s = sum(1 for t in ctx_terms if t in full)
            if s > best_score:
                best_m, best_score = mn, s
        if best_m and best_m != num and best_score >= 2:
            return m.group(0) + f"[编号存疑:应为#{best_m}]"
        return m.group(0) + "[编号存疑:语境不匹配]"

    return re.sub(r"[#＃](\d{1,2})", check, answer)


def answer(question: str, session=None) -> str:
    """红线闸最外层（2026-11-17 DSH 裁决：生成层对红线 0/6 不可靠——危机回答一律走闸）。
    T1 → 模板直出（完全不调生成）；T2 → 生成后校验热线，缺即替换；闸缺失/异常 → 原路径 fail-open。

    session=None 为默认——行为与历史完全一致；传入 redline_session.SessionGuard
    即启用 L2 会话守卫（2026-11-23 Crescendo 防线）：单轮良性但跨轮拼装成 T1 → 模板直出。
    （会话 T2 升级留待双声镜接入——T2 路径涉及声部语气，不在本函数裁决。）
    """
    def _gen():
        hits = retrieve(question, k=8)
        if not hits:
            return "（检索无相关内容——此题不在知识库覆盖内，不硬答。）"
        ctx = "\n".join(f"[来源:{name}] {excerpt[:300]}" for _, name, excerpt in hits)
        prompt = (f"你是知识助手。只依据下面给定的检索片段回答；片段里有的才说，没有的不编。"
                  f"引用时注明来源文件名。简洁回答（3 句内）。\n\n检索片段：\n{ctx}\n\n问题：{question}")
        raw = generate_via_server(prompt)
        if raw is None:
            raw = generate(prompt)  # 服务不可用→原进程内路径（50s 冷加载，行为与历史一致）
        return verify_refs(raw)

    try:
        sys.path.insert(0, r"C:\Users\14676\Documents\Codex")
        from redline_gate import guard
    except ImportError:
        guard = None
    if session is not None:
        try:
            sess = session.check(question)
        except Exception:  # noqa: BLE001 — 会话守卫崩→退单轮,绝不影响答题主路
            sess = None
        if sess and sess["tier"] == "T1":
            from redline_gate import TEMPLATE
            return TEMPLATE  # 会话拼装升级: 模板直出,不调生成(与单轮 T1 同纪律)
    if guard is not None:
        out = guard(question, generate=_gen, channel="dsh_answer")
        return out["text"]
    return _gen()


def main() -> int:
    # csqaq GBK 教训 #3 同款：GBK 控制台打 ✗/emoji 直接崩——强制 UTF-8 输出
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — 老版本 python 无 reconfigure 时忽略
            pass
    q = " ".join(sys.argv[1:]) or "数字不许硬编码的正确做法是什么？"
    print(f"Q: {q}")
    print(f"A: {answer(q)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
