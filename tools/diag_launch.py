"""Diagnostic: launch nine_sorairo.exe cleanly without patch.xp3 for 5s and print stdout/exitcode/pids/windows."""
import os, subprocess, time, ctypes, ctypes.wintypes as wt

user32 = ctypes.windll.user32
EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

def enum_all_pids(pids):
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
            res.append((hwnd, pid.value, cls.value, bool(user32.IsWindowVisible(hwnd)), buf.value))
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return res

game_dir = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
# Run without patch.xp3 first to see baseline behavior
p = subprocess.Popen([os.path.join(game_dir, "nine_sorairo.exe")], cwd=game_dir)
print("Launched baseline PID:", p.pid)
try:
    for s in range(22):
        time.sleep(1)
        rc = p.poll()
        tl = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq nine_sorairo.exe", "/FO", "CSV", "/NH"], text=True, errors="replace").strip()
        pids = set()
        for ln in tl.splitlines():
            cols = [c.strip('"') for c in ln.split('","')]
            if len(cols) >= 2 and cols[0].lower() == "nine_sorairo.exe":
                pids.add(int(parts := cols[1]))
        wins = enum_all_pids(pids)
        print(f"[{s+1}s] rc={rc} pids={pids} wins={wins}")
        if any(w[3] and w[4] for w in wins):
            break
finally:
    subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
