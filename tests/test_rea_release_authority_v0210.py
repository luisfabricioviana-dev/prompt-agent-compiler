import hashlib
import hmac
import unittest

from contracts.rea_release_authority import (
    ReleaseAuthorization,
    verify_destination_bound_authorization,
    verify_release_authorization,
)


class ReleaseAuthorityDirectTests(unittest.TestCase):
    KEY = b"release-authority-test-key-32-bytes-minimum!!"
    SHA = hashlib.sha256(b"artifact").hexdigest()
    ISSUER = "release-owner"
    RELEASE_ID = "release-001"
    DESTINATION = "repo:owner/name"

    def auth_v1(self, *, sha=None, issuer=None, release_id=None):
        sha = self.SHA if sha is None else sha
        issuer = self.ISSUER if issuer is None else issuer
        release_id = self.RELEASE_ID if release_id is None else release_id
        message = (
            f"REA-RELEASE-v1\n{issuer}\n{release_id}\n{sha}"
        ).encode()
        signature = hmac.new(self.KEY, message, hashlib.sha256).hexdigest()
        return ReleaseAuthorization(sha, release_id, issuer, signature)

    def auth_v2(
        self,
        *,
        sha=None,
        issuer=None,
        release_id=None,
        destination=None,
    ):
        sha = self.SHA if sha is None else sha
        issuer = self.ISSUER if issuer is None else issuer
        release_id = self.RELEASE_ID if release_id is None else release_id
        destination = (
            self.DESTINATION if destination is None else destination
        )
        message = (
            f"REA-RELEASE-DEST-v2\n{issuer}\n{release_id}\n"
            f"{sha}\n{destination}"
        ).encode()
        signature = hmac.new(self.KEY, message, hashlib.sha256).hexdigest()
        return ReleaseAuthorization(sha, release_id, issuer, signature)

    def test_v1_valid_authorization(self):
        self.assertTrue(
            verify_release_authorization(
                self.auth_v1(),
                trusted_issuer=self.ISSUER,
                trusted_key=self.KEY,
                artifact_sha256=self.SHA,
            )
        )

    def test_v1_rejects_invalid_boundary_inputs(self):
        valid = self.auth_v1()
        cases = (
            dict(trusted_key=b"weak"),
            dict(trusted_issuer="wrong-owner"),
            dict(auth=ReleaseAuthorization(
                self.SHA, "short", self.ISSUER, valid.signature_hex
            )),
            dict(artifact_sha256="not-a-digest"),
            dict(artifact_sha256="b" * 64),
            dict(auth=ReleaseAuthorization(
                self.SHA, self.RELEASE_ID, self.ISSUER, "bad-signature"
            )),
            dict(auth=ReleaseAuthorization(
                self.SHA, self.RELEASE_ID, self.ISSUER, "0" * 64
            )),
        )
        for override in cases:
            with self.subTest(override=override):
                kwargs = dict(
                    auth=valid,
                    trusted_issuer=self.ISSUER,
                    trusted_key=self.KEY,
                    artifact_sha256=self.SHA,
                )
                kwargs.update(override)
                self.assertFalse(verify_release_authorization(**kwargs))

    def test_v1_rejects_wrong_auth_type(self):
        self.assertFalse(
            verify_release_authorization(
                object(),
                trusted_issuer=self.ISSUER,
                trusted_key=self.KEY,
                artifact_sha256=self.SHA,
            )
        )

    def test_v2_valid_destination_bound_authorization(self):
        self.assertTrue(
            verify_destination_bound_authorization(
                self.auth_v2(),
                trusted_issuer=self.ISSUER,
                trusted_key=self.KEY,
                artifact_sha256=self.SHA,
                destination_id=self.DESTINATION,
            )
        )

    def test_v2_rejects_invalid_boundary_inputs(self):
        valid = self.auth_v2()
        cases = (
            dict(auth=object()),
            dict(destination_id="!"),
            dict(trusted_issuer="wrong-owner"),
            dict(trusted_key=b"weak"),
            dict(auth=ReleaseAuthorization(
                self.SHA, "short", self.ISSUER, valid.signature_hex
            )),
            dict(artifact_sha256="not-a-digest"),
            dict(artifact_sha256="b" * 64),
            dict(auth=ReleaseAuthorization(
                self.SHA, self.RELEASE_ID, self.ISSUER, "bad-signature"
            )),
            dict(auth=ReleaseAuthorization(
                self.SHA, self.RELEASE_ID, self.ISSUER, "0" * 64
            )),
        )
        for override in cases:
            with self.subTest(override=override):
                kwargs = dict(
                    auth=valid,
                    trusted_issuer=self.ISSUER,
                    trusted_key=self.KEY,
                    artifact_sha256=self.SHA,
                    destination_id=self.DESTINATION,
                )
                kwargs.update(override)
                self.assertFalse(
                    verify_destination_bound_authorization(**kwargs)
                )

    def test_v2_signature_is_destination_specific(self):
        auth = self.auth_v2()
        self.assertFalse(
            verify_destination_bound_authorization(
                auth,
                trusted_issuer=self.ISSUER,
                trusted_key=self.KEY,
                artifact_sha256=self.SHA,
                destination_id="repo:other/name",
            )
        )


if __name__ == "__main__":
    unittest.main()
