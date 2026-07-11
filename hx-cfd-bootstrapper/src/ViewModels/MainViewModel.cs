using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using HxCfdBootstrapper.Models;
using HxCfdBootstrapper.Services;

namespace HxCfdBootstrapper;

/// <summary>
/// Main view model for the bootstrapper UI
/// </summary>
public class MainViewModel : INotifyPropertyChanged
{
    private readonly IInstallationService _installationService;
    private readonly ILogger<MainViewModel> _logger;
    private readonly AppSettings _settings;

    private InstallationStage _currentStage = InstallationStage.Initializing;
    private string _currentOperation = "Initializing...";
    private string _currentComponent = "";
    private double _overallProgress = 0;
    private double _downloadProgress = 0;
    private double _extractionProgress = 0;
    private int _componentsCompleted = 0;
    private int _totalComponents = 0;
    private bool _isInstalling = false;
    private bool _isCompleted = false;
    private bool _isCancelled = false;
    private bool _showDetails = false;
    private string _statusText = "Ready to install";
    private ObservableCollection<LogEntry> _logEntries = new();
    private CancellationTokenSource? _cancellationTokenSource;
    private InstallationResult? _lastResult;

    public MainViewModel(IInstallationService installationService, ILogger<MainViewModel> logger, IOptions<AppSettings> settings)
    {
        _installationService = installationService;
        _logger = logger;
        _settings = settings.Value;

        // Commands
        InstallCommand = new RelayCommand(async () => await InstallAsync(), () => !IsInstalling && !IsCompleted);
        CancelCommand = new RelayCommand(Cancel, () => IsInstalling && !IsCompleted);
        CloseCommand = new RelayCommand(Close, () => IsCompleted);
        ToggleDetailsCommand = new RelayCommand(() => ShowDetails = !ShowDetails);

        // Subscribe to log events
        LogService.LogEntryAdded += OnLogEntryAdded;
    }

    #region Properties

    public InstallationStage CurrentStage
    {
        get => _currentStage;
        set => SetProperty(ref _currentStage, value);
    }

    public string CurrentOperation
    {
        get => _currentOperation;
        set => SetProperty(ref _currentOperation, value);
    }

    public string CurrentComponent
    {
        get => _currentComponent;
        set => SetProperty(ref _currentComponent, value);
    }

    public double OverallProgress
    {
        get => _overallProgress;
        set => SetProperty(ref _overallProgress, value);
    }

    public double DownloadProgress
    {
        get => _downloadProgress;
        set => SetProperty(ref _downloadProgress, value);
    }

    public double ExtractionProgress
    {
        get => _extractionProgress;
        set => SetProperty(ref _extractionProgress, value);
    }

    public int ComponentsCompleted
    {
        get => _componentsCompleted;
        set => SetProperty(ref _componentsCompleted, value);
    }

    public int TotalComponents
    {
        get => _totalComponents;
        set => SetProperty(ref _totalComponents, value);
    }

    public bool IsInstalling
    {
        get => _isInstalling;
        set
        {
            if (SetProperty(ref _isInstalling, value))
            {
                ((RelayCommand)InstallCommand).RaiseCanExecuteChanged();
                ((RelayCommand)CancelCommand).RaiseCanExecuteChanged();
                ((RelayCommand)CloseCommand).RaiseCanExecuteChanged();
            }
        }
    }

    public bool IsCompleted
    {
        get => _isCompleted;
        set
        {
            if (SetProperty(ref _isCompleted, value))
            {
                ((RelayCommand)InstallCommand).RaiseCanExecuteChanged();
                ((RelayCommand)CancelCommand).RaiseCanExecuteChanged();
                ((RelayCommand)CloseCommand).RaiseCanExecuteChanged();
            }
        }
    }

    public bool IsCancelled
    {
        get => _isCancelled;
        set => SetProperty(ref _isCancelled, value);
    }

    public bool ShowDetails
    {
        get => _showDetails;
        set => SetProperty(ref _showDetails, value);
    }

    public string StatusText
    {
        get => _statusText;
        set => SetProperty(ref _statusText, value);
    }

    public ObservableCollection<LogEntry> LogEntries
    {
        get => _logEntries;
        set => SetProperty(ref _logEntries, value);
    }

    public InstallationResult? LastResult
    {
        get => _lastResult;
        set => SetProperty(ref _lastResult, value);
    }

    public string ApplicationName => _settings.Application.Name;
    public string ApplicationVersion => _settings.Application.Version;
    public string ApplicationDescription => _settings.Application.Description;

    #endregion

    #region Commands

    public ICommand InstallCommand { get; }
    public ICommand CancelCommand { get; }
    public ICommand CloseCommand { get; }
    public ICommand ToggleDetailsCommand { get; }

    #endregion

    #region Methods

