param(
    [string]$Root = (Join-Path $PSScriptRoot "..\docs"),
    [int[]]$CandidatePorts = @(8080, 8081, 8090, 5500, 5501),
    [switch]$AutoOpen
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-MimeType {
    param([string]$Path)

    $ext = [IO.Path]::GetExtension($Path).ToLowerInvariant()
    switch ($ext) {
        ".html" { "text/html; charset=utf-8" }
        ".htm"  { "text/html; charset=utf-8" }
        ".css"  { "text/css; charset=utf-8" }
        ".js"   { "application/javascript; charset=utf-8" }
        ".json" { "application/json; charset=utf-8" }
        ".txt"  { "text/plain; charset=utf-8" }
        ".xml"  { "application/xml; charset=utf-8" }
        ".svg"  { "image/svg+xml" }
        ".png"  { "image/png" }
        ".jpg"  { "image/jpeg" }
        ".jpeg" { "image/jpeg" }
        ".gif"  { "image/gif" }
        ".webp" { "image/webp" }
        ".ico"  { "image/x-icon" }
        ".mp4"  { "video/mp4" }
        ".webm" { "video/webm" }
        ".mp3"  { "audio/mpeg" }
        ".wav"  { "audio/wav" }
        ".ogg"  { "audio/ogg" }
        ".pdf"  { "application/pdf" }
        ".woff" { "font/woff" }
        ".woff2" { "font/woff2" }
        ".ttf"  { "font/ttf" }
        ".otf"  { "font/otf" }
        default { "application/octet-stream" }
    }
}

function Write-Response {
    param(
        [System.Net.HttpListenerResponse]$Response,
        [int]$StatusCode,
        [string]$Body,
        [string]$ContentType = "text/plain; charset=utf-8"
    )

    $bytes = [Text.Encoding]::UTF8.GetBytes($Body)
    $Response.StatusCode = $StatusCode
    $Response.ContentType = $ContentType
    $Response.ContentLength64 = $bytes.Length
    $Response.OutputStream.Write($bytes, 0, $bytes.Length)
    $Response.OutputStream.Close()
}

$rootFull = [IO.Path]::GetFullPath($Root)
if (-not (Test-Path -LiteralPath $rootFull -PathType Container)) {
    throw "Site root not found: $rootFull"
}

$projectBasePath = ""
$siteConfigPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\site-src\data\site.json"))
if (Test-Path -LiteralPath $siteConfigPath) {
    try {
        $siteConfig = Get-Content -LiteralPath $siteConfigPath -Raw | ConvertFrom-Json
        $bp = [string]$siteConfig.github_pages_project_base_path
        if (-not [string]::IsNullOrWhiteSpace($bp)) {
            $bp = $bp.Replace("\", "/").Trim()
            if (-not $bp.StartsWith("/")) { $bp = "/" + $bp }
            $bp = $bp.TrimEnd("/")
            if ($bp -ne "/") { $projectBasePath = $bp }
        }
    } catch {}
}

$listener = $null
$selectedPort = $null

foreach ($port in $CandidatePorts) {
    $candidate = New-Object System.Net.HttpListener
    $candidate.Prefixes.Add("http://127.0.0.1:$port/")
    $candidate.Prefixes.Add("http://localhost:$port/")
    try {
        $candidate.Start()
        $listener = $candidate
        $selectedPort = $port
        break
    }
    catch {
        try { $candidate.Close() } catch {}
    }
}

if (-not $listener) {
    throw "Unable to start preview server. Tried ports: $($CandidatePorts -join ', ')"
}

$url = "http://127.0.0.1:$selectedPort/"
$urlFile = Join-Path $env:TEMP "aliusresearch-preview-url.txt"
Set-Content -LiteralPath $urlFile -Value $url -Encoding UTF8

Write-Host "Alius Research preview server"
Write-Host "Root: $rootFull"
Write-Host "URL : $url"
Write-Host "Press Ctrl+C to stop."

if ($AutoOpen) {
    try { Start-Process $url | Out-Null } catch {}
}

try {
    while ($listener.IsListening) {
        try {
            $context = $listener.GetContext()
        }
        catch [System.Net.HttpListenerException] {
            break
        }

        $request = $context.Request
        $response = $context.Response
        $response.Headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        $response.Headers["Pragma"] = "no-cache"
        $response.Headers["Expires"] = "0"

        $requestPath = [Uri]::UnescapeDataString($request.Url.AbsolutePath)
        if ([string]::IsNullOrWhiteSpace($requestPath)) {
            $requestPath = "/"
        }
        if (-not [string]::IsNullOrWhiteSpace($projectBasePath)) {
            if ($requestPath -eq $projectBasePath) {
                $requestPath = "/"
            }
            elseif ($requestPath.StartsWith($projectBasePath + "/")) {
                $requestPath = $requestPath.Substring($projectBasePath.Length)
                if ([string]::IsNullOrWhiteSpace($requestPath)) { $requestPath = "/" }
            }
        }

        try {
            $relative = $requestPath.TrimStart("/").Replace("/", "\")
            $target = Join-Path $rootFull $relative

            if (Test-Path -LiteralPath $target -PathType Container) {
                $target = Join-Path $target "index.html"
            }
            elseif (-not (Test-Path -LiteralPath $target -PathType Leaf) -and -not [IO.Path]::GetExtension($target)) {
                $htmlTarget = "$target.html"
                if (Test-Path -LiteralPath $htmlTarget -PathType Leaf) {
                    $target = $htmlTarget
                }
            }

            $targetFull = [IO.Path]::GetFullPath($target)
            if (-not $targetFull.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) {
                Write-Host ("403 {0}" -f $request.Url.AbsolutePath)
                Write-Response -Response $response -StatusCode 403 -Body "Forbidden"
                continue
            }

            if (-not (Test-Path -LiteralPath $targetFull -PathType Leaf)) {
                Write-Host ("404 {0}" -f $request.Url.AbsolutePath)
                Write-Response -Response $response -StatusCode 404 -Body "Not Found"
                continue
            }

            $fileInfo = Get-Item -LiteralPath $targetFull
            $fileLength = [int64]$fileInfo.Length
            $rangeHeader = [string]$request.Headers["Range"]
            $rangeStart = [int64]0
            $rangeEnd = [int64]($fileLength - 1)
            $isPartial = $false

            if (-not [string]::IsNullOrWhiteSpace($rangeHeader)) {
                if ($rangeHeader -match '^bytes=(\d*)-(\d*)$') {
                    $startText = $Matches[1]
                    $endText = $Matches[2]

                    if ([string]::IsNullOrWhiteSpace($startText) -and -not [string]::IsNullOrWhiteSpace($endText)) {
                        $suffixLength = [int64]$endText
                        if ($suffixLength -gt 0) {
                            $rangeStart = [Math]::Max([int64]0, $fileLength - $suffixLength)
                        }
                    }
                    elseif (-not [string]::IsNullOrWhiteSpace($startText)) {
                        $rangeStart = [int64]$startText
                        if (-not [string]::IsNullOrWhiteSpace($endText)) {
                            $rangeEnd = [Math]::Min([int64]$endText, $fileLength - 1)
                        }
                    }

                    if ($rangeStart -lt 0 -or $rangeStart -ge $fileLength -or $rangeEnd -lt $rangeStart) {
                        $response.StatusCode = 416
                        $response.Headers["Content-Range"] = "bytes */$fileLength"
                        $response.OutputStream.Close()
                        Write-Host ("416 {0}" -f $request.Url.AbsolutePath)
                        continue
                    }
                    $isPartial = $true
                }
            }

            $response.StatusCode = if ($isPartial) { 206 } else { 200 }
            $response.ContentType = Get-MimeType -Path $targetFull
            $response.Headers["Accept-Ranges"] = "bytes"
            if ($isPartial) {
                $response.Headers["Content-Range"] = "bytes $rangeStart-$rangeEnd/$fileLength"
            }
            $response.ContentLength64 = $rangeEnd - $rangeStart + 1

            Write-Host ("{0} {1}" -f $response.StatusCode, $request.Url.AbsolutePath)

            if ($request.HttpMethod -ne "HEAD") {
                $stream = [IO.File]::OpenRead($targetFull)
                try {
                    if ($rangeStart -gt 0) {
                        [void]$stream.Seek($rangeStart, [IO.SeekOrigin]::Begin)
                    }
                    $buffer = New-Object byte[] 65536
                    $remaining = $rangeEnd - $rangeStart + 1
                    while ($remaining -gt 0) {
                        $toRead = [int][Math]::Min($buffer.Length, $remaining)
                        $read = $stream.Read($buffer, 0, $toRead)
                        if ($read -le 0) { break }
                        $response.OutputStream.Write($buffer, 0, $read)
                        $remaining -= $read
                    }
                }
                finally {
                    $stream.Dispose()
                }
            }

            $response.OutputStream.Close()
        }
        catch {
            try {
                if (-not $response.OutputStream.CanWrite) {
                    continue
                }
                Write-Host ("500 {0} :: {1}" -f $request.Url.AbsolutePath, $_.Exception.Message)
                Write-Response -Response $response -StatusCode 500 -Body "Internal Server Error"
            }
            catch {}
        }
    }
}
finally {
    if ($listener) {
        try { $listener.Stop() } catch {}
        try { $listener.Close() } catch {}
    }
}
