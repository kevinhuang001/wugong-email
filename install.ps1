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

# 2. Check for existing installation
if ((Test-Path $InstallDir) -and (Test-Path (Join-Path $InstallDir "main.py")) -and (Test-Path (Join-Path $InstallDir ".venv\Scripts\python.exe"))) {
    Write-Host "💡 Wugong Email is already installed at $InstallDir." -ForegroundColor Blue
    Write-Host "🔄 Switching to upgrade mode..." -ForegroundColor Blue
     # Run the existing installation's upgrade command
     & "$InstallDir\.venv\Scripts\python.exe" "$InstallDir\main.py" upgrade $args
     exit
 }

# 3. Source Directory Detection (Local vs Remote)
$SourceDir = $null
$TempDir = $null

if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "main.py")) -and (Test-Path (Join-Path $PSScriptRoot "cli\configure.py"))) {
    # Script is being executed as a local file, and we found source files next to it
    Write-Host "📂 Local source files found at $PSScriptRoot. Using local version." -ForegroundColor Blue
    $SourceDir = $PSScriptRoot
} elseif ((Test-Path "main.py") -and (Test-Path "cli\configure.py")) {
    # We are in the source directory already
    $SourceDir = (Get-Location).Path
    Write-Host "📂 Source files found in current directory. Using local version." -ForegroundColor Blue
} else {
    # Likely being piped or executed remotely (e.g., iwr ... | iex)
    Write-Host "📡 Remote execution detected or source files not found. Cloning from GitHub..." -ForegroundColor Blue
    $TempDir = Join-Path $env:TEMP "wugong_install_$(Get-Random)"
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    try {
        git clone --quiet --depth 1 $RepoUrl $TempDir
        $SourceDir = $TempDir
    } catch {
        Write-Error "❌ Error: Failed to clone repository. Make sure git is installed."
        exit 1
    }
}

# 4. Create Directories
Write-Host "📁 Creating directories..." -ForegroundColor Blue
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null

# 5. Copy Files
Write-Host "📦 Copying source files..." -ForegroundColor Blue
# Use recursive copy to ensure folders like 'mail' are included
# Exclude git/venv/pycache/db/config if they exist in source
$ItemsToCopy = Get-ChildItem -Path $SourceDir | Where-Object { 
    $_.Name -ne ".git" -and 
    $_.Name -ne ".venv" -and 
    $_.Name -ne "__pycache__" -and 
    $_.Extension -ne ".db" -and 
    $_.Name -ne "config.toml" 
}
foreach ($Item in $ItemsToCopy) {
    Copy-Item -Path $Item.FullName -Destination $InstallDir -Recurse -Force
}

# 6. Setup Virtual Environment
Set-Location $InstallDir
Write-Host "🐍 Setting up virtual environment..." -ForegroundColor Blue

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "✨ uv found! Using uv for faster installation..." -ForegroundColor Green
    & uv venv --quiet
    & uv pip install --quiet --python (Join-Path $InstallDir ".venv\Scripts\python.exe") -r requirements.txt
} else {
    Write-Error "❌ Error: uv not found. uv is required for installation."
    Write-Host "💡 Please install uv first: https://github.com/astral-sh/uv" -ForegroundColor Yellow
    exit 1
}

# 7. Setup Wrapper Scripts
Write-Host "🔨 Setting up executable wrapper..." -ForegroundColor Blue
# wugong.bat is already copied in Step 5

# 8. Cleanup
if ($TempDir) {
    Remove-Item $TempDir -Recurse -Force
}

# 9. Final Instructions
Write-Host "`n🎉 Installation Complete!" -ForegroundColor Green
Write-Host "--------------------------------------------------"
Write-Host "Location: $InstallDir"
Write-Host "Config:   $ConfigFile"
Write-Host "`nTo use 'wugong' from anywhere, add this directory to your PATH:" -ForegroundColor Blue
Write-Host "$InstallDir" -ForegroundColor Green
Write-Host "--------------------------------------------------"
Write-Host "Quick Start Guide:"
Write-Host "1. wugong init        - Setup master password & sync schedule"
Write-Host "2. wugong configure   - Modify sync interval or settings"
Write-Host "3. wugong account add - Setup your email accounts"
Write-Host "4. wugong account list- List all configured accounts"
Write-Host "5. wugong sync        - Manually sync emails"
Write-Host "6. wugong list        - View your emails (search with -k)"
Write-Host "7. wugong read -i <ID>- Read an email in terminal"
Write-Host "8. wugong send        - Send an email"
Write-Host "9. wugong delete -i <ID>- Delete an email"
Write-Host "10. wugong folder list- List all mailbox folders"
Write-Host "11. wugong upgrade    - Update to the latest version"
Write-Host "12. wugong uninstall  - Uninstall Wugong Email"
Write-Host "--------------------------------------------------"
