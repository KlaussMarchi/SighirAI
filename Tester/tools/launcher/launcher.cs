// Sighir AI - lancador .exe (o MESMO codigo em Tester/, Server/ e Helper/).
//
// O nome do arquivo decide o agente: <Pasta>_Claude.exe abre o Claude Code,
// <Pasta>_Gemini.exe abre o Antigravity CLI (agy). Todo o resto (dependencias,
// instalacao do agente, modelo, permissoes) fica em tools/boot.py.
//
// Build no Windows (sem instalar nada): powershell -File tools\launcher\build.ps1
// Build no Linux (mono):                bash tools/launcher/build.sh

using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

internal static class Launcher
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern uint GetLongPathName(string shortPath, StringBuilder longPath, uint size);

    // aberto por nome curto (HELPER~2.EXE) o nome nao diria "Gemini": resolve o nome longo antes de decidir
    private static string LongPath(string path)
    {
        try
        {
            var sb = new StringBuilder(1024);
            uint n = GetLongPathName(path, sb, (uint)sb.Capacity);
            return (n > 0 && n < sb.Capacity) ? sb.ToString() : path;
        }
        catch { return path; }
    }

    private static int Main(string[] args)
    {
        string exe = LongPath(Process.GetCurrentProcess().MainModule.FileName);
        string dir = Path.GetDirectoryName(exe);
        string name = Path.GetFileNameWithoutExtension(exe);
        string lower = name.ToLowerInvariant();
        string agent = (lower.Contains("gemini") || lower.Contains("agy")) ? "gemini" : "claude";
        string boot = Path.Combine(dir, Path.Combine("tools", "boot.py"));

        try { Console.Title = name.Replace('_', ' '); } catch { }

        // Ctrl+C e do agente (interrompe a resposta); este processo so espera
        Console.CancelKeyPress += delegate(object sender, ConsoleCancelEventArgs e) { e.Cancel = true; };

        if (!File.Exists(boot))
            return Fail("Nao encontrei tools\\boot.py ao lado deste executavel.\n" +
                        "  Ele precisa ficar dentro da pasta da IA (Tester, Server ou Helper).");

        string python = FindPython();
        if (python == null)
        {
            string script = Path.Combine(dir, Path.Combine("tools", Path.Combine("launcher", "start.ps1")));
            if (File.Exists(script))
            {
                Console.WriteLine("  Python 3.9+ nao encontrado. Vou instalar (pode levar alguns minutos)...");
                Run(PowerShell(), "-NoLogo -NoProfile -ExecutionPolicy Bypass -File " + Quote(script) + " -SoPython", dir);
                python = FindPython();
            }
        }
        if (python == null)
            return Fail("Nao consegui encontrar nem instalar o Python 3.9+.\n" +
                        "  Instale em https://www.python.org/downloads/ (marque 'Add to PATH') e abra de novo.");

        string extra = string.Join(" ", Array.ConvertAll(args, Quote));
        var info = new ProcessStartInfo(python, Quote(boot) + " start " + agent + (extra.Length > 0 ? " " + extra : ""));
        info.UseShellExecute = false;
        info.WorkingDirectory = dir;
        info.EnvironmentVariables["SIGHIR_LAUNCHER"] = "exe";
        info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

        try
        {
            using (Process p = Process.Start(info))
            {
                p.WaitForExit();
                return p.ExitCode;
            }
        }
        catch (Exception e)
        {
            return Fail("Falha ao iniciar o Python (" + python + "): " + e.Message);
        }
    }

    // procura um Python >= 3.9 de verdade (o "python.exe" da Microsoft Store em WindowsApps e so um atalho)
    private static string FindPython()
    {
        string sysdir = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        string launcher = Path.Combine(sysdir, "py.exe");
        if (File.Exists(launcher))
        {
            string real = Capture(launcher, "-3 -c \"import sys; print(sys.executable)\"");
            if (Valid(real)) return real;
        }

        string path = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (string folder in path.Split(Path.PathSeparator))
        {
            try
            {
                string candidate = Path.Combine(folder.Trim().Trim('"'), "python.exe");
                if (Valid(candidate)) return candidate;
            }
            catch { }
        }

        string[] roots = {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), Path.Combine("Programs", "Python")),
            Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
            Environment.GetEnvironmentVariable("ProgramFiles(x86)") ?? ""
        };
        foreach (string root in roots)
        {
            if (root.Length == 0 || !Directory.Exists(root)) continue;
            string[] dirs;
            try { dirs = Directory.GetDirectories(root, "Python3*"); } catch { continue; }
            Array.Sort(dirs);
            Array.Reverse(dirs);
            foreach (string d in dirs)
            {
                string candidate = Path.Combine(d, "python.exe");
                if (Valid(candidate)) return candidate;
            }
        }
        return null;
    }

    private static bool Valid(string python)
    {
        if (string.IsNullOrEmpty(python) || !File.Exists(python)) return false;
        if (python.IndexOf("WindowsApps", StringComparison.OrdinalIgnoreCase) >= 0) return false;
        return Run(python, "-c \"import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)\"", null, 20000, true) == 0;
    }

    private static string Capture(string file, string arguments)
    {
        try
        {
            var info = new ProcessStartInfo(file, arguments);
            info.UseShellExecute = false;
            info.RedirectStandardOutput = true;
            info.RedirectStandardError = true;
            info.CreateNoWindow = true;
            using (Process p = Process.Start(info))
            {
                string text = p.StandardOutput.ReadToEnd();
                p.WaitForExit(20000);
                return p.ExitCode == 0 ? text.Trim() : null;
            }
        }
        catch { return null; }
    }

    private static int Run(string file, string arguments, string dir, int timeout = -1, bool quiet = false)
    {
        try
        {
            var info = new ProcessStartInfo(file, arguments);
            info.UseShellExecute = false;
            if (dir != null) info.WorkingDirectory = dir;
            if (quiet)
            {
                info.RedirectStandardOutput = true;
                info.RedirectStandardError = true;
                info.CreateNoWindow = true;
            }
            using (Process p = Process.Start(info))
            {
                if (quiet)
                {
                    p.StandardOutput.ReadToEnd();
                    p.StandardError.ReadToEnd();
                }
                if (!p.WaitForExit(timeout)) { try { p.Kill(); } catch { } return -1; }
                return p.ExitCode;
            }
        }
        catch { return -1; }
    }

    private static string PowerShell()
    {
        string ps = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),
                                 Path.Combine("WindowsPowerShell", Path.Combine("v1.0", "powershell.exe")));
        return File.Exists(ps) ? ps : "powershell.exe";
    }

    private static string Quote(string s)
    {
        return "\"" + s.Replace("\"", "\\\"") + "\"";
    }

    private static int Fail(string msg)
    {
        Console.WriteLine();
        Console.WriteLine("  " + msg);
        Console.WriteLine();
        Console.Write("  Pressione ENTER para fechar...");
        try { Console.ReadLine(); } catch { }
        return 1;
    }
}
