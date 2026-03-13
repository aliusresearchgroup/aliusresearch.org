param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
  [string]$DocsDir = "docs",
  [string]$StaticDir = "site-src\static",
  [string]$ReportPath = "migration\unused-static-assets.csv"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "..\migrate\Migration.Common.ps1")

$docsRoot = Join-Path $RepoRoot $DocsDir
$staticRoot = Join-Path $RepoRoot $StaticDir
$reportFullPath = Join-Path $RepoRoot $ReportPath

if (-not (Test-Path -LiteralPath $docsRoot -PathType Container)) { throw "Docs dir not found: $docsRoot" }
if (-not (Test-Path -LiteralPath $staticRoot -PathType Container)) { throw "Static dir not found: $staticRoot" }

$projectBasePath = ""
$siteConfigPath = Join-Path $RepoRoot "site-src\data\site.json"
if (Test-Path -LiteralPath $siteConfigPath) {
  try {
    $siteConfig = Get-Content -LiteralPath $siteConfigPath -Raw | ConvertFrom-Json
    $projectBasePath = [string]$siteConfig.github_pages_project_base_path
  } catch {
    Write-Warning "Could not read site config for project base path: $_"
  }
}

$referenceableExtensions = @(
  ".html", ".htm", ".css", ".js", ".json", ".xml", ".txt", ".svg"
)

$referenced = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($docFile in Get-ChildItem -LiteralPath $docsRoot -Recurse -File) {
  if ($referenceableExtensions -notcontains $docFile.Extension.ToLowerInvariant()) { continue }
  $relDoc = Get-RelativePathUnix -Root $docsRoot -Path $docFile.FullName
  $content = Read-TextFileSafe -Path $docFile.FullName
  foreach ($resolved in (Get-ResolvedLocalUrlCandidatesFromText -Text $content -DocumentRelativePath $relDoc -ProjectBasePath $projectBasePath)) {
    [void]$referenced.Add($resolved)
  }
}

$rows = New-Object System.Collections.Generic.List[object]
foreach ($asset in Get-ChildItem -LiteralPath $staticRoot -Recurse -File) {
  $relStatic = Get-RelativePathUnix -Root $staticRoot -Path $asset.FullName
  if ($relStatic -match '(^|/)\.prev-\d{8}-\d{6}(/|$)') { continue }

  $isReferenced = $referenced.Contains($relStatic)
  $rows.Add([pscustomobject]@{
    referenced = $isReferenced
    bytes = [int64]$asset.Length
    ext = if ([string]::IsNullOrWhiteSpace($asset.Extension)) { "(none)" } else { $asset.Extension.ToLowerInvariant() }
    path = $relStatic
  })
}

$unused = @($rows | Where-Object { -not $_.referenced } | Sort-Object -Property @{ Expression = 'bytes'; Descending = $true }, @{ Expression = 'path'; Descending = $false })
Ensure-Directory -Path (Split-Path -Parent $reportFullPath)
$unused | Export-Csv -LiteralPath $reportFullPath -NoTypeInformation -Encoding UTF8

$totalFiles = $rows.Count
$unusedFiles = ($unused | Measure-Object).Count
$unusedMeasure = @($unused | Measure-Object -Property bytes -Sum)
$unusedBytes = if (($unusedMeasure | Measure-Object).Count -gt 0 -and $null -ne $unusedMeasure[0]) {
  if ($null -eq $unusedMeasure[0].Sum) { 0 } else { [int64]$unusedMeasure[0].Sum }
} else {
  0
}
$unusedMb = [math]::Round(($unusedBytes / 1MB), 2)

Write-Output "Wrote unused static asset report: $reportFullPath"
Write-Output ("Static files scanned: {0}" -f $totalFiles)
Write-Output ("Unused files: {0}" -f $unusedFiles)
Write-Output ("Potential archive savings: {0} MB ({1} bytes)" -f $unusedMb, $unusedBytes)

$topUnused = @($unused | Select-Object -First 20)
if (($topUnused | Measure-Object).Count -gt 0) {
  Write-Output ""
  Write-Output "Top unused assets:"
  $topUnused | ForEach-Object {
    Write-Output ("  {0,10}  {1}" -f $_.bytes, $_.path)
  }
}
