# Filename: finish_deadly_setup.ps1
# Usage: .\finish_deadly_setup.ps1
# Description: This connects to the existing DeadlyLinux distro and forces a fresh install of Mambaforge and the Python environment.

Write-Host "💎 DIAMOND SMASHING MACHINE: Finishing the Python Setup 💎" -ForegroundColor Cyan

$DistroName = "DeadlyLinux"
$User = "seanf"

# 1. Check if Distro exists
if (-not (wsl --list --quiet | Select-String $DistroName)) {
    Write-Error "The distro $DistroName was not found. Please run the main installer first."
    exit
}

Write-Host "--- 1. Downloading and Installing Mambaforge (Inside WSL) ---" -ForegroundColor Yellow
# We construct a bash command to download the installer directly to /tmp/ and run it
$InstallMambaCmd = @'
set -e
echo "Downloading Mambaforge..."
wget -qO /tmp/Mambaforge.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh"
echo "Installing Mambaforge..."
bash /tmp/Mambaforge.sh -b -p $HOME/mambaforge
rm /tmp/Mambaforge.sh
echo "Mambaforge Installed."
'@

# Execute the install command
wsl -d $DistroName -u $User -- bash -lc $InstallMambaCmd

Write-Host "--- 2. initializing Shell & Creating Environment ---" -ForegroundColor Yellow
# We need to init conda, then create the env. 
$SetupEnvCmd = @'
set -e
source $HOME/mambaforge/bin/activate
$HOME/mambaforge/bin/conda init bash || true
echo "Creating deadlygraphics environment..."
$HOME/mambaforge/bin/mamba create -n deadlygraphics python=3.11 -y
'@

wsl -d $DistroName -u $User -- bash -lc $SetupEnvCmd

Write-Host "--- 3. Installing Requirements ---" -ForegroundColor Yellow
$ReqPath = "/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/requirements.txt"
$LocalReqPath = "$HOME/deadlygraphics/requirements.txt"

$InstallReqsCmd = @'
set -e
source $HOME/mambaforge/bin/activate
$HOME/mambaforge/bin/mamba activate deadlygraphics
if [ -f "$HOME/deadlygraphics/requirements.txt" ]; then
  pip install -r "$HOME/deadlygraphics/requirements.txt"
else
  pip install -r "/mnt/c/Users/seanf/Documents/GitHub/DeadlyLinux/requirements.txt"
fi
'@

wsl -d $DistroName -u $User -- bash -lc $InstallReqsCmd

Write-Host "--- 💎 SMASH COMPLETE 💎 ---" -ForegroundColor Green
Write-Host "To enter your environment:"
Write-Host "wsl -d DeadlyLinux"
Write-Host "Then: mamba activate deadlygraphics"
