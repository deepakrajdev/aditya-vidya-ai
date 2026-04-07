# VidyaAI Backend Startup Script
Write-Host "🚀 Starting VidyaAI Backend..." -ForegroundColor Cyan
Write-Host ""

# Run the backend
& "./.venv/Scripts/python.exe" -m uvicorn backend.main:app --port 8000

