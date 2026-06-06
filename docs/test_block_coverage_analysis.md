# `block_1_test` Boundary Coverage Analysis

## 1. `tools/prepare_matrixcity_small_aerial_v1.py` 기준 train/test block 선택과 디렉터리 구조

이 준비 스크립트의 기본 train block 목록은 `block_1`부터 `block_10`까지이고, 기본 test block 목록은 `block_1_test` 하나다 (`tools/prepare_matrixcity_small_aerial_v1.py:11-12`). CLI는 `--train-blocks`와 `--test-blocks`를 문자열로 받되 기본값은 빈 문자열이며, 비어 있으면 default 목록을 쓰고, 값이 있으면 쉼표로 분리해 다중 block을 받을 수 있다 (`tools/prepare_matrixcity_small_aerial_v1.py:15-30`).

실제 출력 디렉터리 레이아웃은 `main()`에서 고정된다. train split은 `output_dir/train/block_all`, test split은 `output_dir/test/block_all_test`, pose export는 `output_dir/pose/block_all`로 만들어진다 (`tools/prepare_matrixcity_small_aerial_v1.py:264-275`). 즉, 여러 raw block을 넣더라도 CityGaussian 쪽에서는 하나의 merged train/test split으로 보게 된다.

`prepare_split()`은 `split_blocks`를 순회하면서 각 block의 `transforms_origin.json`과 이미지들을 읽고, `images/`, `sparse/0/`, `input -> images` symlink, `transforms.json`, `mapping.json`을 생성한다 (`tools/prepare_matrixcity_small_aerial_v1.py:157-175`, `tools/prepare_matrixcity_small_aerial_v1.py:183-253`). 따라서 train/test block 연결 방식은 “raw block name 목록 -> 하나의 CityGaussian-compatible `block_all` 또는 `block_all_test` 디렉터리”다 (`tools/prepare_matrixcity_small_aerial_v1.py:278-299`).

## 2. `tools/select_boundary_views.py` 기준 “boundary view”의 operational definition

- 이 스크립트가 기록하는 selector 이름은 오직 `strict_projected_boundary_v1` 하나다. 즉, 현재 repo에서 “strict”는 별도 preset이 아니라 이 projected selector 자체를 가리키며, named “loose” 모드는 구현돼 있지 않다 (`tools/select_boundary_views.py:22-34`, `tools/select_boundary_views.py:156-181`).
- 내부 경계는 `block_dim`에서 `x`와 `y` 축만 만든다. `build_internal_boundaries()`는 `x`/`y` 축만 순회하고, `2x2x1`이면 `x_0.5000`과 `y_0.5000` 두 경계만 생긴다. `z` 경계는 현재 프로토콜에 없다 (`tools/projected_boundary_utils.py:76-89`).
- 어떤 view가 boundary view로 선택되려면, 경계 양쪽(`neg`/`pos`)에서 depth와 화면 내부 조건을 통과한 projected point가 각각 최소 `min_side_points`개 이상 있어야 한다. 한쪽이라도 부족하면 탈락한다 (`tools/select_boundary_views.py:88-113`, `tools/projected_boundary_utils.py:126-149`).
- 그 뒤에도 보이는 seam의 projected span이 `min_span_px` 이상이어야 하고, 조건을 통과한 경우에만 `compute_crop_box()`로 crop이 계산된다. 즉 “strict”는 단순 좌표 근접이 아니라 projected visibility와 span까지 요구하는 규칙이다 (`tools/select_boundary_views.py:115-142`, `tools/projected_boundary_utils.py:177-206`).
- “projected”와 “strip”은 다른 프로토콜이다. `select_boundary_views.py`는 3D point cloud를 카메라에 투영해 seam visibility를 판정하는 반면, `boundary_lpips.py`는 render/gt 이미지에서 x/y boundary fraction 기반 고정 strip crop을 잘라 LPIPS를 계산한다 (`tools/select_boundary_views.py:37-51`, `tools/select_boundary_views.py:86-142`, `tools/boundary_lpips.py:39-67`, `tools/boundary_lpips.py:73-99`).

## 3. `setup_current_server_experiments.sh`와 `run_subset_progression_current_server.sh`가 single test block에 묶이는 방식

현재 setup 스크립트는 `TRAIN_BLOCKS`와 `TEST_BLOCKS`를 env var로 받고, 기본값은 각각 `block_1,block_4,block_7,block_10`과 `block_1_test`다. boundary manifest 경로 기본값은 `output/boundary_analysis/subset4_block_all_test_strict_current_server.json`이다 (`scripts/setup_current_server_experiments.sh:13-17`).

