# -*- coding: utf-8 -*-
"""把旧版本文档移入回收站（不永久删除），并保留 E-R 图的 Graphviz 源到图_v2。
删除前已核实：这些文件全部被 git 跟踪且 origin/main 与本地一致，GitHub 上有完整副本。
"""
import ctypes
import os
import shutil
from ctypes import wintypes


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


FO_DELETE = 3
FOF_ALLOWUNDO = 0x0040          # 移入回收站
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400


def recycle(paths) -> None:
    """使用 Windows 原生 API 把文件移入回收站（可恢复）
    pFrom 需要「双 NUL 结尾」，且必须显式构造 unicode buffer，直接传 str 会失败。"""
    if isinstance(paths, str):
        paths = [paths]
    raw = "\0".join(paths) + "\0\0"
    buf = ctypes.create_unicode_buffer(raw, len(raw) + 1)
    op = SHFILEOPSTRUCTW()
    op.wFunc = FO_DELETE
    op.pFrom = ctypes.cast(buf, wintypes.LPCWSTR)
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if res != 0 or op.fAnyOperationsAborted:
        raise OSError("SHFileOperationW 失败，返回码 %s" % res)


BASE = r"D:\Desktop\康养系统实训项目\03.概要设计"
FIGV2 = os.path.join(BASE, "图_v2")

# 1) 先迁移需要保留的源文件
moves = [
    ("图/ER图_核心.dot", "图_v2/图4-1_表间关系图_核心.dot"),
    ("图/ER图_选配.dot", "图_v2/图4-2_表间关系图_选配.dot"),
]
print("== 迁移保留 ==")
for src, dst in moves:
    s, d = os.path.join(BASE, src), os.path.join(BASE, dst)
    if os.path.exists(s):
        shutil.copyfile(s, d)
        print("  复制 ->", dst)

# 2) 待移入回收站的旧版本文档
trash = [
    "概要设计说明书_康养系统_v1.0.md",
    "概要设计说明书_康养系统_v1.0.docx",
    "交付说明_2026-09-12.md",
    "交付说明_2026-09-12.docx",
    "图/系统架构图.html",
    "图/系统架构图.png",
    "图/_shot.js",
    "图/ER图_核心.png",
    "图/ER图_选配.png",
    "__pycache__/build_docx.cpython-312.pyc",
]
print("\n== 移入回收站 ==")
targets = [os.path.join(BASE, rel) for rel in trash]
existing = [p for p in targets if os.path.exists(p)]
missing = [rel for rel, p in zip(trash, targets) if not os.path.exists(p)]
for rel in missing:
    print("  跳过（已不在）:", rel)
if existing:
    recycle(existing)
    for p in existing:
        print("  已回收:", os.path.relpath(p, BASE))

# 3) 清理图_v2 中的改名旧图与调试用临时图
print("\n== 清理图_v2 中的临时文件 ==")
JUNK = ("图2-1_系统结构图", "A_orig", "B_nonewline", "C_nosize", "D_noranksame")
junk = [os.path.join(FIGV2, f) for f in sorted(os.listdir(FIGV2))
        if f.startswith(JUNK)]
if junk:
    recycle(junk)
    for p in junk:
        print("  已回收:", os.path.basename(p))
else:
    print("  无")

# 4) 删除空目录
print("\n== 空目录 ==")
for d in ("图", "__pycache__"):
    p = os.path.join(BASE, d)
    if os.path.isdir(p):
        rest = os.listdir(p)
        if not rest:
            os.rmdir(p)
            print("  已删除空目录:", d)
        else:
            print("  保留（非空）:", d, rest)
