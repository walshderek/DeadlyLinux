# DeadlyLinux One-Click Deployment
# Bootstraps WSL, installs DeadlyLinux distro, runs install_deadlylinux.sh

param(
    [string]$DistroName = "DeadlyLinux_002",
    [string]$RepoPath = "$PSScriptRoot"
)

Write-Host "💎 DEADLY LINUX DEPLOYMENT 💎" -ForegroundColor Cyan
Write-Host "Distro: $DistroName"
Write-Host "Repo: $RepoPath"
Write-Host ""

# 1. Check if WSL is available
Write-Host "[1/5] Checking WSL..." -ForegroundColor Yellow
if (!(Get-Command wsl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: WSL not found. Run 'wsl --install' first." -ForegroundColor Red
    exit 1
}

# 2. Check if distro already exists
Write-Host "[2/5] Checking distro '$DistroName'..." -ForegroundColor Yellow
$existing = wsl -l -q | Where-Object { $_ -eq $DistroName }
if ($existing) {
    Write-Host "WARNING: Distro '$DistroName' already exists. Delete it first with: wsl --unregister $DistroName" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne 'y') { exit 0 }
} else {
    Write-Host "[3/5] Installing Ubuntu as '$DistroName'..." -ForegroundColor Yellow
    wsl --install -d Ubuntu --no-launch
    wsl --import $DistroName "$env:LOCALAPPDATA\WSL\$DistroName" "$env:LOCALAPPDATA\Packages\CanonicalGroupLimited.Ubuntu_*\LocalState\ext4.vhdx"
}

# 3. Create user and set as default
Write-Host "[4/5] Setting up user 'seanf'..." -ForegroundColor Yellow
wsl -d $DistroName -- bash -c "useradd -m -s /bin/bash seanf || true; echo 'seanf ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"
wsl -d $DistroName -- bash -c "echo '[user]' > /etc/wsl.conf; echo 'default=seanf' >> /etc/wsl.conf"

# 4. Run install script
Write-Host "[5/5] Running install_deadlylinux.sh..." -ForegroundColor Yellow
$installScript = Join-Path $RepoPath "install_deadlylinux.sh"
if (!(Test-Path $installScript)) {
    Write-Host "ERROR: install_deadlylinux.sh not found at $installScript" -ForegroundColor Red
    exit 1
}

# Convert Windows path to WSL path
$wslRepoPath = $RepoPath -replace '\\', '/' -replace 'C:', '/mnt/c'
wsl -d $DistroName -u seanf -- bash "$wslRepoPath/install_deadlylinux.sh"

Write-Host ""
Write-Host "✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. wsl -d $DistroName -u seanf"
Write-Host "  2. source ~/mambaforge/bin/activate deadlygraphics"
Write-Host "  3. ./run_audit.sh --apps"
