$gameDir = 'C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2'
$dst = Join-Path $gameDir 'patch.xp3'
Copy-Item 'd:\code\translate\build\test_patch.xp3' $dst -Force
try {
    Start-Process -FilePath (Join-Path $gameDir 'nine_sorairo.exe') -WorkingDirectory $gameDir
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        $procs = Get-Process -Name 'nine_sorairo' -ErrorAction SilentlyContinue
        if ($procs) {
            $titles = @($procs | Where-Object { $_.MainWindowTitle } | Select-Object -ExpandProperty MainWindowTitle)
            if ($titles.Count -gt 0) {
                Write-Output ("WINDOW_TITLE: " + ($titles -join ' | '))
                if ($titles -match 'PATCH_TEST') { break }
            }
        }
    }
    Start-Sleep -Seconds 2
    Get-Process -Name 'nine_sorairo' -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, MainWindowTitle | Format-Table -AutoSize
} finally {
    Get-Process -Name 'nine_sorairo' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    Remove-Item $dst -Force -ErrorAction SilentlyContinue
}
