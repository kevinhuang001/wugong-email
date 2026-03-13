# --- Configuration ---
$InstallDir = Join-Path $Home ".wugong"
$ConfigDir = Join-Path $Home ".config\wugong"

Write-Host "🗑️  Starting Wugong Email Uninstallation..." -ForegroundColor Blue

# 1. Ask for confirmation
$Confirm = Read-Host "Are you sure you want to uninstall Wugong Email? (y/N)"
if ($Confirm -notmatch '^[Yy]$') {
    Write-Host "❌ Uninstallation cancelled." -ForegroundColor Blue
    exit 0
}

# 2. Ask about configuration
$KeepConfig = Read-Host "Do you want to keep your configuration and email accounts? (Y/n)"
if ($KeepConfig -match '^[Nn]$') {
    if (Test-Path $ConfigDir) {
        Write-Host "📁 Removing configuration directory..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $ConfigDir
    }
}

# 3. Remove installation directory
if (Test-Path $InstallDir) {
    Write-Host "📦 Removing installation directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $InstallDir
}

Write-Host "`n🎉 Wugong Email has been uninstalled successfully!" -ForegroundColor Green
Write-Host "--------------------------------------------------"
Write-Host "Note: Please manually remove '$InstallDir' from your PATH if you added it."
Write-Host "--------------------------------------------------"
