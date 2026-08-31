"""AI inference worker package."""

from worker.model import MODEL_VERSION, PneumoniaPrediction, pneumonia_predictor

__all__ = ["MODEL_VERSION", "PneumoniaPrediction", "pneumonia_predictor"]
