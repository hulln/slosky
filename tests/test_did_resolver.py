from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from slosky.did_resolver import did_document_url, did_web_document_url, extract_resolution


class DidResolverTests(unittest.TestCase):
    def test_did_web_url(self) -> None:
        self.assertEqual(
            did_web_document_url("did:web:example.com"),
            "https://example.com/.well-known/did.json",
        )
        self.assertEqual(
            did_web_document_url("did:web:example.com:user:alice"),
            "https://example.com/user/alice/did.json",
        )

    def test_extract_resolution(self) -> None:
        document = {
            "alsoKnownAs": ["at://oblachek.eu"],
            "service": [
                {
                    "type": "AtprotoPersonalDataServer",
                    "serviceEndpoint": "https://eurosky.social",
                }
            ],
        }
        resolved = extract_resolution(
            "did:plc:test",
            document,
            "https://plc.directory/did:plc:test",
        )
        self.assertEqual(resolved.handle, "oblachek.eu")
        self.assertEqual(resolved.pds_url, "https://eurosky.social")


if __name__ == "__main__":
    unittest.main()
