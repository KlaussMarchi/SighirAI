#include <windows.h>
#include <stdio.h>
#include <string.h>

#define TITLE "Sighir Tester AI"
#define AGENT "agy"

static int fail(const char *msg){
    printf("\n  %s\n\n  Pressione ENTER para sair...", msg);
    getchar();
    return 1;
}

static int run(const char *cmd, int wait){
    char buf[512];
    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    DWORD code = 0;
    strncpy(buf, cmd, sizeof(buf) - 1); buf[sizeof(buf) - 1] = 0;
    if(!CreateProcessA(NULL, buf, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi))
        return -1;
    if(!wait){
        CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
        return 0;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    return (int)code;
}

int main(void){
    char dir[MAX_PATH];
    char *sep;
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleTitleA(TITLE);
    GetModuleFileNameA(NULL, dir, MAX_PATH);
    sep = strrchr(dir, '\\');
    if(sep) *sep = 0;
    if(!SetCurrentDirectoryA(dir))
        return fail("Nao foi possivel entrar na pasta do projeto.");
    if(GetFileAttributesA("GEMINI.md") == INVALID_FILE_ATTRIBUTES)
        return fail("Este executavel precisa ficar DENTRO da pasta SighirTesterAI.");
    if(run("cmd.exe /c where " AGENT " >nul 2>nul", 1) != 0)
        return fail("O agente '" AGENT "' nao foi encontrado no PATH.\n  Instale o Agy e abra este programa novamente.");
    printf("\n  %s\n  %s\n\n", TITLE, dir);
    if(run("cmd.exe /c " AGENT, 1) < 0)
        return fail("Falha ao iniciar o " AGENT ".");
    return 0;
}
