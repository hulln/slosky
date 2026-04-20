from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote
from urllib.request import urlopen


@dataclass
class DidResolution:
    did: str
    pds_url: str
    handle: str | None = None
    source_url: str | None = None


def did_web_document_url(did: str) -> str:
    suffix = did.removeprefix("did:web:")
    parts = [unquote(part) for part in suffix.split(":")]
    host = parts[0]
    path = parts[1:]
    if not path:
        return f"https://{host}/.well-known/did.json"
    return f"https://{host}/{'/'.join(path)}/did.json"


def did_document_url(did: str, plc_base: str = "https://plc.directory") -> str:
    if did.startswith("did:plc:"):
        return plc_base.rstrip("/") + "/" + did
    if did.startswith("did:web:"):
        return did_web_document_url(did)
    raise ValueError(f"Unsupported DID method: {did}")


def extract_resolution(did: str, document: dict, source_url: str) -> DidResolution:
    handle = None
    for aka in document.get("alsoKnownAs") or []:
        if isinstance(aka, str) and aka.startswith("at://"):
            handle = aka.removeprefix("at://")
            break

    for service in document.get("service") or []:
        if service.get("type") == "AtprotoPersonalDataServer":
            endpoint = service.get("serviceEndpoint")
            if endpoint:
                return DidResolution(
                    did=did,
                    pds_url=str(endpoint).rstrip("/"),
                    handle=handle,
                    source_url=source_url,
                )
    raise ValueError(f"No AtprotoPersonalDataServer service found for {did}")


class DidResolver:
    def __init__(
        self,
        *,
        cache_path: Path | None = None,
        plc_base: str = "https://plc.directory",
        timeout: int = 30,
    ) -> None:
        self.cache_path = cache_path
        self.plc_base = plc_base
        self.timeout = timeout
        self._cache: dict[str, DidResolution] = {}
        if cache_path and cache_path.exists():
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            for did, item in raw.items():
                self._cache[did] = DidResolution(**item)

    def _save(self) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {did: asdict(item) for did, item in sorted(self._cache.items())}
        self.cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def resolve(self, did: str) -> DidResolution:
        cached = self._cache.get(did)
        if cached is not None:
            return cached

        source_url = did_document_url(did, plc_base=self.plc_base)
        with urlopen(source_url, timeout=self.timeout) as response:  # noqa: S310
            document = json.loads(response.read().decode("utf-8"))
        resolved = extract_resolution(did, document, source_url)
        self._cache[did] = resolved
        self._save()
        return resolved
