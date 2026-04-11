param([string]$Url,[string]$OutFile)
$ErrorActionPreference = 'Stop'
$edge='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if (-not (Test-Path $edge)) { throw "Edge not found: $edge" }
$outAbs = [System.IO.Path]::GetFullPath($OutFile)
$outDir = Split-Path -Parent $outAbs
if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
if (Test-Path $outAbs) { Remove-Item $outAbs -Force }
$ud=Join-Path $env:TEMP ("alius-edge-headless-profile-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $ud | Out-Null
$stdout = [System.IO.Path]::ChangeExtension($outAbs, '.stdout.log')
$stderr = [System.IO.Path]::ChangeExtension($outAbs, '.stderr.log')
if (Test-Path $stdout) { Remove-Item $stdout -Force }
if (Test-Path $stderr) { Remove-Item $stderr -Force }
try {
  $args = @(
    "--user-data-dir=$ud"
    "--headless"
    "--disable-gpu"
    "--hide-scrollbars"
    "--no-first-run"
    "--no-default-browser-check"
    "--window-size=1366,1200"
    "--virtual-time-budget=10000"
    "--screenshot=$outAbs"
    $Url
  )
  $p = Start-Process -FilePath $edge -ArgumentList $args -PassThru -Wait -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  Write-Output ("Edge exit code: " + $p.ExitCode)
  Write-Output ("Screenshot exists: " + (Test-Path $outAbs))
  if (Test-Path $outAbs) { Write-Output ("Screenshot bytes: " + (Get-Item $outAbs).Length) }
  if (Test-Path $stderr) {
    $errContent = Get-Content $stderr -Raw -ErrorAction SilentlyContinue
    if (-not [string]::IsNullOrWhiteSpace($errContent)) {
      Write-Output 'STDERR:'
      Write-Output $errContent
    }
  }
}
finally {
  try { Remove-Item -LiteralPath $ud -Recurse -Force -ErrorAction SilentlyContinue } catch {}
}
