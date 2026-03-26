param(
  [Parameter(Mandatory=$true)]
  [string[]]$Models,

  [Parameter(Mandatory=$false)]
  [string[]]$Cases = @("A01","B01","C01","D01"),

  [Parameter(Mandatory=$false)]
  [string]$Provider = "openrouter",

  [Parameter(Mandatory=$false)]
  [string]$CondaEnv = "city-marl",

  [Parameter(Mandatory=$false)]
  [int]$Phase = 3
)

$ErrorActionPreference = "Stop"

conda run -n $CondaEnv python ".\\scripts\\run_model_suite.py" --provider $Provider --models $Models --cases $Cases --phase $Phase

