# -*- coding: utf-8 -*-
"""start_pet_once.py — 单实例锁启动器（2026-10-26）
原理：先杀所有旧 dsh-pet electron → 等 5s → 启动一个新实例。
避免 standalone.js 每次调用都 spawn 新窗口的问题。
"""
import subprocess, time, os, sys

def kill_old():
    """杀所有旧 dsh-pet electron"""
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-Process electron -ErrorAction SilentlyContinue | "
        "Where-Object { $_.MainWindowTitle -like '*dsh-pet*' } | "
        "Stop-Process -Force"],
        capture_output=True, timeout=30)
    time.sleep(3)

def start_one():
    """启动一个新实例"""
    pet_js = r"C:\Users\14676\.dsh\profiles\desktop\node_modules\dsh-pet\lib\standalone.js"
    subprocess.Popen(
        ["node", pet_js],
        stdout=open(os.devnull, "w"),
        stderr=subprocess.DEVNULL,
        creationflags=0x08000000  # CREATE_NO_WINDOW
    )

if __name__ == "__main__":
    kill_old()
    time.sleep(3)
    start_one()
    time.sleep(8)
    # 验证只有 1 个
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
        "(Get-Process electron -ErrorAction SilentlyContinue | "
        "Where-Object { $_.MainWindowTitle -like '*dsh-pet*' } | Measure-Object).Count"],
        capture_output=True, text=True, timeout=30)
    count = int(r.stdout.strip()) if r.stdout.strip().isdigit() else -1
    print(f"桌宠窗口数: {count}（{'✓ 单实例' if count == 1 else '✗ 异常'}）")
    sys.exit(0 if count == 1 else 1)
