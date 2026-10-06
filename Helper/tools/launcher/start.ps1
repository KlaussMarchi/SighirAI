<#
  Sighir AI - inicializacao no Windows (mesmo arquivo em Tester/, Server/ e Helper/).

  Uso direto (sem o .exe):
    powershell -ExecutionPolicy Bypass -File tools\launcher\start.ps1 -Agent claude
    powershell -ExecutionPolicy Bypass -File tools\launcher\start.ps1 -Agent gemini [-DryRun] [-SemPrompt]

  -SoPython: so garante um Python 3.9+ (o .exe chama assim quando nao encontra Python).
  Todo o resto (dependencias, instalacao do agente, modelo, permissoes) e o tools\boot.py.
#>
param(
    [ValidateSet('claude', 'gemini', 'agy')][string]$Agent = 'claude',
    [switch]$SoPython,
    [switch]$DryRun,
    [switch]$SemPrompt
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root

function Test-Python([string]$exe) {
    if (-not $exe) { return $false }
    if ($exe -like '*WindowsApps*') { return $false }
    if (-not (Test-Path $exe)) { return $false }
    try {
        & $exe -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-Python {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        try { $real = & $launcher.Source -3 -c "import sys; print(sys.executable)" 2>$null | Select-Object -First 1 } catch { $real = $null }
        if ($real -and (Test-Python $real.Trim())) { return $real.Trim() }
    }
    foreach ($name in 'python', 'python3') {
        foreach ($cmd in @(Get-Command $name -All -ErrorAction SilentlyContinue)) {
            if (Test-Python $cmd.Source) { return $cmd.Source }
        }
    }
    foreach ($dir in @("$env:LOCALAPPDATA\Programs\Python", $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $dir -or -not (Test-Path $dir)) { continue }
        $found = Get-ChildItem -Path $dir -Filter 'Python3*' -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
        foreach ($f in $found) {
            $exe = Join-Path $f.FullName 'python.exe'
            if (Test-Python $exe) { return $exe }
        }
    }
    return $null
}

function Update-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user"
}

function Install-Python {
    Write-Host '[ .. ] Python 3.9+ nao encontrado - instalando o Python 3.12' -ForegroundColor Cyan
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        & $winget.Source install --id Python.Python.3.12 -e --scope user --silent --accept-package-agreements --accept-source-agreements
        Update-Path
        $py = Find-Python
        if ($py) { return $py }
    }
    Write-Host '[ .. ] baixando o instalador oficial em python.org' -ForegroundColor Cyan
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $suffix = if ([Environment]::Is64BitOperatingSystem) { '-amd64' } else { '' }
        $url = "https://www.python.org/ftp/python/3.12.10/python-3.12.10$suffix.exe"
        $file = Join-Path $env:TEMP 'python-3.12-sighir.exe'
        Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing
        Start-Process -FilePath $file -ArgumentList '/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_launcher=1', 'Include_test=0' -Wait
        Remove-Item $file -ErrorAction SilentlyContinue
    } catch {
        Write-Host "[ERRO] download/instalacao do Python falhou: $($_.Exception.Message)" -ForegroundColor Red
    }
    Update-Path
    return Find-Python
}

$py = Find-Python
if (-not $py) { $py = Install-Python }
if (-not $py) {
    Write-Host '[ERRO] Nao consegui instalar o Python. Instale o Python 3.12 (python.org, marque Add to PATH) e abra de novo.' -ForegroundColor Red
    exit 5
}
if ($SoPython) {
    Write-Host "[ OK ] Python: $py" -ForegroundColor Green
    exit 0
}

$bootArgs = @((Join-Path $Root 'tools\boot.py'), 'start', $Agent)
if ($DryRun) { $bootArgs += '--dry-run' }
if ($SemPrompt) { $bootArgs += '--sem-prompt' }
& $py @bootArgs
exit $LASTEXITCODE
