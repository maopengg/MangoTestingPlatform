$ErrorActionPreference = "Stop"

$actuatorRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $actuatorRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "未找到执行器虚拟环境：$python"
}

Push-Location $actuatorRoot
try {
    & $python desktop_main.py --build
}
finally {
    Pop-Location
}
