# 진행 상황

## 2026-06-04

- grid-only second pass 실험을 완료했다.
  - 목표: 현재 best인
    `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`
    merged grid 30k 결과를 다시 xz10 grid로 repartition해서 30000 iteration
    학습한다.
  - config:
    `config/smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_citygs_xz10_30000.yaml`
  - output:
    `output/w2_filtered_manual_passage_no415_best_grid30k_to_citygs_xz10_30000`
  - log:
    `logs/20260604_w2_best_grid30k_to_citygs_xz10_30000.log`
  - pretrain cell counts:
    `[0, 755829, 615137, 147213, 3, 0, 135829, 844931, 476400, 2]`
  - empty PLYs were prepared for cells `0` and `5`; cells `4` and `9`
    remain a risk because they start from only `3` and `2` pretrain
    Gaussians.
  - result: `SSIM 0.8488`, `PSNR 22.7897`, `LPIPS 0.3780`,
    merged Gaussians `868,154`
  - previous best 대비 `SSIM -0.0102`, `PSNR -0.6576`,
    `LPIPS +0.0180`으로 악화했다. PSNR 개선 view는 `7/36`개뿐이다.
  - 결론: grid30k -> manual-unit30k 실패 branch보다는 훨씬 낫지만,
    current best를 대체하지 않는다.
  - run note:
    `docs/reports/20260604_w2_grid30k_secondpass_30000.md`
- grid30k -> manual-unit30k 후속 실험을 완료했다.
  - output: `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000`
  - metrics: `SSIM 0.7822`, `PSNR 15.9809`, `LPIPS 0.4517`, merged Gaussians `7,248,911`
  - 이전 best `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000` 대비 `PSNR -7.4664`, `SSIM -0.0767`, `LPIPS +0.0917`로 크게 악화했다.
  - overlap diagnostic에서는 모든 unit의 `outside_expanded=0`이지만, `411<->412 mean 0.835`, `401<->passage1 mean 0.739`, `passage1<->passage2 mean 0.670`처럼 close-center overlap이 매우 높다.
  - 결론: 이 branch는 current best가 아니며, conflict-aware merge나 post-merge deduplication 없이는 이어가지 않는다. 상세 기록: `docs/reports/20260604_w2_grid30k_to_manual_units_30000.md`
- 현재 best 36-view candidate인
  `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`
  grid 30k 결과를 manual-unit 10분할로 다시 30000 iteration 학습하는
  후속 실험을 시작했다.
  - config:
    `config/smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000.yaml`
  - output:
    `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000`
  - log:
    `logs/20260604_w2_best_grid30k_to_manual_units_30000.log`
  - command:
    `CONFIG=smoke_test/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000 RANGE_FILE=data/W2_4_3_merge_rooms_with_passage_v3_undistorted/sub_passage_manual_no415.txt PYTHON_BIN=.venv/bin/python GPU_RETRY_SECONDS=10 START_DELAY_SECONDS=20 PORT=7000 TRAIN_EXTRA_ARGS='--max_cache_num 256' SKIP_EXISTING_CELLS=1 RUN_RENDER=1 RUN_METRICS=1 ./scripts/run_colmap_unit_citygs_filtered_subtxt_no415_pruned_units.sh`
  - pretrain bounds diagnostic:
    `output/w2_filtered_manual_passage_no415_best_grid30k_to_manual_units_30000/diagnostics/unit_pretrain_counts_iter30000.json`
  - all 10 manual units have non-empty pretrain bounds counts; largest units are
    `passage1` (`1,466,913`) and `passage3` (`1,589,714`), so passage density
    conflict remains the main risk.
  - run note:
    `docs/reports/20260604_w2_grid30k_to_manual_units_30000.md`

## 2026-06-03

- W2 강의실/복도 분할 실험에서는 overlap-aware partition/training/merge를 일단 보류하기로 결정했다.
  - 보류 대상: `data_partition_overlap.py`, `train_large_overlap.py`, `merge_overlap.py`, `config/g1_overlap15*.yaml`, `config/g2_overlap25*.yaml`
  - 현재 W2 실험 축은 `partition_mode: colmap_unit` 기반의 단일 소유 camera assignment, point/core-point 정리, train-time bounds pruning, merge-time bounds filtering을 우선 안정화한다.
  - `unit_aabb_margin`은 bounds padding이며, 여러 block이 같은 camera를 공유하는 overlap-aware 학습이 아니다.
