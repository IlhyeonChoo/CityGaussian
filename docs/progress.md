# 진행 상황

## 2026-03-21

- `Todo/README.md`, `Todo/G1_G2_implementation_plan.md`, `LOCAL_SETUP_NOTES.md`, `CLAUDE.md` 기준으로 G1/G2 overlap 구조 설계를 정리했다.
- baseline 기준선은 `output/mc_small_aerial_coarse/`, `output/mc_small_aerial_c36/`로 확보되어 있음을 확인했다.
- 실험용 디렉토리와 config scaffold를 추가하고, overlap 전용 wrapper/유틸 구조를 만들기 시작했다.

## 다음 단계

- `data_partition_overlap.py`, `train_large_overlap.py`, `merge_overlap.py` 구현 마무리
- `config/smoke_test/g1_overlap15_smoke.yaml` 기준 smoke pipeline 검증
- Boundary LPIPS 및 시각화 도구 정리
