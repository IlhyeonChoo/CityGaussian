# G1/G2 구현 계획: 전략 A (Overlapping Block Partition)

> 작성일: 2026-03-21
> 대상: G1 (Overlap 15%), G2 (Overlap 25%)
> 상태: 계획 수립 완료, 구현 대기

## Context

CityGaussian V1은 블록별 독립 학습 후 단순 concat으로 병합하기 때문에 블록 경계에서 seam/color mismatch/density gap 아티팩트가 발생한다. G1(overlap 15%), G2(overlap 25%) 실험은 블록을 중첩 확장하고, 중첩 영역 freeze + soft blending merge로 경계 아티팩트를 완화하는 전략이다.

**핵심 제약**: 원본 파일은 최소한으로 수정하고, 실험 로직은 새 파일로 분리한다 (G0 baseline 재현 가능 유지).
- **유일한 원본 수정**: `arguments/__init__.py`에 overlap 파라미터 추가 (기본값 0으로 기존 동작 보존)

---

## 현재 파이프라인 핵심 동작 (수정 전)

| 단계 | 동작 | 핵심 포인트 |
|------|------|-------------|
| Partitioning | `data_partition.py` | SSIM 기반 카메라-블록 할당, contracted [0,1]^3 공간에서 경계 계산 |
| Training | `train_large.py` | **모든** coarse Gaussian을 로드하여 학습, 블록 필터링은 save 시에만 적용 |
| Save | `scene/__init__.py` LargeScene.save() | 블록의 **엄격한 경계** 내 Gaussian만 저장 |
| Merge | `merge.py` blockMerge() | 블록별 PLY를 **단순 concat**, 중복 제거 없음 |

**중요 발견**: 학습 중에는 블록 필터링이 없다 (전체 Gaussian으로 학습). 블록 구분은 카메라 할당(partition mask)과 저장 시 필터링에서만 발생한다.

---

## 수정/생성할 파일 (원본 수정 1개 + 신규 10개)

### 0. `arguments/__init__.py` (원본 수정) -- 파라미터 추가

`ModelParams`에 overlap 관련 파라미터를 명시적으로 추가한다. 기본값은 기존 동작을 보존하도록 설정.

```python
# ModelParams에 추가할 필드
overlap_ratio: float = 0.0          # 0.0=기존 동작, 0.15=G1, 0.25=G2
overlap_freeze: bool = False         # True: overlap zone Gaussian freeze
freeze_after_iter: int = 3000        # freeze 시작 iteration
blend_mode: str = "hard"             # "hard"=기존 concat, "soft"=거리 기반 감쇠
prune_duplicates: bool = False       # merge 시 중복 Gaussian 제거
duplicate_threshold: float = 0.01    # 중복 판정 거리
```

> `overlap_ratio=0.0`, `blend_mode="hard"` 일 때 기존 V1과 동일하게 동작하므로 G0 baseline에 영향 없음.
> `--help`에서 파라미터 확인 가능, config YAML에서도 명시적으로 사용 가능.

### 1. `utils/overlap_utils.py` (~200줄) -- 핵심 유틸리티

모든 overlap 관련 공간 연산을 담당한다.

**함수 목록:**

| 함수 | 역할 |
|------|------|
| `compute_overlap_bounds(block_id, block_dim, overlap_ratio)` | 블록의 core bounds와 expanded bounds를 contracted 공간에서 계산. edge 블록은 [0,1]로 clamp |
| `classify_zones(xyz_contracted, core_bounds, expanded_bounds)` | 각 Gaussian을 Core/Overlap/Outside로 분류, boolean mask 반환 |
| `block_filtering_overlap(block_id, xyz_org, aabb, block_dim, overlap_ratio)` | 원본 `block_filtering`의 overlap 확장 버전 (원본의 `max_z` 미확장 버그 수정) |
| `compute_blend_weights(xyz_contracted, core_bounds, expanded_bounds)` | Core=1.0, Overlap=선형 감쇠(1.0→0.0), 축별 최솟값 사용 |
| `find_duplicates(xyz_all, block_ids_all, threshold)` | 다른 블록 소속 Gaussian 간 거리 < threshold인 중복 탐지, 낮은 blend weight 쪽 제거 |

**의존성**: `utils/large_utils.py`의 `contract_to_unisphere()` 재사용

### 2. `data_partition_overlap.py` (~80줄) -- Overlap 파티셔닝

원본 `data_partition.py`의 `block_partitioning()`을 import하여 호출하되, 확장된 블록 영역의 카메라도 포함하도록 보강한다.

