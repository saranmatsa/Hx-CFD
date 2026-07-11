using System.Text.Json;
using HxCfdBootstrapper.Models;

namespace HxCfdBootstrapper.Services;

public interface IInstallationService
{
    Task<InstallationResult> InstallAsync(ComponentManifest manifest, IProgress<InstallationProgress>? progress = null, CancellationToken cancellationToken = default);
    Task<InstallationResult> InstallComponentAsync(Component component, string installDir, IProgress<InstallationProgress>? progress = null, CancellationToken cancellationToken = default);
    Task<bool> VerifyInstallationAsync(InstallationManifest manifest);
    Task<InstallationManifest> LoadManifestAsync(string manifestPath);
    Task SaveManifestAsync(InstallationManifest manifest, string manifestPath);
}

public class InstallationService : IInstallationService
{
    private readonly ILogger<InstallationService> _logger;
    private readonly IDownloadService _downloadService;
    private readonly IExtractionService _extractionService;
    private readonly IShortcutService _shortcutService;
    private readonly IUninstallService _uninstallService;
    private readonly ILaunchService _launchService;
    private readonly AppSettings _settings;

    public InstallationService(
        ILogger<InstallationService> logger,
        IDownloadService downloadService,
        IExtractionService extractionService,
        IShortcutService shortcutService,
        IUninstallService uninstallService,
        ILaunchService launchService,
        IOptions<AppSettings> settings)
    {
        _logger = logger;
        _downloadService = downloadService;
        _extractionService = extractionService;
        _shortcutService = shortcutService;
        _uninstallService = uninstallService;
        _launchService = launchService;
        _settings = settings.Value;
    }

    public async Task<InstallationResult> InstallAsync(ComponentManifest manifest, IProgress<InstallationProgress>? progress = null, CancellationToken cancellationToken = default)
    {
        var result = new InstallationResult();
        var installDir = ExpandEnvironmentVariables(_settings.Installation.InstallDirectory);
        var tempDir = ExpandEnvironmentVariables(_settings.Installation.TempDirectory);
        var totalComponents = manifest.Components.Count(c => c.Enabled);
        var completedComponents = 0;

        try
        {
            _logger.LogInformation("Starting installation of {Application} v{Version}", manifest.Name, manifest.Version);

            // Create installation directory
            Directory.CreateDirectory(installDir);
            Directory.CreateDirectory(tempDir);

            // Report initial progress
            ReportProgress(progress, new InstallationProgress
            {
                Stage = InstallationStage.Initializing,
                CurrentComponent = "",
                ComponentsCompleted = 0,
                TotalComponents = totalComponents,
                OverallProgress = 0,
                CurrentOperation = "Initializing installation..."
            });

            // Download and install each component
            foreach (var component in manifest.Components.Where(c => c.Enabled))
            {
                cancellationToken.ThrowIfCancellationRequested();

                ReportProgress(progress, new InstallationProgress
                {
                    Stage = InstallationStage.Downloading,
                    CurrentComponent = component.Name,
                    ComponentsCompleted = completedComponents,
                    TotalComponents = totalComponents,
                    OverallProgress = (double)completedComponents / totalComponents * 100,
                    CurrentOperation = $"Downloading {component.Name}..."
                });

                var componentResult = await InstallComponentAsync(component, installDir, progress, cancellationToken);
                
                if (!componentResult.Success)
                {
                    result.Success = false;
                    result.ErrorMessage = $"Failed to install component {component.Name}: {componentResult.ErrorMessage}";
                    result.InstalledComponents = result.InstalledComponents;
                    return result;
                }

                result.InstalledComponents.AddRange(componentResult.InstalledFiles);
                completedComponents++;

                ReportProgress(progress, new InstallationProgress
                {
                    Stage = InstallationStage.Extracting,
                    CurrentComponent = component.Name,
                    ComponentsCompleted = completedComponents,
                    TotalComponents = totalComponents,
                    OverallProgress = (double)completedComponents / totalComponents * 100,
                    CurrentOperation = $"Completed {component.Name}"
                });
            }

            // Create installation manifest
            var installationManifest = new InstallationManifest
            {
                ManifestVersion = manifest.Version,
                InstallDir = installDir,
                InstallDate = DateTime.UtcNow,
                Components = manifest.Components.Where(c => c.Enabled).Select(c => new ComponentInstallState
                {
                    ComponentId = c.Id,
                    Version = c.Version,
                    InstallPath = Path.Combine(installDir, c.Id),
                    InstalledFiles = result.InstalledFiles.Where(f => f.StartsWith(Path.Combine(installDir, c.Id))).ToList(),
                    Checksums = c.Archives.ToDictionary(a => a.Url, a => a.Sha256)
                }).ToList(),
                UninstallString = GetUninstallString(installDir)
            };

            // Save installation manifest
            var manifestPath = Path.Combine(installDir, "installation.json");
            await SaveManifestAsync(installationManifest, manifestPath);

            // Configure environment variables
            if (_settings.Installation.ConfigureEnvironment)
            {
                ReportProgress(progress, new InstallationProgress
                {
                    Stage = InstallationStage.Configuring,
                    CurrentComponent = "",
                    ComponentsCompleted = completedComponents,
                    TotalComponents = totalComponents,
                    OverallProgress = 90,
                    CurrentOperation = "Configuring environment..."
                });

                ConfigureEnvironment(installationManifest);
            }

            // Create shortcuts
            if (_settings.Installation.CreateShortcuts)
            {
                ReportProgress(progress, new InstallationProgress
                {
                    Stage = InstallationStage.CreatingShortcuts,
                    CurrentComponent = "",
                    ComponentsCompleted = completedComponents,
                    TotalComponents = totalComponents,
                    OverallProgress = 95,
                    CurrentOperation = "Creating shortcuts..."
                });

                await CreateShortcutsAsync(installationManifest);
            }

            // Register uninstaller
            if (_settings.Installation.RegisterUninstaller)
            {
                ReportProgress(progress, new InstallationProgress
                {
                    Stage = InstallationStage.RegisteringUninstaller,
                    CurrentComponent = "",
                    ComponentsCompleted = completedComponents,
                    TotalComponents = totalComponents,
                    OverallProgress = 98,
                    CurrentOperation = "Registering uninstaller..."
                });

                await _uninstallService.RegisterUninstallAsync(installationManifest, _settings);
            }

            // Final progress
            ReportProgress(progress, new InstallationProgress
            {
                Stage = InstallationStage.Completed,
                CurrentComponent = "",
                ComponentsCompleted = totalComponents,
                TotalComponents = totalComponents,
                OverallProgress = 100,
                CurrentOperation = "Installation completed successfully!"
            });

            result.Success = true;
            result.InstallDirectory = installDir;
            result.Manifest = installationManifest;
            _logger.LogInformation("Installation completed successfully to {InstallDir}", installDir);

            // Launch application if requested
            if (_settings.Application.AutoLaunch)
            {
                await LaunchApplicationAsync(installationManifest);
            }

            return result;
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Installation cancelled");
            result.Success = false;
            result.ErrorMessage = "Installation cancelled by user";
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Installation failed");
            result.Success = false;
            result.ErrorMessage = ex.Message;
            return result;
        }
    }

