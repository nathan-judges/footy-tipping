"""GitHub API commit helper for baked data updates."""

from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubConfig:
    token: str
    repo: str
    branch: str
    bot_name: str = "tipping-bot[bot]"
    bot_email: str = "tipping-bot@users.noreply.github.com"


def _request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method=method,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "footy-tipping-bot",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _safe_request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    try:
        return _request(method=method, url=url, token=token, body=body)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub API error ({exc.code}) for {url}") from exc


def _sha_for_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _get_ref(config: GitHubConfig) -> str:
    data = _safe_request(
        method="GET",
        url=f"https://api.github.com/repos/{config.repo}/git/ref/heads/{config.branch}",
        token=config.token,
    )
    return data["object"]["sha"]


def _get_commit(config: GitHubConfig, sha: str) -> dict:
    return _safe_request(
        method="GET",
        url=f"https://api.github.com/repos/{config.repo}/git/commits/{sha}",
        token=config.token,
    )


def _get_file_content(config: GitHubConfig, path: str) -> str | None:
    try:
        data = _request(
            method="GET",
            url=f"https://api.github.com/repos/{config.repo}/contents/{path}?ref={config.branch}",
            token=config.token,
        )
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"GitHub file fetch error ({exc.code}) for {path}") from exc
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content


def _create_blob(config: GitHubConfig, content: str) -> str:
    data = _safe_request(
        method="POST",
        url=f"https://api.github.com/repos/{config.repo}/git/blobs",
        token=config.token,
        body={"content": content, "encoding": "utf-8"},
    )
    return data["sha"]


def _create_tree(config: GitHubConfig, base_tree_sha: str, files: dict[str, str]) -> str:
    tree = []
    for path, content in files.items():
        tree.append(
            {
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": _create_blob(config, content),
            }
        )
    data = _safe_request(
        method="POST",
        url=f"https://api.github.com/repos/{config.repo}/git/trees",
        token=config.token,
        body={"base_tree": base_tree_sha, "tree": tree},
    )
    return data["sha"]


def _create_commit(config: GitHubConfig, parent_sha: str, tree_sha: str, message: str) -> str:
    data = _safe_request(
        method="POST",
        url=f"https://api.github.com/repos/{config.repo}/git/commits",
        token=config.token,
        body={
            "message": message,
            "tree": tree_sha,
            "parents": [parent_sha],
            "author": {"name": config.bot_name, "email": config.bot_email},
            "committer": {"name": config.bot_name, "email": config.bot_email},
        },
    )
    return data["sha"]


def _update_ref(config: GitHubConfig, sha: str, force: bool = False) -> None:
    _safe_request(
        method="PATCH",
        url=f"https://api.github.com/repos/{config.repo}/git/refs/heads/{config.branch}",
        token=config.token,
        body={"sha": sha, "force": force},
    )


def commit_baked_files(config: GitHubConfig, files: dict[str, str], message: str) -> str:
    """
    Commit baked files with latest-SHA targeting.

    Returns "skipped" if content is unchanged, otherwise commit SHA.
    """
    unchanged = True
    for path, content in files.items():
        existing = _get_file_content(config, path)
        if existing is None or _sha_for_content(existing) != _sha_for_content(content):
            unchanged = False
            break
    if unchanged:
        return "skipped"

    for attempt in range(2):
        ref_sha = _get_ref(config)
        parent_commit = _get_commit(config, ref_sha)
        base_tree_sha = parent_commit["tree"]["sha"]
        tree_sha = _create_tree(config, base_tree_sha, files)
        commit_sha = _create_commit(config, ref_sha, tree_sha, message)
        try:
            _update_ref(config, commit_sha, force=False)
            return commit_sha
        except RuntimeError:
            if attempt == 1:
                raise
    raise RuntimeError("Commit failed after retries")
