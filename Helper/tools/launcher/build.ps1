<#
  Gera <Pasta>_Claude.exe e <Pasta>_Gemini.exe a partir do launcher.cs.
  Nao precisa instalar nada: usa o compilador C# que ja vem com o .NET Framework do Windows.

    powershell -ExecutionPolicy Bypass -File tools\launcher\build.ps1

  Os dois .exe sao o mesmo binario; o nome do arquivo decide qual agente abre.
#>
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)
$name = Split-Path -Leaf $root

$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) { $csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
if (-not (Test-Path $csc)) { throw 'csc.exe do .NET Framework 4 nao encontrado' }

$claude = Join-Path $root "$($name)_Claude.exe"
$gemini = Join-Path $root "$($name)_Gemini.exe"
$icon = Join-Path $here 'icon.ico'
$src = Join-Path $here 'launcher.cs'

$cscArgs = @('/nologo', '/target:exe', '/platform:anycpu', '/optimize+', "/out:$claude", $src)
if (Test-Path $icon) { $cscArgs = @("/win32icon:$icon") + $cscArgs }
& $csc @cscArgs
if ($LASTEXITCODE -ne 0) { throw "csc falhou ($LASTEXITCODE)" }
Copy-Item $claude $gemini -Force
Get-Item $claude, $gemini | Format-Table Name, Length, LastWriteTime -AutoSize
