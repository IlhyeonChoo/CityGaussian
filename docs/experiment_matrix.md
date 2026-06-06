# 실험 매트릭스

> Subset 4-block (block_1, block_4, block_7, block_10) 기준
> block_dim: [2, 2, 1], test: block_1_test (152장)

## 현재 상태 주석

- 이 매트릭스는 MatrixCity subset 기준 G0/G1/G2 overlap feasibility 기록이다.
- 2026-06-03 기준 W2 강의실/복도 실험에서는 overlap-aware 경로를 보류한다.
- W2의 현재 active path는 `partition_mode: colmap_unit` 기반 single-owner unit 실험이며, `unit_aabb_margin`은 bounds padding일 뿐 overlap-aware camera sharing이 아니다.
- overlap 재개 조건은 `docs/reports/20260603_overlap_deferred_for_w2_room_passage.md`를 따른다.
- W2 manual passage split의 corrected coarse-first 15k 결과는
  `docs/reports/20260603_subtxt_passage_manual_no415_pruned_unit_coarsefirst_15000.md`에 기록했다.
  원래 CityGaussian 순서인 coarse 30k 후 unit 15k/merge는 성공했지만,
  36-view review 기준 `SSIM 0.7827`, `PSNR 15.8134`, `LPIPS 0.4396`으로
  non-coarse 15k 대비 개선이 작고 시각 품질도 여전히 불만족스럽다.
  따라서 동일 설정을 30k unit run으로 승격하지 않고, high-overlap pair
  중심의 merge/post-merge cleanup을 먼저 검토한다.
- W2 manual-unit 대신 기존 CityGaussian식 xz10 grid로 재분할하는
  15000-iteration follow-up은 `docs/reports/20260603_grid_citygs_xz10_followups_15000.md`에
  기록했다. 같은 36-view review 기준 coarse->grid는 `SSIM 0.8241`,
  `PSNR 20.3612`, `LPIPS 0.4034`, merged-unit->grid는 `SSIM 0.8428`,
  `PSNR 21.7425`, `LPIPS 0.3811`로 manual-unit 계열보다 크게 개선됐다.
  현재 30k 승격 후보는
  `w2_filtered_manual_passage_no415_repartition_merged15k_citygs_xz10_15000`
  방향이다. 단, 해당 실험은 filtered pretrain이 없는 grid cells
  `0`, `4`, `5`, `9`를 0-vertex PLY로 명시 처리한 점을 리스크로 유지한다.
- W2 30k follow-up은 `docs/reports/20260604_w2_30k_followup_analysis.md`에
  기록했다. 같은 36-view review 기준 best grid15k->grid30k는
  `SSIM 0.8566`, `PSNR 23.3606`, `LPIPS 0.3641`, manual-unit30k->grid30k는
  `SSIM 0.8590`, `PSNR 23.4473`, `LPIPS 0.3600`으로 현재 최선이다.
  반면 direct manual-unit30k는 `SSIM 0.7766`, `PSNR 15.3306`,
  `LPIPS 0.4489`로 악화되어 직접 렌더 후보에서 제외한다.
  단, 이 수치는 `Train cameras: 36, Test cameras: 0`인 review subset
  기준이며, xz10 empty cells `0`, `4`, `5`, `9`와 manual-unit의
  `679/6580` camera 미매칭 경고를 리스크로 유지한다.
- W2 grid30k -> manual-unit30k 후속 실험은 완료했지만 current best가 아니다.
  `docs/reports/20260604_w2_grid30k_to_manual_units_30000.md`에 기록했다.
  같은 36-view review 기준 `SSIM 0.7822`, `PSNR 15.9809`, `LPIPS 0.4517`,
  merged Gaussians `7,248,911`로 이전 best
  `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`보다
  크게 악화했다. bounds leakage는 없지만 close-center overlap이 높아,
  conflict-aware merge나 post-merge deduplication 없이 이 branch를 계속
  진행하지 않는다.
- W2 grid30k -> xz10 grid30k second-pass 실험도 current best가 아니다.
  `docs/reports/20260604_w2_grid30k_secondpass_30000.md`에 기록했다.
  같은 36-view review 기준 `SSIM 0.8488`, `PSNR 22.7897`,
  `LPIPS 0.3780`, merged Gaussians `868,154`로 이전 best보다 작고
  빠른 모델이 됐지만 품질은 하락했다. current best는 계속
  `w2_filtered_manual_passage_no415_manual_units30k_to_citygs_xz10_30000`이다.

## 현재 실험 구성

### Coarse (전처리)

| ID | Config | Iterations | 상태 | 비고 |
|----|--------|-----------|------|------|
| C-5k | `mc_small_aerial_subset_coarse_5k.yaml` | 5,000 | 완료 | |
| C-10k | `mc_small_aerial_subset_coarse_10k.yaml` | 10,000 | 완료 | |

### G0: Baseline (Non-overlap)