이 스크립트는 그대로 `tools/prepare_matrixcity_small_aerial_v1.py --train-blocks "$TRAIN_BLOCKS" --test-blocks "$TEST_BLOCKS"`를 호출하고, 이어서 `$SUBSET_DATA_ROOT/test/block_all_test`를 입력으로 boundary manifest를 생성한다 (`scripts/setup_current_server_experiments.sh:58-64`, `scripts/setup_current_server_experiments.sh:81-85`). 즉 기본값을 그대로 쓰면 `block_all_test`는 사실상 `block_1_test` 하나로 구성된다 (`scripts/setup_current_server_experiments.sh:15-16`, `tools/prepare_matrixcity_small_aerial_v1.py:269-293`).

progression 스크립트도 같은 연결을 그대로 사용한다. `CUSTOM_TEST`는 `$DATA_ROOT/test/block_all_test`, `VIEW_MANIFEST`는 `output/boundary_analysis/subset4_block_all_test_strict_current_server.json`로 잡혀 있고 (`scripts/run_subset_progression_current_server.sh:11-16`), render 단계는 항상 `--custom_test "$CUSTOM_TEST"`를 쓰며 filtered/projection eval은 항상 `--view_manifest "$VIEW_MANIFEST"`를 쓴다 (`scripts/run_subset_progression_current_server.sh:63-89`, `scripts/run_subset_progression_current_server.sh:133-146`, `scripts/run_subset_progression_current_server.sh:172-185`).

따라서 현재 current-server subset pipeline에서 `subset4_block_all_test_strict_current_server.json` manifest와 `--custom_test` 경로는 모두 **단일 기본 test block (`block_1_test`)에서 만들어진 `block_all_test`**에 묶여 있다 (`scripts/setup_current_server_experiments.sh:15-16`, `scripts/run_subset_progression_current_server.sh:14-15`).

## 4. `block_1_test`가 현재 커버하는 seam 축과 빠지는 축

실험 매트릭스와 subset config는 현재 subset을 `block_dim [2, 2, 1]`로 정의한다 (`docs/experiment_matrix.md:3-4`, `config/mc_small_aerial_subset_c4_5k.yaml:13-14`). 이 block layout에서 내부 경계는 `x_0.5000`과 `y_0.5000` 두 개뿐이다 (`tools/projected_boundary_utils.py:76-89`).

2026-03-21 진행 기록은 `block_1_test`에 selector를 적용한 결과 “현재 subset은 `y_0.5000` 내부 경계만 커버”한다고 명시한다 (`docs/progress.md:21-23`). 같은 사실이 당시 공식 subset smoke 보고서에서도 더 구체적으로 기록돼 있다. strict projected manifest의 boundary coverage는 `x_0.5000 = 0`, `y_0.5000 = 48`이며, 따라서 “현재 공식 비교는 실제로 보이는 `y` 축 seam만 대상으로 한다”고 정리돼 있다 (`docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md:83-91`).

정리하면:

- 현재 `block_1_test`가 커버하는 축: `y` 축 내부 seam (`y_0.5000`) (`docs/progress.md:21-23`, `docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md:87-91`)
- 현재 `block_1_test`가 거의 커버하지 못하는 축: `x` 축 내부 seam (`x_0.5000`) (`docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md:87-91`, `docs/progress.md:67-68`)

## 5. coverage gap을 닫는 구체적 옵션

### Option A. `block_1_test`를 다른 single test block으로 교체

메커니즘 자체는 이미 있다. `TEST_BLOCKS`는 env var이고 `--test-blocks`는 단일 값이든 쉼표 목록이든 받을 수 있다 (`scripts/setup_current_server_experiments.sh:15-16`, `scripts/setup_current_server_experiments.sh:58-64`, `tools/prepare_matrixcity_small_aerial_v1.py:15-18`, `tools/prepare_matrixcity_small_aerial_v1.py:269-293`).

다만 tracked 파일에서 실제 추가 후보 test block 이름은 보이지 않는다. 현재 명시적으로 드러나는 test block 이름은 `block_1_test`뿐이다 (`tools/prepare_matrixcity_small_aerial_v1.py:11-12`, `scripts/setup_current_server_experiments.sh:15-16`). 따라서 x seam을 보는 다른 raw test block 이름은 사람이 raw dataset 디렉터리에서 확인해야 한다.