    public async Task<InstallationResult> InstallComponentAsync(Component component, string installDir, IProgress<InstallationProgress>? progress = null, CancellationToken cancellationToken = default)
    {
        var result = new InstallationResult();
        var componentDir = Path.Combine(installDir, component.Id);
        var tempDir = ExpandEnvironmentVariables(_settings.Installation.TempDirectory);

        try
        {
            _logger.LogInformation("Installing component: {Component}", component.Name);

            Directory.CreateDirectory(componentDir);
            Directory.CreateDirectory(tempDir);

            foreach (var archive in component.Archives)
            {
                cancellationToken.ThrowIfCancellationRequested();

                var archiveFileName = Path.GetFileName(new Uri(archive.Url).LocalPath);
                var archivePath = Path.Combine(tempDir, archiveFileName);

                // Download archive
                var downloadProgress = new Progress<DownloadProgress>(p =>
                {
                    ReportProgress(progress, new InstallationProgress
                    {
                        Stage = InstallationStage.Downloading,
                        CurrentComponent = component.Name,
                        CurrentOperation = $"Downloading {archiveFileName}...",
                        DownloadProgress = p
                    });
                });

                var downloadResult = await _downloadService.DownloadAsync(
                    archive.Url, 
                    archivePath, 
                    archive.Sha256, 
                    archive.Size, 
                    downloadProgress, 
                    cancellationToken);

                if (!downloadResult.Success)
                {
                    result.Success = false;
                    result.ErrorMessage = $"Download failed: {downloadResult.ErrorMessage}";
                    return result;
                }

                // Verify archive
                var isValid = await _extractionService.ValidateArchiveAsync(archivePath);
                if (!isValid)
                {
                    result.Success = false;
                    result.ErrorMessage = $"Archive validation failed: {archiveFileName}";
                    return result;
                }

                // Extract archive
                var extractionProgress = new Progress<ExtractionProgress>(p =>
                {
                    ReportProgress(progress, new InstallationProgress
                    {
                        Stage = InstallationStage.Extracting,
                        CurrentComponent = component.Name,
                        CurrentOperation = $"Extracting {p.CurrentFile}...",
                        ExtractionProgress = p
                    });
                });

                var extractResult = await _extractionService.ExtractAsync(
                    archivePath, 
                    componentDir, 
                    archive.ExtractTo, 
                    extractionProgress, 
                    cancellationToken);

                if (!extractResult.Success)
                {
                    result.Success = false;
                    result.ErrorMessage = $"Extraction failed: {extractResult.ErrorMessage}";
                    return result;
                }

                result.InstalledFiles.AddRange(extractResult.ExtractedFiles);

                // Clean up archive if configured
                if (_settings.Installation.CleanupTempFiles)
                {
                    try { File.Delete(archivePath); } catch { }
                }
            }

            result.Success = true;
            return result;
        }
        catch (OperationCanceledException)
        {
            result.Success = false;
            result.ErrorMessage = "Installation cancelled";
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to install component {Component}", component.Name);
            result.Success = false;
            result.ErrorMessage = ex.Message;
            return result;
        }
    }

