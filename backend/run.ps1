$env:UV_CACHE_DIR = Join-Path $PSScriptRoot '.uv-cache'
$env:UV_LINK_MODE = 'copy'
Push-Location $PSScriptRoot
try { uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8000 }
finally { Pop-Location }
