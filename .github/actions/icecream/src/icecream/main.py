"""Usage:
  main.py <gh-wiki-repo-url> <wiki-page-title>

Arguments:
  gh-wiki-repo-url   GitHub wiki repository URL
  wiki-page-title    Title of the wiki page to retrieve

Options:
  -h --help          Show this screen.
"""

from docopt import docopt
from icecream import GitHubRepo, GitHubWiki

REPO_LINK = "https://github.com/cds-snc/notification-terraform.git"

def main():
    # Get arguments from the command line
    arguments = docopt(__doc__)

    # Extract the values of gh-wiki-repo-url and wiki-page-title parameters
    gh_wiki_repo_url = arguments["<gh-wiki-repo-url>"]
    wiki_page_title = arguments["<wiki-page-title>"]

    # Do something with the arguments
    print(f"GitHub Wiki Repository URL: {gh_wiki_repo_url}")
    print(f"Wiki Page Title: {wiki_page_title}")

    gh = GitHubRepo("access", REPO_LINK)
    content = gh.get_repo_content()
    print("content: ", content)


if __name__ == "__main__":
    main()
