@echo off
REM Run in Command Prompt or PowerShell OUTSIDE your IDE to rewrite
REM the last commit with a clean message and force-push to GitHub.
cd /d "%~dp0"
for /f "delims=" %%i in ('git rev-parse "HEAD^{tree}"') do set TREE=%%i
for /f "delims=" %%i in ('git rev-parse HEAD^') do set PARENT=%%i
for /f "delims=" %%i in ('git commit-tree %TREE% -p %PARENT% -m "Add model evaluation script with train/test accuracy and confusion matrix"') do set NEW=%%i
if defined NEW (
  git reset --hard %NEW%
  git push --force origin main
  echo Done. Latest commit message:
  git log -1 --format=%%B
) else (
  echo commit-tree failed.
)
pause