| ID | Config | Iterations | 상태 | 비고 |
|----|--------|-----------|------|------|
| G0-5k | `mc_small_aerial_subset_c4_5k.yaml` | 5,000 | 완료 | SSIM 0.7405, PSNR 25.31, LPIPS 0.4607 |
| G0-10k | `mc_small_aerial_subset_c4_10k.yaml` | 10,000 | OOM (cell1) | legacy 4060 Ti 16GB 서버에서 실패, 현재 서버에서 재시도 대상 |

### G1: Overlap 15%

| ID | Config | Iterations | 상태 | 비고 |
|----|--------|-----------|------|------|
| G1-5k | `g1_overlap15_subset_5k.yaml` | 5,000 | 완료 | SSIM 0.7209, PSNR 24.17, LPIPS 0.4758 |
| G1-10k | `g1_overlap15_subset_10k.yaml` | 10,000 | 미시작 | G0-10k 의존 (동일 coarse) |

### G2: Overlap 25%

| ID | Config | Iterations | 상태 | 비고 |
|----|--------|-----------|------|------|
| G2-5k | `g2_overlap25_subset_5k.yaml` | 5,000 | 미시작 | 신규 config 생성됨 |
| G2-10k | `g2_overlap25_subset_10k.yaml` | 10,000 | 미시작 | 신규 config 생성됨 |

### Smoke Tests

| Config | 용도 |
|--------|------|
| `smoke_test/g1_overlap15_smoke.yaml` | G1 full-data smoke |
| `smoke_test/g1_overlap15_subset_smoke.yaml` | G1 subset smoke |
| `smoke_test/g2_overlap25_smoke.yaml` | G2 full-data smoke (신규) |
| `smoke_test/g2_overlap25_subset_smoke.yaml` | G2 subset smoke (신규) |

## 실행 순서

현재 서버에서는 `run_subset_progression_current_server.sh`를 실행하면 아래 순서로 진행:

1. `setup_current_server_experiments.sh` (데이터 준비, config 생성, manifest 생성)
2. **5k 계열**: C-5k → G0-5k → G1-5k → G2-5k
3. **10k 계열**: C-10k → G0-10k → G1-10k → G2-10k

기완료된 단계는 skip 로직으로 자동 건너뜀.

## 비교 축

### 주 비교: Overlap 비율에 따른 boundary 품질

| 비교 | 검증 포인트 |
|------|------------|
| G0 vs G1 (5k) | overlap 15%가 non-overlap 대비 boundary seam을 줄이는가? |
| G0 vs G2 (5k) | overlap 25%가 15%보다 추가 개선을 주는가? |
| G0 vs G1 vs G2 (10k) | iteration 증가 시 overlap 효과가 유지/확대되는가? |

### 평가 지표

- **전체 test set**: SSIM, PSNR, LPIPS
- **Boundary-view (strict 48장)**: SSIM, PSNR, LPIPS, projected boundary LPIPS
- 도구: `tools/filtered_metrics.py`, `tools/projected_boundary_lpips.py`

## 5k 기준 현재 결과 요약

| 실험 | SSIM | PSNR | LPIPS | Bnd SSIM | Bnd PSNR | Bnd LPIPS | Bnd Proj LPIPS |
|------|------|------|-------|----------|----------|-----------|----------------|
| G0-5k | 0.7405 | 25.31 | 0.4607 | 0.7211 | 24.76 | 0.4822 | 0.4534 |
| G1-5k | 0.7209 | 24.17 | 0.4758 | 0.6692 | 21.92 | 0.5218 | 0.5042 |
| G2-5k | — | — | — | — | — | — | — |

> **참고**: 5k 기준 G1이 G0보다 열세. 100-iter smoke에서는 G1이 소폭 우세했으므로,
> iteration 스케일에 따른 behavior 차이가 존재. G2와 10k 결과로 추가 검증 필요.

## 미결 사항

- [x] 현재 서버 active setup 문서 정리 및 legacy 16GB 메모 분리
- [ ] `output/` 기존 산출물 이관 (coarse 30k, 5k 완료분)
- [ ] G0-10k 새 서버에서 OOM 해소 확인
- [x] 전략 B (Coarse-to-Fine) 코드 경로 조사 → `docs/strategy_b_c2f_feasibility.md`
  - [ ] 설계안 확정: wrapper 실험 우선 vs 정식 기능 (optimizer reset 포함)
  - [ ] 확정된 설계에 맞춰 config/엔트리포인트 작성
- [x] `block_1_test` x축 커버리지 한계 조사 → `docs/test_block_coverage_analysis.md`
  - [ ] 보완책 옵션 선택 (추가 test block vs union manifest vs selector 완화)
  - [ ] 선택된 옵션의 config/script 반영

## 참고 문서

- `docs/strategy_b_c2f_feasibility.md`: 전략 B 구현 가능성 조사 및 최소 설계안
- `docs/test_block_coverage_analysis.md`: boundary-view coverage 한계 분석 및 보완책 옵션
