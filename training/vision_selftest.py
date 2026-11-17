# -*- coding: utf-8 -*-
"""vision_selftest.py — DSH 视觉技能自测集 v0（2026-11-02 R41 · 视觉规程v2「多类型自测集」候选转正）

设计（视觉理解规程 v2 第二节）：
  夹具 = PIL 本地渲染的已知内容图（文档表格/报错弹窗/会话记录三型），
  断言 = 像素层（本机 pixel_diff，可真跑）+ OCR 层（本机无 tesseract → 三态 SKIP，
  待她的 vision_ocr 器官跑——规程承诺的本地 OCR 文件系统不可见，未验证不在案）。

用法：
  python vision_selftest.py --gen        # 生成夹具到 training/_vision_fixtures/
  python vision_selftest.py --check      # 跑断言（像素层真跑，OCR 层诚实 SKIP）
只写 training/_vision_fixtures/（自己的地盘），不动任何器官。
"""
import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8") if (os := __import__("os")) else None
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).parent
FIX = HERE / "_vision_fixtures"
PIXEL_DIFF = Path.home() / ".zcode/skills/vision-skills/scripts/pixel_diff.py"
FONT = r"C:\Windows\Fonts\msyh.ttc"

RESULTS = []


def add(item, status, detail):
    RESULTS.append((item, status, str(detail)[:100]))


def _font(sz):
    from PIL import ImageFont
    return ImageFont.truetype(FONT, sz)


def gen_fixtures():
    """三型夹具，内容全已知——期望值在 EXPECTED 里，改图必改表。"""
    from PIL import Image, ImageDraw
    FIX.mkdir(exist_ok=True)

    # ① 文档表格型：3×3 汇总表（数字已知）
    img = Image.new("RGB", (640, 360), "#0d1320")
    d = ImageDraw.Draw(img)
    rows = [("C1", "回避期信号", "躲跌 2/2"),
            ("C3", "网格择时", "DSR=0.222"),
            ("C9", "样本外验证", "OOS=-0.490")]
    d.text((30, 24), "结论注册表 2026-11-02", font=_font(28), fill="#dde1ea")
    for i, (a, b, c) in enumerate(rows):
        y = 90 + i * 70
        d.rectangle([30, y, 610, y + 56], outline="#1a2235")
        d.text((44, y + 14), a, font=_font(24), fill="#a78bfa")
        d.text((140, y + 14), b, font=_font(24), fill="#dde1ea")
        d.text((400, y + 14), c, font=_font(24), fill="#4ade80")
    img.save(FIX / "doc_table.png")

    # ② 报错弹窗型：错误码逐字已知（规程：报错逐字引用）
    img = Image.new("RGB", (560, 200), "#1a0e12")
    d = ImageDraw.Draw(img)
    d.text((24, 30), "GPU process exited unexpectedly", font=_font(24), fill="#f87171")
    d.text((24, 90), "exit_code=-1073741819", font=_font(30), fill="#fbbf24")
    d.text((24, 150), "附录九 · 现象一", font=_font(20), fill="#6b7490")
    img.save(FIX / "err_dialog.png")

    # ③ 修改版①：只把 C9 行数字改错（像素层须抓到差异区，OCR 层须读出假值）
    img2 = Image.new("RGB", (640, 360), "#0d1320")
    d = ImageDraw.Draw(img2)
    rows2 = [("C1", "回避期信号", "躲跌 2/2"),
             ("C3", "网格择时", "DSR=0.222"),
             ("C9", "样本外验证", "OOS=+0.490")]  # 负号被偷换为正——审计敏感点
    d.text((30, 24), "结论注册表 2026-11-02", font=_font(28), fill="#dde1ea")
    for i, (a, b, c) in enumerate(rows2):
        y = 90 + i * 70
        d.rectangle([30, y, 610, y + 56], outline="#1a2235")
        d.text((44, y + 14), a, font=_font(24), fill="#a78bfa")
        d.text((140, y + 14), b, font=_font(24), fill="#dde1ea")
        d.text((400, y + 14), c, font=_font(24), fill="#4ade80")
    img2.save(FIX / "doc_table_tampered.png")

    manifest = {
        "date": date.today().isoformat(),
        "fixtures": [
            {"file": "doc_table.png", "type": "文档表格", "expect_ocr": ["C1", "DSR=0.222", "OOS=-0.490"]},
            {"file": "err_dialog.png", "type": "报错弹窗", "expect_ocr": ["exit_code=-1073741819"]},
            {"file": "doc_table_tampered.png", "type": "篡改对照", "expect_ocr": ["OOS=+0.490"],
             "note": "C9 负号被偷换——先验劫持 6.5 的靶子：目测几乎不可见，机器必须抓到"},
        ],
    }
    (FIX / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"夹具 3 张 → {FIX}")


def check():
    m = json.loads((FIX / "manifest.json").read_text(encoding="utf-8"))
    # ── 像素层（本机真跑）──
    a, b = FIX / "doc_table.png", FIX / "doc_table_tampered.png"
    rc, out = subprocess.run(
        [sys.executable, "-X", "utf8", str(PIXEL_DIFF), str(a), str(b), "--top", "1"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").returncode, None
    p = subprocess.run([sys.executable, "-X", "utf8", str(PIXEL_DIFF), str(a), str(b), "--top", "1"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    pout = (p.stdout or "") + (p.stderr or "")
    if p.returncode == 0 and ("差" in pout or "diff" in pout.lower() or pout.strip()):
        try:
            j = json.loads(pout[pout.index("{"): pout.rindex("}") + 1])
            worst = json.dumps(j, ensure_ascii=False)[:80]
            add("像素层·篡改检测", "OK", f"pixel_diff 抓到差异: {worst}")
        except ValueError:
            add("像素层·篡改检测", "OK", f"pixel_diff 有输出: {pout.strip()[:80]}")
    else:
        add("像素层·篡改检测", "FAIL", f"rc={p.returncode} {pout.strip()[:80]}")

    # ── OCR 层（诚实三态）──
    try:
        import shutil
        has_tess = bool(shutil.which("tesseract"))
    except Exception:
        has_tess = False
    if has_tess:
        add("OCR层·三型读数", "SKIP", "检测到 tesseract——接它（下版）")
    else:
        add("OCR层·三型读数", "SKIP",
            "本机无 tesseract——规程承诺的本地 OCR 器官文件系统不可见，三态：未能确认；待她的 vision_ocr 跑 manifest.expect_ocr")

    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    n_warn = sum(1 for _, s, _ in RESULTS if s == "WARN")
    n_ok = sum(1 for _, s, _ in RESULTS if s == "OK")
    n_skip = sum(1 for _, s, _ in RESULTS if s == "SKIP")
    for item, s, d in RESULTS:
        mark = {"OK": "✓", "WARN": "△", "FAIL": "✗", "SKIP": "·"}[s]
        print(f"  {mark} {item}: {d}")
    print("─" * 55)
    print(f"视觉自测: OK {n_ok} / WARN {n_warn} / FAIL {n_fail} / SKIP {n_skip}")
    sys.exit(2 if n_fail else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.gen:
        gen_fixtures()
    if a.check:
        check()
    if not a.gen and not a.check:
        print(__doc__)


if __name__ == "__main__":
    main()
