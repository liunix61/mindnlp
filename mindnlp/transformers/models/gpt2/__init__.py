# Copyright 2022 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""
GPT2 Models init
"""
from . import gpt2_config, gpt2_tokenizer, modeling_gpt2
from .modeling_gpt2 import *
from .gpt2_config import *
from .gpt2_tokenizer import *

__all__ = []
__all__.extend(modeling_gpt2.__all__)
__all__.extend(gpt2_config.__all__)
__all__.extend(gpt2_tokenizer.__all__)
