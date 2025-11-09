# run_on_windows.ps1
# Build a portable one-file EXE for MaximumSecurity, then (optionally) launch it
# via an interactive Scheduled Task so the window appears on the desktop session.

[CmdletBinding()]
param(
  [string] $ModUrl = "https://www.moddb.com/mods/maximum-security",
  [switch] $Launch
)

$ErrorActionPreference = "Stop"

# ---------------- Paths ----------------
$ROOT  = Join-Path $HOME "Home\Code\MaximumSecurity"
$BUILD = Join-Path $ROOT "build"
$SRC   = Join-Path $BUILD "src"
$IWADS = Join-Path $BUILD "iwads"
$VENV  = Join-Path $BUILD ".venv"

Write-Host "==> Root:  $ROOT"
Write-Host "==> Build: $BUILD"

# Ensure expected layout exists (Linux side already creates and rsyncs files)
New-Item -ItemType Directory -Force -Path $BUILD,$SRC,$IWADS | Out-Null

# ---------------- Python env ----------------
# Prefer 'python' (VS/pyenv installs) and fall back to 'py -3' if present.
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
  $pythonCmd = "py -3"
} else {
  throw "No suitable Python launcher found in PATH (need 'python' or 'py')."
}

if (-not (Test-Path $VENV)) {
  Write-Host "==> Creating virtualenv at $VENV"
  & $pythonCmd -m venv $VENV
}

$PY = Join-Path $VENV "Scripts\python.exe"
$PIP = Join-Path $VENV "Scripts\pip.exe"

Write-Host "==> Upgrading pip and installing build deps (requests, bs4, pyinstaller)…"
& $PIP install --upgrade pip | Out-Null
& $PIP install requests beautifulsoup4 pyinstaller | Out-Null

# ---------------- Build EXE ----------------
Push-Location $SRC
try {
  # We expect main.py and mod_launcher.py to be present in $SRC (pushed from Linux).
  $mainPath = Join-Path $SRC "main.py"
  if (-not (Test-Path $mainPath)) {
    throw "main.py not found in $SRC (make sure Linux side copied app_src/* to build/src)."
  }

  # Put final EXE next to $BUILD, keep PyInstaller temps in build\pyi_build, spec in build\src
  $distPath = $BUILD
  $workPath = Join-Path $BUILD "pyi_build"
  $specPath = $SRC

  Write-Host "==> Building MaximumSecurity.exe (one-file)…"
  & $PY -m PyInstaller `
      --noconsole `
      --onefile `
      --name MaximumSecurity `
      --distpath "$distPath" `
      --workpath "$workPath" `
      --specpath "$specPath" `
      "$mainPath"

  $exe = Join-Path $BUILD "MaximumSecurity.exe"
  if (-not (Test-Path $exe)) {
    throw "PyInstaller did not produce $exe (see $workPath for logs)."
  }
}
finally {
  Pop-Location
}

# ---------------- (Optional) Launch via Scheduled Task ----------------
if ($Launch.IsPresent) {
  Write-Host "==> Registering interactive scheduled task: \MaximumSecurity\Launch"

  $taskPath = "\MaximumSecurity\"
  $taskName = "Launch"

  # Action runs EXE in the build directory so relative iwads/bin paths work.
  $action    = New-ScheduledTaskAction -Execute $exe -WorkingDirectory $BUILD
  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
  $desc      = "Run Maximum Security portable build"

  # Idempotent: remove old if exists, then register fresh.
  $existing = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
  if ($existing) {
    Unregister-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Confirm:$false
  }

  Register-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Action $action -Principal $principal -Description $desc | Out-Null

  Write-Host "==> Launching now via scheduled task."
  Start-ScheduledTask -TaskPath $taskPath -TaskName $taskName

  Write-Host "==> Done. Switch to the PC display; GZDoom should launch via the scheduled task."
} else {
  Write-Host "==> Build complete. Skipping launch (no -Launch switch). EXE at: $exe"
}
