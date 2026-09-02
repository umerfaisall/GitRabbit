from app.services.github_auth import post_installation_token
import requests
import time
import base64

class GitHubRateLimitError(Exception): 
    """Raised when the GitHub API rate limit is nearly exhausted.""" 
    pass

def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    installationToken = post_installation_token()
    headers = { 
        "Authorization": f"Bearer {installationToken}",
        "Accept": "application/vnd.github+json", 
    }

    url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files'
    response = requests.get(url, headers=headers)
    check_rate_limit_of_response(response)
    response.raise_for_status()
    return response.json()


def check_rate_limit_of_response(response):

    remaining = int(response.headers.get("X-RateLimit-Remaining", 0)) 
    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
    if remaining < 5:
        reset_at = time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime(reset_time) )
        raise GitHubRateLimitError(
            f"Rate limit nearly exhausted, resets at {reset_at}"
        )

    if response.status_code == 403:
        message = response.json().get("message","").lower()
        if "rate limit" in message:
            reset_at = time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime(reset_time) )
            raise GitHubRateLimitError(
                        f"Rate limit nearly exhausted, resets at {reset_at}"
            )


def get_file_content( owner: str, repo: str, file_path: str, ref: str, token: str) -> str:
    """
    Get the current content of a file from GitHub.
    """

    url = (
        "https://api.github.com/repos/"
        f"{owner}/{repo}/contents/{file_path}"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    params = {
        "ref": ref
    }

    response = requests.get(
        url,
        headers=headers,
        params=params
    )

    response.raise_for_status()

    data = response.json()

    if data.get("encoding") != "base64":
        raise ValueError(
            f"Unexpected encoding for {file_path}: "
            f"{data.get('encoding')}"
        )

    return base64.b64decode(data["content"]).decode("utf-8")