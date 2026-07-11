using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace HxCfdBootstrapper.Models;

/// <summary>
/// Installation stages
/// </summary>
public enum InstallationStage
{
    Initializing,
    Downloading,
    Extracting,
    Configuring,
    CreatingShortcuts,
    RegisteringUninstaller,
    Completed,
    Failed,
    Cancelled
}

/// <summary>
/// Progress information for installation
/// </summary>
public class InstallationProgress
{
    public InstallationStage Stage { get; set; } = InstallationStage.Initializing;
    public string CurrentOperation { get; set; } = string.Empty;
    public string CurrentComponent { get; set; } = string.Empty;
    public double OverallProgress { get; set; } = 0;
    public double DownloadProgress { get; set; } = 0;
    public double ExtractionProgress { get; set; } = 0;
    public int ComponentsCompleted { get; set; } = 0;
    public int TotalComponents { get; set; } = 0;
    public string StatusText { get; set; } = string.Empty;
}

/// <summary>
/// Result of installation operation
/// </summary>
public class InstallationResult
{
    public bool Success { get; set; }
    public string? ErrorMessage { get; set; }
    public string? InstallPath { get; set; }
    public List<string> InstalledComponents { get; set; } = new();
    public List<string> CreatedShortcuts { get; set; } = new();
    public bool UninstallerRegistered { get; set; } = false;
    public DateTime CompletedAt { get; set; } = DateTime.UtcNow;
}

/// <summary>
/// Information for launching an application
/// </summary>
public class LaunchInfo
{
    public string ExecutablePath { get; set; } = string.Empty;
    public string Arguments { get; set; } = string.Empty;
    public string WorkingDirectory { get; set; } = string.Empty;
    public bool RunAsAdministrator { get; set; } = false;
    public bool HideWindow { get; set; } = false;
    public bool WaitForExit { get; set; } = false;
    public TimeSpan? Timeout { get; set; }
    public Dictionary<string, string> EnvironmentVariables { get; set; } = new();
}

/// <summary>
/// Result of launch operation
/// </summary>
public class LaunchResult
{
    public bool Success { get; set; }
    public int? ProcessId { get; set; }
    public System.Diagnostics.Process? Process { get; set; }
    public int? ExitCode { get; set; }
    public bool Exited { get; set; }
    public string? ErrorMessage { get; set; }
}

/// <summary>
/// Process information
/// </summary>
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

/// <summary>
/// Application settings
/// </summary>
public class AppSettings
{
    public string ApplicationName { get; set; } = "HxCFD";
    public string ApplicationDescription { get; set; } = "High-Performance Computational Fluid Dynamics";
    public string ApplicationVersion { get; set; } = "1.0.0";
    public string InstallDirectory { get; set; } = @"C:\Program Files\HxCFD";
    public string DownloadBaseUrl { get; set; } = "https://github.com/hx-cfd/releases/download";
    public string ManifestUrl { get; set; } = "https://github.com/hx-cfd/releases/latest/download/manifest.json";
    public bool AutoStartInstallation { get; set; } = false;
    public bool AutoLaunchAfterInstall { get; set; } = true;
    public bool CreateDesktopShortcut { get; set; } = true;
    public bool CreateStartMenuShortcut { get; set; } = true;
    public bool RegisterUninstaller { get; set; } = true;
    public int DownloadTimeoutSeconds { get; set; } = 300;
    public int ExtractionTimeoutSeconds { get; set; } = 120;
    public int MaxConcurrentDownloads { get; set; } = 3;
    public long MaxDownloadSizeBytes { get; set; } = 2_000_000_000; // 2GB
    public string LogLevel { get; set; } = "Information";
}

/// <summary>
/// Component manifest for installation
/// </summary>
public class ComponentManifest
{
    public string Name { get; set; } = string.Empty;
    public string Version { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string DownloadUrl { get; set; } = string.Empty;
    public string Checksum { get; set; } = string.Empty;
    public long SizeBytes { get; set; }
    public string ExtractPath { get; set; } = string.Empty;
    public bool Required { get; set; } = true;
    public List<string> Dependencies { get; set; } = new();
    public Dictionary<string, string> EnvironmentVariables { get; set; } = new();
}

/// <summary>
/// Full installation manifest
/// </summary>
public class InstallationManifest
{
    public string Version { get; set; } = string.Empty;
    public DateTime ReleaseDate { get; set; }
    public string Description { get; set; } = string.Empty;
    public List<ComponentManifest> Components { get; set; } = new();
    public Dictionary<string, string> GlobalEnvironmentVariables { get; set; } = new();
    public string MainExecutable { get; set; } = "hx-cfd.exe";
}