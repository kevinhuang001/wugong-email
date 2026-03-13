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

# 2. Remove Scheduled Tasks (Task Scheduler)
Write-Host "⏰ Removing scheduled sync tasks from Task Scheduler..." -ForegroundColor Blue
try {
    $taskName = "WugongSync"
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "✅ Task Scheduler task '$taskName' removed." -ForegroundColor Green
    } else {
        Write-Host "ℹ️  No Wugong scheduled task found." -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Failed to remove scheduled task. You may need to remove it manually from Task Scheduler." -ForegroundColor Red
}

# 3. Ask about configuration
$RemoveConfig = Read-Host "Do you want to remove your configuration and email accounts? (y/N)"
if ($RemoveConfig -match '^[Yy]$') {
    if (Test-Path $ConfigDir) {
        Write-Host "📁 Removing configuration directory..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $ConfigDir
    }
}

# 4. Remove installation directory
if (Test-Path $InstallDir) {
    Write-Host "📦 Removing installation directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $InstallDir
}

Write-Host "`n🎉 Wugong Email has been uninstalled successfully!" -ForegroundColor Green
Write-Host "--------------------------------------------------"
Write-Host "Note: Please manually remove '$InstallDir' from your PATH if you added it."
Write-Host "--------------------------------------------------"