- 최근 `subtxt_no415_pruned_units` 및 `subtxt_passage_manual_no415_pruned_units` 실행은 overlap-aware 실험이 아니라 single-owner colmap unit 실험으로 분류한다.
- 수동 passage split 기준 1000-iteration smoke 결과는 `docs/reports/20260603_subtxt_passage_manual_no415_pruned_unit_1000.md`에 기록했다.
- single-owner 추천 경로의 bounds/overlap 진단 도구를 `tools/analyze_unit_gaussian_overlap.py`로 추가했고, 1000-iteration 결과 비교는 `docs/reports/20260603_single_owner_overlap_diagnostic_1000.md`에 기록했다.
- 수동 passage split 기준 15000-iteration 학습, merge, 선택 view render를 완료했다.
  - output: `output/scene_W2_4_3_merged_rooms_passage_v3_no405410416_filtered_subtxt_passage_manual_no415_pruned_units_15000`
  - merged Gaussians: `4,991,356`
  - 선택 36-view metrics: `SSIM 0.7785`, `PSNR 15.5608`, `LPIPS 0.4366`
  - 시각 확인 결과 merged render는 여전히 뿌연/흐림 현상이 크며, 특히 passage 및 방-복도 접점이 문제로 보인다.
  - 상세 기록: `docs/reports/20260603_subtxt_passage_manual_no415_pruned_unit_15000.md`
- 같은 수동 passage split을 원래 CityGaussian 순서대로 coarse 30000 후
  unit 15000으로 다시 실행했다.
  - coarse config: `config/smoke_test/w2_filtered_manual_passage_no415_coarse_30000.yaml`
  - unit config: `config/smoke_test/w2_filtered_manual_passage_no415_coarsefirst_units_15000.yaml`
  - output: `output/w2_filtered_manual_passage_no415_coarsefirst_units_15000`
  - coarse output: `output/w2_filtered_manual_passage_no415_coarse_30000/point_cloud/iteration_30000/point_cloud.ply`
  - merged Gaussians: `4,896,739`
  - 선택 36-view metrics: `SSIM 0.7827`, `PSNR 15.8134`, `LPIPS 0.4396`
  - non-coarse 15k 대비 `SSIM +0.0042`, `PSNR +0.2526`,
    `LPIPS +0.0030`으로 수치 개선은 작고, 시각 품질은 여전히 불만족스럽다.
  - bounds diagnostic에서는 모든 unit의 expanded bounds leakage가 `0`이지만,
    cross-unit close-center overlap이 여전히 크다. 주요 pair:
    `411<->412 mean 0.814`, `401<->passage1 mean 0.772`,
    `412<->passage3 mean 0.723`, `passage2<->passage3 mean 0.650`,
    `passage1<->passage2 mean 0.628`.
  - 결론: coarse-first 순서 자체는 성공했지만 30k unit run으로 그대로
    승격하지 않는다. 다음은 high-overlap pair 중심의 merge/post-merge
    conflict cleanup 또는 tighter merge pruning을 먼저 검증한다.
  - 상세 기록: `docs/reports/20260603_subtxt_passage_manual_no415_pruned_unit_coarsefirst_15000.md`
- manual-unit 결과를 유지하는 대신 기존 CityGaussian식 xz10 grid로 다시
  쪼개는 15000-iteration follow-up 두 가지를 완료했다.
  - coarse 30k 결과 -> xz10 grid 15k:
    `output/w2_filtered_manual_passage_no415_coarse_citygs_xz10_15000`
    - merged Gaussians: `1,357,239`
    - 선택 36-view metrics: `SSIM 0.8241`, `PSNR 20.3612`,
      `LPIPS 0.4034`
  - coarse-first manual-unit 15k merged 결과 -> xz10 grid 15k:
    `output/w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000`
    - merged Gaussians: `1,895,774`
    - 선택 36-view metrics: `SSIM 0.8428`, `PSNR 21.7425`,
      `LPIPS 0.3811`
    - `grid_pretrain_filter_mode=bounds`를 사용했고, filtered pretrain이
      없는 grid cells `0`, `4`, `5`, `9`는 0-vertex PLY로 명시 처리했다.
  - contact sheet 기준으로도 manual-unit 계열보다 grid 계열이 훨씬
    안정적이다. 다만 `00004`, `00005`, `00008`, `00029`, `00035` 등 일부
    문/복도 경계 프레임에는 흐림과 번짐이 남아 있다.
  - 현재 30k 후보는
    `w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000`
    경로다.
  - 상세 기록: `docs/reports/20260603_grid_citygs_xz10_followups_15000.md`
