"""흉부 X-Ray 폐렴 예측 ResNet18 모델 로딩 및 추론.

체크포인트 출처: 데이콘 해커톤에서 팀이 직접 학습한 ResNet18
(resnet18_pure_training.ipynb, IMAGENET1K_V1 사전학습 가중치로 파인튜닝).
`best_model_resnet18_pure.pth`는 전체 모델이 아니라 state_dict만 저장되어 있으므로,
학습에 쓰인 것과 동일한 아키텍처를 코드로 재구성한 뒤 가중치를 얹는다.

라벨 기준 (이 프로젝트에서 사용하는 유일한 매핑):
    0 = Normal
    1 = Pneumonia
모델은 학습 시 이 정의를 그대로 따라 label=1(Pneumonia)일 확률을 출력하도록
BCEWithLogitsLoss로 학습되었다. 다른 매핑을 추가하지 않는다.
"""

from dataclasses import dataclass
from enum import IntEnum
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

MODEL_PATH = Path(__file__).resolve().parent / "models" / "best_model_resnet18_pure.pth"
MODEL_VERSION = "resnet18_daycon_pure_v1"

# 학습 시 사용한 것과 동일한 전처리 (resnet18_pure_training.ipynb val_transform)
IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# 검증 데이터(783장)에서 이 threshold로 Recall 0.9983 / Accuracy 0.9962 확인됨.
PNEUMONIA_THRESHOLD = 0.5


class Label(IntEnum):
    """label 0/1의 의미. 이 프로젝트 전체에서 이 정의만 사용한다."""

    NORMAL = 0
    PNEUMONIA = 1


@dataclass(frozen=True, slots=True)
class PneumoniaPrediction:
    is_pneumonia: bool
    pneumonia_probability: float
    model_version: str = MODEL_VERSION


def _build_architecture() -> nn.Module:
    """ImageNet 사전학습 ResNet18과 동일한 구조. 마지막 fc만 이진분류용으로 교체."""
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 1)
    return model


@lru_cache(maxsize=1)
def load_model() -> nn.Module:
    """state_dict를 읽어 모델을 메모리에 1회만 로드한다 (요청마다 재로딩 금지)."""
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"ResNet18 체크포인트를 찾을 수 없습니다: {MODEL_PATH}")

    model = _build_architecture()
    state_dict = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model


def _build_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


_transform = _build_transform()


def predict(image_source: str | Path | BinaryIO) -> PneumoniaPrediction:
    """X-Ray 이미지 하나를 입력받아 폐렴 예측 결과를 반환한다.

    image_source: 이미지 파일 경로 또는 파일 객체.
    """
    model = load_model()

    with Image.open(image_source) as image:
        rgb_image = image.convert("RGB")
        input_tensor = _transform(rgb_image).unsqueeze(0)

    with torch.no_grad():
        logit = model(input_tensor)
        pneumonia_probability = torch.sigmoid(logit).item()

    is_pneumonia = pneumonia_probability >= PNEUMONIA_THRESHOLD
    return PneumoniaPrediction(
        is_pneumonia=is_pneumonia,
        pneumonia_probability=round(pneumonia_probability, 6),
    )