**전략**:
1. 원본 `block_partitioning()` 호출 → base camera mask 생성 (SSIM 기반)
2. `simple_selection = 1.0 + overlap_ratio`로 한 번 더 호출 → 확장 box 기반 mask
3. 두 mask를 OR 병합 → 최종 partition mask 저장

**주의**: `simple_selection` 파라미터는 원본 코드에 이미 존재 (line 84-97)하며, SSIM 체크를 건너뛰고 box 체크만 수행한다.

### 3. `train_large_overlap.py` (~250줄) -- Overlap 학습

원본 `train_large.py`의 `training()` 함수를 기반으로 overlap freeze 로직을 삽입한다.

> **이 파일만 학습 루프 복제가 필요** -- freeze 로직이 `loss.backward()` 직후, `optimizer.step()` 직전에 삽입되어야 하므로.

**삽입 포인트 3곳:**

| 위치 | 삽입 내용 |
|------|-----------|
| 초기화 후 | `compute_overlap_bounds()` → `classify_zones()` → core_mask, overlap_mask 계산 |
| `loss.backward()` 후, `optimizer.step()` 전 | `if iteration > freeze_after_iter`: 모든 param group의 `.grad[overlap_mask] = 0.0` |
| `densify_and_prune()` 후 | Gaussian 수가 변경되므로 zone mask 재계산 |

**Save 오버라이드**: `LargeScene.save()` 대신 expanded bounds로 Gaussian을 필터링하여 저장. 저장 경로: `cells/cell{block_id}/point_cloud_overlap/iteration_{N}/point_cloud.ply`

### 4. `merge_overlap.py` (~150줄) -- Soft Blending Merge

원본 `merge.py`의 `blockMerge()` 패턴을 따르되 3단계 추가:

1. **Load**: 각 블록의 overlap PLY 로드 (expanded bounds 포함)
2. **Blend**: `compute_blend_weights()`로 opacity 조정
   - `_opacity`는 inverse_sigmoid로 저장됨 → `sigmoid(_opacity) * blend_weight`를 다시 inverse_sigmoid
   - clamp 적용으로 수치 안정성 확보
3. **Concat + Dedup**: 전체 concat 후 `find_duplicates()`로 중복 Gaussian 제거

### 5-6. Config 파일

**`config/g1_overlap15.yaml`**, **`config/g2_overlap25.yaml`**

`mc_small_aerial_c36.yaml` 기반 + overlap 파라미터 추가:

```yaml
model_params:
  # ... (mc_small_aerial_c36.yaml과 동일)
  partition_name: "g1_overlap15"  # 또는 "g2_overlap25"
  overlap_ratio: 0.15             # 또는 0.25
  overlap_freeze: true
  freeze_after_iter: 3000
  blend_mode: "soft"
  prune_duplicates: true
  duplicate_threshold: 0.01
```

> 파라미터는 `arguments/__init__.py`의 `ModelParams`에 명시적으로 정의되므로, config YAML에서 바로 사용 가능. `--help`에서도 확인 가능.

### 7-9. 평가 도구 (`tools/` 디렉토리, 각 ~100줄)

| 파일 | 역할 |
|------|------|
| `tools/boundary_lpips.py` | **Primary Metric**. 블록 경계에 해당하는 이미지 영역을 crop하여 LPIPS 계산. 경계 위치는 partition 정보 + 카메라 projection으로 결정 |
| `tools/boundary_crop.py` | 블록 경계를 이미지 좌표로 projection하여 경계 영역 strip을 crop하는 유틸리티. `boundary_lpips.py`와 시각 비교 모두에서 사용 |
| `tools/error_map.py` | GT 이미지와 렌더링 이미지의 pixel-wise 차이를 heatmap으로 시각화. 경계 영역 하이라이트 옵션 포함 |

**추가 도구 (선택적, 후순위):**

| 파일 | 역할 |
|------|------|
| `tools/visualize_partitions.py` | 3D 공간에서 블록 경계와 overlap 영역을 시각화 (matplotlib 3D 또는 open3d) |
| `tools/plot_results.py` | 실험 그룹 간 메트릭 비교 bar chart / table 생성 |

### 10. `config/smoke_test/g1_overlap15_smoke.yaml`

- `iterations: 100`, `densify_until_iter: 50`
- `block_dim: [2, 2, 1]` (4블록, 빠른 검증)
- `overlap_ratio: 0.15`

### 8. `scripts/run_overlap_experiment.sh` (~80줄)

