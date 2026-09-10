param(
    [Parameter(Mandatory=$true)][int]$PriorProcessId,
    [Parameter(Mandatory=$true)][string]$Commit
)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if ($Commit -notmatch '^[a-f0-9]{40}$') { throw 'Expected full commit SHA' }
$taskRemote=(& git remote get-url origin).Trim()
if ($taskRemote -ne 'https://github.com/heyanLE/music_jlpt.git') { throw 'Unexpected remote; refusing upload' }
$taskStatusPath=Join-Path $taskRoot 'transfer/upload-status.local.json'
$taskLogPath=Join-Path $taskRoot 'transfer/upload-progress.local.log'
function Set-TaskStatus([string]$State,[string]$Detail) {
    $taskRecord=@{state=$State;commit=$Commit;remote=$taskRemote;detail=$Detail;updatedAt=[DateTime]::UtcNow.ToString('o')}
    [System.IO.File]::WriteAllText($taskStatusPath,($taskRecord|ConvertTo-Json),[System.Text.UTF8Encoding]::new($false))
}
try {
    Set-TaskStatus 'waiting-current-transfer' 'Waiting for the already-running initial push; no parallel LFS transfer.'
    $taskPrior=Get-Process -Id $PriorProcessId -ErrorAction SilentlyContinue
    if ($taskPrior) {
        if ($taskPrior.ProcessName -ne 'git') { throw 'Prior process is not the expected git push' }
        Wait-Process -InputObject $taskPrior
    }
    Set-TaskStatus 'pushing-final-commit' 'Finite push of the pinned reviewed commit; LFS hooks enabled. No force and no quota purchase.'
    $env:GIT_LFS_FORCE_PROGRESS='1'
    & git push --progress origin "${Commit}:refs/heads/main" *> $taskLogPath
    if ($LASTEXITCODE -ne 0) { throw ('Git/LFS push failed with exit '+$LASTEXITCODE+'; inspect private local progress log. No further retries scheduled.') }
    $taskRemoteLine=& git ls-remote origin refs/heads/main
    if ($LASTEXITCODE -ne 0 -or -not $taskRemoteLine -or ($taskRemoteLine -split '\s+')[0] -ne $Commit) {
        throw 'Remote main verification failed; completion not established'
    }
    Set-TaskStatus 'complete' 'Git push including LFS hooks succeeded and remote main equals the pinned commit. On destination run git lfs pull and git lfs fsck.'
} catch {
    Set-TaskStatus 'failed' $_.Exception.Message
    exit 1
}
