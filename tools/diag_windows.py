"""Check why nine_sorairo.exe showed wins=[] when launched via Popen."""
import ctypes, ctypes.wintypes as wt, os, subprocess, time

user32 = ctypes.windll.user32
EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

def all_windows():
    res = []
    def cb(hwnd, lparam):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        ln = user32.GetWindowTextLengthW(hwnd)
        if ln > 0:
            buf = ctypes.create_unicode_buffer(ln + 1)
            user32.GetWindowTextW(hwnd, buf, ln + 1)
            vis = bool(user32.IsWindowVisible(hwnd))
            if vis or "nine" in buf.value.lower() or "sorairo" in buf.value.lower() or "steam" in buf.value.lower() or "patch" in buf.value.lower():
                cls = ctypes.create_unicode_buffer(128)
                user32.GetClassNameW(hwnd, cls, 128)
                res.append((pid.value, cls.value, vis, buf.value))
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return res

game_dir = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
# Record existing window titles
before = set(all_windows())
p = subprocess.Popen([os.path.join(game_dir, "nine_sorairo.exe")], cwd=game_dir)
try:
    for s in range(30):
        time.sleep(1)
        tl = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq nine_sorairo.exe", "/V", "/FO", "CSV", "/NH"], text=True, errors="replace").strip()
        now = set(all_windows())
        new_w = sorted(now - before)
        if new_w or s in (0, 5, 10, 15, 20, 25, 29):
            print(f"[{s+1}s] tasklist={tl!r} new_wins={new_w}")
        if any("9-nine" in w[3] or "sorairo" in w[3] or "そらいろ" in w[3] or "Episode" in w[3] for w in new_w):
            print("FOUND GAME WINDOW!")
            break
finally:
    subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
