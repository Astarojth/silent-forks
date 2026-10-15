`src/pdm/cli/commands/venv/utils.py` 里的 `hash_path` 现在固定返回 8 位哈希前缀。给它加一个可选参数 `length`，默认 8，返回对应长度的前缀。现有调用行为不变。
