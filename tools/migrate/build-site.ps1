param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
  [string]$DocsOut = "docs",
  [string]$SiteSrc = "site-src",
  [switch]$CleanDocs
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "Migration.Common.ps1")

$siteSrcPath = Join-Path $RepoRoot $SiteSrc
$dataRoot = Join-Path $siteSrcPath "data"
$staticRoot = Join-Path $siteSrcPath "static"
$docsRoot = Join-Path $RepoRoot $DocsOut
$migrationRoot = Join-Path $RepoRoot "migration"
Ensure-Directory -Path $migrationRoot

$projectBasePath = ""
$customDomain = ""
$siteConfigPath = Join-Path $dataRoot "site.json"
if (Test-Path -LiteralPath $siteConfigPath) {
  try {
    $siteConfig = Get-Content -LiteralPath $siteConfigPath -Raw | ConvertFrom-Json
    $projectBasePath = [string]$siteConfig.github_pages_project_base_path
    $customDomain = [string]$siteConfig.github_pages_custom_domain
  } catch {
    Write-Warning "Could not read site config for project base path: $_"
  }
}

if ($CleanDocs -and (Test-Path -LiteralPath $docsRoot)) {
  $stamp = (Get-Date).ToString("yyyyMMdd-HHmmss")
  $backupDocs = Join-Path $RepoRoot ("docs-prev-" + $stamp)
  try {
    Rename-Item -LiteralPath $docsRoot -NewName (Split-Path -Leaf $backupDocs)
  } catch {
    Write-Warning "Could not rename existing docs output; proceeding without cleanup. $_"
  }
}
Ensure-Directory -Path $docsRoot

# Copy static assets into docs root.
if (Test-Path -LiteralPath $staticRoot) {
  Get-ChildItem -LiteralPath $staticRoot -Recurse -File | ForEach-Object {
    $rel = Get-RelativePathUnix -Root $staticRoot -Path $_.FullName
    if ($rel -match '(^|/)[^/]+\.prev-\d{8}-\d{6}(/|$)') {
      return
    }
    $dest = Join-Path $docsRoot ($rel -replace "/", "\")
    Copy-FilePreserveTimestamp -SourcePath $_.FullName -DestinationPath $dest
  }
}

# Copy human-facing page assets from the top-level source folders into clean
# public asset folders. These folders mirror the live navigation structure while
# docs/ remains generated GitHub Pages output.
$sectionAssetRoots = @(
  @{ Source = "Shared\assets"; Destination = "assets\shared" },
  @{ Source = "Home\assets"; Destination = "assets\home" },
  @{ Source = "About\assets"; Destination = "assets\about" },
  @{ Source = "Team\assets"; Destination = "assets\team" },
  @{ Source = "Bulletin\assets"; Destination = "assets\bulletin" },
  @{ Source = "Journal Clubs\assets"; Destination = "assets\journal-clubs" },
  @{ Source = "Events\assets"; Destination = "assets\events" },
  @{ Source = "Membership\assets"; Destination = "assets\membership" }
)

foreach ($assetRoot in $sectionAssetRoots) {
  $sourcePath = Join-Path $RepoRoot $assetRoot.Source
  if (-not (Test-Path -LiteralPath $sourcePath)) {
    continue
  }
  Get-ChildItem -LiteralPath $sourcePath -Recurse -File | ForEach-Object {
    $rel = Get-RelativePathUnix -Root $sourcePath -Path $_.FullName
    $dest = Join-Path $docsRoot (($assetRoot.Destination + "/" + $rel) -replace "/", "\")
    Copy-FilePreserveTimestamp -SourcePath $_.FullName -DestinationPath $dest
  }
}

$pages = Get-Content -LiteralPath (Join-Path $dataRoot "pages.json") -Raw | ConvertFrom-Json
$pages = @($pages) | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.status) -or [string]$_.status -eq "published" }
$rewrittenIndexPath = Join-Path $migrationRoot "rewritten-page-sources.csv"
$rewrittenLookup = @{}
if (Test-Path -LiteralPath $rewrittenIndexPath) {
  foreach ($row in (Import-Csv $rewrittenIndexPath)) {
    $rewrittenLookup[[string]$row.legacy_path] = [string]$row.rewritten_html
  }
}

