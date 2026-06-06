# Strategy B (Coarse-to-Fine) Feasibility

## 1. `arguments/__init__.py` 기준 C2F 관련 파라미터

### 1.1 `arguments/__init__.py` 안에 실제로 있는 항목

`arguments/__init__.py`를 끝까지 읽으면, C2F를 직접 표현하는 전용 필드는 없고, 단계 전환에 재사용할 수 있는 것은 학습 길이, LR 스케줄, densification 윈도우, 그리고 overlap freeze 타이밍 정도다. `ModelParams` 쪽에는 `sh_degree`, `overlap_ratio`, `overlap_freeze`, `freeze_after_iter`, `blend_mode`, `prune_duplicates`, `duplicate_threshold`가 있고, `OptimizationParams` 쪽에는 `iterations`, 각종 LR, densification 관련 윈도우가 있다 (`arguments/__init__.py:47-95`).

| Field | File:line | C2F 관점 의미 |
|---|---|---|
| `sh_degree` | `arguments/__init__.py:49` | coarse/fine 단계에서 표현력 상한을 달리 쓰고 싶을 때 재사용 가능하다. 현재는 단계별 분리가 없다. |
| `overlap_ratio` | `arguments/__init__.py:57` | Strategy A+B에서 coarse/fine 단계 모두 같은 overlap geometry를 유지할지 결정할 때 인접하게 작용한다. |
| `overlap_freeze` | `arguments/__init__.py:58` | overlap 영역을 후반 단계에서 고정하는 staged behavior에 직접 연결된다. |
| `freeze_after_iter` | `arguments/__init__.py:59` | coarse 구간 종료 또는 fine 구간 진입 시점을 iteration으로 표현할 때 직접 사용 가능하다. |
| `blend_mode` | `arguments/__init__.py:60` | 학습 단계가 아니라 merge 쪽 옵션이지만, A+B 실험에서는 coarse/fine 학습 후 merge 해석에 영향을 준다. |
| `prune_duplicates` | `arguments/__init__.py:61` | stage 자체는 아니지만 overlap-aware fine 결과를 merge할 때 계층형 실험의 최종 품질에 영향을 준다. |
| `duplicate_threshold` | `arguments/__init__.py:62` | 위와 동일하게 fine 결과 병합 품질의 후처리 임계값이다. |
| `iterations` | `arguments/__init__.py:79` | coarse/fine 단계별 예산을 나누려면 가장 먼저 분리해야 하는 총 iteration 예산이다. |
| `position_lr_init` | `arguments/__init__.py:80` | stage별 초기 LR 재시작이 필요할 때 핵심이다. |
| `position_lr_final` | `arguments/__init__.py:81` | fine stage에서 더 낮은 종단 LR을 쓰는 설계에 필요하다. |
| `position_lr_delay_mult` | `arguments/__init__.py:82` | coarse/fine 각각의 early-step 완화 강도를 분리할 때 쓸 수 있다. |
| `position_lr_max_steps` | `arguments/__init__.py:83` | stage 길이가 달라지면 xyz LR decay horizon도 stage별로 달라져야 한다. |
| `feature_lr` | `arguments/__init__.py:84` | fine stage에서 SH/color만 더 조심스럽게 조정할지 결정할 때 필요하다. |
| `opacity_lr` | `arguments/__init__.py:85` | stage별 opacity 안정화 강도를 바꾸려면 필요하다. |
| `scaling_lr` | `arguments/__init__.py:86` | coarse 구조 형성 대 fine refinement를 나눌 때 shape update 강도에 직접 영향이 있다. |
| `rotation_lr` | `arguments/__init__.py:87` | fine stage에서 orientation refinement를 별도로 조정할 수 있다. |
| `densification_interval` | `arguments/__init__.py:90` | coarse stage에서는 더 공격적, fine stage에서는 더 보수적으로 바꾸고 싶을 수 있다. |
| `opacity_reset_interval` | `arguments/__init__.py:91` | coarse/fine 경계 전후 opacity reset 정책을 분리할 때 필요하다. |
| `densify_from_iter` | `arguments/__init__.py:92` | coarse stage에서만 densify를 허용하거나 fine stage 시작 후 지연시키는 데 필요하다. |
| `densify_until_iter` | `arguments/__init__.py:93` | coarse stage만 densify하고 fine stage는 refinement-only로 두려면 핵심이다. |
| `densify_grad_threshold` | `arguments/__init__.py:94` | stage별 densification 민감도를 조정할 때 필요하다. |

