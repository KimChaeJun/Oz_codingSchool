# 폐렴 예측 모델

- 파일: `pneumonia_resnet18_v1.pt`
- 구조: ImageNet 사전학습 ResNet18 + Dropout(0.30) + 2-class Linear head
- 입력: 흑백 X-Ray를 3채널로 변환한 160×160 이미지
- 정규화: ImageNet mean/std
- 모델 버전: `resnet18_imagenet_layer4_v1`
- 폐렴 판정 임계값: `0.8183`
- 검증 Recall: `0.9124`
- 검증 Accuracy: `0.9349`

체크포인트는 `state_dict` 형식이며 `torch.load(..., weights_only=True)`로
로드합니다. 성능 수치는 교육용 검증 데이터 기준으로, 임상 진단 성능을
보장하지 않습니다.
