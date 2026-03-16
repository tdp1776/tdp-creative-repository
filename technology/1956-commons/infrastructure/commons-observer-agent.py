import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class Observation:
    timestamp: str
    category: str
    path: str
    summary: str


class CommonsObserverAgent:
    """
    Obi-1 — Observer Bot 001 for 1956 Commons.

    What Obi-1 does:
    - Watches the LIVE GitHub repository for changes in key Commons paths
    - Logs observations to the Commons observer log
    - Detects first external contact
    - Updates the public first-contact-report.html page
    - Maintains the Commons Census ledger

    What Obi-1 does NOT do:
    - vote
    - govern
    - alter governance outcomes
    - communicate on behalf of humans
    """

    WATCH_PATHS = [
        "technology/1956-commons/proposals",
        "technology/1956-commons/debates",
        "technology/1956-commons/votes",
        "technology/1956-commons/records",
        "technology/1956-commons/guilds",
        "technology/1956-commons/participants",
        "technology/1956-commons/constitution",
        "START-HERE.md",
        "WHY-1956-COMMONS.md",
        "AGENTS.md",
    ]

    # Add any names you consider internal / founder activity here.
    KNOWN_INTERNAL_AUTHORS = {
        "tdp1776",
        "tdp",
    }

    FIRST_CONTACT_FILE = "first-contact-report.html"
    CENSUS_FILE = "technology/1956-commons/records/commons-census.md"
    LOG_FILE = "technology/1956-commons/participants/observer-log.md"
    STATE_FILE = "technology/1956-commons/participants/observer-state.json"

    def __init__(
        self,
        repo_owner: str = "tdp1776",
        repo_name: str = "tdp-creative-repository",
        branch: str = "main",
        repo_root: str = ".",
    ) -> None:
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.repo_root = Path(repo_root).resolve()

        self.state_file = self.repo_root / self.STATE_FILE
        self.log_file = self.repo_root / self.LOG_FILE
        self.first_contact_page = self.repo_root / self.FIRST_CONTACT_FILE
        self.census_file = self.repo_root / self.CENSUS_FILE

        self.state = self._load_state()
        self.state.setdefault("known_participants", [])

    def _load_state(self) -> Dict[str, object]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                return {}
        return {}

    def _save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def _now(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def _github_commits_url(self, path: str) -> str:
        encoded_path = urllib.parse.quote(path)
        return (
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits"
            f"?sha={self.branch}&path={encoded_path}&per_page=1"
        )

    def _fetch_latest_commit(self, path: str) -> Optional[dict]:
        url = self._github_commits_url(path)
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "1956-commons-obi-1",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, list) and data:
                    return data[0]
        except Exception as exc:
            self._append_log(
                [
                    Observation(
                        timestamp=self._now(),
                        category="error",
                        path=path,
                        summary=f"GitHub polling failed for {path}: {exc}",
                    )
                ]
            )
        return None

    def _commit_author(self, commit: dict) -> str:
        commit_block = commit.get("commit", {})
        return commit_block.get("author", {}).get("name", "unknown")

    def _commit_message(self, commit: dict) -> str:
        commit_block = commit.get("commit", {})
        return commit_block.get("message", "No commit message")

    def _commit_sha(self, commit: dict) -> str:
        return commit.get("sha", "")

    def _summarize_commit(self, path: str, commit: dict) -> str:
        sha = self._commit_sha(commit)[:7]
        author = self._commit_author(commit)
        message = self._commit_message(commit).splitlines()[0]
        return f"Observed new GitHub commit in {path}: {sha} by {author} — {message}"

    def _is_external_contact(self, commit: dict) -> bool:
        author = self._commit_author(commit).strip().lower()
        internal = {name.strip().lower() for name in self.KNOWN_INTERNAL_AUTHORS}
        return author not in internal

    def _record_participant(self, author_name: str) -> None:
        current = set(self.state.get("known_participants", []))
        if author_name and author_name not in current:
            current.add(author_name)
            self.state["known_participants"] = sorted(current)

    def _count_markdown_files(self, directory: Path) -> int:
        if not directory.exists():
            return 0
        return len([p for p in directory.glob("*.md") if p.is_file()])

    def _list_guilds(self, guilds_dir: Path) -> List[str]:
        if not guilds_dir.exists():
            return []
        return sorted([p.name for p in guilds_dir.iterdir() if p.is_dir()])

    def _write_first_contact_page(self, observation: Observation, commit: dict) -> None:
        author = self._commit_author(commit)
        message = self._commit_message(commit)
        sha = self._commit_sha(commit)

        html = f"""<!DOCTYPE html>
<html>
<head>
<title>1956 Commons — First Contact Report</title>
<meta charset="UTF-8">
</head>
<body style="font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 40px; line-height: 1.6;">
<h1>1956 Commons — First Contact Report</h1>
<p><strong>Status:</strong> External contact detected.</p>
<ul>
  <li><strong>Timestamp:</strong> {observation.timestamp}</li>
  <li><strong>Author:</strong> {author}</li>
  <li><strong>Path:</strong> {observation.path}</li>
  <li><strong>Commit:</strong> {sha}</li>
  <li><strong>Message:</strong> {message}</li>
</ul>
<p>Observer Bot 001 (Obi-1) recorded the first external interaction with the Commons.</p>
</body>
</html>
"""
        self.first_contact_page.write_text(html, encoding="utf-8")

    def _write_first_contact_ledger(self, observation: Observation, commit: dict) -> None:
        ledger_file = self.repo_root / "technology/1956-commons/records/first-contact.md"
        author = self._commit_author(commit)
        message = self._commit_message(commit)
        sha = self._commit_sha(commit)

        content = f"""# 1956 Commons — First Contact Ledger

Status: External contact recorded.

## First Contact Event

Timestamp: {observation.timestamp}  
Author: {author}  
Repository Path: {observation.path}  
Commit: {sha}  

Commit Message:
{message}

---

Observer Bot: Obi-1  
Recorded automatically by the Commons observer system.
"""
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        ledger_file.write_text(content, encoding="utf-8")

    def _update_census(self) -> None:
        guilds_dir = self.repo_root / "technology/1956-commons/guilds"
        proposals_dir = self.repo_root / "technology/1956-commons/proposals"
        debates_dir = self.repo_root / "technology/1956-commons/debates"
        votes_dir = self.repo_root / "technology/1956-commons/votes"

        known_participants: Set[str] = set(self.state.get("known_participants", []))
        if "tdp1776" not in known_participants:
            known_participants.add("tdp1776")

        guild_names = self._list_guilds(guilds_dir)
        proposal_count = self._count_markdown_files(proposals_dir)
        debate_count = self._count_markdown_files(debates_dir)
        vote_count = self._count_markdown_files(votes_dir)

        participant_lines = []
        for name in sorted(known_participants):
            if name == "tdp1776":
                participant_lines.append("- tdp1776 (Founder)")
            else:
                participant_lines.append(f"- {name}")

        guild_lines = [f"- {name}" for name in guild_names] if guild_names else ["- None recorded"]

        census_text = f"""# 1956 Commons Census

Observer: Obi-1

This document records the ongoing population and activity of the 1956 Commons.

The census is automatically maintained by the Commons Observer Bot.

---

## Last Updated

{self._now()}

---

## Current Population

Population: {len(known_participants)}

Participants:

{chr(10).join(participant_lines)}

---

## Guilds

Total Guilds: {len(guild_names)}

{chr(10).join(guild_lines)}

---

## Governance Activity

Proposals Submitted: {proposal_count}  
Debates Opened: {debate_count}  
Votes Recorded: {vote_count}  

---

## Purpose

The Commons Census records the growth of the Commons society over time.

Population growth, guild formation, and governance activity are tracked as indicators of the health and evolution of the Commons ecosystem.
"""

        self.census_file.parent.mkdir(parents=True, exist_ok=True)
        self.census_file.write_text(census_text, encoding="utf-8")

    def _append_log(self, observations: List[Observation]) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.write_text("# Commons Observer Log\n\n", encoding="utf-8")

        with self.log_file.open("a", encoding="utf-8") as f:
            for obs in observations:
                f.write(f"## {obs.timestamp}\n")
                f.write(f"- Category: {obs.category}\n")
                f.write(f"- Path: {obs.path}\n")
                f.write(f"- Observation: {obs.summary}\n\n")

    def observe_once(self) -> List[Observation]:
        observations: List[Observation] = []

        for path in self.WATCH_PATHS:
            latest_commit = self._fetch_latest_commit(path)
            if not latest_commit:
                continue

            sha = self._commit_sha(latest_commit)
            known_sha = self.state.get(path)

            author = self._commit_author(latest_commit)
            if author:
                self._record_participant(author)

            if sha and sha != known_sha:
                category = path.split("/")[2] if path.startswith("technology/1956-commons/") else "root"
                observation = Observation(
                    timestamp=self._now(),
                    category=category,
                    path=path,
                    summary=self._summarize_commit(path, latest_commit),
                )
                observations.append(observation)
                self.state[path] = sha

                if self._is_external_contact(latest_commit) and not self.state.get("first_external_contact"):
                    self._write_first_contact_page(observation, latest_commit)
                    self._write_first_contact_ledger(observation, latest_commit)
                    self.state["first_external_contact"] = "true"
                    observations.append(
                        Observation(
                            timestamp=self._now(),
                            category="external-contact",
                            path=path,
                            summary="First external contact recorded by Obi-1",
                        )
                    )

        self._update_census()

        if observations:
            self._append_log(observations)

        self._save_state()
        return observations

    def run(self, interval_seconds: int = 60) -> None:
        print("Obi-1 Observer Bot is watching the 1956 Commons...")
        while True:
            observations = self.observe_once()
            if observations:
                for obs in observations:
                    print(asdict(obs))
            time.sleep(interval_seconds)


if __name__ == "__main__":
    agent = CommonsObserverAgent(
        repo_owner="tdp1776",
        repo_name="tdp-creative-repository",
        branch="main",
        repo_root=".",
    )

    try:
        agent.run(interval_seconds=60)
    except KeyboardInterrupt:
        print("Observer stopped manually.")