### 1.2 `arguments/__init__.py`에는 없지만 현재 실제 코드 경로에 필요한 항목

중요한 점은 현재 실행 경로가 `arguments/__init__.py`만으로 구성되지 않는다는 것이다. 실제 YAML 파싱은 `utils/general_utils.py`의 `get_default_lp/get_default_op/get_default_pp`와 `parse_cfg()`를 사용하고, `extract_args()`는 YAML의 모든 key를 `lp/op/pp`에 그대로 복사한다 (`utils/general_utils.py:151-215`, `utils/general_utils.py:217-235`). 그래서 block training에 coarse 결과를 연결하는 핵심 키인 `pretrain_path`는 `arguments/__init__.py`가 아니라 `utils/general_utils.py`에 정의돼 있다 (`utils/general_utils.py:163-178`).

| Field | File:line | C2F 관점 의미 |
|---|---|---|
| `pretrain_path` | `utils/general_utils.py:163-165` | coarse global model을 block training과 partition에 연결하는 현재 C2F-like 경로의 핵심 입력이다. |
| `partition_name` | `utils/general_utils.py:167-170` | coarse 결과로 만든 partition metadata를 block fine training에 연결한다. |
| `block_dim` / `block_id` | `utils/general_utils.py:169-170` | 계층형 설계가 block-wise stage를 돌릴 때 필수다. |
| `aabb` | `utils/general_utils.py:171` | coarse 결과를 어떤 공간 분할로 해석할지 결정한다. |
| `save_block_only` | `utils/general_utils.py:172` | block stage 산출물 저장 형태를 제어하므로 다단계 artifact layout에 영향이 있다. |

## 2. `pretrain_path`가 block training에서 어떻게 소비되는가

현재 subset block config들은 모두 `pretrain_path`를 coarse output의 iteration 디렉터리로 지정한다. baseline block config는 `output/mc_small_aerial_subset_coarse_5k/point_cloud/iteration_5000`, overlap block config는 같은 coarse output을 가리킨다 (`config/mc_small_aerial_subset_c4_5k.yaml:9-10`, `config/g1_overlap15_subset_5k.yaml:9-10`). `parse_cfg()`는 `model_params`를 `lp`에 그대로 복사하므로 이 값은 trainer로 전달된다 (`utils/general_utils.py:227-235`).

`train_large.py`는 `training()` 안에서 Gaussian 인스턴스를 만든 뒤 `LargeScene(dataset, gaussians)`를 호출하고, 그 다음에 `gaussians.training_setup(opt)`를 호출한다 (`train_large.py:40-48`). `train_large_overlap.py`도 같은 순서를 사용한다 (`train_large_overlap.py:87-95`).

`LargeScene`은 생성 시 `args.pretrain_path`를 `self.pretrain_path`에 저장하고, `load_iteration`이 없고 `pretrain_path`가 있으면 `self.gaussians.load_ply(os.path.join(self.pretrain_path, "point_cloud.ply"))`를 실행한 뒤 `spatial_lr_scale`을 설정한다 (`scene/__init__.py:106-110`, `scene/__init__.py:167-170`). `GaussianModel.load_ply()`는 PLY의 xyz/features/opacity/scaling/rotation을 읽어 모두 `nn.Parameter`로 다시 만든다 (`scene/gaussian_model.py:241-283`). 그 뒤 `training_setup()`가 현재 메모리의 Gaussian 파라미터들 위에 optimizer와 LR scheduler를 붙인다 (`scene/gaussian_model.py:162-180`).

따라서 현재 block training의 정확한 호출 경로는 다음과 같다.

1. block config YAML이 `pretrain_path`를 coarse output iteration 디렉터리로 지정한다 (`config/mc_small_aerial_subset_c4_5k.yaml:9-10`, `config/g1_overlap15_subset_5k.yaml:9-10`).
2. `parse_cfg()`가 그 값을 `lp.pretrain_path`로 복사한다 (`utils/general_utils.py:227-235`).
3. trainer가 `LargeScene(lp, gaussians)`를 만든다 (`train_large.py:40-43`, `train_large_overlap.py:87-90`).
4. `LargeScene`가 coarse `point_cloud.ply`를 읽어 Gaussian 파라미터를 초기화한다 (`scene/__init__.py:167-170`, `scene/gaussian_model.py:241-283`).
5. trainer가 그 Gaussian 위에 optimizer를 세팅하고 학습을 시작한다 (`train_large.py:48`, `train_large_overlap.py:95`, `scene/gaussian_model.py:162-180`).

