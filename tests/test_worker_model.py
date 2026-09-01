from io import BytesIO

import pytest
from PIL import Image

from worker.model import InvalidXrayImageError, MODEL_VERSION, pneumonia_predictor


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("L", (160, 160), color=128).save(buffer, format="PNG")
    return buffer.getvalue()


def test_model_is_loaded_once_and_returns_valid_prediction() -> None:
    result = pneumonia_predictor.predict(_png_bytes())

    assert result.model_version == MODEL_VERSION
    assert isinstance(result.is_pneumonia, bool)
    assert 0.0 <= result.confidence <= 100.0
    assert 0.0 <= result.pneumonia_probability <= 1.0
    assert pneumonia_predictor.model.training is False


def test_invalid_image_is_rejected() -> None:
    with pytest.raises(InvalidXrayImageError):
        pneumonia_predictor.predict(b"not-an-image")
