using System.Runtime.InteropServices;
using HxCfdBootstrapper.Models;

namespace HxCfdBootstrapper.Services;

public interface IShortcutService
{
    Task<ShortcutResult> CreateShortcutAsync(ShortcutInfo shortcutInfo);
    Task<bool> RemoveShortcutAsync(string shortcutPath);
    Task<bool> ShortcutExistsAsync(string shortcutPath);
}

public class ShortcutService : IShortcutService
{
    private readonly ILogger<ShortcutService> _logger;

    public ShortcutService(ILogger<ShortcutService> logger)
    {
        _logger = logger;
    }

    public async Task<ShortcutResult> CreateShortcutAsync(ShortcutInfo shortcutInfo)
    {
        var result = new ShortcutResult { ShortcutPath = shortcutInfo.TargetPath };

        try
        {
            _logger.LogInformation("Creating shortcut: {Name} -> {Target}", shortcutInfo.Name, shortcutInfo.TargetPath);

            var shortcutPath = GetShortcutPath(shortcutInfo);
            var directory = Path.GetDirectoryName(shortcutPath);
            
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                await CreateWindowsShortcutAsync(shortcutInfo, shortcutPath);
            }
            else
            {
                // For non-Windows, create a .desktop file or shell script
                await CreateUnixShortcutAsync(shortcutInfo, shortcutPath);
            }

            result.Success = true;
            result.ShortcutPath = shortcutPath;
            _logger.LogInformation("Shortcut created successfully: {Path}", shortcutPath);
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create shortcut for {Name}", shortcutInfo.Name);
            result.Success = false;
            result.ErrorMessage = ex.Message;
            return result;
        }
    }

    private async Task CreateWindowsShortcutAsync(ShortcutInfo shortcutInfo, string shortcutPath)
    {
        // Use Windows Script Host COM object to create shortcut
        var shellType = Type.GetTypeFromProgID("WScript.Shell");
        if (shellType == null)
        {
            throw new InvalidOperationException("Windows Script Host not available");
        }

        dynamic shell = Activator.CreateInstance(shellType)!;
        dynamic shortcut = shell.CreateShortcut(shortcutPath);
        
        shortcut.TargetPath = shortcutInfo.TargetPath;
        shortcut.Arguments = shortcutInfo.Arguments ?? "";
        shortcut.WorkingDirectory = shortcutInfo.WorkingDirectory ?? Path.GetDirectoryName(shortcutInfo.TargetPath) ?? "";
        shortcut.Description = shortcutInfo.Description ?? "";
        
        if (!string.IsNullOrEmpty(shortcutInfo.IconPath) && File.Exists(shortcutInfo.IconPath))
        {
            shortcut.IconLocation = shortcutInfo.IconPath;
        }

        shortcut.Save();
        
        await Task.CompletedTask;
    }

    private async Task CreateUnixShortcutAsync(ShortcutInfo shortcutInfo, string shortcutPath)
    {
        var desktopEntry = $@"[Desktop Entry]
Type=Application
Name={shortcutInfo.Name}
Exec={shortcutInfo.TargetPath} {shortcutInfo.Arguments ?? ""}
Icon={shortcutInfo.IconPath ?? ""}
Terminal=false
Categories=Engineering;Science;
";

        await File.WriteAllTextAsync(shortcutPath, desktopEntry);
        
        // Make executable
        if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
        {
            var chmod = new ProcessStartInfo("chmod", "+x " + shortcutPath)
            {
                UseShellExecute = false,
                CreateNoWindow = true
            };
            Process.Start(chmod)?.WaitForExit();
        }
    }

    private string GetShortcutPath(ShortcutInfo shortcutInfo)
    {
        var extension = RuntimeInformation.IsOSPlatform(OSPlatform.Windows) ? ".lnk" : ".desktop";
        var fileName = $"{shortcutInfo.Name}{extension}";

        return shortcutInfo.Location switch
        {
            ShortcutLocation.Desktop => Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                fileName),
            ShortcutLocation.StartMenu => Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),
                "Programs",
                shortcutInfo.StartMenuFolder ?? "HX CFD",
                fileName),
            ShortcutLocation.Startup => Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Startup),
                fileName),
            _ => Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                fileName)
        };
    }

    public async Task<bool> RemoveShortcutAsync(string shortcutPath)
    {
        try
        {
            if (File.Exists(shortcutPath))
            {
                File.Delete(shortcutPath);
                _logger.LogInformation("Shortcut removed: {Path}", shortcutPath);
                return true;
            }
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to remove shortcut: {Path}", shortcutPath);
            return false;
        }
    }

    public async Task<bool> ShortcutExistsAsync(string shortcutPath)
    {
        return await Task.FromResult(File.Exists(shortcutPath));
    }
}

public class ShortcutInfo
{
    public string Name { get; set; } = string.Empty;
    public string TargetPath { get; set; } = string.Empty;
    public string? Arguments { get; set; }
    public string? WorkingDirectory { get; set; }
    public string? Description { get; set; }
    public string? IconPath { get; set; }
    public ShortcutLocation Location { get; set; } = ShortcutLocation.Desktop;
    public string? StartMenuFolder { get; set; }
}

public enum ShortcutLocation
{
    Desktop,
    StartMenu,
    Startup
}

public class ShortcutResult
{
    public bool Success { get; set; }
    public string ShortcutPath { get; set; } = string.Empty;
    public string? ErrorMessage { get; set; }
}