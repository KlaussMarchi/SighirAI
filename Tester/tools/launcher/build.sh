#!/usr/bin/env bash
set -e

src=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$src/../.." && pwd)
out="$root/SighirTesterAI.exe"

if ! command -v x86_64-w64-mingw32-windres >/dev/null; then
    echo ">> instalando toolchain mingw-w64 (pede senha do sudo)"
    sudo apt-get install -y gcc-mingw-w64-x86-64-win32 binutils-mingw-w64-x86-64
fi

cc=x86_64-w64-mingw32-gcc-win32
command -v $cc >/dev/null || cc=x86_64-w64-mingw32-gcc

cp "$root/icon.ico" "$src/icon.ico"
x86_64-w64-mingw32-windres "$src/index.rc" -O coff -o "$src/index.res" -I "$src"
$cc "$src/index.c" "$src/index.res" -o "$out" -mconsole -Os -s
rm -f "$src/index.res" "$src/icon.ico"

echo ">> gerado:"; ls -lh "$out"
