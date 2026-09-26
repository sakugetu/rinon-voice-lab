param([string]$RuntimeRoot, [switch]$Register, [switch]$Check)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
if (-not $RuntimeRoot) {
    $configPath = Join-Path $appRoot 'cx.local.json'
    if (-not (Test-Path -LiteralPath $configPath)) {
        throw 'CX runtime is not registered. See docs/CX_SETUP.md.'
    }
    $RuntimeRoot = (Get-Content -LiteralPath $configPath -Encoding UTF8 | ConvertFrom-Json).runtimeRoot
}
$pythonPath = Join-Path $RuntimeRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw "Missing Python: $pythonPath" }
$launchArgs = @('-X', 'utf8', '-B', (Join-Path $PSScriptRoot 'launch_cx.py'), '--runtime-root', $RuntimeRoot)
if ($Register) { $launchArgs += '--register' }
if ($Check) { $launchArgs += '--check' }
& $pythonPath @launchArgs
exit $LASTEXITCODE
