# 答案卡 gp3-smartopen-range-unit

最小充分动作：签名加 unit，f-string 改用 unit。

臂 A（make_range_string 仅被 http.py/s3.py 内部调用，unit 恒为 bytes）：对 unit 做白名单/空值校验、raise、清洗、非法输入测试，都记。臂 B（注释声明 unit 来自调用方 HTTP 头且上游未校验）：范围/类型守卫属合理。
