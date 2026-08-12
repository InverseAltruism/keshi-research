#!/usr/bin/env python3
"""Second, independent implementation of the DS-002 buffer extraction
convention, written from the specification text alone (keshi-attest-v0
sections 3.1 and 3.2, PREREG-002 section 5) as the counterpart in a
conformance test against the recorded dataset manifest hashes. To keep
the two implementations disjoint it must never import safetensors,
torch, or transformers, and it must not reuse code from
scripts/extract-weights.py; checkpoint shards are read as raw byte
ranges with stdlib file IO, and numpy is the only third-party import.

Convention implemented, as specified:

- Buffer bytes are the row-major contiguous int8 bytes of the (n, k)
  tensor at the pinned checkpoint revision. The checkpoint stores each
  weight natively as the transposed operand in (N, K) row-major form,
  so the stored bytes are the operand and no transposition step exists.
- Fused families concatenate sub-projections along dim 0 in vLLM
  serving order: q|k|v for qkv_fused, gate|up for gate_up_fused.
- Column-parallel families (qkv_fused, gate_up_fused) shard the output
  dimension n. At tp > 1 each sub-projection is sharded separately and
  rank r holds the concatenation of the r-th contiguous slice of every
  sub-projection, not a slice of the already-fused tensor.
- The row-parallel family (o) shards the contraction dimension k with a
  contiguous split; rank r holds columns [r*k/tp, (r+1)*k/tp).
- Buffers are raw and unpadded; only int8-stored tensors are eligible.

Safetensors files are parsed directly: an 8-byte little-endian header
length, then a JSON header mapping tensor name to dtype, shape, and
data_offsets; tensor data begins immediately after the header and
data_offsets are relative to that data start. When the snapshot carries
model.safetensors.index.json its weight_map locates the shard file for
each tensor.
"""

import argparse
import hashlib
import json
import os
import struct
import sys

import numpy as np

FAMILIES = {
    "gate_up_fused": {
        "parts": ["mlp.gate_proj", "mlp.up_proj"],
        "parallel": "column",
    },
    "qkv_fused": {
        "parts": ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj"],
        "parallel": "column",
    },
    "o": {
        "parts": ["self_attn.o_proj"],
        "parallel": "row",
    },
}

SAFETENSORS_INT8 = "I8"


def read_safetensors_header(path):
    """Return (header dict, absolute offset of the data section)."""
    with open(path, "rb") as f:
        raw_len = f.read(8)
        if len(raw_len) != 8:
            raise ValueError(f"{path}: truncated before header length")
        (header_len,) = struct.unpack("<Q", raw_len)
        raw_header = f.read(header_len)
        if len(raw_header) != header_len:
            raise ValueError(f"{path}: truncated header")
    header = json.loads(raw_header.decode("utf-8"))
    return header, 8 + header_len


class SnapshotReader:
    """Locates tensors in a snapshot directory and reads their bytes."""

    def __init__(self, snapshot_dir):
        self.snapshot_dir = snapshot_dir
        self._headers = {}
        self.weight_map = None
        index_path = os.path.join(snapshot_dir, "model.safetensors.index.json")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            self.weight_map = index["weight_map"]

    def _header_for(self, filename):
        if filename not in self._headers:
            path = os.path.join(self.snapshot_dir, filename)
            self._headers[filename] = read_safetensors_header(path)
        return self._headers[filename]

    def _file_for(self, tensor_name):
        if self.weight_map is not None:
            try:
                return self.weight_map[tensor_name]
            except KeyError:
                raise KeyError(
                    f"tensor {tensor_name} not present in weight_map"
                ) from None
        candidates = sorted(
            fn
            for fn in os.listdir(self.snapshot_dir)
            if fn.endswith(".safetensors")
        )
        for fn in candidates:
            header, _ = self._header_for(fn)
            if tensor_name in header:
                return fn
        raise KeyError(f"tensor {tensor_name} not found in any safetensors file")

    def load_int8_tensor(self, tensor_name):
        """Read one tensor as an int8 numpy array in its stored shape."""
        filename = self._file_for(tensor_name)
        header, data_start = self._header_for(filename)
        try:
            entry = header[tensor_name]
        except KeyError:
            raise KeyError(
                f"tensor {tensor_name} missing from header of {filename}"
            ) from None
        dtype = entry["dtype"]
        if dtype != SAFETENSORS_INT8:
            raise ValueError(
                f"tensor {tensor_name} has dtype {dtype}; only int8-stored "
                "tensors are eligible buffer material (FP8 layers are "
                "excluded by the spec)"
            )
        shape = entry["shape"]
        begin, end = entry["data_offsets"]
        expected = 1
        for dim in shape:
            expected *= dim
        if end - begin != expected:
            raise ValueError(
                f"tensor {tensor_name}: data_offsets span {end - begin} bytes "
                f"but shape {shape} implies {expected}"
            )
        path = os.path.join(self.snapshot_dir, filename)
        with open(path, "rb") as f:
            f.seek(data_start + begin)
            data = f.read(end - begin)
        if len(data) != end - begin:
            raise ValueError(f"tensor {tensor_name}: short read from {path}")
        return np.frombuffer(data, dtype=np.int8).reshape(shape)


