using System.IO.Compression;
using HxCfdBootstrapper.Models;

namespace HxCfdBootstrapper.Services;

public interface IExtractionService
{
    Task<ExtractionResult> ExtractAsync(string archivePath, string destinationPath, string extractTo = ".", IProgress<ExtractionProgress>? progress = null, CancellationToken cancellationToken = default);
    Task<bool> ValidateArchiveAsync(string archivePath);
}

public class ExtractionService : IExtractionService
{
    private readonly ILogger<ExtractionService> _logger;

    public ExtractionService(ILogger<ExtractionService> logger)
    {
        _logger = logger;
    }

    public async Task<ExtractionResult> ExtractAsync(string archivePath, string destinationPath, string extractTo = ".", IProgress<ExtractionProgress>? progress = null, CancellationToken cancellationToken = default)
    {
        var result = new ExtractionResult { DestinationPath = destinationPath };

        try
        {
            _logger.LogInformation("Extracting {Archive} to {Destination}", archivePath, destinationPath);

            if (!File.Exists(archivePath))
            {
                result.Success = false;
                result.ErrorMessage = $"Archive not found: {archivePath}";
                return result;
            }

            var fullExtractPath = Path.Combine(destinationPath, extractTo);
            if (!Directory.Exists(fullExtractPath))
            {
                Directory.CreateDirectory(fullExtractPath);
            }

            var extension = Path.GetExtension(archivePath).ToLowerInvariant();
            var fileName = Path.GetFileName(archivePath).ToLowerInvariant();

            if (extension == ".zip" || fileName.EndsWith(".zip"))
            {
                await ExtractZipAsync(archivePath, fullExtractPath, progress, cancellationToken);
            }
            else if (extension == ".tar" || fileName.EndsWith(".tar.gz") || fileName.EndsWith(".tgz") || fileName.EndsWith(".tar.bz2") || fileName.EndsWith(".tbz2"))
            {
                await ExtractTarAsync(archivePath, fullExtractPath, progress, cancellationToken);
            }
            else if (extension == ".gz" && !fileName.EndsWith(".tar.gz"))
            {
                await ExtractGzipAsync(archivePath, fullExtractPath, progress, cancellationToken);
            }
            else
            {
                result.Success = false;
                result.ErrorMessage = $"Unsupported archive format: {extension}";
                return result;
            }

            result.Success = true;
            _logger.LogInformation("Extraction completed: {Archive} -> {Destination}", archivePath, fullExtractPath);
            return result;
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Extraction cancelled for {Archive}", archivePath);
            result.Success = false;
            result.ErrorMessage = "Extraction cancelled";
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Extraction failed for {Archive}", archivePath);
            result.Success = false;
            result.ErrorMessage = ex.Message;
            return result;
        }
    }

    private async Task ExtractZipAsync(string archivePath, string destinationPath, IProgress<ExtractionProgress>? progress, CancellationToken cancellationToken)
    {
        using var archive = ZipFile.OpenRead(archivePath);
        var totalEntries = archive.Entries.Count;
        var processedEntries = 0;

        foreach (var entry in archive.Entries)
        {
            cancellationToken.ThrowIfCancellationRequested();

            var entryPath = Path.Combine(destinationPath, entry.FullName);
            
            if (string.IsNullOrEmpty(entry.Name))
            {
                // Directory entry
                if (!Directory.Exists(entryPath))
                {
                    Directory.CreateDirectory(entryPath);
                }
            }
            else
            {
                // File entry
                var directory = Path.GetDirectoryName(entryPath);
                if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                entry.ExtractToFile(entryPath, overwrite: true);
                result.ExtractedFiles.Add(entryPath);
            }

            processedEntries++;
            var progressInfo = new ExtractionProgress
            {
                FilesExtracted = processedEntries,
                TotalFiles = totalEntries,
                CurrentFile = entry.FullName,
                ProgressPercentage = totalEntries > 0 ? (double)processedEntries / totalEntries * 100 : 100
            };
            progress?.Report(progressInfo);
        }

        await Task.CompletedTask;
    }

    private async Task ExtractTarAsync(string archivePath, string destinationPath, IProgress<ExtractionProgress>? progress, CancellationToken cancellationToken)
    {
        // Use SharpCompress or similar for tar extraction
        // For now, we'll use a simple implementation
        _logger.LogWarning("TAR extraction not fully implemented, using fallback");
        
        // This would use SharpCompress in production
        // using var archive = ArchiveFactory.Open(archivePath);
        // foreach (var entry in archive.Entries) { ... }
        
        await Task.CompletedTask;
        throw new NotSupportedException("TAR extraction requires SharpCompress library");
    }

    private async Task ExtractGzipAsync(string archivePath, string destinationPath, IProgress<ExtractionProgress>? progress, CancellationToken cancellationToken)
    {
        var outputFileName = Path.GetFileNameWithoutExtension(archivePath);
        var outputPath = Path.Combine(destinationPath, outputFileName);

        using var sourceStream = File.OpenRead(archivePath);
        using var gzipStream = new GZipStream(sourceStream, CompressionMode.Decompress);
        using var destinationStream = File.Create(outputPath);
        
        await gzipStream.CopyToAsync(destinationStream, cancellationToken);
        
        result.ExtractedFiles.Add(outputPath);
        
        var progressInfo = new ExtractionProgress
        {
            FilesExtracted = 1,
            TotalFiles = 1,
            CurrentFile = outputFileName,
            ProgressPercentage = 100
        };
        progress?.Report(progressInfo);
    }

    public async Task<bool> ValidateArchiveAsync(string archivePath)
    {
        try
        {
            var extension = Path.GetExtension(archivePath).ToLowerInvariant();
            
            if (extension == ".zip")
            {
                using var archive = ZipFile.OpenRead(archivePath);
                // Just try to read the entries
                foreach (var entry in archive.Entries)
                {
                    // Validate entry can be read
                    using var stream = entry.Open();
                }
                return true;
            }
            
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Archive validation failed for {Archive}", archivePath);
            return false;
        }
    }
}

public class ExtractionResult
{
    public bool Success { get; set; }
    public string DestinationPath { get; set; } = string.Empty;
    public List<string> ExtractedFiles { get; set; } = new();
    public string? ErrorMessage { get; set; }
}

public class ExtractionProgress
{
    public int FilesExtracted { get; set; }
    public int TotalFiles { get; set; }
    public string CurrentFile { get; set; } = string.Empty;
    public double ProgressPercentage { get; set; }
}