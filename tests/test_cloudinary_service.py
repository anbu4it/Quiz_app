"""Tests for cloudinary_service module."""

import os
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.datastructures import FileStorage

from app import create_app
from services.cloudinary_service import (
    delete_avatar,
    init_cloudinary,
    is_cloudinary_url,
    upload_avatar,
)


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        yield app


def test_is_cloudinary_url_true():
    """Test detection of Cloudinary URLs."""
    assert is_cloudinary_url("https://res.cloudinary.com/mycloud/image/upload/avatar.jpg")


def test_is_cloudinary_url_false():
    """Test rejection of non-Cloudinary URLs."""
    assert not is_cloudinary_url("uploads/avatar.png")
    assert not is_cloudinary_url(None)
    assert not is_cloudinary_url("")


def test_init_cloudinary_success():
    """Test Cloudinary initialization with valid credentials."""
    with patch.dict(
        os.environ,
        {
            "CLOUDINARY_CLOUD_NAME": "test_cloud",
            "CLOUDINARY_API_KEY": "test_key",
            "CLOUDINARY_API_SECRET": "test_secret",
        },
    ):
        result = init_cloudinary()
        assert result is True


def test_init_cloudinary_missing_credentials():
    """Test Cloudinary initialization without credentials."""
    with patch.dict(os.environ, {}, clear=True):
        result = init_cloudinary()
        assert result is False


@patch("services.cloudinary_service.cloudinary.uploader.upload")
def test_upload_avatar_to_cloudinary(mock_upload, app):
    """Test avatar upload to Cloudinary when configured."""
    mock_upload.return_value = {"secure_url": "https://res.cloudinary.com/test/avatar.jpg"}

    with patch.dict(
        os.environ,
        {
            "CLOUDINARY_CLOUD_NAME": "test",
            "CLOUDINARY_API_KEY": "key",
            "CLOUDINARY_API_SECRET": "secret",
        },
    ):
        file = FileStorage(
            stream=BytesIO(b"fake image data"), filename="test.jpg", content_type="image/jpeg"
        )

        result = upload_avatar(file, user_id=1)
        assert result == "https://res.cloudinary.com/test/avatar.jpg"
        mock_upload.assert_called_once()


@patch("services.cloudinary_service.cloudinary.uploader.upload", side_effect=Exception("Upload failed"))
def test_upload_avatar_cloudinary_fallback_to_local(mock_upload, app):
    """Test fallback to local storage when Cloudinary upload fails."""
    with patch.dict(
        os.environ,
        {
            "CLOUDINARY_CLOUD_NAME": "test",
            "CLOUDINARY_API_KEY": "key",
            "CLOUDINARY_API_SECRET": "secret",
        },
    ):
        file = FileStorage(
            stream=BytesIO(b"fake image data"), filename="test.jpg", content_type="image/jpeg"
        )

        result = upload_avatar(file, user_id=1)
        # Should return local path after fallback
        assert result.startswith("uploads/user_1_")
        assert result.endswith(".jpg")


def test_upload_avatar_local_storage(app):
    """Test direct upload to local storage when Cloudinary not configured."""
    with patch.dict(os.environ, {}, clear=True):
        file = FileStorage(
            stream=BytesIO(b"fake image data"), filename="avatar.png", content_type="image/png"
        )

        result = upload_avatar(file, user_id=42)
        assert result.startswith("uploads/user_42_")
        assert result.endswith(".png")

        # Verify file was saved
        full_path = os.path.join(app.static_folder, result)
        assert os.path.exists(full_path)

        # Cleanup
        try:
            os.remove(full_path)
        except Exception:
            pass


@patch("services.cloudinary_service.cloudinary.uploader.destroy")
def test_delete_cloudinary_avatar(mock_destroy, app):
    """Test deletion of Cloudinary avatar."""
    with patch.dict(
        os.environ,
        {
            "CLOUDINARY_CLOUD_NAME": "test",
            "CLOUDINARY_API_KEY": "key",
            "CLOUDINARY_API_SECRET": "secret",
        },
    ):
        url = "https://res.cloudinary.com/test/image/upload/v123/quiz_app_avatars/user_1.jpg"
        result = delete_avatar(url)
        assert result is True
        mock_destroy.assert_called_once_with("quiz_app_avatars/user_1")


def test_delete_local_avatar(app):
    """Test deletion of local avatar file."""
    # Create a dummy file
    test_path = "uploads/test_avatar_delete.png"
    full_path = os.path.join(app.static_folder, test_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, "w") as f:
        f.write("test")

    assert os.path.exists(full_path)

    result = delete_avatar(test_path)
    assert result is True
    assert not os.path.exists(full_path)


def test_delete_avatar_none():
    """Test deletion with None path returns False."""
    assert delete_avatar(None) is False


def test_delete_avatar_nonexistent_local():
    """Test deletion of non-existent local file returns False."""
    with create_app({"TESTING": True}).app_context():
        result = delete_avatar("uploads/nonexistent.png")
        assert result is False
