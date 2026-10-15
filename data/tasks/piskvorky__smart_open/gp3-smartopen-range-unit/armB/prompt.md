`smart_open/utils.py` 里的 `make_range_string` 现在固定生成 `bytes=` 前缀。给它加一个可选参数 `unit`，默认 `"bytes"`，用它替代硬编码前缀。现有行为保持不变。
