# Copyright 2023 Huawei Technologies Co., Ltd
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
# pylint: disable=C0103
# pylint: disable=W0613
"""Tokenization classes for ChatGLM."""
import os
from typing import List, Optional, Union, Dict

import sentencepiece as spm
import numpy as np

from ...tokenization_utils import PreTrainedTokenizer
from ....utils.generic import PaddingStrategy

PRETRAINED_VOCAB_MAP = {
    'chatglm-6b': 'https://download.mindspore.cn/toolkits/mindnlp/models/glm/chatglm-6b/ice_text.model'
}


PRETRAINED_POSITIONAL_EMBEDDINGS_SIZES = {
    "chatglm-6b": 2048,
}

class TextTokenizer:
    """Text Tokenizer."""
    def __init__(self, model_path):
        self.sp = spm.SentencePieceProcessor()
        self.sp.Load(model_path)
        self.num_tokens = self.sp.vocab_size()

    def encode(self, text):
        """encode"""
        return self.sp.EncodeAsIds(text)

    def decode(self, ids: List[int]):
        """decode"""
        return self.sp.DecodeIds(ids)

    def tokenize(self, text):
        """tokenize"""
        return self.sp.EncodeAsPieces(text)

    def convert_tokens_to_string(self, tokens):
        """convert tokens to string"""
        return self.sp.DecodePieces(tokens)

    def convert_tokens_to_ids(self, tokens):
        """convert token to ids"""
        return [self.sp.PieceToId(token) for token in tokens]

    def convert_token_to_id(self, token):
        """convert token to id"""
        return self.sp.PieceToId(token)

    def convert_id_to_token(self, idx):
        """convert id to token"""
        return self.sp.IdToPiece(idx)

    def __len__(self):
        return self.num_tokens


class SPTokenizer:
    """SP Tokenizer."""
    def __init__(
            self,
            vocab_file,
            num_image_tokens=20000,
            max_blank_length=80,
            byte_fallback=True,
    ):
        assert vocab_file is not None
        self.vocab_file = vocab_file
        self.num_image_tokens = num_image_tokens
        self.special_tokens = ["[MASK]", "[gMASK]", "[sMASK]", "<unused_0>", "<sop>", "<eop>", "<ENC>", "<dBLOCK>"]
        self.max_blank_length = max_blank_length
        self.byte_fallback = byte_fallback
        self.text_tokenizer = TextTokenizer(vocab_file)

    def _get_text_tokenizer(self):
        return self.text_tokenizer

    @staticmethod
    def get_blank_token(length: int):
        """get blank token."""
        assert length >= 2
        return f"<|blank_{length}|>"

    @staticmethod
    def get_tab_token():
        """get tab token."""
        return "<|tab|>"

    @property
    def num_text_tokens(self):
        """num text tokens"""
        return self.text_tokenizer.num_tokens

    @property
    def num_tokens(self):
        """num tokens"""
        return self.num_image_tokens + self.num_text_tokens

    @staticmethod
    def _encode_whitespaces(text: str, max_len: int = 80):
        text = text.replace("\t", SPTokenizer.get_tab_token())
        for i in range(max_len, 1, -1):
            text = text.replace(" " * i, SPTokenizer.get_blank_token(i))
        return text

    def _preprocess(self, text: str, linebreak=True, whitespaces=True):
        if linebreak:
            text = text.replace("\n", "<n>")
        if whitespaces:
            text = self._encode_whitespaces(text, max_len=self.max_blank_length)
        return text

    def encode(
            self, text: str, linebreak=True, whitespaces=True, add_dummy_prefix=True
    ) -> List[int]:
        """
        @param text: Text to encode.
        @param linebreak: Whether to encode newline (\n) in text.
        @param whitespaces: Whether to encode multiple whitespaces or tab in text, useful for source code encoding.
        @param special_tokens: Whether to encode special token ([MASK], [gMASK], etc.) in text.
        @param add_dummy_prefix: Whether to add dummy blank space in the beginning.
        """
        text = self._preprocess(text, linebreak, whitespaces)
        if not add_dummy_prefix:
            text = "<n>" + text
        tmp = self._get_text_tokenizer().encode(text)
        tokens = [x + self.num_image_tokens for x in tmp]
        return tokens if add_dummy_prefix else tokens[2:]

    def postprocess(self, text):
        """postprocess"""
        text = text.replace("<n>", "\n")
        text = text.replace(SPTokenizer.get_tab_token(), "\t")
        for i in range(2, self.max_blank_length + 1):
            text = text.replace(self.get_blank_token(i), " " * i)
        return text

    def decode(self, text_ids: List[int]) -> str:
        """decode."""
        ids = [int(_id) - self.num_image_tokens for _id in text_ids]
        ids = [_id for _id in ids if _id >= 0]
        text = self._get_text_tokenizer().decode(ids)
        text = self.postprocess(text)
        return text

    def decode_tokens(self, tokens: List[str]) -> str:
        """decode tokens"""
        text = self._get_text_tokenizer().convert_tokens_to_string(tokens)
        text = self.postprocess(text)
        return text

    def tokenize(
            self, text: str, linebreak=True, whitespaces=True, add_dummy_prefix=True
    ) -> List[str]:
        """
        @param text: Text to encode.
        @param linebreak: Whether to encode newline (\n) in text.
        @param whitespaces: Whether to encode multiple whitespaces or tab in text, useful for source code encoding.
        @param special_tokens: Whether to encode special token ([MASK], [gMASK], etc.) in text.
        @param add_dummy_prefix: Whether to add dummy blank space in the beginning.
        """
        text = self._preprocess(text, linebreak, whitespaces)
        if not add_dummy_prefix:
            text = "<n>" + text
        tokens = self._get_text_tokenizer().tokenize(text)
        return tokens if add_dummy_prefix else tokens[2:]

    def __getitem__(self, x: Union[int, str]):
        if isinstance(x, int):
            if x < self.num_image_tokens:
                return f"<image_{x}>"
            return self.text_tokenizer.convert_id_to_token(x - self.num_image_tokens)
        if isinstance(x, str):
            if x.startswith("<image_") and x.endswith(">") and x[7:-1].isdigit():
                return int(x[7:-1])
            return self.text_tokenizer.convert_token_to_id(x) + self.num_image_tokens
        raise ValueError("The key should be str or int.")