```bash
# 1. Coarse 학습 (G0에서 이미 완료, skip)
# 2. Overlap 파티셔닝
python data_partition_overlap.py --config config/g1_overlap15.yaml

# 3. 블록별 학습 (병렬 가능)
for block_id in $(seq 0 35); do
  python train_large_overlap.py --config config/g1_overlap15.yaml --block_id $block_id
done

# 4. Overlap Merge
python merge_overlap.py --config config/g1_overlap15.yaml

# 5. 렌더링 (원본 그대로 사용)
python render_large.py --config config/g1_overlap15.yaml --custom_test ...

# 6. 메트릭 (원본 그대로 사용)
python metrics_large.py -m output/g1_overlap15 -t val
```

---

## 구현 순서

```
Phase 1: arguments/__init__.py 수정 (overlap 파라미터 추가)
    ↓
Phase 2: utils/overlap_utils.py (핵심 유틸리티)
    ↓
Phase 3: config 파일 3개 (g1, g2, smoke)
    ↓
Phase 4: data_partition_overlap.py
    ↓
Phase 5: train_large_overlap.py
    ↓
Phase 6: merge_overlap.py
    ↓
Phase 7: 평가 도구 (boundary_crop → boundary_lpips → error_map)
    ↓
Phase 8: scripts/run_overlap_experiment.sh
    ↓
Phase 9: Smoke Test 실행 및 검증
```

---

## 검증 계획

### Smoke Test (Phase 7)

| 단계 | 검증 항목 | 성공 기준 |
|------|-----------|-----------|
| Partitioning | 카메라 할당 수 비교 | overlap 블록이 baseline보다 카메라 수 많음 |
| Training | zone mask 출력 | core/overlap/outside 비율이 합리적 (예: 70/20/10) |
| Training | gradient freeze 동작 | `freeze_after_iter` 이후 overlap Gaussian의 위치 변화 없음 |
| Training | expanded PLY 저장 | strict bounds PLY보다 Gaussian 수 많음 |
| Merge | blend weight 적용 | overlap Gaussian의 opacity가 감소됨 |
| Merge | duplicate pruning | 병합 후 총 Gaussian 수 < (블록별 합산) |
| E2E | 렌더링 + 메트릭 | 에러 없이 PSNR/SSIM/LPIPS 수치 출력 |

### 본 실험 검증 (G1 → G2 순서)

1. G1 (overlap 15%) 전체 36블록 학습 → merge → 렌더링 → 메트릭
2. G0 대비 Boundary LPIPS 개선 확인
3. 전체 PSNR/SSIM 손실 범위 확인
4. G2 (overlap 25%) 동일 과정 반복
5. G1 vs G2 trade-off 분석 (품질 향상 vs 모델 크기/학습 시간 증가)

---

## 주요 참조 파일

| 파일 | 참조 이유 | 수정 여부 |
|------|-----------|-----------|
| `arguments/__init__.py` | overlap 파라미터 추가 | **수정** |
| `utils/large_utils.py` | `contract_to_unisphere()` import, `block_filtering()` 참조 (max_z 버그 주의) | 읽기 전용 |
| `train_large.py` | `training()` 함수 구조 복제 기반 | 읽기 전용 |
| `scene/__init__.py` | `LargeScene.save()` 로직 참조 (expanded bounds 저장 구현 시) | 읽기 전용 |
| `merge.py` | `blockMerge()` 패턴 참조 | 읽기 전용 |
| `data_partition.py` | `block_partitioning()` import 및 호출 | 읽기 전용 |
| `config/mc_small_aerial_c36.yaml` | G1/G2 config 템플릿 | 읽기 전용 |
| `scene/gaussian_model.py` | optimizer 구조, param group 이름, `_opacity` 저장 방식 참조 | 읽기 전용 |
| `metrics_large.py` | 메트릭 계산 흐름 참조 (boundary_lpips 구현 시) | 읽기 전용 |

---

## 주의사항

- **`max_z` 버그**: 원본 `block_filtering()`의 line 67에서 `max_z += delta_z/2`가 누락됨. `overlap_utils.py`에서 자체 구현 시 수정
- **Densification 후 mask 갱신**: `densify_and_prune()` 호출 후 반드시 zone mask 재계산
- **Opacity 수치 안정성**: `sigmoid(x) * w`가 0이 되면 `inverse_sigmoid` 발산 → epsilon clamp 필수
- **Edge 블록**: scene 경계의 블록은 expanded bounds를 [0,1]로 clamp
- **대규모 중복 탐지**: `find_duplicates`에서 voxel hashing 또는 KD-tree 사용 (naive O(N^2) 금지)
