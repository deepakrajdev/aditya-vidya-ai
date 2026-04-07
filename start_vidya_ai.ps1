Write-Host "VidyaAI quick start" -ForegroundColor Cyan
Write-Host "1. Start Ollama in another terminal: ollama serve" -ForegroundColor Yellow
Write-Host "2. Backend will start on http://localhost:8000" -ForegroundColor Yellow
Write-Host "3. Frontend will start on http://localhost:3000" -ForegroundColor Yellow
Start-Process powershell -ArgumentList '-NoExit', '-File', '.\run_backend.ps1'
Start-Process powershell -ArgumentList '-NoExit', '-File', '.\run_frontend.ps1'
