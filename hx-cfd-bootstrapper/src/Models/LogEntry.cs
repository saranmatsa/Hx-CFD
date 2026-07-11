using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace HxCfdBootstrapper.Models;

/// <summary>
/// Represents a log entry for UI display
/// </summary>
public class LogEntry : INotifyPropertyChanged
{
    private DateTime _timestamp;
    private LogLevel _level;
    private string _message = string.Empty;

    public DateTime Timestamp
    {
        get => _timestamp;
        set => SetProperty(ref _timestamp, value);
    }

    public LogLevel Level
    {
        get => _level;
        set => SetProperty(ref _level, value);
    }

    public string Message
    {
        get => _message;
        set => SetProperty(ref _message, value);
    }

    public string FormattedTime => Timestamp.ToString("HH:mm:ss.fff");

    public string LevelText => Level switch
    {
        LogLevel.Trace => "TRACE",
        LogLevel.Debug => "DEBUG",
        LogLevel.Information => "INFO",
        LogLevel.Warning => "WARN",
        LogLevel.Error => "ERROR",
        LogLevel.Critical => "CRIT",
        _ => Level.ToString().ToUpper()
    };

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
}

/// <summary>
/// Static service for logging to UI
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
    public static void Warn(string message) => Log(LogLevel.Warning, message);
    public static void Error(string message) => Log(LogLevel.Error, message);
    public static void Debug(string message) => Log(LogLevel.Debug, message);
}