- W2 30k follow-up sequence를 완료하고 분석했다.
  - 1단계: best grid 15k merged 결과 ->
    `w2_filtered_manual_passage_no415_best_grid15k_to_citygs_xz10_30000`
    완료
    - merged Gaussians: `2,076,198`
    - 선택 36-view metrics: `SSIM 0.8566`, `PSNR 23.3606`,
      `LPIPS 0.3641`
  - 2단계: coarse 30k 재사용 -> manual-unit 30k merged 모델
    `w2_filtered_manual_passage_no415_manual_units_coarse30k_30000`
    완료
    - merged Gaussians: `5,980,856`
    - 선택 36-view metrics: `SSIM 0.7766`, `PSNR 15.3306`,
      `LPIPS 0.4489`
    - 직접 렌더 모델로는 15k manual-unit보다 악화
  - 3단계: manual-unit 30k merged 모델 -> xz10 grid 30k
    `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`
    완료
    - merged Gaussians: `2,057,987`
    - 선택 36-view metrics: `SSIM 0.8590`, `PSNR 23.4473`,
      `LPIPS 0.3600`
    - 현재 36-view 기준 best render candidate
  - 완료 시각: `2026-06-04T02:14:36+0000`
  - logs:
    `logs/20260603_w2_best_grid15k_to_citygs_xz10_30000.log`,
    `logs/20260603_w2_manual_units_coarse30k_30000.log`,
    `logs/20260603_w2_manual_units30k_to_citygs_xz10_30000.log`,
    `logs/20260603_w2_30k_followup_sequence.log`
  - 주의: metrics는 `Train cameras: 36, Test cameras: 0`인
    `manual_passage_review_15000` 기준이며, held-out 일반화 지표가 아니다.
    xz10 grid cells `0`, `4`, `5`, `9`는 여전히 empty cell이고,
    manual-unit partition에는 `679/6580` camera 미매칭 경고가 남아 있다.
  - 상세 runbook:
    `docs/reports/20260603_w2_30k_followup_runbook.md`
  - 상세 분석:
    `docs/reports/20260604_w2_30k_followup_analysis.md`
- overlap 보류 결정과 재개 조건은 `docs/reports/20260603_overlap_deferred_for_w2_room_passage.md`에 별도 기록했다.

## 2026-04-06

- 이전 임시 `RTX 4060 Ti 16GB` 서버 기준 setup 메모를 `docs/legacy/20260321_local_setup_prev_server.md`로 분리했다.
- 이전/현재 서버 비교 문서와 worktree 이관 판단 문서를 `docs/legacy/`로 이동해 historical context로 분류했다.
- 이전 16GB 복구 스크립트는 `scripts/legacy/run_subset_progression_resume.sh`로 아카이브했고, 현재 기본 progression 경로는 `scripts/run_subset_progression_current_server.sh`로 정리했다.
- 루트 `LOCAL_SETUP_NOTES.md`는 현재 서버 기준 active setup 메모로 갱신했다.

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
- `config/g1_overlap15_subset_5k.yaml` 기준 G1 5k는 partition과 cell0 5k 학습까지 완료했고, 나머지 `G1 5k -> 10k progression`은 현재 `scripts/legacy/run_subset_progression_resume.sh`로 보관된 복구 스크립트로 이어서 재시작 가능하게 정리했다.

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
- 현재 `scripts/legacy/run_subset_progression_resume.sh`로 보관된 복구 스크립트는 `TRAIN_EXTRA_ARGS`를 받아 checkpoint 저장 인자를 block 학습에 전달하도록 확장했다.
  - 결과: `MAX_CACHE_NUM=16`에서도 `cell1`이 `step 3550` 부근 densification 중 다시 `torch.OutOfMemoryError`로 중단
  - 에러: `Tried to allocate 36.00 MiB`, 당시 free VRAM `27.31 MiB`
  - 중간 checkpoint `output/mc_small_aerial_subset_c4_10k/cells/cell1/chkpnt3500.pth`는 저장됨

## 다음 단계

- subset 4-block 기준 `10k`는 `max_cache_num 16`에서도 실패했으므로, 더 낮은 cache, checkpoint resume, 또는 densification 완화 같은 추가 대응안을 검토
- 현재 `block_1_test`가 `x` 경계를 거의 보지 못하므로, 두 축 seam을 모두 커버하는 test block 또는 manifest 확장 여부 검토
- 필요 시 subset block 수를 늘려 `2x2x1` 또는 더 세분화된 partition에서 확장 검증
