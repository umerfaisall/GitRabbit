from pydantic import BaseModel

class ChangedFile(BaseModel):
    filename: str
    status : str # added / modified / removed
    changed_functions : list[str]

class DiffParserOutput(BaseModel):
    pr_id : int
    commit_sha : str
    repo: str
    files : list[ChangedFile]
    