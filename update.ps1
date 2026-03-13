# --- Configuration ---
$InstallDir = Join-Path $Home ".wugong"
$RepoUrl = "https://github.com/kevinhuang001/wugong-email.git"
$ScriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent

Write-Host "🔄 Checking for updates for Wugong Email..." -ForegroundColor Blue

# 1. Check if running from a git repository or needs to be cloned
$UpdateNeeded = $false
if (-not (Test-Path (Join-Path $ScriptDir ".git"))) {
    Write-Host "ℹ️  Not running from a git repository. Using GitHub as source." -ForegroundColor Yellow
    $TempDir = Join-Path $env:TEMP ([System.IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $TempDir | Out-Null
    git clone --depth 1 $RepoUrl $TempDir
    $SourceDir = $TempDir
    $UpdateNeeded = $true
} else {
    Write-Host "📡 Fetching remote changes..." -ForegroundColor Blue
    Set-Location $ScriptDir
    git fetch origin
    
    $Local = git rev-parse @
    $Remote = git rev-parse @{u}
    
    if ($Local -eq $Remote) {
        Write-Host "✅ Wugong Email is already up to date." -ForegroundColor Green
        exit 0
    }
    $SourceDir = $ScriptDir
    $UpdateNeeded = $true
}

# 2. Ask for confirmation
if ($UpdateNeeded) {
    Write-Host "🔔 A new version of Wugong Email is available!" -ForegroundColor Yellow
    $Confirm = Read-Host "Do you want to update to the latest version? (y/N)"
    if ($Confirm -notmatch '^[Yy]$') {
        Write-Host "❌ Update cancelled." -ForegroundColor Blue
        if ($TempDir) { Remove-Item -Recurse -Force $TempDir }
        exit 0
    }
}

# 3. Perform Update
if ($TempDir) {
    Write-Host "🚀 Using files from cloned repository..." -ForegroundColor Blue
} else {
    Write-Host "🚀 Pulling latest changes..." -ForegroundColor Blue
    git pull origin main
}

# 4. Update Installation
if (Test-Path $InstallDir) {
    Write-Host "📦 Updating files..." -ForegroundColor Blue
    
    # Custom sync logic: copy files individually
    $FilesToSync = Get-ChildItem -Path $SourceDir -Include *.py, *.ps1, *.sh, requirements.txt, README.md, .gitignore -File
    foreach ($File in $FilesToSync) {
        if ($File.Name -ne "update.ps1") {
            Copy-Item -Path $File.FullName -Destination (Join-Path $InstallDir $File.Name) -Force
        }
    }

    # Update dependencies
    Set-Location $InstallDir
    if (Test-Path ".venv") {
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            & .\.venv\Scripts\python.exe -m uv pip install -r requirements.txt | Out-Null
        } else {
            & .\.venv\Scripts\python.exe -m pip install -r requirements.txt | Out-Null
        }
    }
    
    # Finally, update the update script itself
    Copy-Item -Path (Join-Path $SourceDir "update.ps1") -Destination (Join-Path $InstallDir "update.ps1") -Force
    
    Write-Host "✅ Update completed." -ForegroundColor Green
} else {
    Write-Host "ℹ️  Installation directory not found, update only applied to source." -ForegroundColor Yellow
}

# 5. Cleanup
if ($TempDir) { Remove-Item -Recurse -Force $TempDir }

Write-Host "`n🎉 Wugong Email has been updated successfully!" -ForegroundColor Green
Write-Host "--------------------------------------------------"
