"""Explicitly authorized Knowledge Pack Git release and rollback workflow.

No command runs implicitly. A human first reviews the generated diff, creates a
short-lived HMAC-protected approval, and then separately confirms publication.
Only the configured Knowledge Pack directory is staged and committed.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .knowledge_pack import load_knowledge_pack
from .knowledge_pack_diff import generate_publication_diff


APPROVAL_VERSION = 1
APPROVAL_TTL = timedelta(hours=24)


def _canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _key_from_env(env_name: str) -> bytes:
    value = os.environ.get(env_name, "")
    if len(value) < 32:
        raise ValueError(f"{env_name} must contain at least 32 characters")
    return value.encode("utf-8")


def _diff_identity(current_path: str | Path, candidate_path: str | Path) -> tuple[dict, dict]:
    current = load_knowledge_pack(current_path)
    candidate = load_knowledge_pack(candidate_path)
    diff = generate_publication_diff(current, candidate)
    if diff["change_count"] < 1:
        raise ValueError("candidate pack contains no publishable changes")
    return diff, {
        "current_manifest_sha256": current.manifest_sha256,
        "candidate_manifest_sha256": candidate.manifest_sha256,
        "candidate_pack_version": candidate.pack_version,
        "diff_sha256": hashlib.sha256(_canonical(diff)).hexdigest(),
    }


def create_approval(current_path: str | Path, candidate_path: str | Path, *,
                    reviewer: str, key: bytes, confirm_diff: bool,
                    confirm_rights: bool, now: datetime | None = None) -> dict:
    if confirm_diff is not True or confirm_rights is not True:
        raise ValueError("explicit diff and rights review confirmations are required")
    if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 120:
        raise ValueError("reviewer must be non-empty bounded text")
    diff, identity = _diff_identity(current_path, candidate_path)
    created = now or datetime.now(timezone.utc)
    if created.tzinfo is None:
        raise ValueError("approval timestamp must be timezone-aware")
    payload = {
        "approval_version": APPROVAL_VERSION,
        "reviewer": reviewer.strip(),
        "created_at": created.astimezone(timezone.utc).isoformat(),
        "expires_at": (created.astimezone(timezone.utc) + APPROVAL_TTL).isoformat(),
        **identity,
        "change_count": diff["change_count"],
        "human_confirmed_diff_review": True,
        "human_confirmed_rights_review": True,
    }
    return {"payload": payload, "hmac_sha256": hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()}


def verify_approval(approval: dict, current_path: str | Path, candidate_path: str | Path, *,
                    key: bytes, now: datetime | None = None) -> dict:
    if not isinstance(approval, dict) or set(approval) != {"payload", "hmac_sha256"}:
        raise ValueError("invalid approval envelope")
    payload = approval["payload"]
    if not isinstance(payload, dict) or not hmac.compare_digest(
        str(approval["hmac_sha256"]), hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()
    ):
        raise ValueError("publication approval signature is invalid")
    if payload.get("approval_version") != APPROVAL_VERSION:
        raise ValueError("unsupported publication approval version")
    if payload.get("human_confirmed_diff_review") is not True or payload.get("human_confirmed_rights_review") is not True:
        raise ValueError("required human approval gates are missing")
    try:
        expires = datetime.fromisoformat(payload["expires_at"])
        created = datetime.fromisoformat(payload["created_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("approval timestamps are invalid") from exc
    instant = now or datetime.now(timezone.utc)
    if expires.tzinfo is None or created.tzinfo is None or instant >= expires or created > instant:
        raise ValueError("publication approval is expired or has an invalid timestamp")
    _, identity = _diff_identity(current_path, candidate_path)
    for key_name, value in identity.items():
        if payload.get(key_name) != value:
            raise ValueError(f"approval no longer matches the reviewed pack: {key_name}")
    return payload


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["git", *args], cwd=repo, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result


def _validate_branch(branch: str):
    if not isinstance(branch, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,200}", branch):
        raise ValueError("invalid branch name")
    if ".." in branch or branch.endswith("/") or branch.endswith("."):
        raise ValueError("invalid branch name")


def publish_pack(repo_path: str | Path, candidate_path: str | Path, target_relative: str, *,
                 approval_path: str | Path, branch: str, expected_head: str,
                 key: bytes, confirm_publish: bool) -> dict:
    if confirm_publish is not True:
        raise ValueError("publication requires explicit --confirm-publish")
    _validate_branch(branch)
    if not re.fullmatch(r"[0-9a-f]{40,64}", expected_head):
        raise ValueError("expected_head must be a full Git commit SHA")
    repo = Path(repo_path).resolve()
    top = Path(_git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if repo != top:
        raise ValueError("repo_path must be the Git worktree root")
    target = (repo / target_relative).resolve()
    if not target.is_relative_to(repo) or target == repo or Path(repo / target_relative).is_symlink():
        raise ValueError("publication target must be a non-symlink path inside the repository")
    if not target.is_dir():
        raise ValueError("current published Knowledge Pack directory does not exist")
    if _git(repo, "status", "--porcelain", "--untracked-files=all").stdout.strip():
        raise ValueError("Git worktree must be completely clean before publication")
    current_branch = _git(repo, "branch", "--show-current").stdout.strip()
    if current_branch != branch:
        raise ValueError("checked-out branch does not match the explicitly selected release branch")
    actual_head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    if actual_head != expected_head:
        raise ValueError("Git HEAD changed since the expected-head review")
    approval = json.loads(Path(approval_path).read_text(encoding="utf-8"))
    payload = verify_approval(approval, target, candidate_path, key=key)
    candidate = Path(candidate_path).resolve()
    if candidate == target or candidate.is_relative_to(target) or target.is_relative_to(candidate):
        raise ValueError("candidate and published target must be separate directories")
    stage = Path(tempfile.mkdtemp(prefix=".knowledge-release-", dir=target.parent))
    staged_pack = stage / "pack"
    backup = stage / "backup"
    moved_old = False
    committed = False
    relative = target.relative_to(repo).as_posix()
    try:
        shutil.rmtree(staged_pack, ignore_errors=True)
        shutil.copytree(candidate_path, staged_pack, symlinks=True)
        load_knowledge_pack(staged_pack)
        os.replace(target, backup)
        moved_old = True
        try:
            os.replace(staged_pack, target)
        except Exception:
            os.replace(backup, target)
            moved_old = False
            raise
        _git(repo, "add", "--", relative)
        staged = _git(repo, "diff", "--cached", "--quiet", check=False)
        if staged.returncode == 0:
            raise ValueError("no staged Knowledge Pack changes remain")
        if staged.returncode != 1:
            raise RuntimeError("unable to inspect staged Git changes")
        changed = _git(repo, "diff", "--cached", "--name-only").stdout.splitlines()
        if not changed or any(not (name == relative or name.startswith(relative + "/")) for name in changed):
            raise ValueError("release staging escaped the configured Knowledge Pack directory")
        _git(repo, "commit", "-m", f"publish: Knowledge Pack {payload['candidate_pack_version']}")
        committed = True
        commit_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
        push = _git(repo, "push", f"--force-with-lease=refs/heads/{branch}:{expected_head}",
                    "origin", f"HEAD:refs/heads/{branch}", check=False)
        if push.returncode:
            raise RuntimeError(f"local publication commit {commit_sha} was created but push failed: {push.stderr.strip()}")
        return {"published": True, "commit_sha": commit_sha, "branch": branch,
                "target": relative, "candidate_manifest_sha256": payload["candidate_manifest_sha256"],
                "rollback_command_requires_explicit_confirmation": True}
    except Exception:
        if not committed:
            try:
                _git(repo, "reset", "--", relative, check=False)
            except Exception:
                pass
            if moved_old and backup.exists():
                if target.exists():
                    shutil.rmtree(target)
                os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def rollback_pack(repo_path: str | Path, commit_sha: str, *, branch: str,
                 expected_head: str, confirm_rollback: bool, target_relative: str = "knowledge") -> dict:
    if confirm_rollback is not True:
        raise ValueError("rollback requires explicit --confirm-rollback")
    _validate_branch(branch)
    if not re.fullmatch(r"[0-9a-f]{40,64}", commit_sha) or not re.fullmatch(r"[0-9a-f]{40,64}", expected_head):
        raise ValueError("commit and expected head must be full Git commit SHAs")
    repo = Path(repo_path).resolve()
    if Path(_git(repo, "rev-parse", "--show-toplevel").stdout.strip()).resolve() != repo:
        raise ValueError("repo_path must be the Git worktree root")
    if _git(repo, "branch", "--show-current").stdout.strip() != branch:
        raise ValueError("checked-out branch does not match selected rollback branch")
    if _git(repo, "rev-parse", "HEAD").stdout.strip() != expected_head:
        raise ValueError("Git HEAD changed since rollback review")
    if _git(repo, "status", "--porcelain", "--untracked-files=all").stdout.strip():
        raise ValueError("Git worktree must be completely clean before rollback")
    parents = _git(repo, "rev-list", "--parents", "-n", "1", commit_sha).stdout.split()
    if len(parents) != 2:
        raise ValueError("rollback currently supports only single-parent commits")
    _git(repo, "merge-base", "--is-ancestor", commit_sha, expected_head)
    target_path = Path(target_relative)
    if target_path.is_absolute() or ".." in target_path.parts or not target_path.parts:
        raise ValueError("rollback target must be a safe repository-relative path")
    target_name = target_path.as_posix()
    changed = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha).stdout.splitlines()
    if not changed or any(not (name == target_name or name.startswith(target_name + "/")) for name in changed):
        raise ValueError("rollback commit must change only the configured Knowledge Pack directory")
    _git(repo, "revert", "--no-edit", commit_sha)
    revert_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    push = _git(repo, "push", f"--force-with-lease=refs/heads/{branch}:{expected_head}",
                "origin", f"HEAD:refs/heads/{branch}", check=False)
    if push.returncode:
        raise RuntimeError(f"local rollback commit {revert_sha} was created but push failed: {push.stderr.strip()}")
    return {"rolled_back": True, "revert_commit_sha": revert_sha, "reverted_commit_sha": commit_sha,
            "branch": branch}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-env", default="IELTS_PUBLICATION_APPROVAL_KEY")
    sub = parser.add_subparsers(dest="command", required=True)
    approve = sub.add_parser("approve")
    approve.add_argument("--current", required=True)
    approve.add_argument("--candidate", required=True)
    approve.add_argument("--approval-file", required=True)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--confirm-diff", action="store_true")
    approve.add_argument("--confirm-rights", action="store_true")
    publish = sub.add_parser("publish")
    publish.add_argument("--repo", required=True)
    publish.add_argument("--candidate", required=True)
    publish.add_argument("--target", default="knowledge")
    publish.add_argument("--approval-file", required=True)
    publish.add_argument("--branch", required=True)
    publish.add_argument("--expected-head", required=True)
    publish.add_argument("--confirm-publish", action="store_true")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("--repo", required=True)
    rollback.add_argument("--commit", required=True)
    rollback.add_argument("--branch", required=True)
    rollback.add_argument("--expected-head", required=True)
    rollback.add_argument("--target", default="knowledge")
    rollback.add_argument("--confirm-rollback", action="store_true")
    args = parser.parse_args(argv)
    try:
        key = _key_from_env(args.key_env)
        if args.command == "approve":
            diff, _ = _diff_identity(args.current, args.candidate)
            print(json.dumps(diff, ensure_ascii=False, indent=2))
            approval = create_approval(args.current, args.candidate, reviewer=args.reviewer,
                                       key=key, confirm_diff=args.confirm_diff,
                                       confirm_rights=args.confirm_rights)
            destination = Path(args.approval_file)
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=".approval-", dir=destination.parent)
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(approval, handle, ensure_ascii=False, sort_keys=True, indent=2)
                    handle.write("\n")
                os.replace(temp_name, destination)
            except Exception:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
                raise
            print(json.dumps({"approval_created": str(destination), "expires_at": approval["payload"]["expires_at"]}))
        elif args.command == "publish":
            print(json.dumps(publish_pack(args.repo, args.candidate, args.target,
                approval_path=args.approval_file, branch=args.branch, expected_head=args.expected_head,
                key=key, confirm_publish=args.confirm_publish), indent=2))
        else:
            print(json.dumps(rollback_pack(args.repo, args.commit, branch=args.branch,
                expected_head=args.expected_head, confirm_rollback=args.confirm_rollback,
                target_relative=args.target), indent=2))
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
