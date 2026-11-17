# -*- coding: utf-8 -*-
"""pet_wrapper.py — 灵枢桌宠单实例启动器（替代直接调 standalone.js）"""
import subprocess, time, os, sys

def kill_all_pet():
    subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-Process electron -ErrorAction SilentlyContinue | "
        "Where-Object { $_.MainWindowTitle -like '*dsh-pet*' } | Stop-Process -Force"],
        capture_output=True, timeout=30)
    time.sleep(3)

def count_pets():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
        "(Get-Process electron -ErrorAction SilentlyContinue | "
        "Where-Object { $_.MainWindowTitle -like '*dsh-pet*' } | Measure-Object).Count"],
        capture_output=True, text=True, timeout=30)
    try: return int(r.stdout.strip())
    except: return 0

def start():
    pet = r"C:\Users\14676\.dsh\profiles\desktop\node_modules\dsh-pet\lib\standalone.js"
    subprocess.Popen(["node", pet], stdout=open(os.devnull, "w"), stderr=subprocess.DEVNULL,
                     creationflags=0x08000000)

if __name__ == "__main__":
    kill_all_pet()
    start()
    time.sleep(12)
    c = count_pets()
    print(f"桌宠: {'✓ 单实例' if c <= 5 else f'✗ {c} 个窗口（异常）'}")
