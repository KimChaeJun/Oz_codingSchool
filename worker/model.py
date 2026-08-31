from pathlib import Path

import torch
import torch.nn as nn
import sys
from PIL import Image
from torchvision import transforms


class SimpleCNN(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
        )

        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32768, num_classes),
        )

    def forward(self, x):
        x = self.conv(x)
        return self.fc(x)


MODEL_PATH = Path(__file__).parent / "models" / "model.pth"

sys.modules["__main__"].SimpleCNN = SimpleCNN

model = torch.load(
    MODEL_PATH,
    map_location="cpu",
    weights_only=False,
)
model.eval()

transform = transforms.Compose(
    [
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
    ]
)


def predict_pneumonia(image_path: str) -> dict:
    image = Image.open(image_path).convert("RGB")
    image_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        output = model(image_tensor)
        probability = torch.softmax(output, dim=1)
        predicted_class = int(torch.argmax(probability, dim=1).item())

    labels = ["NORMAL", "PNEUMONIA"]

    return {
        "result": labels[predicted_class],
        "is_pneumonia": labels[predicted_class] == "PNEUMONIA",
        "confidence": round(float(probability[0][predicted_class]), 4),
    }