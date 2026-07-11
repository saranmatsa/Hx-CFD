using Microsoft.Win32;
using HxCfdBootstrapper.Models;

namespace HxCfdBootstrapper.Services;

public interface IUninstallService
{
    Task<UninstallResult> RegisterUninstallAsync(InstallationManifest manifest, AppSettings settings);
    Task<bool> UnregisterUninstallAsync(string uninstallKeyName);
    Task<UninstallInfo?> GetUninstallInfoAsync(string uninstallKeyName);
}

public class UninstallService : IUninstallService
{
    private readonly ILogger<UninstallService> _logger;
    private readonly AppSettings _settings;

    public UninstallService(ILogger<UninstallService> logger, IOptions<AppSettings> settings)
    {
        _logger = logger;
        _settings = settings.Value;
    }

    public async Task<UninstallResult> RegisterUninstallAsync(InstallationManifest manifest, AppSettings settings)
    {
        var result = new UninstallResult();

        try
        {
            _logger.LogInformation("Registering uninstall information for {Application}", settings.Application.Name);

            var uninstallKeyName = GetUninstallKeyName(settings.Application.Name);
            var uninstallKeyPath = GetUninstallKeyPath(settings.Installation.PerUserInstall);

            using var baseKey = settings.Installation.PerUserInstall 
                ? Registry.CurrentUser 
                : Registry.LocalMachine;
            
            using var uninstallKey = baseKey.CreateSubKey(uninstallKeyPath, true);
            using var appKey = uninstallKey.CreateSubKey(uninstallKeyName, true);

            if (appKey == null)
            {
                result.Success = false;
                result.ErrorMessage = "Failed to create uninstall registry key";
                return result;
            }

            // Set uninstall information
            appKey.SetValue("DisplayName", settings.Application.Name);
            appKey.SetValue("DisplayVersion", settings.Application.Version);
            appKey.SetValue("Publisher", settings.Application.Publisher);
            appKey.SetValue("InstallLocation", manifest.InstallDir);
            appKey.SetValue("InstallDate", DateTime.Now.ToString("yyyyMMdd"));
            appKey.SetValue("UninstallString", manifest.UninstallString);
            appKey.SetValue("QuietUninstallString", $"{manifest.UninstallString} /quiet");
            appKey.SetValue("NoModify", 1, RegistryValueKind.DWord);
            appKey.SetValue("NoRepair", 1, RegistryValueKind.DWord);
            appKey.SetValue("EstimatedSize", CalculateInstallSize(manifest.InstallDir), RegistryValueKind.DWord);
            appKey.SetValue("SystemComponent", 0, RegistryValueKind.DWord);
            appKey.SetValue("WindowsInstaller", 0, RegistryValueKind.DWord);
            appKey.SetValue("HelpLink", "https://hx-cfd.com/support");
            appKey.SetValue("URLInfoAbout", "https://hx-cfd.com");
            appKey.SetValue("URLUpdateInfo", "https://hx-cfd.com/updates");

            // Store component information as JSON
            var componentJson = JsonSerializer.Serialize(manifest.Components);
            appKey.SetValue("Components", componentJson);

            result.Success = true;
            result.UninstallKeyName = uninstallKeyName;
            _logger.LogInformation("Uninstall registered successfully under {KeyPath}\\{KeyName}", uninstallKeyPath, uninstallKeyName);

            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to register uninstall information");
            result.Success = false;
            result.ErrorMessage = ex.Message;
            return result;
        }
    }

    public async Task<bool> UnregisterUninstallAsync(string uninstallKeyName)
    {
        try
        {
            var uninstallKeyPath = GetUninstallKeyPath(_settings.Installation.PerUserInstall);
            
            using var baseKey = _settings.Installation.PerUserInstall 
                ? Registry.CurrentUser 
                : Registry.LocalMachine;
            
            using var uninstallKey = baseKey.OpenSubKey(uninstallKeyPath, true);
            if (uninstallKey != null)
            {
                uninstallKey.DeleteSubKeyTree(uninstallKeyName, false);
                _logger.LogInformation("Uninstall information removed for {KeyName}", uninstallKeyName);
                return true;
            }
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to unregister uninstall information for {KeyName}", uninstallKeyName);
            return false;
        }
    }

    public async Task<UninstallInfo?> GetUninstallInfoAsync(string uninstallKeyName)
    {
        try
        {
            var uninstallKeyPath = GetUninstallKeyPath(_settings.Installation.PerUserInstall);
            
            using var baseKey = _settings.Installation.PerUserInstall 
                ? Registry.CurrentUser 
                : Registry.LocalMachine;
            
            using var uninstallKey = baseKey.OpenSubKey(uninstallKeyPath, false);
            using var appKey = uninstallKey?.OpenSubKey(uninstallKeyName, false);

            if (appKey == null) return null;

            return new UninstallInfo
            {
                DisplayName = appKey.GetValue("DisplayName")?.ToString() ?? "",
                DisplayVersion = appKey.GetValue("DisplayVersion")?.ToString() ?? "",
                Publisher = appKey.GetValue("Publisher")?.ToString() ?? "",
                InstallLocation = appKey.GetValue("InstallLocation")?.ToString() ?? "",
                UninstallString = appKey.GetValue("UninstallString")?.ToString() ?? "",
                InstallDate = appKey.GetValue("InstallDate")?.ToString() ?? "",
                EstimatedSize = Convert.ToInt32(appKey.GetValue("EstimatedSize") ?? 0)
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get uninstall info for {KeyName}", uninstallKeyName);
            return null;
        }
    }

    private string GetUninstallKeyName(string appName)
    {
        // Create a safe registry key name
        var safeName = string.Join("_", appName.Split(Path.GetInvalidFileNameChars()));
        return $"{safeName}_{_settings.Application.Version.Replace(".", "_")}";
    }

    private string GetUninstallKeyPath(bool perUser)
    {
        return perUser
            ? @"Software\Microsoft\Windows\CurrentVersion\Uninstall"
            : @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall";
    }

    private int CalculateInstallSize(string installDir)
    {
        try
        {
            if (!Directory.Exists(installDir)) return 0;

            var totalSize = 0L;
            var files = Directory.GetFiles(installDir, "*", SearchOption.AllDirectories);
            foreach (var file in files)
            {
                var info = new FileInfo(file);
                totalSize += info.Length;
            }

            // Return size in KB
            return (int)(totalSize / 1024);
        }
        catch
        {
            return 0;
        }
    }
}

public class UninstallResult
{
    public bool Success { get; set; }
    public string UninstallKeyName { get; set; } = string.Empty;
    public string? ErrorMessage { get; set; }
}

public class UninstallInfo
{
    public string DisplayName { get; set; } = string.Empty;
    public string DisplayVersion { get; set; } = string.Empty;
    public string Publisher { get; set; } = string.Empty;
    public string InstallLocation { get; set; } = string.Empty;
    public string UninstallString { get; set; } = string.Empty;
    public string InstallDate { get; set; } = string.Empty;
    public int EstimatedSize { get; set; }
}