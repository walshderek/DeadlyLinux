# Filename: Install_deadlylinux.ps1
# MASTER INSTALLER V3: Discrete steps to avoid WSL Relay errors.

$DistroName = "DeadlyLinux"
$TargetTarPath = "$env:TEMP\ubuntu.tar"
$TargetInstallPath = "$env:LOCALAPPDATA\WSL\$DistroName"
$LinuxUsername = "seanf" 

Write-Host "--- 1. Shutting down WSL service for clean deployment ---"
wsl --shutdown

# --- 2. Check and Unregister Old Distro ---
Write-Host "--- 2. Checking for existing $DistroName distro..."
if ((wsl --list --quiet) -contains $DistroName) {
    Write-Host "Found existing $DistroName. Unregistering..."
    wsl --unregister $DistroName
}

# --- 3. Download and Import Base Image ---
Write-Host "--- 3. Downloading base Ubuntu image... ---"
$DownloadUri = "https://cloud-images.ubuntu.com/wsl/releases/22.04/current/ubuntu-jammy-wsl-amd64-wsl.rootfs.tar.gz"
Invoke-WebRequest -Uri $DownloadUri -OutFile $TargetTarPath -ErrorAction Stop

Write-Host "--- Importing distro as $DistroName... ---"
New-Item -ItemType Directory -Force -Path $TargetInstallPath | Out-Null
wsl --import $DistroName $TargetInstallPath $TargetTarPath --version 2
Remove-Item $TargetTarPath -Force

# --- 4. Configure User (Step-by-Step to avoid WSL Error) ---
Write-Host "--- 4. Creating user account: $LinuxUsername ---"

# Step A: Create the user
wsl -d $DistroName -u root useradd -m -s /bin/bash $LinuxUsername

# Step B: Add user to Sudoers (Passwordless)
# We use standard input (echo | wsl) to avoid quoting issues
"echo '$LinuxUsername ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/seanf" | wsl -d $DistroName -u root bash

# Step C: Set default user in wsl.conf
"echo -e '[user]\ndefault=$LinuxUsername' > /etc/wsl.conf" | wsl -d $DistroName -u root bash

# Step D: Restart Distro to apply User Change
wsl --terminate $DistroName

# --- 5. Run the Main Linux Installer ---
Write-Host "--- 5. Launching install_deadlylinux.sh ---"
Write-Host "NOTE: If asked for a password, it is for the Windows mount, usually not needed."

# We run this command AS the new user. 
# It navigates to the C: drive repo and runs the script.
wsl -d $DistroName -u $LinuxUsername --cd "/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux" --exec bash install_deadlylinux.sh

Write-Host "--- Deployment Complete! ---"
Write-Host "To enter your new environment: wsl -d DeadlyLinux"