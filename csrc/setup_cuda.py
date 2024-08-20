# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess

import paddle
from paddle.utils.cpp_extension import CUDAExtension, setup


def strtobool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ValueError(
            f"Truthy value expected: got {v} but expected one of yes/no, true/false, t/f, y/n, 1/0 (case insensitive)."
        )


def clone_git_repo(version, repo_url, destination_path):
    try:
        subprocess.run(["git", "clone", "-b", version, "--single-branch", repo_url, destination_path], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def get_sm_version():
    prop = paddle.device.cuda.get_device_properties()
    cc = prop.major * 10 + prop.minor
    return cc


def get_gencode_flags():
    if not strtobool(os.getenv("FLAG_LLM_PDC", "False")):
        prop = paddle.device.cuda.get_device_properties()
        cc = prop.major * 10 + prop.minor
        return ["-gencode", "arch=compute_{0},code=sm_{0}".format(cc)]
    else:
        # support more cuda archs
        return [
            "-gencode",
            "arch=compute_80,code=sm_80",
            "-gencode",
            "arch=compute_75,code=sm_75",
            "-gencode",
            "arch=compute_70,code=sm_70",
        ]


gencode_flags = get_gencode_flags()
library_path = os.environ.get("LD_LIBRARY_PATH", "/usr/local/cuda/lib64")

sources = [
    "./generation/save_with_output.cc",
    "./generation/set_value_by_flags.cu",
    "./generation/token_penalty_multi_scores.cu",
    "./generation/token_penalty_multi_scores_v2.cu",
    "./generation/stop_generation_multi_ends.cu",
    "./generation/fused_get_rope.cu",
    "./generation/get_padding_offset.cu",
    "./generation/qkv_transpose_split.cu",
    "./generation/rebuild_padding.cu",
    "./generation/transpose_removing_padding.cu",
    "./generation/write_cache_kv.cu",
    "./generation/encode_rotary_qk.cu",
    "./generation/get_padding_offset_v2.cu",
    "./generation/rebuild_padding_v2.cu",
    "./generation/set_value_by_flags_v2.cu",
    "./generation/stop_generation_multi_ends_v2.cu",
    "./generation/update_inputs.cu",
    "./generation/get_output.cc",
    "./generation/save_with_output_msg.cc",
    "./generation/write_int8_cache_kv.cu",
    "./generation/step.cu",
    "./generation/quant_int8.cu",
    "./generation/dequant_int8.cu",
    "./generation/flash_attn_bwd.cc",
    "./generation/tune_cublaslt_gemm.cu",
]

cutlass_dir = "./generation/cutlass_kernels/cutlass"
if not os.path.exists(cutlass_dir) or not os.listdir(cutlass_dir):
    if not os.path.exists(cutlass_dir):
        os.makedirs(cutlass_dir)
    clone_git_repo("v3.5.0", "https://github.com/NVIDIA/cutlass.git", cutlass_dir)
gencode_flags += [
    "-Igeneration/cutlass_kernels",
    "-Igeneration/cutlass_kernels/cutlass/include",
    "-Igeneration/fp8_gemm_with_cutlass",
    "-Igeneration",
]
cc = get_sm_version()

if cc >= 89:
    sources += [
        "./generation/fp8_gemm_with_cutlass/fp8_fp8_half_gemm.cu",
        "./generation/cutlass_kernels/fp8_gemm_fused/fp8_fp8_gemm_scale_bias_act.cu",
        "./generation/fp8_gemm_with_cutlass/fp8_fp8_fp8_dual_gemm.cu",
        "./generation/cutlass_kernels/fp8_gemm_fused/fp8_fp8_dual_gemm_scale_bias_act.cu",
    ]

setup(
    name="paddlenlp_ops",
    ext_modules=CUDAExtension(
        sources=sources,
        extra_compile_args={
            "cxx": ["-O3"],
            "nvcc": [
                "-O3",
                "-U__CUDA_NO_HALF_OPERATORS__",
                "-U__CUDA_NO_HALF_CONVERSIONS__",
                "-U__CUDA_NO_BFLOAT16_OPERATORS__",
                "-U__CUDA_NO_BFLOAT16_CONVERSIONS__",
                "-U__CUDA_NO_BFLOAT162_OPERATORS__",
                "-U__CUDA_NO_BFLOAT162_CONVERSIONS__",
            ]
            + gencode_flags,
        },
        libraries=["cublasLt"],
        library_dirs=[library_path],
    ),
)
