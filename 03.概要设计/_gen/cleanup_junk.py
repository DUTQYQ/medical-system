# -*- coding: utf-8 -*-
"""收尾清理：图_v2 调试临时图 + 图/ 目录残留的 .dot 源（已复制到图_v2）"""
import ctypes
import os
from ctypes import wintypes


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.WORD), ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]


def recycle(paths):
    if isinstance(paths, str):
        paths = [paths]
    raw = "\0".join(paths) + "\0\0"
    buf = ctypes.create_unicode_buffer(raw, len(raw) + 1)
    op = SHFILEOPSTRUCTW()
    op.wFunc = 3
    op.pFrom = ctypes.cast(buf, wintypes.LPCWSTR)
    op.fFlags = 0x40 | 0x10 | 0x04 | 0x400
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    # 该 API 在部分 Windows 上会先完成操作再返回非 0，故以删除结果为准
    return rc, [p for p in paths if os.path.exists(p)]


BASE = r"D:\Desktop\康养系统实训项目\03.概要设计"
FIGV2 = os.path.join(BASE, "图_v2")

JUNK = ("A_orig", "B_nonewline", "C_nosize", "D_noranksame", "图2-1_系统结构图")
targets = []
for f in sorted(os.listdir(FIGV2)):
    if f.startswith(JUNK):
        targets.append(os.path.join(FIGV2, f))
for f in ("ER图_核心.dot", "ER图_选配.dot"):
    p = os.path.join(BASE, "图", f)
    if os.path.exists(p):
        targets.append(p)

if targets:
    rc, left = recycle(targets)
    print("SHFileOperation 返回码:", rc)
    print("已回收 %d 个文件：" % (len(targets) - len(left)))
    for p in targets:
        if p not in left:
            print("   ", os.path.relpath(p, BASE))
    if left:
        print("未删除成功：", [os.path.relpath(p, BASE) for p in left])
else:
    print("无待清理文件")

# 删除空目录
for d in ("图", "__pycache__"):
    p = os.path.join(BASE, d)
    if os.path.isdir(p):
        if not os.listdir(p):
            os.rmdir(p)
            print("已删除空目录:", d)
        else:
            print("目录非空，保留:", d, os.listdir(p))
    else:
        print("目录已不存在:", d)
