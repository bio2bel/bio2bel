import os

from github import Github

BIO2BEL_DIRECTORY = os.path.join(os.path.expanduser('~'), 'dev', 'biobel')
os.makedirs(BIO2BEL_DIRECTORY, exist_ok=True)


def main():
    g = Github()
    r = g.get_organization('bio2bel')

    repo_urls = sorted(
        repo.git_url
        for repo in r.get_repos()
        if (
            not repo.name.startswith('bio2bel')
            and not os.path.exists(os.path.join(BIO2BEL_DIRECTORY, repo.name))
        )
    )

    for url in repo_urls:
        command = f'cd {BIO2BEL_DIRECTORY}; git clone {url}'
        print(command)
        os.system(command)


if __name__ == '__main__':
    main()
