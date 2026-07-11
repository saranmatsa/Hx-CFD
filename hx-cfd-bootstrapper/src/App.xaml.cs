using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using HxCfdBootstrapper.Models;
using HxCfdBootstrapper.Services;

namespace HxCfdBootstrapper;

/// <summary>
/// Interaction logic for App.xaml
/// </summary>
public partial class App : Application
{
    private IHost? _host;

    public IServiceProvider Services => _host?.Services ?? throw new InvalidOperationException("Host not initialized");

    protected override async void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        _host = CreateHostBuilder(e.Args).Build();

        // Initialize services
        await _host.StartAsync();

        // Show main window
        var mainWindow = _host.Services.GetRequiredService<MainWindow>();
        mainWindow.Show();
    }

    protected override async void OnExit(ExitEventArgs e)
    {
        if (_host != null)
        {
            await _host.StopAsync(TimeSpan.FromSeconds(5));
            _host.Dispose();
        }
        base.OnExit(e);
    }

    private static IHostBuilder CreateHostBuilder(string[] args) =>
        Host.CreateDefaultBuilder(args)
            .ConfigureAppConfiguration((context, config) =>
            {
                config.SetBasePath(AppContext.BaseDirectory);
                config.AddJsonFile("appsettings.json", optional: false, reloadOnChange: true);
                config.AddJsonFile($"appsettings.{context.HostingEnvironment.EnvironmentName}.json", optional: true);
                config.AddCommandLine(args);
            })
            .ConfigureServices((context, services) =>
            {
                // Configuration
                services.Configure<AppSettings>(context.Configuration.GetSection("AppSettings"));
                services.Configure<ComponentManifest>(context.Configuration.GetSection("ComponentManifest"));

                // Logging
                services.AddLogging(builder =>
                {
                    builder.ClearProviders();
                    builder.AddConfiguration(context.Configuration.GetSection("Logging"));
                    builder.AddDebug();
                    builder.AddConsole();
                });

                // Services
                services.AddSingleton<IDownloadService, DownloadService>();
                services.AddSingleton<IExtractionService, ExtractionService>();
                services.AddSingleton<IShortcutService, ShortcutService>();
                services.AddSingleton<IUninstallService, UninstallService>();
                services.AddSingleton<ILaunchService, LaunchService>();
                services.AddSingleton<IInstallationService, InstallationService>();

                // UI
                services.AddSingleton<MainWindow>();
                services.AddSingleton<MainViewModel>();
            })
            .UseConsoleLifetime();
}