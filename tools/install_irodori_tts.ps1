[CmdletBinding()]
param(
  [string] $IrodoriRoot = $(if ($env:IRODORI_ROOT) { $env:IRODORI_ROOT } else { Join-Path (Split-Path -Parent $PSScriptRoot) '..\Irodori-TTS' }),
  [string] $RepositoryUrl = 'https://github.com/Aratako/Irodori-TTS.git',
  [ValidateSet('cu128', 'cpu', 'rocm', 'xpu')]
  [string] $TorchExtra = $(if ($env:IRODORI_TORCH_EXTRA) { $env:IRODORI_TORCH_EXTRA } else { 'cu128' }),
  [switch] $SkipUvInstall
)

$ErrorActionPreference = 'Stop'

function Require-Command {
  param(
    [Parameter(Mandatory = $true)]
    [string] $Name,
    [Parameter(Mandatory = $true)]
    [string] $Hint
  )
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name was not found. $Hint"
  }
}

function Ensure-Uv {
  if (Get-Command uv -ErrorAction SilentlyContinue) {
    return
  }
  if ($SkipUvInstall) {
    throw 'uv was not found. Install uv first, or rerun without -SkipUvInstall.'
  }
  Write-Host 'uv was not found. Installing uv with the official installer...'
  powershell -ExecutionPolicy Bypass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
  $uvBin = Join-Path $env:USERPROFILE '.local\bin'
  if (Test-Path $uvBin) {
    $env:PATH = "$uvBin;$env:PATH"
  }
  Require-Command 'uv' 'Install uv from https://docs.astral.sh/uv/ and rerun this script.'
}

$root = [System.IO.Path]::GetFullPath($IrodoriRoot)
$parent = Split-Path -Parent $root

Require-Command 'git' 'Install Git for Windows and rerun this script.'
Ensure-Uv

if (-not (Test-Path $root)) {
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  Write-Host "Cloning Irodori-TTS into $root"
  git clone $RepositoryUrl $root
} elseif (-not (Test-Path (Join-Path $root 'pyproject.toml'))) {
  throw "IrodoriRoot exists but does not look like Irodori-TTS: $root"
}

Push-Location $root
try {
  Write-Host "Installing Irodori-TTS dependencies with uv extra '$TorchExtra'..."
  uv sync --extra $TorchExtra

  $python = Join-Path $root '.venv\Scripts\python.exe'
  if (-not (Test-Path $python)) {
    throw "Expected virtual environment was not created: $python"
  }

  @'
import importlib.util
missing = [name for name in ("gradio", "torch", "soundfile") if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit("Missing modules after install: " + ", ".join(missing))
print("Irodori-TTS environment looks ready.")
'@ | & $python -
}
finally {
  Pop-Location
}

Write-Host "Irodori-TTS install complete: $root"
