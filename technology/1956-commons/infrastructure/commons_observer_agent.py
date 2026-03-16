import json
import time
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
    A lightweight observer for the 1956 Commons repository.

    This agent does not modify governance documents.
    It only watches the Commons structure, notices changes,
    and writes observations to a log file.

    The observer is designed to run continuously until:
      • the program is stopped manually
      • a maximum runtime is reached (optional)
      • a maximum number of observation cycles is reached (optional)

    This makes the agent behave like a passive "sentinel" inside the Commons.
    """

    WATCH_DIRS = [
        "technology/1956-commons/proposals",
        "technology/1956-commons/debates",
        "technology/1956-commons/votes",
        "technology/1956-commons/records",
        "technology/1956-commons/guilds",
        "technology/1956-commons/participants",
    ]

    def __init__(self, repo_root: str = ".") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.state_file = self.repo_root / "technology/1956-commons/participants/observer-state.json"
        self.log_file = self.repo_root / "technology/1956-commons/participants/observer-log.md"
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, float]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception:
                return {}
        return {}

    def _save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def _scan_files(self) -> List[Path]:
        files: List[Path] = []
        for rel_dir in self.WATCH_DIRS:
            full_dir = self.repo_root / rel_dir
            if not full_dir.exists():
                continue
            for path in full_dir.rglob("*.md"):
                if path.name == self.log_file.name:
                    continue
                files.append(path)
        return sorted(files)

    def _summarize_change(self, path: Path) -> str:
        rel = path.relative_to(self.repo_root).as_posix()
        text = path.read_text(errors="ignore")[:800]

        if "/proposals/" in rel:
            return f"Proposal file updated: {path.stem}"
        if "/debates/" in rel:
            return f"Debate record updated: {path.stem}"
        if "/votes/" in rel:
            return f"Vote record updated: {path.stem}"
        if "/records/" in rel:
            return f"Commons record updated: {path.stem}"
        if "/guilds/" in rel:
            return f"Guild document updated: {path.stem}"
        if "/participants/" in rel:
            return f"Participant register updated: {path.stem}"

        first_line = text.splitlines()[0] if text.splitlines() else "No content"
        return f"Observed change in {rel}: {first_line}"

    def observe_once(self) -> List[Observation]:
        observations: List[Observation] = []
        for path in self._scan_files():
            rel = path.relative_to(self.repo_root).as_posix()
            mtime = path.stat().st_mtime
            known = self.state.get(rel)

            if known is None or mtime > known:
                category = rel.split("/")[2] if rel.startswith("technology/1956-commons/") else "general"
                observations.append(
                    Observation(
                        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                        category=category,
                        path=rel,
                        summary=self._summarize_change(path),
                    )
                )
                self.state[rel] = mtime

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

    def run(self, interval_seconds: int = 60, max_cycles: Optional[int] = None, max_runtime_seconds: Optional[int] = None) -> None:
        """
        Run the observer.

        interval_seconds: time between scans
        max_cycles: optional limit to how many scans occur
        max_runtime_seconds: optional time limit
        """

        print("Commons Observer Agent is running...")

        start_time = time.time()
        cycle_count = 0

        while True:
            observations = self.observe_once()

            if observations:
                for obs in observations:
                    print(asdict(obs))

            cycle_count += 1

            # stop if max cycles reached
            if max_cycles is not None and cycle_count >= max_cycles:
                print("Observer stopping: max cycles reached.")
                break

            # stop if max runtime reached
            if max_runtime_seconds is not None and (time.time() - start_time) >= max_runtime_seconds:
                print("Observer stopping: max runtime reached.")
                break

            time.sleep(interval_seconds)


if __name__ == "__main__":
    agent = CommonsObserverAgent(repo_root=".")

    # Default behavior: run indefinitely until stopped
    try:
        agent.run(interval_seconds=60)
    except KeyboardInterrupt:
        print("Observer stopped manually.")

