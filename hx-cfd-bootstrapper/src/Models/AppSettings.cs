using System.Text.Json.Serialization;

namespace HxCfdBootstrapper.Models;

public class AppSettings
{
    [JsonPropertyName("Application")]
    public ApplicationSettings Application { get; set; } = new();

    [JsonPropertyName("Download")]
    public DownloadSettings Download { get; set; } = new();

    [JsonPropertyName("Components")]
    public ComponentSettings Components { get; set; } = new();

    [JsonPropertyName("Installation")]
    public InstallationSettings Installation { get; set; } = new();

    [JsonPropertyName("Logging")]
    public LoggingSettings Logging { get; set; } = new();

    [JsonPropertyName("UI")]
    public UISettings UI { get; set; } = new();
}

public class ApplicationSettings
{
    [JsonPropertyName("Name")]
    public string Name { get; set; } = "HX CFD";

    [JsonPropertyName("Version")]
    public string Version { get; set; } = "1.0.0";

    [JsonPropertyName("Publisher")]
    public string Publisher { get; set; } = "HX CFD Team";

    [JsonPropertyName("InstallDirName")]
    public string InstallDirName { get; set; } = "HX CFD";

    [JsonPropertyName("ExecutableName")]
    public string ExecutableName { get; set; } = "hx-cfd.exe";

    [JsonPropertyName("StartMenuFolder")]
    public string StartMenuFolder { get; set; } = "HX CFD";

    [JsonPropertyName("DesktopShortcut")]
    public bool DesktopShortcut { get; set; } = true;

    [JsonPropertyName("StartMenuShortcut")]
    public bool StartMenuShortcut { get; set; } = true;

    [JsonPropertyName("AutoLaunch")]
    public bool AutoLaunch { get; set; } = true;
}

public class DownloadSettings
{
    [JsonPropertyName("BaseUrl")]
    public string BaseUrl { get; set; } = "https://releases.hx-cfd.com/runtime/{version}/";

    [JsonPropertyName("TimeoutSeconds")]
    public int TimeoutSeconds { get; set; } = 300;

    [JsonPropertyName("MaxRetries")]
    public int MaxRetries { get; set; } = 3;

    [JsonPropertyName("RetryDelaySeconds")]
    public int RetryDelaySeconds { get; set; } = 5;

    [JsonPropertyName("ConcurrentDownloads")]
    public int ConcurrentDownloads { get; set; } = 2;

    [JsonPropertyName("VerifyChecksums")]
    public bool VerifyChecksums { get; set; } = true;

    [JsonPropertyName("UserAgent")]
    public string UserAgent { get; set; } = "HX-CFD-Bootstrapper/1.0.0";
}

public class ComponentSettings
{
    [JsonPropertyName("Required")]
    public List<string> Required { get; set; } = new();

    [JsonPropertyName("Optional")]
    public List<string> Optional { get; set; } = new();
}

public class InstallationSettings
{
    [JsonPropertyName("RequireAdmin")]
    public bool RequireAdmin { get; set; } = false;

    [JsonPropertyName("PerUserInstall")]
    public bool PerUserInstall { get; set; } = true;

    [JsonPropertyName("CreateUninstaller")]
    public bool CreateUninstaller { get; set; } = true;

    [JsonPropertyName("RegisterUninstall")]
    public bool RegisterUninstall { get; set; } = true;

    [JsonPropertyName("AddToPath")]
    public bool AddToPath { get; set; } = false;
}

public class LoggingSettings
{
    [JsonPropertyName("LogLevel")]
    public string LogLevel { get; set; } = "Information";

    [JsonPropertyName("LogToFile")]
    public bool LogToFile { get; set; } = true;

    [JsonPropertyName("LogFilePath")]
    public string LogFilePath { get; set; } = "%LOCALAPPDATA%\\HX CFD\\Logs\\bootstrapper.log";

    [JsonPropertyName("MaxLogFiles")]
    public int MaxLogFiles { get; set; } = 5;

    [JsonPropertyName("MaxLogFileSizeMB")]
    public int MaxLogFileSizeMB { get; set; } = 10;
}

public class UISettings
{
    [JsonPropertyName("ShowProgress")]
    public bool ShowProgress { get; set; } = true;

    [JsonPropertyName("ShowDetails")]
    public bool ShowDetails { get; set; } = true;

    [JsonPropertyName("AutoCloseOnSuccess")]
    public bool AutoCloseOnSuccess { get; set; } = true;

    [JsonPropertyName("AutoCloseDelaySeconds")]
    public int AutoCloseDelaySeconds { get; set; } = 5;

    [JsonPropertyName("Theme")]
    public string Theme { get; set; } = "Light";
}