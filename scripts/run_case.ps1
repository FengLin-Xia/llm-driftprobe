param(
  [Parameter(Mandatory=$true)]
  [string]$CaseId,

  [Parameter(Mandatory=$false)]
  [string]$Model = "anthropic/claude-3.7-sonnet",

  [Parameter(Mandatory=$false)]
  [string]$Provider = "openrouter",

  [Parameter(Mandatory=$false)]
  [string]$CondaEnv = "city-marl",

  [Parameter(Mandatory=$false)]
  [int]$Phase = 3
)

$ErrorActionPreference = "Stop"

conda run -n $CondaEnv python ".\\scripts\\run_single_case.py" --case-id $CaseId --provider $Provider --model $Model --phase $Phase

