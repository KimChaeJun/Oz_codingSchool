from app.models.user import User
from app.models.patient import Patient
from app.models.medical_record import MedicalRecord
from app.models.xray_image import XrayImage
from app.models.ai_analysis_result import AiAnalysisResult

__all__ = [
    "User",
    "Patient",
    "MedicalRecord",
    "XrayImage",
    "AiAnalysisResult",
]