결론: 현재 `pretrain_path`는 block training의 실제 초기값으로 소비된다. 단순 참고용이 아니라, coarse Gaussian이 block training의 starting state로 들어간다 (`scene/__init__.py:167-170`, `scene/gaussian_model.py:241-283`).

## 3. coarse 결과가 partition 단계에 어떻게 들어가는가

`data_partition.py`도 trainer와 동일하게 `parse_cfg()`로 YAML을 읽고 `LargeScene(lp, gaussians, shuffle=False)`를 만든다 (`data_partition.py:131-154`). 이때 subset block config가 `pretrain_path`를 coarse iteration 디렉터리로 가지고 있으므로, partition 단계 역시 `LargeScene` 내부에서 coarse `point_cloud.ply`를 먼저 로드한다 (`config/mc_small_aerial_subset_c4_5k.yaml:9-10`, `scene/__init__.py:167-170`).

그 다음 `block_partitioning()`은 로드된 Gaussian의 좌표 `gaussians.get_xyz`를 contraction space로 옮겨 block mask를 만들고, 원본 Gaussian과 block-masked Gaussian을 각각 렌더한 뒤 SSIM 차이로 camera assignment를 정한다 (`data_partition.py:22-24`, `data_partition.py:46-58`, `data_partition.py:66-76`, `data_partition.py:105-112`). 즉, coarse 결과는 partition의 입력 point cloud이자 camera assignment 판단 근거로 직접 쓰인다 (`data_partition.py:20-118`, `scene/__init__.py:167-170`).

현재 current-server progression도 이 순서를 명시적으로 따른다. 먼저 `run_coarse`가 coarse global model을 만들고, 그 다음 `run_non_overlap`/`run_overlap`이 partition을 만들고 block training으로 들어간다 (`scripts/run_subset_progression_current_server.sh:95-108`, `scripts/run_subset_progression_current_server.sh:110-146`, `scripts/run_subset_progression_current_server.sh:149-185`, `scripts/run_subset_progression_current_server.sh:193-202`).

이 흐름은 이미 **de-facto single-level C2F**로 볼 수 있다. coarse global model이 1) partition 생성과 2) block initialization 둘 다를 결정하기 때문이다 (`data_partition.py:131-154`, `train_large.py:40-48`, `scene/__init__.py:167-170`). 다만 이것은 어디까지나 **global coarse -> one-shot block fine** 한 번뿐인 구조다. 진짜 multi-stage hierarchical schedule이라면 최소한 아래가 더 필요하다.

- block 내부에서 coarse stage와 fine stage를 명시적으로 나누는 추가 budget/control
- stage boundary에서 optimizer/LR/densification policy를 의도적으로 재설정하는 코드
- stage별 artifact 저장 규약과 재개 경로
- 필요하다면 coarse block stage와 fine block stage를 구분하는 명시적 config schema

현재 코드는 block trainer 하나당 `while iteration <= opt.iterations` 단일 루프만 돌기 때문에, block 내부의 2-stage schedule은 아직 없다 (`train_large.py:64-67`, `train_large_overlap.py:110-118`).

## 4. non-vendored 코드에서 보이는 staged training / resume 힌트

literal repo-wide grep 결과를 자동 수집하지는 못했지만, authoritative non-vendored entrypoints와 scripts를 직접 확인했을 때 C2F와 가장 가까운 힌트는 아래였다.

