#!/usr/bin/env python3

from dataclasses import dataclass
from github import Github
from github.ContentFile import ContentFile
from github.Repository import Repository
from typing import Iterable


class GitHubRepo:
    def __init__(self, access_token: str, repo_link: str) -> None:
        self._gh = Github(access_token)
        self._repo = self._gh.get_repo(repo_link)

    def get_repo_content(self) -> Iterable[ContentFile]:
        files = []
        contents = self._repo.get_contents("")
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(self._repo.get_contents(file_content.path))
            else:
                files.append(file_content)

        return filter(lambda f: f.name.endswith(".tf"), files)

class GitHubWiki:
    pass