$pageCount = 0
foreach ($page in $pages) {
  $legacy = [string]$page.legacy_path
  $canonical = [string]$page.canonical_path
  $declaredSource = [string]$page.source_html
  $sourceRel = if (-not [string]::IsNullOrWhiteSpace($declaredSource)) {
    $declaredSource
  } elseif ($rewrittenLookup.ContainsKey($legacy)) {
    $rewrittenLookup[$legacy]
  } else {
    ""
  }
  $sourceAbs = Join-Path $siteSrcPath ($sourceRel -replace "/", "\")
  if (-not (Test-Path -LiteralPath $sourceAbs)) {
    Write-Warning "Missing source for page ${legacy}: $sourceAbs"
    continue
  }
  $html = Read-TextFileSafe -Path $sourceAbs
  $html = Optimize-PublishedHtml -Html $html
  $html = Add-ProjectBasePathToRootRelativeUrls -Text $html -BasePath $projectBasePath

  if ($canonical -eq "/") {
    $outPath = Join-Path $docsRoot "index.html"
  } else {
    $routeSegments = $canonical.Trim("/").Split("/", [System.StringSplitOptions]::RemoveEmptyEntries)
    $dir = Join-Path $docsRoot ([System.IO.Path]::Combine($routeSegments))
    $outPath = Join-Path $dir "index.html"
  }

  Write-TextFileUtf8NoBom -Path $outPath -Content $html
  $pageCount++
}

Write-TextFileUtf8NoBom -Path (Join-Path $docsRoot ".nojekyll") -Content ""
if (-not [string]::IsNullOrWhiteSpace($customDomain)) {
  Write-TextFileUtf8NoBom -Path (Join-Path $docsRoot "CNAME") -Content ($customDomain.Trim())
}

& (Join-Path $PSScriptRoot "generate-redirects.ps1") -RepoRoot $RepoRoot -DocsOut $DocsOut -SiteSrc $SiteSrc | Out-Null

if (-not [string]::IsNullOrWhiteSpace((Normalize-ProjectBasePath -BasePath $projectBasePath))) {
  # Ensure inline and external CSS assets also resolve under project Pages subpath.
  Get-ChildItem -LiteralPath $docsRoot -Recurse -Include *.css -File | ForEach-Object {
    try {
      $css = Read-TextFileSafe -Path $_.FullName
      $rewritten = Add-ProjectBasePathToRootRelativeUrls -Text $css -BasePath $projectBasePath
      if ($rewritten -ne $css) {
        Write-TextFileUtf8NoBom -Path $_.FullName -Content $rewritten
      }
    } catch {
      Write-Warning "Failed project-base rewrite for CSS $($_.FullName): $_"
    }
  }
}

# Post-process: wrap <img> in <picture> with webp <source> when sibling exists.
$wrapScript = Join-Path $RepoRoot "tools\minify\wrap-images-in-picture.py"
if (Test-Path -LiteralPath $wrapScript) {
  try {
    & python $wrapScript | Out-Null
  } catch {
    Write-Warning "Picture-element post-processing failed: $_"
  }
}

$summary = @(
  "Generated UTC: $([DateTime]::UtcNow.ToString('o'))",
  "Docs output: $docsRoot",
  "Canonical pages written: $pageCount",
  "Static root copied: $staticRoot",
  "Redirect stubs: $(if (Test-Path -LiteralPath (Join-Path $dataRoot 'redirects.json')) { (Get-Content -LiteralPath (Join-Path $dataRoot 'redirects.json') -Raw | ConvertFrom-Json).Count } else { 0 })",
  "GitHub Pages project base path: $(if ([string]::IsNullOrWhiteSpace((Normalize-ProjectBasePath -BasePath $projectBasePath))) { '(none)' } else { Normalize-ProjectBasePath -BasePath $projectBasePath })",
  "GitHub Pages custom domain: $(if ([string]::IsNullOrWhiteSpace($customDomain)) { '(none)' } else { $customDomain.Trim() })"
)
Write-LinesUtf8NoBom -Path (Join-Path $migrationRoot "build-summary.txt") -Lines $summary

Write-Output "Built canonical site into $docsRoot ($pageCount pages + static assets + redirects)"