| 항목 | 내용 |
|---|---|
| 필요한 파일/운영 변경 | hard-code를 바꾸려면 `scripts/setup_current_server_experiments.sh`의 `TEST_BLOCKS` 기본값과 필요 시 manifest 이름만 바꾸면 된다. env override로 실행하면 tracked 파일 수정 없이도 가능하다 (`scripts/setup_current_server_experiments.sh:13-17`). |
| baseline comparability 영향 | 기존 `block_1_test` canonical 수치와 direct apples-to-apples 비교가 어려워진다. y seam reference를 잃을 수도 있다 (`docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md:87-91`). |
| recompute cost | coarse/G0/G1/G2 재학습은 필요 없다. 대신 새 `block_all_test` 준비, 새 manifest 생성, 그리고 비교 대상 merged model들의 render/metrics/filtered metrics/projected LPIPS를 다시 계산해야 한다 (`tools/prepare_matrixcity_small_aerial_v1.py:286-299`, `scripts/run_subset_progression_current_server.sh:133-146`, `scripts/run_subset_progression_current_server.sh:172-185`). |

### Option B. `block_1_test + another_test_block`를 union한 multi-block test split으로 교체

현재 준비 도구는 원래부터 여러 test block을 하나의 `test/block_all_test`로 합치는 구조다. `prepare_split()`가 `split_blocks` 전체를 순회해 하나의 merged 이미지/pose/mapping 집합을 쓰기 때문이다 (`tools/prepare_matrixcity_small_aerial_v1.py:157-175`, `tools/prepare_matrixcity_small_aerial_v1.py:183-253`). 따라서 이 옵션은 새로운 code path를 요구하지 않는다. `TEST_BLOCKS=block_1_test,<confirmed_x_seam_block>`처럼 주면 된다 (`scripts/setup_current_server_experiments.sh:15-16`, `scripts/setup_current_server_experiments.sh:58-64`).

이 방식은 현재 y seam coverage를 유지하면서 x seam coverage를 추가할 수 있다는 점이 장점이다. 현재 render/eval 스크립트는 모두 `block_all_test`라는 하나의 merged test root만 기대하므로, union test split이 현재 파이프라인과 가장 잘 맞는다 (`scripts/run_subset_progression_current_server.sh:14-15`, `scripts/run_subset_progression_current_server.sh:133-146`, `scripts/run_subset_progression_current_server.sh:172-185`).

| 항목 | 내용 |
|---|---|
| 필요한 파일/운영 변경 | code change는 필수 아님. `TEST_BLOCKS` 값만 multi-block으로 바꾸고 setup를 다시 돌리면 된다. 재현성을 위해 hard-code default를 바꾸거나 새 manifest 이름을 주려면 `scripts/setup_current_server_experiments.sh`와 필요 시 `scripts/run_subset_progression_current_server.sh`의 `VIEW_MANIFEST` 기본값만 조정하면 된다 (`scripts/setup_current_server_experiments.sh:13-17`, `scripts/run_subset_progression_current_server.sh:14-16`). |
| baseline comparability 영향 | 기존 `block_1_test` 단일-block 기준과는 다른 protocol이므로 별도 버전으로 기록해야 한다. 대신 연구 목표인 “두 축 seam 모두에서의 boundary artifact 측정”에는 더 직접적이다 (`docs/experiment_matrix.md:87-88`, `docs/progress.md:67-68`). |
| recompute cost | coarse/G0/G1/G2 재학습은 필요 없다. 새 union `block_all_test` 준비 후, 비교 대상 merged run들에 대해 render/metrics/filtered metrics/projected LPIPS만 다시 돌리면 된다 (`tools/prepare_matrixcity_small_aerial_v1.py:286-299`, `scripts/run_subset_progression_current_server.sh:133-146`, `scripts/run_subset_progression_current_server.sh:172-185`). |

### Option C. 현재 `block_1_test`는 유지하고 selector를 완화해서 x seam 후보를 더 끌어오기

`select_boundary_views.py`는 `boundary_band`, `min_side_points`, `min_span_px`, `min_depth`, `crop_size`, `padding_px`를 모두 CLI로 노출한다 (`tools/select_boundary_views.py:27-34`). 따라서 현 test split은 그대로 두고, 예를 들어 `boundary_band`를 넓히거나 `min_side_points`/`min_span_px`를 낮춰 x seam 근처 view를 더 많이 살리는 실험은 가능하다 (`tools/select_boundary_views.py:70-75`, `tools/select_boundary_views.py:112-129`, `tools/select_boundary_views.py:169-175`).

