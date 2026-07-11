using System.Diagnostics;
using HxCfdBootstrapper.Models;

namespace HxCfdBootstrapper.Services;

public interface ILaunchService
{
    Task<LaunchResult> LaunchAsync(LaunchInfo launchInfo);
    Task<bool> IsProcessRunningAsync(int processId);
    Task<ProcessInfo?> GetProcessInfoAsync(int processId);
    Task<bool> WaitForExitAsync(int processId, TimeSpan? timeout = null);
    Task<bool> KillProcessAsync(int processId, bool force = false);
}

public class LaunchService : ILaunchService
{
    private readonly ILogger<LaunchService> _logger;

    public LaunchService(ILogger<LaunchService> logger)
    {
        _logger = logger;
    }

    public async Task<LaunchResult> LaunchAsync(LaunchInfo launchInfo)
    {
        var result = new LaunchResult();

        try
        {
            _logger.LogInformation("Launching application: {Executable} with args: {Arguments}", 
                launchInfo.ExecutablePath, launchInfo.Arguments);

            if (!File.Exists(launchInfo.ExecutablePath))
            {
                result.Success = false;
                result.ErrorMessage = $"Executable not found: {launchInfo.ExecutablePath}";
                _logger.LogError("Executable not found: {Path}", launchInfo.ExecutablePath);
                return result;
            }

            var startInfo = new ProcessStartInfo
            {
                FileName = launchInfo.ExecutablePath,
                Arguments = launchInfo.Arguments ?? "",
                WorkingDirectory = launchInfo.WorkingDirectory ?? Path.GetDirectoryName(launchInfo.ExecutablePath) ?? "",
                UseShellExecute = launchInfo.RunAsAdministrator,
                Verb = launchInfo.RunAsAdministrator ? "runas" : "",
                CreateNoWindow = launchInfo.HideWindow,
                WindowStyle = launchInfo.HideWindow ? ProcessWindowStyle.Hidden : ProcessWindowStyle.Normal
            };

            // Set environment variables if provided
            if (launchInfo.EnvironmentVariables != null)
            {
                foreach (var env in launchInfo.EnvironmentVariables)
                {
                    startInfo.EnvironmentVariables[env.Key] = env.Value;
                }
            }

            var process = Process.Start(startInfo);
            
            if (process == null)
            {
                result.Success = false;
                result.ErrorMessage = "Failed to start process";
                _logger.LogError("Process.Start returned null for {Executable}", launchInfo.ExecutablePath);
                return result;
            }

            result.Success = true;
            result.ProcessId = process.Id;
            result.Process = process;
            
            _logger.LogInformation("Application launched successfully with PID: {ProcessId}", process.Id);

            // If we need to wait for exit
            if (launchInfo.WaitForExit)
            {
                var exited = await WaitForExitAsync(process.Id, launchInfo.Timeout);
                result.ExitCode = process.ExitCode;
                result.Exited = exited;
            }

            return result;
        }
        catch (System.ComponentModel.Win32Exception ex) when (ex.NativeErrorCode == 1223)
        {
            // User cancelled UAC prompt
            _logger.LogWarning("User cancelled UAC elevation prompt");
            result.Success = false;
            result.ErrorMessage = "User cancelled elevation prompt";
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to launch application: {Executable}", launchInfo.ExecutablePath);
            result.Success = false;
            result.ErrorMessage = ex.Message;
            return result;
        }
    }

    public async Task<bool> IsProcessRunningAsync(int processId)
    {
        try
        {
            var process = Process.GetProcessById(processId);
            return !process.HasExited;
        }
        catch (ArgumentException)
        {
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error checking process {ProcessId}", processId);
            return false;
        }
    }

    public async Task<ProcessInfo?> GetProcessInfoAsync(int processId)
    {
        try
        {
            var process = Process.GetProcessById(processId);
            
            return new ProcessInfo
            {
                ProcessId = process.Id,
                ProcessName = process.ProcessName,
                StartTime = process.StartTime,
                HasExited = process.HasExited,
                ExitCode = process.HasExited ? process.ExitCode : null,
                WorkingSet64 = process.WorkingSet64,
                PrivateMemorySize64 = process.PrivateMemorySize64,
                TotalProcessorTime = process.TotalProcessorTime,
                MainWindowTitle = process.MainWindowTitle,
                Responding = process.Responding
            };
        }
        catch (ArgumentException)
        {
            return null;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting process info for {ProcessId}", processId);
            return null;
        }
    }

    public async Task<bool> WaitForExitAsync(int processId, TimeSpan? timeout = null)
    {
        try
        {
            var process = Process.GetProcessById(processId);
            var timeoutMs = timeout?.TotalMilliseconds ?? Timeout.Infinite;
            
            if (timeoutMs == Timeout.Infinite)
            {
                process.WaitForExit();
                return true;
            }
            else
            {
                return process.WaitForExit((int)timeoutMs);
            }
        }
        catch (ArgumentException)
        {
            // Process already exited
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error waiting for process {ProcessId}", processId);
            return false;
        }
    }

    public async Task<bool> KillProcessAsync(int processId, bool force = false)
    {
        try
        {
            var process = Process.GetProcessById(processId);
            
            if (process.HasExited)
            {
                return true;
            }

            if (force)
            {
                process.Kill(true);
                _logger.LogInformation("Force killed process {ProcessId}", processId);
            }
            else
            {
                var closed = process.CloseMainWindow();
                if (!closed)
                {
                    // Wait a bit then force kill
                    await Task.Delay(2000);
                    if (!process.HasExited)
                    {
                        process.Kill(true);
                        _logger.LogWarning("Force killed process {ProcessId} after graceful close failed", processId);
                    }
                }
                else
                {
                    _logger.LogInformation("Gracefully closed process {ProcessId}", processId);
                }
            }

            return true;
        }
        catch (ArgumentException)
        {
            // Process already exited
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error killing process {ProcessId}", processId);
            return false;
        }
    }
}

public class LaunchInfo
{
    public string ExecutablePath { get; set; } = string.Empty;
    public string? Arguments { get; set; }
    public string? WorkingDirectory { get; set; }
    public bool RunAsAdministrator { get; set; } = false;
    public bool HideWindow { get; set; } = false;
    public bool WaitForExit { get; set; } = false;
    public TimeSpan? Timeout { get; set; }
    public Dictionary<string, string>? EnvironmentVariables { get; set; }
}

public class LaunchResult
{
    public bool Success { get; set; }
    public int ProcessId { get; set; }
    public Process? Process { get; set; }
    public int? ExitCode { get; set; }
    public bool Exited { get; set; }
    public string? ErrorMessage { get; set; }
}

public class ProcessInfo
{
    public int ProcessId { get; set; }
    public string ProcessName { get; set; } = string.Empty;
    public DateTime StartTime { get; set; }
    public bool HasExited { get; set; }
    public int? ExitCode { get; set; }
    public long WorkingSet64 { get; set; }
    public long PrivateMemorySize64 { get; set; }
    public TimeSpan TotalProcessorTime { get; set; }
    public string MainWindowTitle { get; set; } = string.Empty;
    public bool Responding { get; set; }
}