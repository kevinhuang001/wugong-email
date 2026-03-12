# Wugong Email Windows Installation Script
# This script installs Wugong Email on Windows using PowerShell.

$ErrorActionPreference = "Stop"

# --- Configuration ---
$InstallDir = Join-Path $HOME ".wugong"
$ConfigDir = Join-Path $HOME ".config\wugong"
$ConfigFile = Join-Path $ConfigDir "config.toml"
$RepoUrl = "https://github.com/kevinhuang001/wugong-email.git"
$MinPythonVersion = [version]"3.8"

Write-Host "🚀 Starting Wugong Email Installation for Windows..." -ForegroundColor Cyan

# 1. Check Python
try {
    $pythonVersionStr = python --version 2>&1
    if ($pythonVersionStr -match "Python (\d+\.\d+\.\d+)") {
        $currentVersion = [version]$matches[1]
        if ($currentVersion -lt $MinPythonVersion) {
            Write-Error "❌ Error: Python version $currentVersion is too low. Required: >= $MinPythonVersion"
        }
        Write-Host "✅ Python $currentVersion found." -ForegroundColor Green
    } else {
        throw "Could not parse python version"
    }
} catch {
    Write-Error "❌ Error: python is not installed or not in PATH. Please install Python >= $MinPythonVersion first."
}

# 2. Source Directory
$SourceDir = $PSScriptRoot
if (-not (Test-Path (Join-Path $SourceDir "cli.py")) -or -not (Test-Path (Join-Path $SourceDir "wizard.py"))) {
    Write-Host "📡 Source files not found locally. Cloning from GitHub..." -ForegroundColor Blue
    $TempDir = Join-Path $env:TEMP "wugong_install_$(Get-Random)"
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    git clone --depth 1 $RepoUrl $TempDir
    $SourceDir = $TempDir
} else {
    Write-Host "📂 Local source files found. Using current directory." -ForegroundColor Blue
}

# 3. Create Directories
Write-Host "📁 Creating directories..." -ForegroundColor Blue
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null

# 4. Copy Files
Write-Host "📦 Copying source files..." -ForegroundColor Blue
Copy-Item "$SourceDir\*.py" "$InstallDir\" -Force
Copy-Item "$SourceDir\requirements.txt" "$InstallDir\" -Force

# 5. Setup Virtual Environment
Set-Location $InstallDir
Write-Host "🐍 Setting up virtual environment..." -ForegroundColor Blue
python -m venv .venv
& "$InstallDir\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$InstallDir\.venv\Scripts\pip.exe" install -r requirements.txt

# 6. Create Wrapper Batch Script
Write-Host "🔨 Creating executable wrapper..." -ForegroundColor Blue
$BatchContent = @"
@echo off
set "WUGONG_CONFIG=$ConfigFile"
"$InstallDir\.venv\Scripts\python.exe" "$InstallDir\cli.py" %*
"@
$BatchContent | Out-File -FilePath (Join-Path $InstallDir "wugong.bat") -Encoding ascii

# 7. Cleanup
if ($TempDir) {
    Remove-Item $TempDir -Recurse -Force
}

# 8. Final Instructions
Write-Host "`n🎉 Installation Complete!" -ForegroundColor Green
Write-Host "--------------------------------------------------"
Write-Host "Location: $InstallDir"
Write-Host "Config:   $ConfigFile"
Write-Host "`nTo use 'wugong' from anywhere, add this directory to your PATH:" -ForegroundColor Blue
Write-Host "$InstallDir" -ForegroundColor Green
Write-Host "--------------------------------------------------"
Write-Host "Run 'wugong configure' to setup your accounts."
Write-Host "Run 'wugong list' to view your emails."
