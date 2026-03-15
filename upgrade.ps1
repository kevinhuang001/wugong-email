param (
    [switch]$yes
)

# --- Configuration ---
$InstallDir = Join-Path $Home ".wugong"
$RepoUrl = "https://github.com/kevinhuang001/wugong-email.git"
$ScriptDir = if ($MyInvocation.MyCommand.Path) { Split-Path $MyInvocation.MyCommand.Path -Parent } else { (Get-Location).Path }

if (-not $yes) {
    Write-Host "🔄 Checking for upgrades for Wugong Email..." -ForegroundColor Blue
}

# 1. Check if running from a git repository or needs to be cloned
$UpgradeNeeded = $false
$NewVersion = ""
if (-not (Test-Path (Join-Path $ScriptDir ".git"))) {
    Write-Host "ℹ️  Using GitHub as source." -ForegroundColor Yellow
    
    # Check local version
    $LocalVersion = ""
    $VersionFile = Join-Path $InstallDir ".version"
    if (Test-Path $VersionFile) {
        $LocalVersion = (Get-Content $VersionFile).Trim()
    }

    # Get remote head version
    $RemoteVersion = (Invoke-RestMethod -Uri "https://raw.githubusercontent.com/kevinhuang001/wugong-email/main/.version").Trim()
    
    if ($LocalVersion -eq $RemoteVersion -and $LocalVersion -ne "") {
        Write-Host "✅ Wugong Email is already up to date (v$LocalVersion)." -ForegroundColor Green
        exit 0
    }

    $TempDir = Join-Path $env:TEMP ([System.IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $TempDir | Out-Null
    
    # Hide git output
    git clone --depth 1 $RepoUrl $TempDir 2>$null | Out-Null
    if (-not $?) {
        Write-Host "❌ Error: Failed to clone repository." -ForegroundColor Red
        exit 1
    }
    
    $SourceDir = $TempDir
    $UpgradeNeeded = $true
    $NewVersion = $RemoteVersion
} else {
    Write-Host "📡 Fetching remote changes..." -ForegroundColor Blue
    Set-Location $ScriptDir
    # Hide git output
    git fetch origin 2>$null | Out-Null
    
    $LocalVersion = (Get-Content (Join-Path $ScriptDir ".version") 2>$null).Trim()
    $RemoteVersion = (git show origin/main:.version | Out-String).Trim()
    
    if ($LocalVersion -eq $RemoteVersion -and $LocalVersion -ne "") {
        Write-Host "✅ Wugong Email is already up to date (v$LocalVersion)." -ForegroundColor Green
        exit 0
    }
    $SourceDir = $ScriptDir
    $UpgradeNeeded = $true
    $NewVersion = $RemoteVersion
}

# 2. Ask for confirmation
if ($UpgradeNeeded -and -not $yes) {
    Write-Host "🔔 A new version of Wugong Email is available! (v$LocalVersion -> v$RemoteVersion)" -ForegroundColor Yellow
    
    # 2a. Show changelog between versions
    $ChangelogPath = Join-Path $SourceDir "CHANGELOG.md"
    if (Test-Path $ChangelogPath) {
        Write-Host "📄 What's new:" -ForegroundColor Blue
        Write-Host "----------------------------------------" -ForegroundColor Blue
        $Lines = Get-Content $ChangelogPath
        $Found = $false
        $Count = 0
        foreach ($Line in $Lines) {
            if ($Line -match "^## \[") {
                if ($LocalVersion -ne "" -and $Line -match "\[$([regex]::Escape($LocalVersion))\]") {
                    break
                }
                if ($LocalVersion -eq "" -and $Count -ge 1) {
                    break
                }
                $Count++
                $Found = $true
            }
            if ($Found) {
                Write-Host $Line
            }
        }
        Write-Host "----------------------------------------" -ForegroundColor Blue
    }

    $Confirm = Read-Host "Do you want to upgrade to the latest version? (y/N)"
    if ($Confirm -notmatch '^[Yy]$') {
        Write-Host "❌ Upgrade cancelled." -ForegroundColor Blue
        if ($TempDir) { Remove-Item -Recurse -Force $TempDir }
        exit 0
    }
}

# 3. Perform Upgrade
if ($TempDir) {
    Write-Host "🚀 Using files from cloned repository..." -ForegroundColor Blue
} else {
    Write-Host "🚀 Pulling latest changes..." -ForegroundColor Blue
    git pull origin main
}

# 4. Upgrade Installation
if (Test-Path $InstallDir) {
    Write-Host "📦 Upgrading files..." -ForegroundColor Blue
    
    # Custom sync logic: copy ALL files and directories except hidden/venv/pycache/db and the upgrade script itself
    $ItemsToSync = Get-ChildItem -Path $SourceDir | Where-Object { 
        $_.Name -ne "upgrade.ps1" -and 
        $_.Name -notmatch "^\." -and # No hidden files/dirs
        $_.Name -ne "venv" -and 
        $_.Name -ne "__pycache__" -and
        $_.Name -ne "config.toml" -and # Don't overwrite local config
        $_.Extension -ne ".db" # Don't overwrite local cache
    }
    # Manually remove old core files to simulate --delete
    $OldFiles = Join-Path $InstallDir "read_config.py"
    if (Test-Path $OldFiles) { Remove-Item $OldFiles -Force }
    
    foreach ($Item in $ItemsToSync) {
        $Dest = Join-Path $InstallDir $Item.Name
        # Ensure overwrite by forcing Copy-Item and removing the destination first if it's a directory
        if (Test-Path $Dest) {
            Remove-Item $Dest -Recurse -Force
        }
        if ($Item.PSIsContainer) {
            Copy-Item -Path $Item.FullName -Destination $Dest -Recurse -Force
        } else {
            Copy-Item -Path $Item.FullName -Destination $Dest -Force
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
    
    # Finally, update the upgrade script itself
    # Use Remove-Item + Copy-Item to avoid script file corruption during self-upgrade
    $DestUpgradeScript = Join-Path $InstallDir "upgrade.ps1"
    if (Test-Path $DestUpgradeScript) { Remove-Item $DestUpgradeScript -Force }
    Copy-Item -Path (Join-Path $SourceDir "upgrade.ps1") -Destination $DestUpgradeScript -Force
    
    # Save the current version if we cloned it
    if ($NewVersion -ne "") {
        $NewVersion | Out-File -FilePath (Join-Path $InstallDir ".version") -Encoding utf8
    }
    
    Write-Host "✅ Upgrade completed." -ForegroundColor Green
} else {
    Write-Host "ℹ️  Installation directory not found, upgrade only applied to source." -ForegroundColor Yellow
}

# 5. Cleanup
if ($TempDir) { Remove-Item -Recurse -Force $TempDir }

Write-Host "`n🎉 Wugong Email has been upgraded successfully!" -ForegroundColor Green
