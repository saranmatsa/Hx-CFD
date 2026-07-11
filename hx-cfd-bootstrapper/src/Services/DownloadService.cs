using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using HxCfdBootstrapper.Models;

namespace HxCfdBootstrapper.Services;

public interface IDownloadService
{
    Task<DownloadResult> DownloadAsync(string url, string destinationPath, string expectedSha256, long expectedSize, IProgress<DownloadProgress>? progress = null, CancellationToken cancellationToken = default);
    Task<bool> VerifyChecksumAsync(string filePath, string expectedSha256);
}

public class DownloadService : IDownloadService
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<DownloadService> _logger;

    public DownloadService(HttpClient httpClient, ILogger<DownloadService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
        _httpClient.Timeout = TimeSpan.FromMinutes(30);
    }

    public async Task<DownloadResult> DownloadAsync(string url, string destinationPath, string expectedSha256, long expectedSize, IProgress<DownloadProgress>? progress = null, CancellationToken cancellationToken = default)
    {
        var result = new DownloadResult { DestinationPath = destinationPath };

        try
        {
            _logger.LogInformation("Starting download from {Url} to {Path}", url, destinationPath);

            var directory = Path.GetDirectoryName(destinationPath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            using var response = await _httpClient.GetAsync(url, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
            response.EnsureSuccessStatusCode();

            var totalBytes = response.Content.Headers.ContentLength ?? expectedSize;
            var buffer = new byte[81920];
            var totalRead = 0L;
            var lastReportTime = DateTime.UtcNow;

            using var fileStream = new FileStream(destinationPath, FileMode.Create, FileAccess.Write, FileShare.None, bufferSize: 81920, useAsync: true);
            using var contentStream = await response.Content.ReadAsStreamAsync(cancellationToken);

            while (true)
            {
                var bytesRead = await contentStream.ReadAsync(buffer, cancellationToken);
                if (bytesRead == 0) break;

                await fileStream.WriteAsync(buffer.AsMemory(0, bytesRead), cancellationToken);
                totalRead += bytesRead;

                var now = DateTime.UtcNow;
                if ((now - lastReportTime).TotalMilliseconds >= 100 || totalRead == totalBytes)
                {
                    var progressInfo = new DownloadProgress
                    {
                        BytesDownloaded = totalRead,
                        TotalBytes = totalBytes,
                        ProgressPercentage = totalBytes > 0 ? (double)totalRead / totalBytes * 100 : 0,
                        SpeedBytesPerSecond = CalculateSpeed(totalRead, now)
                    };
                    progress?.Report(progressInfo);
                    lastReportTime = now;
                }
            }

            await fileStream.FlushAsync(cancellationToken);

            _logger.LogInformation("Download completed: {Path} ({Size} bytes)", destinationPath, totalRead);

            // Verify checksum
            var isValid = await VerifyChecksumAsync(destinationPath, expectedSha256);
            if (!isValid)
            {
                result.Success = false;
                result.ErrorMessage = "Checksum verification failed";
                _logger.LogError("Checksum verification failed for {Path}", destinationPath);
                File.Delete(destinationPath);
                return result;
            }

            // Verify size
            var fileInfo = new FileInfo(destinationPath);
            if (expectedSize > 0 && fileInfo.Length != expectedSize)
            {
                result.Success = false;
                result.ErrorMessage = $"Size mismatch: expected {expectedSize}, got {fileInfo.Length}";
                _logger.LogError("Size mismatch for {Path}: expected {Expected}, got {Actual}", destinationPath, expectedSize, fileInfo.Length);
                File.Delete(destinationPath);
                return result;
            }

            result.Success = true;
            result.BytesDownloaded = totalRead;
            return result;
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Download cancelled for {Url}", url);
            result.Success = false;
            result.ErrorMessage = "Download cancelled";
            if (File.Exists(destinationPath)) File.Delete(destinationPath);
            return result;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Download failed for {Url}", url);
            result.Success = false;
            result.ErrorMessage = ex.Message;
            if (File.Exists(destinationPath)) File.Delete(destinationPath);
            return result;
        }
    }

    public async Task<bool> VerifyChecksumAsync(string filePath, string expectedSha256)
    {
        try
        {
            using var sha256 = SHA256.Create();
            using var stream = File.OpenRead(filePath);
            var hash = await sha256.ComputeHashAsync(stream);
            var actualSha256 = Convert.ToHexString(hash).ToLowerInvariant();
            var expected = expectedSha256.ToLowerInvariant();

            return actualSha256 == expected;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Checksum verification failed for {Path}", filePath);
            return false;
        }
    }

    private double CalculateSpeed(long bytesRead, DateTime now)
    {
        // Simplified speed calculation - in a real implementation, track time windows
        return bytesRead / Math.Max(1, (now - DateTime.UtcNow.AddSeconds(-1)).TotalSeconds);
    }
}

public class DownloadResult
{
    public bool Success { get; set; }
    public string DestinationPath { get; set; } = string.Empty;
    public long BytesDownloaded { get; set; }
    public string? ErrorMessage { get; set; }
}

public class DownloadProgress
{
    public long BytesDownloaded { get; set; }
    public long TotalBytes { get; set; }
    public double ProgressPercentage { get; set; }
    public double SpeedBytesPerSecond { get; set; }
    public TimeSpan EstimatedTimeRemaining => SpeedBytesPerSecond > 0 
        ? TimeSpan.FromSeconds((TotalBytes - BytesDownloaded) / SpeedBytesPerSecond) 
        : TimeSpan.Zero;
}