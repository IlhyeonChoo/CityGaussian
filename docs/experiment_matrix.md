# 실험 매트릭스

> Subset 4-block (block_1, block_4, block_7, block_10) 기준
> block_dim: [2, 2, 1], test: block_1_test (152장)

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
| G0-10k | `mc_small_aerial_subset_c4_10k.yaml` | 10,000 | OOM (cell1) | 4060Ti 16GB에서 실패, 새 서버에서 재시도 필요 |

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

새 서버에서 `run_subset_progression_current_server.sh`를 실행하면 아래 순서로 진행:

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

- [ ] 새 서버 환경 확정 및 `LOCAL_SETUP_NOTES.md` 업데이트
- [ ] `output/` 기존 산출물 이관 (coarse 30k, 5k 완료분)
- [ ] G0-10k 새 서버에서 OOM 해소 확인
- [ ] 전략 B (Coarse-to-Fine) 실험 config 설계 — 현재 코드 경로 미확인
- [ ] `block_1_test`가 x축 경계를 커버하지 못하는 한계 — test block 확장 검토