| 힌트 | File:line | 의미 |
|---|---|---|
| `pretrain_path` 주석 | `utils/general_utils.py:163-165` | 코드 주석 자체가 이를 “coarse global model” 경로라고 정의한다. |
| `load_iteration` support | `scene/__init__.py:31-45`, `scene/__init__.py:112-117` | scene/renderer가 특정 iteration 산출물을 다시 여는 경로는 이미 있다. |
| render-time `iteration` 로딩 | `render_large.py:81-92`, `render_large.py:112-137` | post-training 단계는 특정 iteration을 명시적으로 로드할 수 있다. |
| LoD render도 `load_iteration` 사용 | `render_large_lod.py:32-39`, `render_large_lod.py:88-105`, `render_large_lod.py:129-154` | iteration-based artifact loading은 block training 밖에서도 재사용되고 있다. |
| trainer checkpoint CLI | `train_large.py:294-296`, `train_large.py:311`, `train_large_overlap.py:271-273`, `train_large_overlap.py:287-297` | `--checkpoint_iterations`와 `--start_checkpoint`로 2-pass wrapper 실험은 가능하다. |
| checkpoint restore implementation | `train_large.py:49-52`, `train_large_overlap.py:96-99`, `scene/gaussian_model.py:90-106` | resume 시 Gaussian뿐 아니라 optimizer state까지 복원한다. |
| legacy resume wrapper | `scripts/legacy/run_subset_progression_resume.sh:16`, `scripts/legacy/run_subset_progression_resume.sh:40-59`, `scripts/legacy/run_subset_progression_resume.sh:94-107` | 현재 repo는 이미 “resume via checkpoint”를 실험 운영 도구로 쓴 적이 있다. |

반대로, `train_large.py`와 `train_large_overlap.py` 안에는 `stage`, `phase`, `fine` 같은 명시적 stage-machine이 없고, coarse/fine을 구분하는 내부 branch도 없다. 현재 staged behavior는 `freeze_after_iter` 같은 단일 임계값 기반일 뿐이다 (`train_large.py:64-67`, `train_large_overlap.py:170-176`).

## 5. Strategy B를 기존 config + wrapper만으로 구현할 수 있는가

### 5.1 가능한 부분: 약한 형태의 2-pass 실험

기존 코드만으로도 아래와 같은 “약한” Strategy B pilot은 가능하다.

1. global coarse는 현재처럼 `pretrain_path`로 준비한다 (`config/mc_small_aerial_subset_c4_5k.yaml:9-10`, `scripts/run_subset_progression_current_server.sh:95-108`).
2. block trainer를 짧은 `iterations`의 stage-1 config로 먼저 실행한다 (`arguments/__init__.py:79-95`).
3. stage 경계에서 checkpoint를 저장한다 (`train_large.py:294-295`, `train_large_overlap.py:271-272`).
4. stage-2 config로 같은 block trainer를 다시 실행하면서 `--start_checkpoint`로 이어받는다 (`train_large.py:49-52`, `train_large.py:311`, `train_large_overlap.py:96-99`, `train_large_overlap.py:287-297`).

즉, **wrapper-only pilot** 자체는 가능하다. coarse global initialization과 checkpoint resume라는 두 조각은 이미 있다 (`scene/__init__.py:167-170`, `train_large.py:49-52`).

### 5.2 부족한 부분: “repo에 남길 만한” 진짜 C2F는 아직 아님

문제는 `--start_checkpoint`가 Gaussian만 아니라 optimizer state도 함께 복원한다는 점이다 (`scene/gaussian_model.py:90-106`). 그리고 현재 per-iteration LR 업데이트는 `xyz` param group만 갱신한다 (`scene/gaussian_model.py:182-188`). 따라서 stage-2에서 다른 LR budget을 기대하더라도, checkpoint에서 돌아온 non-xyz optimizer state는 그대로 유지될 가능성이 높다. 이 부분은 코드로 확인되는 사실들로부터의 합리적 추론이다 (`scene/gaussian_model.py:90-106`, `scene/gaussian_model.py:182-188`).

그래서 결론은 다음과 같다.

- **pilot 수준의 wrapper-only 2-pass**: 가능
- **진짜 Strategy B를 baseline-preserving 기능으로 repo에 넣기**: 새 코드가 필요

필요한 위치는 정확히 다음이다.

1. `train_large.py`: block 내부 2-stage orchestration 추가
2. `train_large_overlap.py`: overlap-aware 2-stage orchestration 추가
3. `scene/gaussian_model.py`: “optimizer까지 복원”과 “model만 복원 후 optimizer reset”을 구분하는 helper 추가
4. `utils/general_utils.py`: `c2f_*` 기본값을 문서화된 runtime defaults로 추가

## 6. overlap 인프라를 재사용하는 최소 C2F 설계 제안

### 6.1 제안하는 새 config field와 기본값

