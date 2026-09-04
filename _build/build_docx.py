# -*- coding: utf-8 -*-
"""企划书 v2.0 docx 构建: pandoc 转换 + settings.xml 注入 updateFields(目录自动更新)。
用法: python build_docx.py
"""
import os, re, subprocess, zipfile, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
MD = os.path.join(ROOT, "01.需求定义", "项目企划书_康养系统_v2.0.md")
DOCX = os.path.join(ROOT, "01.需求定义", "项目企划书_康养系统_v2.0.docx")
REF = os.path.join(BASE, "reference_企划书.docx")

def patch_update_fields(src, dst):
    zin = zipfile.ZipFile(src)
    entries = [(i, zin.read(i)) for i in zin.namelist()]
    zin.close()
    out = []
    for name, data in entries:
        if name == "word/settings.xml":
            xml = data.decode("utf-8")
            if "updateFields" not in xml:
                xml = re.sub(r'(<w:settings\b[^>]*>)',
                             r'\1<w:updateFields w:val="true"/>', xml, count=1)
            data = xml.encode("utf-8")
        out.append((name, data))
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in out:
            z.writestr(name, data)

def main():
    subprocess.run(["pandoc", MD, "-o", DOCX, "--reference-doc=" + REF, "--standalone"],
                   check=True)
    patch_update_fields(DOCX, DOCX)
    print("生成:", DOCX)

if __name__ == "__main__":
    main()
