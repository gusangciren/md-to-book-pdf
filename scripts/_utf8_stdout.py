"""
_utf8_stdout.py —— 保证脚本在任何终端都能打印中文。

为什么需要：
Windows 的 Python 在非 UTF-8 终端（如 cmd / PowerShell 默认的 cp1252/cp936）
里 stdout 编码不是 UTF-8，`print("中文")` 会抛
    UnicodeEncodeError: 'charmap' codec can't encode characters ...
本工具所有脚本都有中文输出，因此在 GitHub Actions、cmd、部分 IDE 终端里
会直接崩溃（已实测：cp1252 下打印中文必崩）。

解决：把 stdout/stderr 重配为 UTF-8，并对无法编码的字符降级为替换而不是抛错。
注意只改终端输出，不动 argv —— argv 的解码由Python 依据系统 locale 处理，
改它反而会引入别的乱码。
"""

import io
import sys


def enable():
    """把 stdout/stderr 切到 UTF-8，且对无法编码的字符降级而非抛错。"""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        try:
            # Python 3.7+ 首选
            stream.reconfigure(encoding="utf-8", errors="replace")
            continue
        except (AttributeError, ValueError):
            pass
        # 老版本 Python 或流不支持 reconfigure → 用文本包装兜底
        try:
            buffer = getattr(stream, "buffer", None)
            if buffer is not None:
                setattr(sys, name, io.TextIOWrapper(
                    buffer, encoding="utf-8", errors="replace", line_buffering=True))
        except Exception:
            # 实在无能为力就放弃——总比抛异常导致脚本挂掉好
            pass


enable()