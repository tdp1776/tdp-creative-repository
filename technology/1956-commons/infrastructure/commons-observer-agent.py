import json
import os
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class Observation:
    timestamp: str
    category: str
    path: str
    summary: str


class CommonsObserverAgent:
    """
    Obi‑1 — Observer Bot 001 for 1956 Commons.

    Watches the LIVE GitHub repository and records activity.

    On the FIRST detected external contact it will:

    • log the observation
    • update first-contact-report.html in the repository root

    External contact = commit author not in KNOWN_INTERNAL_AUTHORS
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

    KNOWN_INTERNAL_AUTHORS = {
        "tdp1776",
        "tdp",
    }

    FIRST_CONTACT_FILE = "first-contact-report.html"

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

        self.state_file = self.repo_root / "technology/1956-commons/participants/observer-state.json"
        self.log_file = self.repo_root / "technology/1956-commons/participants/observer-log.md"
        self.first_contact_page = self.repo_root / self.FIRST_CONTACT_FILE

        self.state = self._load_state()

    def _load_state(self) -> Dict[str, str]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                return {}
        return {}

    def _save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2))

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
                "User-Agent": "1956-commons-observer-bot-001",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, list) and data:
                    return data[0]
        except Exception:
            pass

        return None

    def _commit_author(self, commit: dict) -> str:

        commit_block = commit.get("commit", {})
        return commit_block.get("author", {}).get("name", "unknown")

    def _summarize_commit(self, path: str, commit: dict) -> str:

        sha = commit.get("sha", "")[:7]
        commit_block = commit.get("commit", {})

        message = commit_block.get("message", "No commit message").splitlines()[0]

        author = self._commit_author(commit)

        return f"Observed new GitHub commit in {path}: {sha} by {author} — {message}"

    def _is_external_contact(self, commit: dict) -> bool:

        author = self._commit_author(commit).strip().lower()

        normalized_internal = {name.strip().lower() for name in self.KNOWN_INTERNAL_AUTHORS}

        return author not in normalized_internal

    def _write_first_contact_page(self, observation: Observation, commit: dict) -> None:

        commit_block = commit.get("commit", {})

        author = self._commit_author(commit)

        message = commit_block.get("message", "No commit message")

        sha = commit.get("sha", "")

        html = f"""<!DOCTYPE html>
<html>
<head>
<title>1956 Commons — First Contact Report</title>
</head>

<body style="font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 40px;">

<h1>1956 Commons — First Contact Report</h1>

<p><strong>Status:</strong> External contact detected.</p>

<ul>
<li><strong>Timestamp:</strong> {observation.timestamp}</li>
<li><strong>Author:</strong> {author}</li>
<li><strong>Path:</strong> {observation.path}</li>
<li><strong>Commit:</strong> {sha}</li>
<li><strong>Message:</strong> {message}</li>
</ul>

<p>
Observer Bot 001 (Obi‑1) recorded the first external interaction with the Commons.
</p>

</body>
</html>
"""

        self.first_contact_page.write_text(html)

    def observe_once(self) -> List[Observation]:

        observations: List[Observation] = []

        for path in self.WATCH_PATHS:

            latest_commit = self._fetch_latest_commit(path)

            if not latest_commit:
                continue

            sha = latest_commit.get("sha", "")

            known_sha = self.state.get(path)

            if sha and sha != known_sha:

                category = path.split("/")[2] if path.startswith("technology/1956-commons/") else "root"

                summary = self._summarize_commit(path, latest_commit)

                observation = Observation(
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    category=category,
                    path=path,
                    summary=summary,
                )

                observations.append(observation)

                self.state[path] = sha

                if self._is_external_contact(latest_commit) and not self.state.get("first_external_contact"):

                    self._write_first_contact_page(observation, latest_commit)

                    self.state["first_external_contact"] = "true"

                    observations.append(
                        Observation(
                            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                            category="external-contact",
                            path=path,
                            summary="First external contact recorded by Obi‑1",
                        )
                    )

        if observations:
            self._append_log(observations)
            self._save_state()

        return observations

    def _append_log(self, observations: List[Observation]) -> None:

        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_file.exists():
            self.log_file.write_text("# Commons Observer Log\n\n")

        with self.log_file.open("a", encoding="utf-8") as f:

            for obs in observations:

                f.write(f"## {obs.timestamp}\n")
                f.write(f"- Category: {obs.category}\n")
                f.write(f"- Path: {obs.path}\n")
                f.write(f"- Observation: {obs.summary}\n\n")

    def run(self, interval_seconds: int = 60) -> None:

        print("Obi‑1 Observer Bot is watching the 1956 Commons...")

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
