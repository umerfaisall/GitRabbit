import sys

from app.services.github_client import get_pr_files

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("usage: uv run python scripts/test_github_client.py <owner> <repo> <pr_number>")
        sys.exit(1)

    owner, repo, pr_number = sys.argv[1], sys.argv[2], int(sys.argv[3])
    files = get_pr_files(owner, repo, pr_number)

    print(f"{len(files)} file(s) changed:")
    for f in files:
        print(f" - {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})")
