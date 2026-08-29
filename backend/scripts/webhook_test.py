import hashlib, hmac, json, urllib.request

secret = b"testsecret123"
body = json.dumps({
    "action": "opened",
    "pull_request": {
        "number": 1,
        "head": {"sha": "abc123def456"},
    },
    "repository": {"full_name": "acme/widgets"},
}).encode()
sig = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

req = urllib.request.Request(
    "http://localhost:8000/api/webhook/github",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-Hub-Signature-256": sig,
        "X-GitHub-Event": "pull_request",
    },
)
print(urllib.request.urlopen(req).read())