아래 이름들은 현재 읽은 `arguments/__init__.py`와 `utils/general_utils.py`의 기본값 집합에 없으므로, additive opt-in field로 넣기 적합하다 (`arguments/__init__.py:47-117`, `utils/general_utils.py:151-215`).

| Proposed field | Default | 위치 제안 | 이유 |
|---|---|---|---|
| `c2f_enabled` | `False` | `model_params` 또는 `optim_params` | baseline-preserving opt-in gate가 필요하다. |
| `c2f_coarse_iterations` | `0` | `optim_params` | block-local coarse stage 길이를 명시한다. `0`이면 비활성화된다. |
| `c2f_reset_optimizer` | `True` | `model_params` 또는 `optim_params` | stage-2 진입 시 checkpoint optimizer state를 그대로 쓸지, clean restart할지 분기한다. |

필요 시 2차 확장으로 `c2f_stage_checkpoint`나 `c2f_refilter_at_boundary` 같은 옵션을 더할 수 있지만, 최소 설계에는 위 세 개면 충분하다. 현재 `extract_args()`가 YAML key를 그대로 `lp/op/pp`에 복사하므로, 구현 코드는 `getattr(..., default)`로 시작해도 되고, 정식화하려면 `utils/general_utils.py`에 기본값을 추가하면 된다 (`utils/general_utils.py:217-235`).

### 6.2 새 entrypoint가 필요한가

최소 설계 기준으로는 **새 `train_large_c2f.py`가 꼭 필요하지 않다**. 기존 `train_large.py`와 `train_large_overlap.py`를 `c2f_*` 플래그로 확장하는 쪽이 중복이 적다. 두 파일은 이미 동일한 main structure를 공유하고, overlap trainer는 zone mask / overlap freeze를 추가로 가지고 있기 때문에 A+B 실험은 `train_large_overlap.py`를 그대로 재사용하는 편이 자연스럽다 (`train_large.py:281-314`, `train_large_overlap.py:259-300`, `train_large_overlap.py:26-80`, `train_large_overlap.py:170-176`).

추천 방향:

- baseline C2F: `train_large.py`에 `c2f_*` 추가
- overlap + C2F (A+B): `train_large_overlap.py`에 같은 `c2f_*` 추가
- orchestration script는 기존 호출을 그대로 유지

### 6.3 바꿔야 할 파일과 diff shape

| File | 변경 형태 | 이유 |
|---|---|---|
| `utils/general_utils.py` | `get_default_lp()` 또는 `get_default_op()`에 `c2f_*` 기본값 추가 | runtime defaults를 코드에 명시해 baseline config와 diff를 줄인다. |
| `scene/gaussian_model.py` | `restore(..., restore_optimizer=True)` 형태의 additive API 또는 `restore_model_only()` helper 추가 | stage-2 진입 시 optimizer reset을 clean하게 지원하려면 필요하다. |
| `train_large.py` | 단일 `training()` 루프를 stage-aware helper로 분리하거나, 내부에 `if c2f_enabled and block_id >= 0` 분기 추가 | baseline fine-only와 C2F를 한 entrypoint에서 공존시키기 위함이다. |
| `train_large_overlap.py` | 위와 동일한 stage-aware 분기 추가 | overlap freeze / zone recompute를 유지한 채 A+B에 재사용하기 위함이다. |
| `config/*_c2f*.yaml` | 기존 subset/smoke config의 additive variant 생성 | baseline-preserving 실험 분리를 위해 기존 config를 덮어쓰지 않는 편이 맞다. |
| `scripts/run_subset_progression_current_server.sh` | 선택적 | 기존 trainer 확장 방식을 쓰면 필수는 아니고, 전용 progression label을 추가하고 싶을 때만 건드리면 된다. |

### 6.4 subset 100-iter smoke test 계획

현재 smoke 파이프라인은 coarse 10 iter + block train 100 iter 구조를 이미 갖고 있다 (`config/mc_small_aerial_subset_coarse_smoke.yaml:25-43`, `config/mc_small_aerial_subset_c4_smoke.yaml:30-48`, `config/smoke_test/g1_overlap15_subset_smoke.yaml:37-55`). 이를 그대로 이용한 최소 smoke 계획은 다음이 적절하다.

