import pytest

from scripts.lib.github_commit import GitHubConfig, commit_baked_files


def test_commit_baked_files_retries_ref_update_once(monkeypatch: pytest.MonkeyPatch) -> None:
    config = GitHubConfig(token="token", repo="owner/repo", branch="main")
    files = {"data/current_round_tips.json": '{"ok": true}\n'}

    monkeypatch.setattr("scripts.lib.github_commit._get_file_content", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("scripts.lib.github_commit._get_ref", lambda *_args, **_kwargs: "parent-sha")
    monkeypatch.setattr(
        "scripts.lib.github_commit._get_commit",
        lambda *_args, **_kwargs: {"tree": {"sha": "base-tree-sha"}},
    )
    monkeypatch.setattr("scripts.lib.github_commit._create_tree", lambda *_args, **_kwargs: "tree-sha")
    monkeypatch.setattr("scripts.lib.github_commit._create_commit", lambda *_args, **_kwargs: "commit-sha")

    calls = {"count": 0}

    def fake_update_ref(*_args, **_kwargs) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("simulated ref race")

    monkeypatch.setattr("scripts.lib.github_commit._update_ref", fake_update_ref)
    commit_sha = commit_baked_files(config=config, files=files, message="test")

    assert commit_sha == "commit-sha"
    assert calls["count"] == 2
