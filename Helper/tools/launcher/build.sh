#!/usr/bin/env bash
# Gera <Pasta>_Claude.exe e <Pasta>_Gemini.exe no Linux (compilador C# do mono).
#   bash tools/launcher/build.sh
# No Windows use o build.ps1 (não precisa instalar nada).
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
name=$(basename "$root")

if ! command -v mcs >/dev/null 2>&1; then
    echo ">> instalando o compilador C# do mono (pede a senha do sudo)"
    sudo apt-get install -y mono-mcs
fi

icon=()
[ -f "$here/icon.ico" ] && icon=(-win32icon:"$here/icon.ico")
mcs -nologo -target:exe -optimize+ "${icon[@]}" -out:"$root/${name}_Claude.exe" "$here/launcher.cs"
cp "$root/${name}_Claude.exe" "$root/${name}_Gemini.exe"
ls -lh "$root/${name}_Claude.exe" "$root/${name}_Gemini.exe"
