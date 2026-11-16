"""Check window titles created by nine_sorairo.exe with test_patch.xp3."""

import ctypes
import ctypes.wintypes as wt
import os
import shutil
import subprocess
import time

user32 = ctypes.windll.user32
EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

def list_windows_for_pid(pids):
    res = []
    def cb(hwnd, lparam):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            ln = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(ln + 1)
            user32.GetWindowTextW(hwnd, buf, ln + 1)
            cls = ctypes.create_unicode_buffer(128)
            user32.GetClassNameW(hwnd, cls, 128)
            vis = bool(user32.IsWindowVisible(hwnd))
            rect = wt.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            res.append((hwnd, pid.value, cls.value, vis, (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top), buf.value))
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return res

def get_pids_by_name(name="nine_sorairo.exe"):
    out = subprocess.check_output(["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH"], text=True, errors="replace")
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].lower() == name.lower():
            try: pids.add(int(parts[1]))
            except ValueError: pass
    return pids

game_dir = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
patch_dst = os.path.join(game_dir, "patch.xp3")
shutil.copy2(r"d:\code\translate\build\test_patch.xp3", patch_dst)

try:
    proc = subprocess.Popen([os.path.join(game_dir, "nine_sorairo.exe")], cwd=game_dir)
    print("Started PID:", proc.pid)
    seen_titles = set()
    for sec in range(25):
        time.sleep(1)
        pids = get_pids_by_name("nine_sorairo.exe")
        wins = list_windows_for_pid(pids)
        for w in wins:
            sig = (w[1], w[2], w[3], w[4], w[5])
            if sig not in seen_titles:
                seen_titles.add(sig)
                print(f"[{sec+1}s] pid={w[1]} cls={w[2]!r} vis={w[3]} size={w[4][2]}x{w[4][3]} title={w[5]!r}")
        if any("PATCH_TEST" in w[5] for w in wins):
            print("SUCCESS! Observed PATCH_TEST in live window title!")
            break
        if any("エラー" in w[5] or "Error" in w[5] or "Warning" in w[5] for w in wins):
            print("ERROR DIALOG DETECTED:", wins)
            break
finally:
    subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    if os.path.exists(patch_dst):
        os.remove(patch_dst)
    print("Cleaned up patch.xp3 and process.")
