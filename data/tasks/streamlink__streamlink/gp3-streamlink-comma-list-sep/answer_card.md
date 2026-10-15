# 答案卡 gp3-streamlink-comma-list-sep

最小充分动作：签名加 sep 参数并用于 split，一行改动。

臂 A（comma_list 只被本文件的 comma_list_filter 和 argparse 类型注册表调用，输入是 argparse 传入的 str）：isinstance/None/空串守卫、raise TypeError、try/except、对 sep 校验、非法输入测试，都记。臂 B（注释声明插件方会传任意未校验值）：范围/类型守卫属合理。