    private async Task InstallAsync()
    {
        IsInstalling = true;
        IsCompleted = false;
        IsCancelled = false;
        OverallProgress = 0;
        DownloadProgress = 0;
        ExtractionProgress = 0;
        ComponentsCompleted = 0;
        LogEntries.Clear();
        _cancellationTokenSource = new CancellationTokenSource();

        try
        {
            _logger.LogInformation("Starting installation of {Application} v{Version}", ApplicationName, ApplicationVersion);
            AddLog(LogLevel.Information, $"Starting installation of {ApplicationName} v{ApplicationVersion}");

            var progress = new Progress<InstallationProgress>(OnProgressUpdate);
            
            var result = await _installationService.InstallAsync(progress, _cancellationTokenSource.Token);
            
            LastResult = result;

            if (result.Success)
            {
                IsCompleted = true;
                IsInstalling = false;
                StatusText = "Installation completed successfully!";
                CurrentOperation = "Installation completed successfully!";
                OverallProgress = 100;
                AddLog(LogLevel.Information, $"Installation completed successfully to {result.InstallDirectory}");
                _logger.LogInformation("Installation completed successfully to {InstallDir}", result.InstallDirectory);
            }
            else
            {
                IsCompleted = true;
                IsInstalling = false;
                IsCancelled = true;
                StatusText = $"Installation failed: {result.ErrorMessage}";
                CurrentOperation = $"Installation failed: {result.ErrorMessage}";
                AddLog(LogLevel.Error, $"Installation failed: {result.ErrorMessage}");
                _logger.LogError("Installation failed: {Error}", result.ErrorMessage);
            }
        }
        catch (OperationCanceledException)
        {
            IsCancelled = true;
            IsInstalling = false;
            IsCompleted = true;
            StatusText = "Installation cancelled";
            CurrentOperation = "Installation cancelled by user";
            AddLog(LogLevel.Warning, "Installation cancelled by user");
            _logger.LogWarning("Installation cancelled by user");
        }
        catch (Exception ex)
        {
            IsCompleted = true;
            IsInstalling = false;
            StatusText = $"Installation error: {ex.Message}";
            CurrentOperation = $"Error: {ex.Message}";
            AddLog(LogLevel.Error, $"Installation error: {ex.Message}");
            _logger.LogError(ex, "Installation error");
        }
    }

    private void Cancel()
    {
        _cancellationTokenSource?.Cancel();
        AddLog(LogLevel.Warning, "Cancellation requested...");
        _logger.LogInformation("Cancellation requested by user");
    }

    private void Close()
    {
        Application.Current.Shutdown();
    }

    private void OnProgressUpdate(InstallationProgress progress)
    {
        CurrentStage = progress.Stage;
        CurrentOperation = progress.CurrentOperation;
        CurrentComponent = progress.CurrentComponent;
        OverallProgress = progress.OverallProgress;
        ComponentsCompleted = progress.ComponentsCompleted;
        TotalComponents = progress.TotalComponents;

        if (progress.DownloadProgress != null)
        {
            DownloadProgress = progress.DownloadProgress.ProgressPercentage;
        }

        if (progress.ExtractionProgress != null)
        {
            ExtractionProgress = progress.ExtractionProgress.ProgressPercentage;
        }

        // Update status text based on stage
        StatusText = progress.Stage switch
        {
            InstallationStage.Initializing => "Initializing installation...",
            InstallationStage.Downloading => $"Downloading {progress.CurrentComponent}...",
            InstallationStage.Extracting => $"Extracting {progress.CurrentComponent}...",
            InstallationStage.Configuring => "Configuring environment...",
            InstallationStage.CreatingShortcuts => "Creating shortcuts...",
            InstallationStage.RegisteringUninstaller => "Registering uninstaller...",
            InstallationStage.Completed => "Installation completed!",
            InstallationStage.Failed => "Installation failed!",
            _ => progress.CurrentOperation
        };
    }

    private void OnLogEntryAdded(object? sender, LogEntry logEntry)
    {
        Application.Current.Dispatcher.Invoke(() =>
        {
            LogEntries.Add(logEntry);
            
            // Auto-scroll to bottom (handled by UI)
            // Limit log entries to prevent memory issues
            while (LogEntries.Count > 1000)
            {
                LogEntries.RemoveAt(0);
            }
        });
    }

    private void AddLog(LogLevel level, string message)
    {
        var entry = new LogEntry
        {
            Timestamp = DateTime.Now,
            Level = level,
            Message = message
        };
        LogEntries.Add(entry);
    }

    #endregion

    #region INotifyPropertyChanged

    public event PropertyChangedEventHandler? PropertyChanged;

    protected virtual void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }

    protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }

    #endregion
}

/// <summary>
/// Log entry for the details view
/// </summary>
public class LogEntry
{
    public DateTime Timestamp { get; set; }
    public LogLevel Level { get; set; }
    public string Message { get; set; } = string.Empty;

    public string FormattedTime => Timestamp.ToString("HH:mm:ss.fff");
    public string LevelText => Level.ToString().ToUpper();
}

/// <summary>
/// Simple log service for UI logging
/// </summary>
public static class LogService
{
    public static event EventHandler<LogEntry>? LogEntryAdded;

    public static void Log(LogLevel level, string message)
    {
        var entry = new LogEntry
        {
            Timestamp = DateTime.Now,
            Level = level,
            Message = message
        };
        LogEntryAdded?.Invoke(null, entry);
    }

    public static void Info(string message) => Log(LogLevel.Information, message);
    public static void Warning(string message) => Log(LogLevel.Warning, message);
    public static void Error(string message) => Log(LogLevel.Error, message);
    public static void Debug(string message) => Log(LogLevel.Debug, message);
}

/// <summary>
/// Simple relay command implementation
/// </summary>
public class RelayCommand : ICommand
{
    private readonly Func<Task> _executeAsync;
    private readonly Action _execute;
    private readonly Func<bool> _canExecute;

    public RelayCommand(Func<Task> executeAsync, Func<bool>? canExecute = null)
    {
        _executeAsync = executeAsync ?? throw new ArgumentNullException(nameof(executeAsync));
        _canExecute = canExecute ?? (() => true);
    }

    public RelayCommand(Action execute, Func<bool>? canExecute = null)
    {
        _execute = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute ?? (() => true);
    }

    public event EventHandler? CanExecuteChanged;

    public bool CanExecute(object? parameter) => _canExecute();

    public async void Execute(object? parameter)
    {
        if (_executeAsync != null)
            await _executeAsync();
        else
            _execute?.Invoke();
    }

    public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}