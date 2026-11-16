import ctypes
from ctypes import wintypes
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumChildWindows = user32.EnumChildWindows
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetClassNameW = user32.GetClassNameW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def get_text(hwnd):
    n = GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 2)
    GetWindowTextW(hwnd, buf, n + 2)
    return buf.value


def get_cls(hwnd):
    buf = ctypes.create_unicode_buffer(128)
    GetClassNameW(hwnd, buf, 128)
    return buf.value


def get_nine_pids():
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name='nine_sorairo.exe'\" | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, text=True
    )
    return res.stdout.strip()


def enum_windows_for_pids(pids):
    found = []
    def cb(hwnd, lparam):
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            vis = bool(IsWindowVisible(hwnd))
            cls = get_cls(hwnd)
            txt = get_text(hwnd)
            children = []
            def ccb(chwnd, lp):
                children.append((get_cls(chwnd), get_text(chwnd)))
                return True
            EnumChildWindows(hwnd, WNDENUMPROC(ccb), 0)
            found.append((pid.value, vis, cls, txt, children))
        return True
    EnumWindows(WNDENUMPROC(cb), 0)
    return found


def get_current_pids():
    res = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq nine_sorairo.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, errors="replace"
    )
    pids = set()
    for line in res.stdout.splitlines():
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) >= 2 and parts[1].isdigit():
            pids.add(int(parts[1]))
    return pids


def kill_game():
    subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
    for _ in range(10):
        if not get_current_pids():
            break
        time.sleep(0.3)


def wait_and_observe(label, marker_paths, max_sec=24):
    print(f"\n=== Launching {label} ===")
    subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
    last_info = ""
    saw_game_window = False
    for s in range(1, max_sec + 1):
        time.sleep(1)
        pids = get_current_pids()
        wins = enum_windows_for_pids(pids) if pids else []
        hits = [mp for mp in marker_paths if os.path.exists(mp)]
        info = f"pids={sorted(pids)} wins={[(p, v, c, t, ch) for p, v, c, t, ch in wins if t or ch]} hits={hits}"
        if info != last_info:
            print(f"  [{s:2d}s] {info}")
            last_info = info
        for p, v, c, t, ch in wins:
            flat = t + " " + " ".join(ct for _, ct in ch)
            if "PROBE" in flat:
                print(f"  >>> DETECTED PROBE IN WINDOW @ {s}s!")
                return True
            if v and "9-nine-" in t:
                saw_game_window = True
        if hits:
            print(f"  >>> DETECTED MARKER FILE @ {s}s!")
            return True
        if saw_game_window and s >= 8:
            # Main window already appeared and no probe hit
            pass
    print(f"  [{label}] Finished {max_sec}s; final procs: {get_nine_pids()}")
    return False


def main():
    kill_game()
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw_app, _ = xp3.read_entry(data_xp3, de["AppConfig.tjs"])
    app_orig = xp3.decode_txtobf(raw_app)

    patch_dst = os.path.join(GAME_DIR, "patch.xp3")
    data_dir = os.path.join(GAME_DIR, "data")
    marker1 = os.path.join(GAME_DIR, "_probe_hit.txt")
    marker2 = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo\_probe_hit.txt")

    def clean():
        kill_game()
        for f in (patch_dst, marker1, marker2):
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)

    clean()
    try:
        # Case 1: patch.xp3 with AppConfig.tjs (plain UTF-16LE)
        probe_tjs = (
            '["HIT_XP3"].save(System.exePath + "_probe_hit.txt");\r\n'
            '["HIT_XP3"].save(System.dataPath + "_probe_hit.txt");\r\n'
            'System.inform("PROBE_XP3_HIT");\r\n'
        ) + app_orig
        src_xp3 = r"d:\code\translate\build\probe_patch.xp3"
        xp3.pack_xp3(src_xp3, {"AppConfig.tjs": probe_tjs.encode("utf-16")}, compress=False)
        shutil.copy2(src_xp3, patch_dst)
        hit1 = wait_and_observe("Case1_patch_xp3_AppConfig", [marker1, marker2], max_sec=22)
        clean()
        if hit1:
            return

        # Case 2: loose data/AppConfig.tjs
        probe_loose = (
            '["HIT_LOOSE"].save(System.exePath + "_probe_hit.txt");\r\n'
            '["HIT_LOOSE"].save(System.dataPath + "_probe_hit.txt");\r\n'
            'System.inform("PROBE_LOOSE_HIT");\r\n'
        ) + app_orig
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "AppConfig.tjs"), "wb") as f:
            f.write(probe_loose.encode("utf-16"))
        hit2 = wait_and_observe("Case2_loose_data_AppConfig", [marker1, marker2], max_sec=22)
        clean()
        if hit2:
            return

        # Case 3: patch.xp3 with startup.tjs AND system/Initialize.tjs
        st_raw, _ = xp3.read_entry(data_xp3, de["startup.tjs"])
        xp3.pack_xp3(src_xp3, {
            "AppConfig.tjs": probe_tjs.encode("utf-16"),
            "AfterInit.tjs": 'System.inform("PROBE_AFTERINIT");\r\n'.encode("utf-16"),
            "sysscn/AfterInit.tjs": 'System.inform("PROBE_SYSSCN_AFTERINIT");\r\n'.encode("utf-16"),
            "main/ConfigEx.tjs": 'System.inform("PROBE_CONFIGEX");\r\n'.encode("utf-16"),
        }, compress=True)
        shutil.copy2(src_xp3, patch_dst)
        wait_and_observe("Case3_patch_xp3_multi", [marker1, marker2], max_sec=22)
    finally:
        clean()


if __name__ == "__main__":
    main()
