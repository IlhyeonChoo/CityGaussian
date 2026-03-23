# Local Setup Notes

## 현재 상태

- 이 레포는 `V1-Original` 기준 별도 clone이다.
- `origin`은 `git@github.com:IlhyeonChoo/CityGaussian.git`, `upstream`은 `git@github.com:DekuLiuTesla/CityGaussian.git`로 연결했다.
- 현재 로컬 실험 GPU는 `NVIDIA GeForce RTX 4060 Ti (VRAM 16GB)`다.
- VRAM 부족으로 실험 진행이 불가능하다 판단
- VRAM 32GB의 RTX PRO 4500 GPU가 장착된 서버로 옮겨서 마저 진행할 예정 
- 로컬 환경은 `.venv` 기준 `Python 3.11`, `PyTorch 2.7.1+cu128`, `CUDA 12.8`, `TORCH_CUDA_ARCH_LIST=12.0`으로 맞췄다.
- 서브모듈 로컬 수정은 `third_party_patches/`와 `scripts/apply_third_party_patches.sh`로 재적용 가능하게 정리했다.

## 내가 적용한 변경

- `submodules/diff-gaussian-rasterization`, `submodules/simple-knn`가 `CUDA 12.8`에서 빌드되도록 로컬 호환성 패치를 적용했다.
- `LargeLightGaussian` 쪽 이미지 로딩 경로에도 파일 핸들 누적 방지 패치를 적용했다.
- `scene/dataset_readers.py`, `utils/camera_utils.py`, `metrics_large.py`, `merge.py`에서 파일 핸들 누적으로 `Too many open files`가 나던 문제를 수정했다.
- `tools/prepare_matrixcity_small_aerial_v1.py`를 추가해 raw `MatrixCity/small_city/aerial`를 V1이 요구하는 `data/matrix_city/aerial/train/block_all` 구조로 변환할 수 있게 했다.
- `config/mc_small_aerial_coarse.yaml`, `config/mc_small_aerial_c36.yaml`, `config/mc_small_aerial_coarse_smoke.yaml`를 추가했다.
- `config/drjohnson_smoke.yaml`, `config/drjohnson_block2x2.yaml`로 작은 장면에서 coarse 및 block-wise 흐름을 검증했다.

## 검증한 항목

- `../DataCurrent/tandt/db/drjohnson`으로 coarse 학습 스모크를 통과했다.
- `drjohnson_block2x2` block-wise 학습과 merge를 통과했고, 대표 지표는 `SSIM 0.8801 / PSNR 28.2284 / LPIPS 0.3154`였다.
- `MatrixCity small_city aerial`을 V1 형식으로 변환했고, `7672` train 이미지 + `152` test 이미지 구조를 만들었다.
- `mc_small_aerial_coarse_smoke.yaml` 기준 10-iteration coarse 학습과 test 렌더/metric 스모크를 통과했다.

## 주의사항

- `MatrixCity`의 실제 block-wise 학습은 `mc_small_aerial_coarse.yaml`로 30k coarse를 끝낸 뒤 `mc_small_aerial_c36.yaml`로 partition/36개 cell 학습/merge 순서로 진행해야 한다.
- `block_dim`은 현재 `6x6x1`로 맞춰져 있어 총 `36`개 블록이다.
- 기본 이미지 폭이 커서 자동으로 `1600px`로 다운스케일된다. 원본 해상도로 돌리려면 `--resolution 1`을 명시해야 한다.
- `max_cache_num`은 `64`부터 시작하는 편이 안전하다.
- raw `MatrixCity`를 다시 정리하려면 루트 wrapper `../scripts/prepare_citygaussianv1_matrixcity_small_aerial.sh` 또는 내부 도구 `tools/prepare_matrixcity_small_aerial_v1.py`를 사용하면 된다.
- 새 머신에서는 `git submodule update --init --recursive` 뒤 `./scripts/apply_third_party_patches.sh`를 먼저 실행하는 편이 안전하다.
