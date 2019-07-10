workflow "Continuous Integration" {
  on = "push"
  resolves = [
    "docker://cdssnc/seekret-github-action",
    "docker://python:3.6-slim-stretch",
  ]
}

action "docker://cdssnc/seekret-github-action" {
  uses = "docker://cdssnc/seekret-github-action"
}

action "docker://python:3.6-slim-stretch" {
  uses = "docker://python:3.6-slim-stretch"
  runs = ["/bin/bash", "-c", "./github/workspace/scripts/bootstrap.sh && ./github/workspace/scripts/run_tests.sh"]
}
