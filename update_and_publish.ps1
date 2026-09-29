$ErrorActionPreference = 'Stop'

Set-Location -LiteralPath $PSScriptRoot

$pythonPath = 'C:\Users\nemam\AppData\Local\Python\bin\python3.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python nebyl nalezen: $pythonPath"
}

& $pythonPath .\scraper.py
if ($LASTEXITCODE -ne 0) {
    throw "Scraper skoncil s kodem $LASTEXITCODE"
}

$concertsStatus = git status --porcelain -- .\concerts.json
if (-not $concertsStatus) {
    Write-Output 'Zadne zmeny v concerts.json, push neni potreba.'
    exit 0
}

git add -- .\concerts.json
if ($LASTEXITCODE -ne 0) {
    throw 'Git add selhal.'
}

git commit -m 'daily concert update'
if ($LASTEXITCODE -ne 0) {
    throw 'Git commit selhal.'
}

git push origin main
if ($LASTEXITCODE -ne 0) {
    throw 'Git push selhal.'
}

Write-Output 'Koncerty byly aktualizovany a odeslany na GitHub.'