using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows;
using System.Windows.Input;
using HxCfdBootstrapper.Models;
using HxCfdBootstrapper.Services;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;

namespace HxCfdBootstrapper;

/// <summary>
/// Interaction logic for MainWindow.xaml
/// </summary>
public partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;

    public MainWindow(MainViewModel viewModel)
    {
        InitializeComponent();
        _viewModel = viewModel;
        DataContext = _viewModel;
        
        // Handle window closing
        Closing += MainWindow_Closing;
        
        // Load version info
        Loaded += MainWindow_Loaded;
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        // Auto-start installation if configured
        if (_viewModel.AutoStartInstallation)
        {
            await _viewModel.InstallAsync();
        }
    }

    private void MainWindow_Closing(object? sender, CancelEventArgs e)
    {
        if (_viewModel.IsInstalling && !_viewModel.IsCompleted)
        {
            var result = MessageBox.Show(
                "Installation is in progress. Are you sure you want to cancel?",
                "Confirm Cancel",
                MessageBoxButton.YesNo,
                MessageBoxImage.Question);

            if (result == MessageBoxResult.No)
            {
                e.Cancel = true;
                return;
            }

            _viewModel.Cancel();
        }
    }
}

/// <summary>
/// Main ViewModel for the bootstrapper UI
/// </summary>
public class MainViewModel : INotifyPropertyChanged
{
    private readonly IInstallationService _installationService;
    private readonly ILogger<MainViewModel> _logger;
    private readonly AppSettings _settings;
    private readonly ILaunchService _launchService;

    private InstallationStage _currentStage = InstallationStage.Initializing;
    private string _currentOperation = "Ready to install";
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
    private string _statusText = "Ready to install HxCFD";
    private ObservableCollection<LogEntry> _logEntries = new();
    private CancellationTokenSource? _cancellationTokenSource;
    private InstallationResult? _lastResult;

    public MainViewModel(
        IInstallationService installationService,
        ILaunchService launchService,
        ILogger<MainViewModel> logger,
        IOptions<AppSettings> settings)
    {
        _installationService = installationService;
        _launchService = launchService;
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
        set => SetProperty(ref _isInstalling, value);
    }

    public bool IsCompleted
    {
        get => _isCompleted;
        set => SetProperty(ref _isCompleted, value);
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

    public string ApplicationVersion => _settings.ApplicationVersion;

    public bool AutoStartInstallation => _settings.AutoStartInstallation;

    #endregion

    #region Commands

    public ICommand InstallCommand { get; }
    public ICommand CancelCommand { get; }
    public ICommand CloseCommand { get; }
    public ICommand ToggleDetailsCommand { get; }

    #endregion

    #region Public Methods

    public async Task InstallAsync()
    {
        if (IsInstalling) return;

        IsInstalling = true;
        IsCompleted = false;
        IsCancelled = false;
        OverallProgress = 0;
        DownloadProgress = 0;
        ExtractionProgress = 0;
        ComponentsCompleted = 0;
        LogEntries.Clear();

        _cancellationTokenSource = new CancellationTokenSource();
        var progress = new Progress<InstallationProgress>(OnProgressUpdate);

        try
        {
            _logger.LogInformation("Starting installation...");
            AddLog(LogLevel.Information, "Starting HxCFD installation...");

            _lastResult = await _installationService.InstallAsync(progress, _cancellationTokenSource.Token);

            if (_lastResult.Success)
            {
                _logger.LogInformation("Installation completed successfully");
                AddLog(LogLevel.Information, "Installation completed successfully!");
                
                CurrentStage = InstallationStage.Completed;
                CurrentOperation = "Installation complete";
                OverallProgress = 100;
                IsCompleted = true;
                StatusText = "Installation completed successfully";

                // Auto-launch if configured
                if (_settings.AutoLaunchAfterInstall && !string.IsNullOrEmpty(_lastResult.InstallPath))
                {
                    await LaunchApplicationAsync(_lastResult.InstallPath);
                }
            }
            else
            {
                _logger.LogError("Installation failed: {Error}", _lastResult.ErrorMessage);
                AddLog(LogLevel.Error, $"Installation failed: {_lastResult.ErrorMessage}");
                
                CurrentStage = InstallationStage.Failed;
                CurrentOperation = "Installation failed";
                IsCompleted = true;
                IsCancelled = true;
                StatusText = $"Installation failed: {_lastResult.ErrorMessage}";
            }
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("Installation cancelled by user");
            AddLog(LogLevel.Warning, "Installation cancelled by user");
            
            CurrentStage = InstallationStage.Cancelled;
            CurrentOperation = "Installation cancelled";
            IsCancelled = true;
            IsCompleted = true;
            StatusText = "Installation cancelled";
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Installation failed with exception");
            AddLog(LogLevel.Error, $"Installation failed: {ex.Message}");
            
            CurrentStage = InstallationStage.Failed;
            CurrentOperation = "Installation failed";
            IsCompleted = true;
            IsCancelled = true;
            StatusText = $"Installation failed: {ex.Message}";
        }
        finally
        {
            IsInstalling = false;
            _cancellationTokenSource?.Dispose();
            _cancellationTokenSource = null;
            
            // Refresh command states
            (InstallCommand as RelayCommand)?.RaiseCanExecuteChanged();
            (CancelCommand as RelayCommand)?.RaiseCanExecuteChanged();
            (CloseCommand as RelayCommand)?.RaiseCanExecuteChanged();
        }
    }

    public void Cancel()
    {
        _cancellationTokenSource?.Cancel();
        AddLog(LogLevel.Warning, "Cancelling installation...");
    }

    public void Close()
    {
        Application.Current.Shutdown();
    }

    #endregion

    #region Private Methods

    private void OnProgressUpdate(InstallationProgress progress)
    {
        Application.Current.Dispatcher.Invoke(() =>
        {
            CurrentStage = progress.Stage;
            CurrentOperation = progress.CurrentOperation;
            CurrentComponent = progress.CurrentComponent;
            OverallProgress = progress.OverallProgress;
            DownloadProgress = progress.DownloadProgress;
            ExtractionProgress = progress.ExtractionProgress;
            ComponentsCompleted = progress.ComponentsCompleted;
            TotalComponents = progress.TotalComponents;
            StatusText = progress.StatusText;
        });
    }

    private async Task LaunchApplicationAsync(string installPath)
    {
        try
        {
            AddLog(LogLevel.Information, "Launching HxCFD...");
            var launchResult = await _launchService.LaunchAsync(new LaunchInfo
            {
                ExecutablePath = Path.Combine(installPath, "hx-cfd.exe"),
                WorkingDirectory = installPath,
                WaitForExit = false
            });

            if (launchResult.Success)
            {
                AddLog(LogLevel.Information, $"HxCFD launched successfully (PID: {launchResult.ProcessId})");
            }
            else
            {
                AddLog(LogLevel.Warning, $"Failed to launch HxCFD: {launchResult.ErrorMessage}");
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to launch application");
            AddLog(LogLevel.Error, $"Failed to launch: {ex.Message}");
        }
    }

    private void OnLogEntryAdded(object? sender, LogEntry entry)
    {
        Application.Current.Dispatcher.Invoke(() =>
        {
            LogEntries.Add(entry);
            
            // Auto-scroll to bottom (handled by TextBox binding)
            if (LogEntries.Count > 1000)
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
        {
            await _executeAsync();
        }
        else
        {
            _execute();
        }
    }

    public void RaiseCanExecuteChanged()
    {
        CanExecuteChanged?.Invoke(this, EventArgs.Empty);
    }
}