1. coarse pretrain은 기존 `config/mc_small_aerial_subset_coarse_smoke.yaml`을 그대로 사용한다. 현재도 `output/mc_small_aerial_subset_coarse_smoke/point_cloud/iteration_10`을 block config의 `pretrain_path`로 쓰고 있다 (`config/mc_small_aerial_subset_coarse_smoke.yaml:25-43`, `config/smoke_test/g1_overlap15_subset_smoke.yaml:9-10`).
2. 새 smoke config를 하나 추가한다. 예시 이름은 `config/smoke_test/g1_overlap15_subset_c2f_smoke.yaml`이고, 기존 smoke config에 `c2f_enabled: true`, `c2f_coarse_iterations: 20`, `c2f_reset_optimizer: true`, `optim_params.iterations: 100`을 더하는 방식이 충분하다. 이 제안 필드들은 현재 코드에 없는 신규안이다 (`config/smoke_test/g1_overlap15_subset_smoke.yaml:1-55`, `arguments/__init__.py:47-117`).
3. 실행 순서는 기존 smoke와 동일하게 `data_partition_overlap.py` -> `train_large_overlap.py --block_id 0..3` -> `merge_overlap.py` -> `render_large.py` -> `metrics_large.py`를 따르되, stage 경계 artifact가 남도록 `20`과 `100` 시점 저장을 확인하는 방향이 적절하다. 현재 subset progression의 coarse/partition/train/merge/render/metrics 순서는 이미 정리돼 있다 (`scripts/run_subset_progression_current_server.sh:95-146`, `scripts/run_subset_progression_current_server.sh:149-202`).
4. 성공 기준은 다음 네 가지면 충분하다.
   - cell별 stage-1 경계 시점 artifact가 남는다.
   - stage-2까지 정상 완료된다.
   - overlap merge와 render가 그대로 통과한다.
   - boundary metric 도구가 기존처럼 후처리 가능하다 (`tools/select_boundary_views.py:156-184`, `scripts/run_subset_progression_current_server.sh:63-89`).

## 7. owner agent 판정

Agent 2 가이드에는 소유 범위로 `Freeze scheduling and staged optimization`, `Coarse-to-fine or similar training schedules`, `Checkpoint flow, resume behavior, and per-block training control`이 명시돼 있다 (`.codex/agents/agent2_training_merge.md:15-21`). 따라서 Strategy B의 구현 주체는 기본적으로 **Agent 2**가 맞다.

Agent 1은 `Dataset-to-block partition logic`, `Spatial ranges`, `partition metadata`, `camera assignment rules`를 소유하며, training schedule 변화는 Agent 2로 넘기라고 적혀 있다 (`.codex/agents/agent1_partition_overlap.md:16-21`, `.codex/agents/agent1_partition_overlap.md:69-72`). 따라서 위의 **최소 C2F 설계처럼 현재 partition layout을 그대로 쓰는 경우에는 Agent 1이 필수 소유자가 아니다**.

다만 아래 두 경우에는 Agent 1 협업이 필요하다.

- coarse stage와 fine stage에서 `block_dim` 자체를 다르게 가져가려는 경우
- stage별로 다른 partition metadata나 camera assignment rule을 도입하려는 경우 (`.codex/agents/agent1_partition_overlap.md:16-21`)

## Open Questions / Human Confirmation Needed

- Strategy B를 당장 원하는 수준이 “wrapper-only pilot”인지, 아니면 “optimizer reset까지 포함한 first-class repo feature”인지 확인이 필요하다. 전자면 임시 스크립트로도 가능하지만, 후자면 `scene/gaussian_model.py`와 trainer 본체 수정이 필요하다 (`scene/gaussian_model.py:90-106`, `train_large.py:49-52`).
- stage-2 진입 시 optimizer를 완전히 reset할지, 아니면 checkpoint optimizer를 그대로 이어받을지 연구 의도를 먼저 정해야 한다. 현재 코드만으로는 후자 쪽이 기본이며, 이는 진짜 stage split과는 다를 수 있다 (`scene/gaussian_model.py:90-106`, `scene/gaussian_model.py:182-188`).
- 만약 Strategy B를 “coarse partition -> fine partition” 같은 공간 계층까지 확장하려는 뜻이라면 Agent 1 범위가 즉시 포함된다 (`.codex/agents/agent1_partition_overlap.md:16-21`).
