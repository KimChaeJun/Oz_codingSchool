from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import BinaryIO, TypeAlias

import torch
from PIL import Image, UnidentifiedImageError
from torch import nn
from torchvision import models, transforms

MODEL_VERSION = "resnet18_imagenet_layer4_v1"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "pneumonia_resnet18_v1.pt"
IMAGE_SIZE = 160
PNEUMONIA_THRESHOLD = 0.8183

ImageSource: TypeAlias = str | Path | bytes | bytearray | BinaryIO


class InvalidXrayImageError(ValueError):
    """Raised when an input cannot be decoded as an X-Ray image."""


@dataclass(frozen=True, slots=True)
class PneumoniaPrediction:
    is_pneumonia: bool
    confidence: float
    pneumonia_probability: float
    model_version: str = MODEL_VERSION


class PneumoniaPredictor:
    """In-memory ResNet18 predictor trained for chest X-Ray classification."""

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._inference_lock = Lock()
        self.transform = transforms.Compose(
            [
                transforms.Grayscale(num_output_channels=3),
                transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
        self.model = self._load_model()

    def _load_model(self) -> nn.Module:
        if not self.model_path.is_file():
            raise FileNotFoundError(f"폐렴 예측 모델을 찾을 수 없습니다: {self.model_path}")

        model = models.resnet18(weights=None)
        in_features = model.fc.in_features
        model.fc = nn.Sequential(nn.Dropout(p=0.30), nn.Linear(in_features, 2))

        state_dict = torch.load(
            self.model_path,
            map_location=self.device,
            weights_only=True,
        )
        model.load_state_dict(state_dict, strict=True)
        model.to(self.device)
        model.eval()
        return model

    @staticmethod
    def _open_image(source: ImageSource) -> Image.Image:
        image_source: str | Path | BytesIO | BinaryIO
        if isinstance(source, (bytes, bytearray)):
            image_source = BytesIO(source)
        else:
            image_source = source

        try:
            with Image.open(image_source) as image:
                image.load()
                return image.convert("L")
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            raise InvalidXrayImageError(
                "유효한 흉부 X-Ray 이미지를 읽을 수 없습니다."
            ) from exc

    @torch.inference_mode()
    def predict(self, source: ImageSource) -> PneumoniaPrediction:
        image = self._open_image(source)
        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        # A single model instance is shared by the web process. Serializing the
        # forward pass avoids backend-specific races while keeping the weights
        # resident in memory between requests.
        with self._inference_lock:
            logits = self.model(input_tensor)
            pneumonia_probability = torch.softmax(logits, dim=1)[0, 1].item()

        is_pneumonia = pneumonia_probability >= PNEUMONIA_THRESHOLD
        predicted_class_probability = (
            pneumonia_probability if is_pneumonia else 1.0 - pneumonia_probability
        )
        return PneumoniaPrediction(
            is_pneumonia=is_pneumonia,
            confidence=round(predicted_class_probability * 100.0, 4),
            pneumonia_probability=round(pneumonia_probability, 6),
        )


# Importing this module loads the model once. API requests reuse this instance
# instead of deserializing the 44 MB state_dict for every inference.
pneumonia_predictor = PneumoniaPredictor()