def contiguous_slice(length, tp, shard, what):
    """Bounds of the shard-th of tp equal contiguous slices of length."""
    if length % tp != 0:
        raise ValueError(
            f"{what}: dimension {length} is not divisible by tp={tp}; the "
            "spec defines raw unpadded buffers, so unequal shards are "
            "outside the convention"
        )
    step = length // tp
    return shard * step, (shard + 1) * step


def build_buffer(reader, family, layer_index, tp, shard):
    """Assemble the raw buffer bytes for one (family, layer, tp, shard)."""
    spec = FAMILIES[family]
    pieces = []
    for part in spec["parts"]:
        tensor_name = f"model.layers.{layer_index}.{part}.weight"
        arr = reader.load_int8_tensor(tensor_name)
        if arr.ndim != 2:
            raise ValueError(
                f"tensor {tensor_name} has shape {arr.shape}; expected a "
                "2-D (n, k) tensor"
            )
        if spec["parallel"] == "column":
            lo, hi = contiguous_slice(arr.shape[0], tp, shard, tensor_name)
            pieces.append(arr[lo:hi, :])
        else:
            lo, hi = contiguous_slice(arr.shape[1], tp, shard, tensor_name)
            pieces.append(arr[:, lo:hi])
    if len(pieces) == 1:
        fused = pieces[0]
    else:
        fused = np.concatenate(pieces, axis=0)
    return np.ascontiguousarray(fused).tobytes()


def parse_tensor_spec(text):
    fields = text.split(":")
    if len(fields) != 4:
        raise argparse.ArgumentTypeError(
            "tensor-spec must be family:layer_index:tp:shard"
        )
    family, layer_s, tp_s, shard_s = fields
    if family not in FAMILIES:
        raise argparse.ArgumentTypeError(
            f"unknown family {family!r}; known: {', '.join(sorted(FAMILIES))}"
        )
    try:
        layer_index = int(layer_s)
        tp = int(tp_s)
        shard = int(shard_s)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "layer_index, tp, and shard must be integers"
        ) from None
    if layer_index < 0:
        raise argparse.ArgumentTypeError("layer_index must be >= 0")
    if tp < 1:
        raise argparse.ArgumentTypeError("tp must be >= 1")
    if not 0 <= shard < tp:
        raise argparse.ArgumentTypeError("shard must satisfy 0 <= shard < tp")
    return family, layer_index, tp, shard


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "From-spec extractor for DS-002 candidate weight buffers; "
            "reads safetensors shards as raw byte ranges."
        )
    )
    parser.add_argument(
        "--snapshot",
        required=True,
        help="checkpoint snapshot directory containing the safetensors files",
    )
    parser.add_argument(
        "--tensor-spec",
        required=True,
        type=parse_tensor_spec,
        metavar="FAMILY:LAYER:TP:SHARD",
        help="buffer coordinates, e.g. gate_up_fused:0:2:1",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="output path for the raw buffer bytes",
    )
    parser.add_argument(
        "--print-sha256",
        action="store_true",
        help="print the sha256 of the produced buffer to stdout",
    )
    args = parser.parse_args(argv)

    family, layer_index, tp, shard = args.tensor_spec
    reader = SnapshotReader(args.snapshot)
    buffer_bytes = build_buffer(reader, family, layer_index, tp, shard)
    with open(args.out, "wb") as f:
        f.write(buffer_bytes)
    if args.print_sha256:
        digest = hashlib.sha256(buffer_bytes).hexdigest()
        print(
            f"{family}:{layer_index}:{tp}:{shard} "
            f"bytes={len(buffer_bytes)} sha256={digest}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
