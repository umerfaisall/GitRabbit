from app.config import get_settings
import jwt
import time
import requests

settings = get_settings()
def get_installation_token() -> str:

    with open(settings.github_private_key_path, "r") as f:
        privateKey = f.read()
    appID = settings.github_app_id
    now = int(time.time())

    payload = {
    "iat": now - 60,  # backdated to tolerate clock drift vs GitHub's servers
    "exp": now + 600,  # 10 minutes
    "iss": appID,
    }

    token = jwt.encode(
    payload,
    privateKey,
    algorithm="RS256"
    )
    return token 
    

def post_installation_token() :
    jwtToken = get_installation_token()
    installationId = settings.github_installation_id
    url = f'https://api.github.com/app/installations/{installationId}/access_tokens'
    headers = { "Authorization": f"Bearer {jwtToken}", 
               "Accept": "application/vnd.github+json", 
               }
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()["token"]


if __name__ == "__main__":
    token = post_installation_token()
    print("got token:", token[:10] + "...")