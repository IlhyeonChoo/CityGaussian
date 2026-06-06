# Local Setup Notes

## 역할

- 이 파일은 현재 서버 기준의 active setup 메모다.
- 이전 임시 `RTX 4060 Ti 16GB` 서버 메모는 `docs/legacy/20260321_local_setup_prev_server.md`로 분리했다.
- 이전/현재 서버 비교와 이관 판단 문서는 `docs/legacy/` 아래에서 역사적 기록으로만 유지한다.

## 현재 서버 기준 워크플로우

- 현재 subset 준비의 기본 진입점은 `scripts/setup_current_server_experiments.sh`다.
- 현재 subset progression의 기본 진입점은 `scripts/run_subset_progression_current_server.sh`다.
- 이전 16GB 서버 복구용 흐름은 `scripts/legacy/run_subset_progression_resume.sh`로 아카이브했다.
- 서브모듈/환경 패치는 `scripts/apply_third_party_patches.sh`로 재적용 가능하게 유지한다.

## 현재 기준 환경 메모

- 가상환경은 `.venv` 기준이다.
- 2026-04-06 기준 검증한 Python 버전은 `3.11.14`다.
- 프로젝트 목표 런타임은 `PyTorch 2.7.1+cu128`, `CUDA 12.8`, `TORCH_CUDA_ARCH_LIST=12.0`이다.
- 현재 서버 준비 스크립트 기본 경로는 다음과 같다.
  - raw data: `/mnt/3dgs-ssd/3dgs-stage/MatrixCity/small_city/aerial`
  - subset data root: `data/matrix_city/aerial_subset`
  - runtime configs: `output/runtime_configs/current_server`
  - boundary manifest: `output/boundary_analysis/subset4_block_all_test_strict_current_server.json`

## 현재 기준 준비 절차

1. `git submodule update --init --recursive`
2. `./scripts/apply_third_party_patches.sh`
3. `bash scripts/setup_current_server_experiments.sh`
4. 필요 시 `bash scripts/run_subset_progression_current_server.sh`

## 현재 기준 검증 포인트

- `.venv` Python이 살아 있어야 한다.
- `diff_gaussian_rasterization`, `simple_knn` import가 성공해야 한다.
- subset dataset, current-server runtime config, boundary manifest가 생성되어야 한다.
- active setup 문서는 이 파일과 `docs/progress.md`를 우선 참조한다.

## 주의사항

- 이전 서버 기준 OOM 메모와 재시도 파라미터는 역사적 참고사항으로만 사용한다.
- 현재 서버에서 다시 실험을 돌릴 때는 `current_server` runtime config와 boundary manifest를 기준으로 삼는다.
- `docs/reports/`의 subset 5k 보고서는 실험 결과 기록으로 유지되지만, 환경/이관 판단 문서는 `docs/legacy/`를 먼저 본다.
