# 진행 상황

## 2026-03-21

- `Todo/README.md`, `Todo/G1_G2_implementation_plan.md`, `LOCAL_SETUP_NOTES.md`, `CLAUDE.md` 기준으로 G1/G2 overlap 구조 설계를 정리했다.
- baseline 기준선은 `output/mc_small_aerial_coarse/`, `output/mc_small_aerial_c36/`로 확보되어 있음을 확인했다.
- 실험용 디렉토리와 config scaffold를 추가하고, overlap 전용 wrapper/유틸 구조를 만들기 시작했다.
- 로컬 `NVIDIA GeForce RTX 4060 Ti (VRAM 16GB)` 머신에 `.venv` / Python 3.11 / PyTorch 2.7.1+cu128 / CUDA extension 환경을 다시 맞췄다.
- MatrixCity `small_city/aerial` subset raw를 내려받아 `block_1, block_4, block_7, block_10` train 3504장과 `block_1_test` 152장으로 smoke용 prepared data를 만들었다.
- `config/mc_small_aerial_subset_coarse_smoke.yaml` 기준 coarse subset smoke를 완료했다.
- `config/smoke_test/g1_overlap15_subset_smoke.yaml` 기준 overlap15 subset smoke를 완료했고 결과 보고서를 `docs/reports/G1_20260321_overlap15_subset_smoke.md`에 기록했다.
- `config/mc_small_aerial_subset_c4_smoke.yaml` 기준 non-overlap subset baseline smoke를 완료했다.
- subset 4-block 조건에서 G0 non-overlap vs G1 overlap15 비교 및 `RTX 4060 Ti (VRAM 16GB)` 실행 가능성 추정을 `docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md`에 기록했다.
- `tools/select_boundary_views.py`, `tools/filtered_metrics.py`, `tools/projected_boundary_lpips.py`를 추가해 실제 경계가 보이는 test view만 추려 재평가할 수 있게 했다.
- subset 4-block의 `block_1_test`에 selector를 적용한 결과, 엄격 projected-boundary 기준으로 48 view가 선택됐고 현재 subset은 `y_0.5000` 내부 경계만 커버한다는 점을 확인했다.
- 같은 48 view 기준 공식 비교에서 G1 overlap15는 G0 non-overlap 대비 `SSIM +0.0030`, `PSNR +0.2614`, `LPIPS -0.0042`, `projected boundary LPIPS -0.0035`로 모두 소폭 우세했다.
- `config/mc_small_aerial_subset_coarse_5k.yaml`, `config/mc_small_aerial_subset_c4_5k.yaml`, `config/g1_overlap15_subset_5k.yaml`와 대응되는 `10k` pilot config들을 추가했다.
- `config/mc_small_aerial_subset_c4_5k.yaml` 기준 G0 5k pilot을 완료했다.
  - 전체 test: `SSIM 0.7405`, `PSNR 25.3124`, `LPIPS 0.4607`
  - strict boundary-view 48장: `SSIM 0.7211`, `PSNR 24.7609`, `LPIPS 0.4822`, `projected boundary LPIPS 0.4534`
  - 4060 Ti 16GB에서는 block 학습 중 `max_cache_num 64`가 OOM을 일으켜 `max_cache_num 32`와 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`를 기본 fallback으로 확정했다.
- `config/g1_overlap15_subset_5k.yaml` 기준 G1 5k는 partition과 cell0 5k 학습까지 완료했고, 나머지 `G1 5k -> 10k progression`은 `scripts/run_subset_progression_resume.sh`로 이어서 재시작 가능하게 정리했다.

## 2026-03-22

- `config/g1_overlap15_subset_5k.yaml` 기준 G1 5k pilot을 완료했다.
  - 전체 test: `SSIM 0.7209`, `PSNR 24.1718`, `LPIPS 0.4758`
  - strict boundary-view 48장: `SSIM 0.6692`, `PSNR 21.9210`, `LPIPS 0.5218`, `projected boundary LPIPS 0.5042`
- subset 4-block의 현재 공식 pilot 비교 기준을 `5k`로 확정했고, canonical 보고서를 `docs/reports/G0_G1_20260322_subset4_5k_canonical.md`에 기록했다.
- 현재 `block_1_test`의 strict boundary-view 기준에서는 G0 non-overlap이 G1 overlap15보다 우세했다.
  - 전체 test delta (`G1 - G0`): `SSIM -0.0196`, `PSNR -1.1407`, `LPIPS +0.0151`
  - strict boundary-view delta (`G1 - G0`): `SSIM -0.0519`, `PSNR -2.8400`, `LPIPS +0.0396`, `projected boundary LPIPS +0.0508`
- `10k`는 현재 공식 결론에서 제외하고 부분 완료 상태로만 기록한다.
  - coarse 10k는 완료
  - G0 10k는 `cell0` 완료, `cell1`은 TensorBoard event 기준 `step 3819 / num_points 9,287,927`에서 중단
  - traceback는 없지만 4060 Ti 16GB의 이전 실패 패턴과 맞아 `OOM 의심`으로 기록
  - G1 10k는 아직 시작하지 않음
- 기존 `100 iter smoke` 보고서와 projected boundary-view smoke 비교 문서는 reference로 유지하고 덮어쓰지 않기로 했다.
- `G0 10k cell1`을 `max_cache_num 32`와 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`로 다시 실행해 OOM 여부를 확인했다.
  - 결과: `torch.OutOfMemoryError`로 OOM 확정
  - 중단 지점: `step 3810`
  - 에러: `Tried to allocate 456.00 MiB`, 당시 free VRAM `327.31 MiB`
  - 로그:
    - `logs/20260322_160104_g0_10k_cell1_retry.log`
    - `logs/20260322_160104_g0_10k_cell1_retry_gpu.csv`
    - `logs/20260322_160104_g0_10k_cell1_retry_meta.txt`
- 이후 `MAX_CACHE_NUM=16`과 `TRAIN_EXTRA_ARGS="--checkpoint_iterations 3000 3500 3800 4000 5000 7000 10000"`로 10k progression을 다시 시작했다.
  - 재시도 로그:
    - `logs/20260322_162431_subset_10k_progression_cache16.log`
    - `logs/20260322_162431_subset_10k_progression_cache16_gpu.csv`
    - `logs/20260322_162431_subset_10k_progression_cache16_meta.txt`
  - `scripts/run_subset_progression_resume.sh`는 `TRAIN_EXTRA_ARGS`를 받아 checkpoint 저장 인자를 block 학습에 전달하도록 확장했다.
  - 결과: `MAX_CACHE_NUM=16`에서도 `cell1`이 `step 3550` 부근 densification 중 다시 `torch.OutOfMemoryError`로 중단
  - 에러: `Tried to allocate 36.00 MiB`, 당시 free VRAM `27.31 MiB`
  - 중간 checkpoint `output/mc_small_aerial_subset_c4_10k/cells/cell1/chkpnt3500.pth`는 저장됨

## 다음 단계

- subset 4-block 기준 `10k`는 `max_cache_num 16`에서도 실패했으므로, 더 낮은 cache, checkpoint resume, 또는 densification 완화 같은 추가 대응안을 검토
- 현재 `block_1_test`가 `x` 경계를 거의 보지 못하므로, 두 축 seam을 모두 커버하는 test block 또는 manifest 확장 여부 검토
- 필요 시 subset block 수를 늘려 `2x2x1` 또는 더 세분화된 partition에서 확장 검증
