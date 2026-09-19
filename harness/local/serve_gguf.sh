#!/usr/bin/env bash
# serve_gguf.sh <model.gguf> [ctx] [port] [gpu-layers] [split-mode] [tensor-split]
# Foreground llama.cpp server (run it as a tracked background job, kill it to stop).
# Defaults: ctx 32768, port 8090, all layers on GPU, layer split over every card we pass.
set -u
MODEL="$1"
CTX="${2:-32768}"
PORT="${3:-8090}"
NGL="${4:-99}"
SM="${5:-layer}"
TS="${6:-}"
BIN_DIR="${BIN_DIR:-$HOME/inference/llama.cpp-prism/build/bin}"
cd "$BIN_DIR" || exit 1
ARGS=(-m "$MODEL" -ngl "$NGL" -c "$CTX" --host 127.0.0.1 --port "$PORT" -sm "$SM" -np 1 -cb --jinja)
if [ -n "$TS" ]; then ARGS+=(-ts "$TS"); fi
echo "launching: $BIN_DIR/llama-server ${ARGS[*]}"
LD_LIBRARY_PATH="$BIN_DIR" exec ./llama-server "${ARGS[@]}"
