using System.Text.Json.Serialization;

namespace HxCfdBootstrapper.Models;

public class ComponentManifest
{
    [JsonPropertyName("version")]
    public string Version { get; set; } = "1.0.0";

    [JsonPropertyName("components")]
    public List<Component> Components { get; set; } = new();
}

public class Component
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("version")]
    public string Version { get; set; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; set; } = string.Empty;

    [JsonPropertyName("required")]
    public bool Required { get; set; } = true;

    [JsonPropertyName("platforms")]
    public List<string> Platforms { get; set; } = new();

    [JsonPropertyName("archives")]
    public List<ComponentArchive> Archives { get; set; } = new();

    [JsonPropertyName("dependencies")]
    public List<string> Dependencies { get; set; } = new();

    [JsonPropertyName("environmentVariables")]
    public Dictionary<string, string> EnvironmentVariables { get; set; } = new();
}

public class ComponentArchive
{
    [JsonPropertyName("url")]
    public string Url { get; set; } = string.Empty;

    [JsonPropertyName("sha256")]
    public string Sha256 { get; set; } = string.Empty;

    [JsonPropertyName("size")]
    public long Size { get; set; }

    [JsonPropertyName("extractTo")]
    public string ExtractTo { get; set; } = ".";
}

public class ComponentInstallState
{
    public string ComponentId { get; set; } = string.Empty;
    public string Version { get; set; } = string.Empty;
    public DateTime InstalledAt { get; set; } = DateTime.UtcNow;
    public List<string> ExtractedFiles { get; set; } = new();
    public Dictionary<string, string> EnvironmentVariables { get; set; } = new();
    public bool IsValid { get; set; } = true;
    public string? ErrorMessage { get; set; }
}

public class InstallationManifest
{
    public string Version { get; set; } = "1.0.0";
    public string InstallDir { get; set; } = string.Empty;
    public DateTime InstalledAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    public List<ComponentInstallState> Components { get; set; } = new();
    public Dictionary<string, string> EnvironmentVariables { get; set; } = new();
    public string UninstallString { get; set; } = string.Empty;
}