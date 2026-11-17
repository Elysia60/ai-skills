# -*- coding: utf-8 -*-
"""selector_heal.py — 选择器腐坏自愈（2026-11-18 · REA 蒸馏自 D4Vinci/Scrapling）

来源（REA 逆向，源码级）:
  - 指纹结构: Scrapling/core/utils/_utils.py:84 element_to_dict
  - 相似度评分: Scrapling/parser.py:823 __calculate_similarity_score（7 项平均）
  - 重定位: Scrapling/parser.py:525 relocate（全页扫描+最高分+阈值）
  - 自愈闭环: Scrapling/parser.py:681-687 xpath空结果→retrieve→relocate→save更新

蒸馏原则（REA 标准打法）:
  - 提取算法思想，零依赖重实现——Scrapling 用 lxml，这里用 stdlib html.parser + difflib
  - 指纹/评分/重定位语义与原版 1:1 对应，便于对照验证

自愈闭环（对齐原版 adaptive 语义）:
  1. 选择器命中 → save(元素) 存指纹
  2. 选择器空结果 → retrieve 指纹 → relocate 全页打分 → 找回
  3. 找回成功 → save 更新指纹（网站改版后自动跟上）

用法:
    from selector_heal import parse_html, HealSelector
    tree = parse_html(html)
    heal = HealSelector("price", threshold=40)      # 用 class 定位，自带自愈
    el = heal.find(tree, lambda t: t.find_class("price"))
    # 网站改版后 class 失效 → find 返回 None 但内部已按指纹重定位并更新

设计要点（逆向所得）:
  - 相似度 = 7 项检查的平均值，不是加权和——单项缺失只摊薄不炸分
  - class/id/href/src 单独算——整站 class 重构时 path/parent 项仍能撑分
  - 属性分母用 max(len(原), len(候))——属性少的候选不吃便宜，属性多的受惩罚
  - siblings/path 用序列 SequenceMatcher——顺序敏感，乱序自动降分
"""
from __future__ import annotations

import difflib
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional

# ── 迷你 DOM（stdlib html.parser，零依赖替代 lxml） ──

_VOID = {"br", "img", "input", "hr", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}


