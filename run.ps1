# run.ps1

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Starting AMD Hackathon Project" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Start the Python backend using Start-Process
Write-Host "[1/2] Starting Python backend..." -ForegroundColor Yellow
$backendProcess = Start-Process -FilePath "python" -ArgumentList "app.py" -PassThru -NoNewWindow

# Move to the frontend directory
Set-Location -Path "frontend"

# Start the Vite React frontend
Write-Host "[2/2] Starting Vite React frontend..." -ForegroundColor Yellow
$frontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev" -PassThru -NoNewWindow

Write-Host "=========================================" -ForegroundColor Green
Write-Host "Both frontend and backend are starting up!" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop both servers." -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green

try {
    # Keep the script running to block the console until manually exited
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "`nStopping all processes..." -ForegroundColor Red
    
    if ($backendProcess -and !$backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    if ($frontendProcess -and !$frontendProcess.HasExited) {
        Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "Processes stopped." -ForegroundColor Red
    Set-Location -Path ".."
}
