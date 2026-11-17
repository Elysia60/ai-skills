# -*- coding: utf-8 -*-
"""pet_launcher.py — 灵枢桌宠单实例启动器（2026-10-26 ZCode）
先杀所有旧 dsh-pet electron → 启动一个新实例 → 验证只有一个。
注册为计划任务替代直接调 standalone.js（根治多窗口叠加）。
"""
import subprocess
import time
import sys

PET_JS = r"C:\Users\14676\.dsh\profiles\desktop\node_modules\dsh-pet\lib\standalone.js"


def kill_all_pet():
    """杀所有 dsh-pet 相关 electron（通过窗口标题精确匹配）"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process electron -ErrorAction SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -like '*dsh-pet*' } | "
         "Stop-Process -Force"],
        capture_output=True, timeout=30
    )
    # 同时杀残留子进程（无窗口但路径含 dsh-pet 的）
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process electron -ErrorAction SilentlyContinue | "
         "Where-Object { $_.Path -and $_.Path -like '*dsh-pet*' } | "
         "Stop-Process -Force"],
        capture_output=True, timeout=30
    )
    time.sleep(3)


def count_windows():
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process electron -ErrorAction SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle -like '*dsh-pet*' } | "
         "Measure-Object).Count"],
        capture_output=True, text=True, timeout=30
    )
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


def start_one():
    subprocess.Popen(
        ["node", PET_JS],
        stdout=open(os.devnull, "w"),
        stderr=subprocess.DEVNULL,
        creationflags=0x08000000
    )


if __name__ == "__main__":
    import os
    kill_all_pet()
    time.sleep(2)
    start_one()
    time.sleep(10)
    count = count_windows()
    print(f"桌宠窗口: {count}（{'✓ 单实例正常' if count == 1 else '✗ 异常'}）")
    sys.exit(0 if count == 1 else 1)