class ChatGLMTokenizer(PreTrainedTokenizer):
    """
    Construct a ChatGLM tokenizer. Based on byte-level Byte-Pair-Encoding.

    Args:
        vocab_file (`str`):
            Path to the vocabulary file.
    """

    model_input_names = ["input_ids", "attention_mask", "position_ids"]
    max_model_input_sizes = PRETRAINED_POSITIONAL_EMBEDDINGS_SIZES
    pretrained_vocab_map = PRETRAINED_VOCAB_MAP

    def __init__(
            self,
            vocab_file,
            do_lower_case=False,
            remove_space=False,
            bos_token='<sop>',
            eos_token='<eop>',
            end_token='</s>',
            mask_token='[MASK]',
            gmask_token='[gMASK]',
            padding_side="left",
            pad_token="<pad>",
            unk_token="<unk>",
            num_image_tokens=0,
            **kwargs
    ) -> None:
        super().__init__(
            do_lower_case=do_lower_case,
            remove_space=remove_space,
            padding_side=padding_side,
            bos_token=bos_token,
            eos_token=eos_token,
            end_token=end_token,
            mask_token=mask_token,
            gmask_token=gmask_token,
            pad_token=pad_token,
            unk_token=unk_token,
            num_image_tokens=num_image_tokens,
            **kwargs
        )

        self.do_lower_case = do_lower_case
        self.remove_space = remove_space
        self.vocab_file = vocab_file

        self.bos_token = bos_token
        self.eos_token = eos_token
        self.end_token = end_token
        self.mask_token = mask_token
        self.gmask_token = gmask_token

        self._tokenizer = SPTokenizer(vocab_file, num_image_tokens=num_image_tokens)

        """ Initialisation """

    @property
    def gmask_token_id(self) -> Optional[int]:
        """gmask token id"""
        if self.gmask_token is None:
            return None
        return self.convert_tokens_to_ids(self.gmask_token)

    @property
    def end_token_id(self) -> Optional[int]:
        """
        `Optional[int]`: Id of the end of context token in the vocabulary. Returns `None` if the token has not been
        set.
        """
        if self.end_token is None:
            return None
        return self.convert_tokens_to_ids(self.end_token)

    @property
    def vocab_size(self):
        """ Returns vocab size """
        return self._tokenizer.num_tokens

    def get_vocab(self):
        """ Returns vocab as a dict """
        vocab = {self._convert_id_to_token(i): i for i in range(self.vocab_size)}
        vocab.update(self.added_tokens_encoder)
        return vocab

    def preprocess_text(self, inputs):
        """preprocess text."""
        if self.remove_space:
            outputs = " ".join(inputs.strip().split())
        else:
            outputs = inputs

        if self.do_lower_case:
            outputs = outputs.lower()

        return outputs

    def _tokenize(self, text, **kwargs):
        """Returns a tokenized string. """
        text = self.preprocess_text(text)

        seq = self._tokenizer.tokenize(text)

        return seq

    def convert_tokens_to_string(self, tokens: List[str]) -> str:
        """convert tokens to string."""
        return self._tokenizer.decode_tokens(tokens)

    def _decode(
            self,
            token_ids: Union[int, List[int]],
            **kwargs
    ) -> str:
        if isinstance(token_ids, int):
            token_ids = [token_ids]
        if len(token_ids) == 0:
            return ""
        if self.pad_token_id in token_ids:  # remove pad
            token_ids = list(filter((self.pad_token_id).__ne__, token_ids))
        return super()._decode(token_ids, **kwargs)

    def _convert_token_to_id(self, token):
        """ Converts a token (str) in an id using the vocab. """
        return self._tokenizer[token]

    def _convert_id_to_token(self, index):
        """Converts an index (integer) in a token (str) using the vocab."""
        return self._tokenizer[index]

    def save_vocabulary(self, save_directory):
        """
        Save the vocabulary and special tokens file to a directory.

        Args:
            save_directory (`str`):
                The directory in which to save the vocabulary.
            filename_prefix (`str`, *optional*):
                An optional prefix to add to the named of the saved files.

        Returns:
            `Tuple(str)`: Paths to the files saved.
        """
        if os.path.isdir(save_directory):
            vocab_file = os.path.join(
                save_directory, self.vocab_files_names["vocab_file"]
            )
        else:
            vocab_file = save_directory

        with open(self.vocab_file, 'rb') as fin:
            proto_str = fin.read()

        with open(vocab_file, "wb") as writer:
            writer.write(proto_str)

        return (vocab_file,)

    def build_inputs_with_special_tokens(
            self, token_ids_0: List[int], token_ids_1: Optional[List[int]] = None
    ) -> List[int]:
        """
        Build model inputs from a sequence or a pair of sequence for sequence classification tasks by concatenating and
        adding special tokens. A BERT sequence has the following format:

        - single sequence: `[CLS] X [SEP]`
        - pair of sequences: `[CLS] A [SEP] B [SEP]`

        Args:
            token_ids_0 (`List[int]`):
                List of IDs to which the special tokens will be added.
            token_ids_1 (`List[int]`, *optional*):
                Optional second list of IDs for sequence pairs.

        Returns:
            `List[int]`: List of [input IDs](../glossary#input-ids) with the appropriate special tokens.
        """
        gmask_id = self._tokenizer[self.gmask_token]
        eos_id = self._tokenizer[self.eos_token]
        token_ids_0 = token_ids_0 + [gmask_id, self._tokenizer[self.bos_token]]
        if token_ids_1 is not None:
            token_ids_0 = token_ids_0 + token_ids_1 + [eos_id]
        return token_ids_0

    def _pad(
            self,
            encoded_inputs: Dict,
            max_length: Optional[int] = None,
            padding_strategy: PaddingStrategy = PaddingStrategy.DO_NOT_PAD,
            pad_to_multiple_of: Optional[int] = None,
    ) -> dict:
        """
        Pad encoded inputs (on left/right and up to predefined length or max length in the batch)

        Args:
            encoded_inputs:
                Dictionary of tokenized inputs (`List[int]`) or batch of tokenized inputs (`List[List[int]]`).
            max_length: maximum length of the returned list and optionally padding length (see below).
                Will truncate by taking into account the special tokens.
            padding_strategy: PaddingStrategy to use for padding.

                - PaddingStrategy.LONGEST Pad to the longest sequence in the batch
                - PaddingStrategy.MAX_LENGTH: Pad to the max length (default)
                - PaddingStrategy.DO_NOT_PAD: Do not pad
                The tokenizer padding sides are defined in self.padding_side:

                    - 'left': pads on the left of the sequences
                    - 'right': pads on the right of the sequences
            pad_to_multiple_of: (optional) Integer if set will pad the sequence to a multiple of the provided value.
                This is especially useful to enable the use of Tensor Core on NVIDIA hardware with compute capability
                `>= 7.5` (Volta).
            return_attention_mask:
                (optional) Set to False to avoid returning attention mask (default: set to model specifics)
        """
        # Load from model defaults
        bos_token_id = self._tokenizer[self.bos_token]
        mask_token_id = self._tokenizer[self.mask_token]
        gmask_token_id = self._tokenizer[self.gmask_token]
        assert self.padding_side == "left"

        required_input = encoded_inputs[self.model_input_names[0]]
        seq_length = len(required_input)

        if padding_strategy == PaddingStrategy.LONGEST:
            max_length = len(required_input)

        if max_length is not None and pad_to_multiple_of is not None and (max_length % pad_to_multiple_of != 0):
            max_length = ((max_length // pad_to_multiple_of) + 1) * pad_to_multiple_of

        needs_to_be_padded = padding_strategy != PaddingStrategy.DO_NOT_PAD and len(required_input) != max_length

        # Initialize attention mask if not present.
        if max_length is not None:
            if "attention_mask" not in encoded_inputs:
                if bos_token_id in required_input:
                    context_length = required_input.index(bos_token_id)
                else:
                    context_length = seq_length
                attention_mask = np.ones((1, seq_length, seq_length))
                attention_mask = np.tril(attention_mask)
                attention_mask[:, :, :context_length] = 1
                attention_mask = np.bool_(attention_mask < 0.5)
                encoded_inputs["attention_mask"] = attention_mask

            if "position_ids" not in encoded_inputs:
                if bos_token_id in required_input:
                    context_length = required_input.index(bos_token_id)
                else:
                    context_length = seq_length
                position_ids = np.arange(seq_length, dtype=np.int64)
                mask_token = mask_token_id if mask_token_id in required_input else gmask_token_id
                if mask_token in required_input:
                    mask_position = required_input.index(mask_token)
                    position_ids[context_length:] = mask_position
                block_position_ids = np.concatenate(
                    [np.zeros(context_length, dtype=np.int64),
                     np.arange(1, seq_length - context_length + 1, dtype=np.int64)])
                encoded_inputs["position_ids"] = np.stack([position_ids, block_position_ids], axis=0)

        if needs_to_be_padded:
            difference = max_length - len(required_input)

            if "attention_mask" in encoded_inputs:
                encoded_inputs["attention_mask"] = np.pad(encoded_inputs["attention_mask"],
                                                          pad_width=[(0, 0), (difference, 0), (difference, 0)],
                                                          mode='constant', constant_values=True)
            if "token_type_ids" in encoded_inputs:
                encoded_inputs["token_type_ids"] = [self.pad_token_type_id] * difference + encoded_inputs[
                    "token_type_ids"
                ]
            if "special_tokens_mask" in encoded_inputs:
                encoded_inputs["special_tokens_mask"] = [1] * difference + encoded_inputs["special_tokens_mask"]
            if "position_ids" in encoded_inputs:
                encoded_inputs["position_ids"] = np.pad(encoded_inputs["position_ids"],
                                                        pad_width=[(0, 0), (difference, 0)])
            encoded_inputs[self.model_input_names[0]] = [self.pad_token_id] * difference + required_input

        return encoded_inputs

    def __call__(self, text_input):
        """
        Call method for input conversion for eager mode with C++ implementation.
        """
        if isinstance(text_input, str):
            text_input = np.array(text_input)
        elif not isinstance(text_input, np.ndarray):
            raise TypeError(
                f"Input should be a text line in 1-D NumPy format, got {type(text_input)}.")
        return super().__call__(text_input)

    def execute_py(self, text_input):
        """
        Execute method.
        """
        return self._execute_py(text_input)

    def _execute_py(self, text_input):
        """
        Execute method.
        """
        text = self._convert_to_unicode(text_input)
        output = self._tokenizer.encode(text)
        output = self.build_inputs_with_special_tokens(output)
        return np.array(output)

    def _convert_to_unicode(self, text_input):
        """Converts `text` to Unicode (if it's not already), assuming utf-8 input."""
        if isinstance(text_input, str):
            return text_input
        if isinstance(text_input, bytes):
            return text_input.decode("utf-8", "ignore")
        if isinstance(text_input, np.ndarray):
            if text_input.dtype.type is np.bytes_:
                text_input = np.char.decode(text_input, "utf-8")
            return str(text_input)
        raise ValueError(f"Unsupported string type: {type(text_input)}, {text_input.dtype}")

__all__ = ['ChatGLMTokenizer']
