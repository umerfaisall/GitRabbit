from app.services.github_client import get_pr_files, get_file_content
from app.services.github_auth import post_installation_token
import re
import ast
from app.models.diff import DiffParserOutput,ChangedFile
import requests


def parser_patch(patch: str) -> list[tuple[int, int]]:
    lines = patch.splitlines()
    hunkHeader = []
    for line in lines :
        match = re.match(
            r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",
            line 
            )
        if match:
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1
            new_end = new_start + new_count - 1
            hunkHeader.append((new_start, new_end))

    return hunkHeader

def find_changed_functions(file_content, changed_ranges):
    tree = ast.parse(file_content)
    changed_functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_start, func_end = node.lineno, node.end_lineno
            for change_start, change_end in changed_ranges:
                if change_start <= func_end and func_start <= change_end:
                    changed_functions.append(node.name)
                    break  # already matched, no need to check other ranges

    return changed_functions


def DiffParser(owner, repo, pr_number, commit_sha) -> DiffParserOutput:
    prFiles = get_pr_files(owner, repo, pr_number)
    token = post_installation_token()
    changed_files = []

    for file in prFiles:
        fileName = file["filename"]
        status = file["status"]

        patch = file.get("patch")
        changed_ranges = parser_patch(patch) if patch else []

        changed_functions = []
        if changed_ranges and status != "removed" and fileName.endswith(".py"):
            file_content = get_file_content(owner, repo, fileName, commit_sha, token)
            changed_functions = find_changed_functions(file_content, changed_ranges)

        changed_files.append(
            ChangedFile(
                filename=fileName,
                status=status,
                changed_functions=changed_functions,
            )
        )

    return DiffParserOutput(
        pr_id=pr_number,
        commit_sha=commit_sha,
        repo=repo,
        files=changed_files,
    )