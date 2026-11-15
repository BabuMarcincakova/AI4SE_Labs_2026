# Task 1 report

The repository was cloned using the workspace terminal through PowerShell.
Agent (model GPT-5.6 Luna) ran:

```powershell
git clone https://github.com/Neltharion59/AI4SE_Playground Week_06_Implementation\Assignments\Task_1\AI4SE_Playground
```

This used Git's HTTPS transport to download the repository contents into the
`AI4SE_Playground` subfolder of the Task 1 assignment directory.

To prevent nested repository metadata and history conflicts with the outer
repository, the agent then removed only the cloned repository's `.git` directory:

```powershell
Remove-Item -LiteralPath Week_06_Implementation\Assignments\Task_1\AI4SE_Playground\.git -Recurse -Force
```

The clone was checked after cleanup to confirm that the repository contents
remain available and the nested `.git` directory is absent.