    public async Task<bool> VerifyInstallationAsync(InstallationManifest manifest)
    {
        try
        {
            _logger.LogInformation("Verifying installation at {InstallDir}", manifest.InstallDir);

            if (!Directory.Exists(manifest.InstallDir))
            {
                _logger.LogError("Install directory does not exist: {InstallDir}", manifest.InstallDir);
                return false;
            }

            foreach (var component in manifest.Components)
            {
                var componentPath = Path.Combine(manifest.InstallDir, component.ComponentId);
                if (!Directory.Exists(componentPath))
                {
                    _logger.LogError("Component directory missing: {ComponentPath}", componentPath);
                    return false;
                }

                // Verify installed files exist
                foreach (var file in component.InstalledFiles)
                {
                    if (!File.Exists(file))
                    {
                        _logger.LogError("Installed file missing: {File}", file);
                        return false;
                    }
                }
            }

            _logger.LogInformation("Installation verification successful");
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Installation verification failed");
            return false;
        }
    }

    public async Task<InstallationManifest> LoadManifestAsync(string manifestPath)
    {
        try
        {
            if (!File.Exists(manifestPath))
            {
                throw new FileNotFoundException("Manifest file not found", manifestPath);
            }

            var json = await File.ReadAllTextAsync(manifestPath);
            var manifest = JsonSerializer.Deserialize<InstallationManifest>(json, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            });

            return manifest ?? throw new InvalidOperationException("Failed to deserialize manifest");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load manifest from {ManifestPath}", manifestPath);
            throw;
        }
    }

    public async Task SaveManifestAsync(InstallationManifest manifest, string manifestPath)
    {
        try
        {
            var json = JsonSerializer.Serialize(manifest, new JsonSerializerOptions
            {
                WriteIndented = true,
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            });

            await File.WriteAllTextAsync(manifestPath, json);
            _logger.LogInformation("Installation manifest saved to {ManifestPath}", manifestPath);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to save manifest to {ManifestPath}", manifestPath);
            throw;
        }
    }

    private void ConfigureEnvironment(InstallationManifest manifest)
    {
        try
        {
            _logger.LogInformation("Configuring environment variables");

            var installDir = manifest.InstallDir;
            var binPath = Path.Combine(installDir, "bin");
            
            if (Directory.Exists(binPath))
            {
                var currentPath = Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.Process) ?? "";
                if (!currentPath.Split(';').Contains(binPath, StringComparer.OrdinalIgnoreCase))
                {
                    Environment.SetEnvironmentVariable("PATH", currentPath + ";" + binPath, EnvironmentVariableTarget.Process);
                }
            }

            // Set HX_CFD_HOME environment variable
            Environment.SetEnvironmentVariable("HX_CFD_HOME", installDir, EnvironmentVariableTarget.Process);

            _logger.LogInformation("Environment configured successfully");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to configure environment");
        }
    }

    private async Task CreateShortcutsAsync(InstallationManifest manifest)
    {
        try
        {
            _logger.LogInformation("Creating shortcuts");

            // Find main executable
            var mainExe = FindMainExecutable(manifest.InstallDir);
            if (string.IsNullOrEmpty(mainExe))
            {
                _logger.LogWarning("Main executable not found, skipping shortcut creation");
                return;
            }

            var iconPath = FindIcon(manifest.InstallDir);

            // Desktop shortcut
            var desktopShortcut = new ShortcutInfo
            {
                Name = _settings.Application.Name,
                TargetPath = mainExe,
                WorkingDirectory = manifest.InstallDir,
                Description = $"{_settings.Application.Name} {_settings.Application.Version}",
                IconPath = iconPath,
                Location = ShortcutLocation.Desktop
            };

            await _shortcutService.CreateShortcutAsync(desktopShortcut);

            // Start Menu shortcut
            var startMenuShortcut = new ShortcutInfo
            {
                Name = _settings.Application.Name,
                TargetPath = mainExe,
                WorkingDirectory = manifest.InstallDir,
                Description = $"{_settings.Application.Name} {_settings.Application.Version}",
                IconPath = iconPath,
                Location = ShortcutLocation.StartMenu,
                StartMenuFolder = _settings.Application.Name
            };

            await _shortcutService.CreateShortcutAsync(startMenuShortcut);

            _logger.LogInformation("Shortcuts created successfully");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to create shortcuts");
        }
    }

    private string? FindMainExecutable(string installDir)
    {
        // Look for common executable patterns
        var patterns = new[] { "*.exe", "hx-cfd*.exe", "cfd*.exe" };
        
        foreach (var pattern in patterns)
        {
            var files = Directory.GetFiles(installDir, pattern, SearchOption.AllDirectories);
            if (files.Length > 0)
            {
                // Prefer executable in bin folder or root
                var preferred = files.FirstOrDefault(f => 
                    f.Contains("bin", StringComparison.OrdinalIgnoreCase) || 
                    Path.GetDirectoryName(f)?.Equals(installDir, StringComparison.OrdinalIgnoreCase) == true);
                
                return preferred ?? files[0];
            }
        }

        return null;
    }

    private string? FindIcon(string installDir)
    {
        var iconFiles = Directory.GetFiles(installDir, "*.ico", SearchOption.AllDirectories);
        return iconFiles.Length > 0 ? iconFiles[0] : null;
    }

    private string GetUninstallString(string installDir)
    {
        var uninstallExe = Path.Combine(installDir, "uninstall.exe");
        if (File.Exists(uninstallExe))
        {
            return $"\"{uninstallExe}\"";
        }
        
        // Fallback to bootstrapper itself
        var currentExe = Environment.ProcessPath ?? "";
        return $"\"{currentExe}\" /uninstall";
    }

    private async Task LaunchApplicationAsync(InstallationManifest manifest)
    {
        try
        {
            var mainExe = FindMainExecutable(manifest.InstallDir);
            if (string.IsNullOrEmpty(mainExe))
            {
                _logger.LogWarning("Main executable not found, skipping auto-launch");
                return;
            }

            var launchInfo = new LaunchInfo
            {
                ExecutablePath = mainExe,
                WorkingDirectory = manifest.InstallDir,
                RunAsAdministrator = false,
                HideWindow = false,
                WaitForExit = false
            };

            var result = await _launchService.LaunchAsync(launchInfo);
            if (result.Success)
            {
                _logger.LogInformation("Application launched successfully (PID: {Pid})", result.ProcessId);
            }
            else
            {
                _logger.LogWarning("Failed to auto-launch application: {Error}", result.ErrorMessage);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error during auto-launch");
        }
    }

    private string ExpandEnvironmentVariables(string path)
    {
        return Environment.ExpandEnvironmentVariables(path);
    }

    private void ReportProgress(IProgress<InstallationProgress>? progress, InstallationProgress progressInfo)
    {
        progress?.Report(progressInfo);
    }
}

public class InstallationResult
{
    public bool Success { get; set; }
    public string InstallDirectory { get; set; } = string.Empty;
    public InstallationManifest? Manifest { get; set; }
    public List<string> InstalledFiles { get; set; } = new();
    public List<string> InstalledComponents { get; set; } = new();
    public string? ErrorMessage { get; set; }
}

public class InstallationProgress
{
    public InstallationStage Stage { get; set; }
    public string CurrentComponent { get; set; } = string.Empty;
    public int ComponentsCompleted { get; set; }
    public int TotalComponents { get; set; }
    public double OverallProgress { get; set; }
    public string CurrentOperation { get; set; } = string.Empty;
    public DownloadProgress? DownloadProgress { get; set; }
    public ExtractionProgress? ExtractionProgress { get; set; }
}

public enum InstallationStage
{
    Initializing,
    Downloading,
    Extracting,
    Configuring,
    CreatingShortcuts,
    RegisteringUninstaller,
    Completed,
    Failed
}