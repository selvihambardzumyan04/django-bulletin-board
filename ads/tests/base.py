import io
import random
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

FAST_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


def make_image(name="test.jpg", size=(50, 50), noisy=False):
    """Build a real in-memory image file for upload tests."""
    image = Image.new("RGB", size, "blue")
    if noisy:
        pixels = size[0] * size[1]
        image.putdata(
            [(random.randint(0, 255),) * 3 for _ in range(pixels)]
        )
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=100)
    return SimpleUploadedFile(
        name, buffer.getvalue(), content_type="image/jpeg"
    )


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class BaseTestCase(TestCase):
    def login(self, user):
        self.client.force_login(user)
        return user


class MediaTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_root = tempfile.mkdtemp(prefix="ads-test-media-")
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