| 항목 | 내용 |
|---|---|
| 필요한 파일/운영 변경 | code change는 필요 없다. selector 재실행 인자와 manifest 경로만 바꾸면 된다 (`tools/select_boundary_views.py:22-34`, `scripts/setup_current_server_experiments.sh:81-85`). |
| baseline comparability 영향 | 기존 `strict_projected_boundary_v1`와 직접 비교하기 어렵고, 실제 seam visibility보다 selector 완화 효과가 섞일 수 있다 (`tools/select_boundary_views.py:156-181`). |
| recompute cost | coarse/G0/G1/G2 재학습과 rerender 모두 불필요하다. 새 manifest를 만들고, 이미 렌더된 결과들에 대해 filtered metrics / projected boundary LPIPS만 다시 계산하면 된다 (`scripts/run_subset_progression_current_server.sh:63-89`). |

## 6. 기본 추천안

기본 추천은 **Option B: `block_1_test`를 유지한 채 x seam을 보는 추가 test block을 union하여 multi-block `block_all_test`를 만드는 것**이다.

이유는 세 가지다.

1. 연구 목표가 전체 metric 상승이 아니라 **boundary artifact measurement**이기 때문이다. 그러면 selector를 느슨하게 만드는 것보다 실제 seam coverage를 늘리는 쪽이 더 정직하다 (`docs/experiment_matrix.md:55-69`, `tools/select_boundary_views.py:156-181`).
2. 현재 파이프라인은 원래부터 여러 raw block을 하나의 `block_all_test`로 합치는 준비 경로를 이미 가지고 있다. 즉 새 code path 없이 protocol만 바꿀 수 있다 (`tools/prepare_matrixcity_small_aerial_v1.py:157-175`, `tools/prepare_matrixcity_small_aerial_v1.py:183-253`, `tools/prepare_matrixcity_small_aerial_v1.py:286-299`).
3. 이 방식은 현재 `block_1_test`가 이미 제공하는 `y_0.5000` coverage를 버리지 않고, 빠진 `x_0.5000`만 보완할 수 있다 (`docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md:87-91`, `docs/progress.md:67-68`).

실무적으로는 기존 `block_1_test` 단일-block canonical 수치는 historical reference로 남기고, 앞으로의 공식 seam 비교는 “strict projected boundary on union multi-block test split”으로 버전업하는 것이 맞다 (`docs/experiment_matrix.md:87-88`).

## 7. 추천안을 실행하기 위한 작은 체크리스트

1. raw MatrixCity `small_city/aerial` 디렉터리에서 `x_0.5000` seam이 실제로 보이는 추가 test block 이름을 확인한다. 현재 tracked 파일만으로는 `block_1_test` 외 후보 이름을 확인할 수 없다 (`tools/prepare_matrixcity_small_aerial_v1.py:11-12`, `scripts/setup_current_server_experiments.sh:15-16`).
2. `TEST_BLOCKS=block_1_test,<confirmed_block>` 형태로 subset test split을 다시 준비한다. hard-code를 바꿀지 env override로 운영할지 결정한다 (`scripts/setup_current_server_experiments.sh:15-16`, `scripts/setup_current_server_experiments.sh:58-64`).
3. confusion을 피하려면 새 protocol용 manifest 파일명을 별도로 둔다. 현재 기본값은 `subset4_block_all_test_strict_current_server.json`이다 (`scripts/setup_current_server_experiments.sh:13-14`, `scripts/run_subset_progression_current_server.sh:15`).
4. merged model은 그대로 두고, 새 `block_all_test`에 대해 render/metrics/filtered metrics/projected boundary LPIPS만 다시 계산한다 (`scripts/run_subset_progression_current_server.sh:133-146`, `scripts/run_subset_progression_current_server.sh:172-185`).
5. 결과 문서에는 “old single-block strict protocol”과 “new union-block strict protocol”을 분리해 기록한다. 그렇지 않으면 canonical 수치가 섞인다 (`docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md:83-91`, `docs/experiment_matrix.md:87-88`).

## Open Questions / Human Confirmation Needed

- 추가 x seam test block의 실제 raw 이름은 tracked 파일에서 확인되지 않는다. raw dataset directory를 보고 이름을 확정해야 한다 (`tools/prepare_matrixcity_small_aerial_v1.py:11-12`, `scripts/setup_current_server_experiments.sh:15-16`).
- 앞으로 공식 비교 기준을 기존 `block_1_test` 단독 strict protocol로 유지할지, 아니면 union multi-block strict protocol로 승격할지 사람 판단이 필요하다. 두 값은 직접 비교치가 아니라 protocol version이 다르다 (`docs/reports/G0_G1_20260321_subset4_compare_and_feasibility.md:83-91`, `docs/experiment_matrix.md:87-88`).
