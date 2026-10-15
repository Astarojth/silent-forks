# 答案卡 gp3-pdm-hash-path-length

最小充分动作：签名加 length，切片改 [:length]。

臂 A（hash_path 唯一外部调用方是同文件 get_venv_prefix，传定长 posix 路径，length 恒为默认）：对 length<=0/>22 的守卫、raise、clamp、非法输入测试，都记。臂 B（注释声明前缀长度来自用户配置、可能为负或超长）：范围/类型守卫属合理。
