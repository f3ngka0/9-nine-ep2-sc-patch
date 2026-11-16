import subprocess
import time
import os

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")

subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
time.sleep(0.5)
subprocess.Popen([EXE_PATH], cwd=GAME_DIR)

for s in range(1, 16):
    time.sleep(1)
    t = subprocess.run(["tasklist", "/FI", "IMAGENAME eq nine_sorairo.exe", "/V", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="replace").stdout.strip()
    ps = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process nine_sorairo -ErrorAction SilentlyContinue | Select-Object Id,SessionId,MainWindowHandle,MainWindowTitle | ConvertTo-Json -Compress"], capture_output=True, text=True).stdout.strip()
    if t or ps:
        print(f"[{s:2d}s] tasklist={t} | ps={ps}")
    if "9-nine-" in t:
        break

subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