class Element:
    """轻量元素节点：tag/attrs/text(直下文本)/children/parent。"""

    __slots__ = ("tag", "attrs", "text", "children", "parent")

    def __init__(self, tag: str, attrs: Dict[str, str], parent: Optional["Element"] = None):
        self.tag = tag
        self.attrs = attrs
        self.text: Optional[str] = None
        self.children: List[Element] = []
        self.parent = parent

    # 派生视图（指纹用）
    @property
    def path(self) -> tuple:
        node, out = self, []
        while node is not None:
            out.insert(0, node.tag)
            node = node.parent
        return tuple(out)

    @property
    def siblings(self) -> tuple:
        if self.parent is None:
            return ()
        return tuple(c.tag for c in self.parent.children if c is not self)

    def iter_all(self):
        """深度优先遍历全部元素（relocate 全页扫描用）。"""
        for c in self.children:
            yield c
            yield from c.iter_all()

    def find_class(self, name: str) -> Optional[Element]:
        for el in self.iter_all():
            if name in el.attrs.get("class", "").split():
                return el
        return None

    def find_tag(self, tag: str) -> Optional[Element]:
        for el in self.iter_all():
            if el.tag == tag:
                return el
        return None


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("[root]", {})
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        el = Element(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(el)
        if tag not in _VOID:
            self.cur = el

    def handle_startendtag(self, tag, attrs):
        el = Element(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(el)

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent  # 容错：未闭合标签向上找
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        if self.cur.text is None and data.strip():
            self.cur.text = data.strip()  # lxml 语义：直下文本（首段）
        elif self.cur.text is not None and not self.cur.children:
            pass  # 已有直下文本，不再累加（评分用首段足够）


def parse_html(html: str) -> Element:
    b = _TreeBuilder()
    b.feed(html)
    return b.root


# ── 指纹（对应原版 element_to_dict，9 字段） ──

_KEY_ATTRS = ("class", "id", "href", "src")


def fingerprint(el: Element) -> Dict[str, Any]:
    # 对齐原版 __clean_attributes(_utils.py:78)：丢弃空值属性
    attrs = {k: v.strip() for k, v in el.attrs.items() if v and v.strip()}
    fp: Dict[str, Any] = {
        "tag": el.tag,
        "attributes": attrs,
        "text": el.text,
        "path": el.path,
    }
    p = el.parent
    if p is not None:
        p_attrs = {k: v.strip() for k, v in p.attrs.items() if v and v.strip()}
        fp.update({
            "parent_name": p.tag,
            "parent_attribs": p_attrs,
            "parent_text": p.text,
            "siblings": el.siblings,
            "children": tuple(c.tag for c in el.children),
        })
    return fp


# ── 相似度评分（对应原版 __calculate_similarity_score，7 项平均） ──

def _dict_diff(d1: Dict, d2: Dict) -> float:
    """原版语义：键序列 0.5 + 值序列 0.5。"""
    sm = difflib.SequenceMatcher
    return (sm(None, tuple(d1.keys()), tuple(d2.keys())).ratio() * 0.5
            + sm(None, tuple(d1.values()), tuple(d2.values())).ratio() * 0.5)


def similarity_score(orig: Dict[str, Any], cand: Element) -> float:
    """0-100 百分比。7 项检查平均：单项缺失摊薄总分而非归零。"""
    score, checks = 0.0, 0
    sm = difflib.SequenceMatcher

    score += 1 if orig["tag"] == cand.tag else 0
    checks += 1

    if orig["text"]:
        score += sm(None, orig["text"], cand.text or "").ratio()
        checks += 1

    score += _dict_diff(orig["attributes"], dict(cand.attrs))
    checks += 1

    for attrib in _KEY_ATTRS:  # class/id/href/src 单独算——结构性变化的容错
        if orig["attributes"].get(attrib):
            score += sm(None, orig["attributes"][attrib], cand.attrs.get(attrib, "")).ratio()
            checks += 1

    score += sm(None, orig["path"], cand.path).ratio()
    checks += 1

    if orig.get("parent_name"):
        if cand.parent is not None:
            score += sm(None, orig["parent_name"], cand.parent.tag).ratio()
            checks += 1
            score += _dict_diff(orig["parent_attribs"], dict(cand.parent.attrs))
            checks += 1
            if orig.get("parent_text"):
                score += sm(None, orig["parent_text"], cand.parent.text or "").ratio()
                checks += 1

    if orig.get("siblings"):
        score += sm(None, orig["siblings"], cand.siblings).ratio()
        checks += 1

    return round((score / checks) * 100, 2)


# ── 重定位（对应原版 relocate：全页扫描→最高分桶→阈值） ──

def relocate(tree: Element, fp: Dict[str, Any], threshold: float = 40.0) -> List[Element]:
    """网站改版后按指纹找回元素。返回最高分元素列表（可能有并列），低于阈值返回空。"""
    score_table: Dict[float, List[Element]] = {}
    for node in tree.iter_all():
        s = similarity_score(fp, node)
        score_table.setdefault(s, []).append(node)
    if not score_table:
        return []
    top = max(score_table.keys())
    if top < threshold:
        return []
    return score_table[top]


# ── 自愈选择器（对应原版 adaptive 闭环） ──

class HealSelector:
    """选择器 + 指纹自愈。选择器失效时按指纹重定位并自动更新指纹。

    用法（csqaq/astock 采集器防改版断链）:
        heal = HealSelector("price", threshold=40)
        el = heal.find(tree, lambda t: t.find_class("price"))
    """

    def __init__(self, identifier: str, threshold: float = 40.0):
        self.identifier = identifier
        self.threshold = threshold
        self._fp: Optional[Dict[str, Any]] = None
        self.last_mode: str = ""  # "selector" | "relocated" | "miss"（审计用）

    def find(self, tree: Element, selector_fn: Callable[[Element], Optional[Element]]) -> Optional[Element]:
        el = selector_fn(tree)
        if el is not None:
            self._fp = fingerprint(el)  # auto_save：命中即更新指纹
            self.last_mode = "selector"
            return el
        if self._fp is not None:  # 空结果 → retrieve → relocate
            hits = relocate(tree, self._fp, self.threshold)
            if hits:
                self._fp = fingerprint(hits[0])  # 找回成功 → 更新指纹（自愈闭环）
                self.last_mode = "relocated"
                return hits[0]
        self.last_mode = "miss"
        return None
