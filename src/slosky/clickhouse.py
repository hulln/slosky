from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, Iterator


DEFAULT_ENDPOINT = "https://sql-clickhouse.clickhouse.com/"
DEFAULT_USER = "demo"
DEFAULT_PASSWORD = ""


class ClickHouseError(RuntimeError):
    """Raised when a ClickHouse query fails."""


def render_sql(template_path: Path, params: Dict[str, str]) -> str:
    text = template_path.read_text(encoding="utf-8")
    for key, value in params.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


class ClickHouseClient:
    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        user: str = DEFAULT_USER,
        password: str = DEFAULT_PASSWORD,
        timeout: int = 300,
    ) -> None:
        self.endpoint = endpoint
        self.user = user
        self.password = password
        self.timeout = timeout

    def _command(self) -> list[str]:
        auth = f"{self.user}:{self.password}"
        return [
            "curl",
            "-s",
            "--user",
            auth,
            "--data-binary",
            "@-",
            self.endpoint,
        ]

    def execute_bytes(self, query: str) -> bytes:
        completed = subprocess.run(
            self._command(),
            check=False,
            capture_output=True,
            input=query.encode("utf-8"),
            timeout=self.timeout,
        )
        if completed.returncode != 0:  # pragma: no cover - subprocess failure path
            stderr = completed.stderr.decode("utf-8", errors="replace").strip()
            raise ClickHouseError(stderr or f"curl exited with {completed.returncode}")

        stdout = completed.stdout
        if stdout.lstrip().startswith(b"Code:") or b"DB::Exception" in stdout:
            raise ClickHouseError(stdout.decode("utf-8", errors="replace").strip())
        return stdout

    def execute_json(self, query: str) -> dict:
        return json.loads(self.execute_bytes(query).decode("utf-8"))

    def iter_json_each_row(self, query: str) -> Iterator[dict]:
        process = subprocess.Popen(
            self._command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdin is not None
        process.stdin.write(query)
        process.stdin.close()
        assert process.stdout is not None
        buffered_error: list[str] = []
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                buffered_error.append(line)
                break

        stderr = ""
        if process.stderr is not None:
            stderr = process.stderr.read().strip()
        return_code = process.wait(timeout=self.timeout)
        if return_code != 0:  # pragma: no cover - subprocess failure path
            raise ClickHouseError(stderr or f"curl exited with {return_code}")
        if buffered_error:
            message = "\n".join(buffered_error)
            raise ClickHouseError(message)
