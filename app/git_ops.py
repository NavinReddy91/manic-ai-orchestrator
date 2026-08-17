"""
Actual git/GitHub operations the coder and shipper sub-agents use. Runs entirely
on the server (Celery worker) — no local machine involved. Each call operates on
a throwaway temp clone that gets deleted after push.
"""

import os
import logging
import subprocess
import httpx

logger = logging.getLogger(__name__)


def _authed_url(repo_full_name: str, token: str) -> str:
    return f"https://x-access-token:{token}@github.com/{repo_full_name}.git"


def _run(cmd: list[str], cwd: str | None = None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd[:2])}...\n{result.stderr}")
    return result.stdout


def clone_repo(
    repo_full_name: str, token: str, workdir: str, branch: str | None = None
):
    """
    If `branch` is given and already exists on the remote, clones that branch
    directly so this agent builds on top of what earlier agents already pushed.
    Returns (repo_path, branch_already_existed).
    """
    url = _authed_url(repo_full_name, token)
    dest = os.path.join(workdir, "repo")

    if branch:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", branch, url, dest],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return dest, True

    _run(["git", "clone", "--depth", "1", url, dest])
    return dest, False


def create_branch(repo_path: str, branch: str):
    _run(["git", "checkout", "-b", branch], cwd=repo_path)


def write_files(repo_path: str, files: list[dict]):
    """
    files: [{"path": "src/foo.py", "content": "..."}]

    Includes path traversal protection: rejects any path that resolves outside
    the repo directory (e.g. via "../" sequences).
    """
    real_repo = os.path.realpath(repo_path)
    for f in files:
        full_path = os.path.realpath(os.path.join(repo_path, f["path"]))
        if not full_path.startswith(real_repo + os.sep) and full_path != real_repo:
            raise ValueError(
                f"Path traversal blocked: {f['path']} resolves outside repo"
            )
        os.makedirs(os.path.dirname(full_path) or repo_path, exist_ok=True)
        with open(full_path, "w") as fh:
            fh.write(f["content"])


def commit_and_push(
    repo_path: str, branch: str, message: str, token: str, repo_full_name: str
):
    _run(["git", "add", "-A"], cwd=repo_path)
    _run(
        [
            "git",
            "-c",
            "user.email=agent@sonic-ai.com",
            "-c",
            "user.name=Sonic Agent",
            "commit",
            "-m",
            message,
        ],
        cwd=repo_path,
    )
    url = _authed_url(repo_full_name, token)
    _run(["git", "push", url, branch], cwd=repo_path)


async def open_pull_request(
    repo_full_name: str, token: str, branch: str, base: str, title: str, body: str
) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo_full_name}/pulls",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"title": title, "head": branch, "base": base, "body": body},
        )
        resp.raise_for_status()
        return resp.json()["html_url"]
