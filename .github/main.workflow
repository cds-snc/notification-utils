workflow "Continuous Integration" {
  on = "push"
  resolves = [
    "docker://cdssnc/seekret-github-action",
    "docker://python:3.6-alpine",
  ]
}

action "docker://cdssnc/seekret-github-action" {
  uses = "docker://cdssnc/seekret-github-action"
}

action "docker://python:3.6-alpine" {
  uses = "docker://python:3.6-alpine"
  runs = ["/bin/sh", "-c", "sh /github/workspace/scripts/bootstrap.sh && sh /github/workspace/scripts/run_tests.sh"]
}
