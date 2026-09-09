import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings


class PublicMediaTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.settings_override = override_settings(MEDIA_ROOT=self.root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        for folder in ("avatars", "company_logos", "cvs", "application_cvs"):
            (self.root / folder).mkdir()
        (self.root / "avatars" / "photo.png").write_bytes(b"public-image")
        (self.root / "cvs" / "private.pdf").write_bytes(b"%PDF-private")

    def test_public_image_remains_accessible(self):
        response = self.client.get("/media/avatars/photo.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"public-image")
        response.close()

    def test_public_prefix_cannot_escape_into_private_storage(self):
        paths = (
            "/media/cvs/private.pdf",
            "/media/avatars/../cvs/private.pdf",
            "/media/avatars/%2e%2e/cvs/private.pdf",
            "/media/avatars/..%5ccvs%5cprivate.pdf",
            "/media/company_logos/../cvs/private.pdf",
        )
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                try:
                    self.assertEqual(response.status_code, 404)
                finally:
                    response.close()
