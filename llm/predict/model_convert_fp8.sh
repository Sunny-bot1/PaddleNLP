# Copyright (c) 2024 PaddlePaddle Authors. All Rights Reserved.
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

export PYTHONPATH=$(dirname $(pwd)):$PYTHONPATH

model_path=${1:-"/path/to/ckpt"}

python ./predict/model_convert_fp8.py  \
        --model_name_or_path ${model_path} 

python ./predict/export_model.py \
        --model_name_or_path ${model_path} \
        --output_path ${model_path}/export \
        --dtype float16 \
        --quant_type a8w8_fp8 \
        --inference_model \
        --block_attn
        