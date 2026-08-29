from pydantic import BaseModel

class PrEvent(BaseModel):
    pr_id: int
    commit_sha: str
    repo: str
    action: str

    @classmethod
    def from_payload(cls, payload: dict) -> "PrEvent":
        return cls(
            pr_id=payload["pull_request"]["number"],
            commit_sha=payload["pull_request"]["head"]["sha"],
            repo=payload["repository"]["full_name"],
            action=payload["action"],
        )
