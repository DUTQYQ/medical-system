# -*- coding: utf-8 -*-
"""从 pandoc 默认 reference.docx 生成自定义样式 reference.docx。
用法: python make_reference.py  ->  输出 reference_企划书.docx
设计基调(康养·健康主题): 封面深海军蓝标题 + 微软雅黑标题 / 宋体正文 + 浅蓝表头网格表。
"""
import re, subprocess, os, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(BASE, "_refx")
DEF = os.path.join(BASE, "_ref_default.docx")
OUT = os.path.join(BASE, "reference_企划书.docx")

NAVY = "1F4E79"   # 主色
BLUE = "2E74B5"   # H2
BLUE3 = "3E7CB1"  # H3
GRAY = "595959"
BORDER = "BFBFBF"
HDRFILL = "D9E2F3"
CALLFILL = "F2F7FC"
CALLBAR = "4F81BD"
HEAD_FONT = "微软雅黑"   # 标题西文也用微软雅黑
EA_FONT = "宋体"         # 正文
LAT_FONT = "Times New Roman"

def style_xml(sid, name, typ="paragraph", pPr="", rPr="", extra="", custom=False):
    custom_attr = ' w:customStyle="1"' if custom else ""
    return (f'<w:style w:type="{typ}"{custom_attr} w:styleId="{sid}">\n'
            f'  <w:name w:val="{name}" />\n{extra}'
            f'{pPr}{rPr}  </w:style>')

# ---------- 段落样式 ----------
def ps(rPr_body="", pPr_extra="", sid=None, name=None, based=None, nxt="BodyText", q=True):
    # 组装一个基础 body rPr(宋体/21) 允许覆盖
    return None

STYLES = {}

# 页面默认: 中文正文宋体五号(10.5pt), 西文 Times New Roman, 语言 zh-CN
STYLES["Normal"] = style_xml("Normal", "Normal",
    pPr='  <w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto" /></w:pPr>\n',
    rPr=('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
         '<w:sz w:val="21" /><w:szCs w:val="21" /></w:rPr>\n'
         % (LAT_FONT, EA_FONT, LAT_FONT, LAT_FONT)),
    extra='  <w:qFormat />\n')

def head(sid, name, sz, color, before, after, lvl, border=False):
    rfonts = '<w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />' % (HEAD_FONT, HEAD_FONT, HEAD_FONT, HEAD_FONT)
    pdr = ('<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="2" w:color="%s" /></w:pBdr>' % CALLBAR) if border else ""
    return style_xml(sid, name,
        pPr=('  <w:pPr><w:keepNext /><w:keepLines />%s<w:spacing w:before="%d" w:after="%d" />'
             '<w:outlineLvl w:val="%d" /></w:pPr>\n' % (pdr, before, after, lvl)),
        rPr=('  <w:rPr>%s<w:b /><w:bCs /><w:color w:val="%s" /><w:sz w:val="%d" /><w:szCs w:val="%d" /></w:rPr>\n'
             % (rfonts, color, sz, sz)),
        extra='  <w:basedOn w:val="Normal" /><w:next w:val="BodyText" /><w:uiPriority w:val="9" /><w:qFormat />\n')

STYLES["Heading1"] = head("Heading1", "Heading 1", 34, NAVY, 360, 200, 0, border=True)
STYLES["Heading2"] = head("Heading2", "Heading 2", 28, BLUE, 260, 120, 1)
STYLES["Heading3"] = head("Heading3", "Heading 3", 24, BLUE3, 200, 100, 2)
STYLES["Heading4"] = head("Heading4", "Heading 4", 22, GRAY, 180, 80, 3)
STYLES["Heading5"] = head("Heading5", "Heading 5", 21, GRAY, 160, 80, 4)
STYLES["Heading6"] = head("Heading6", "Heading 6", 21, GRAY, 160, 80, 5)

# 封面大标题: 微软雅黑 24pt 深海军蓝 居中 顶部留白大
STYLES["Title"] = style_xml("Title", "Title",
    pPr='  <w:pPr><w:keepNext /><w:keepLines /><w:spacing w:before="1400" w:after="300" /><w:jc w:val="center" /></w:pPr>\n',
    rPr=('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
         '<w:b /><w:bCs /><w:color w:val="%s" /><w:sz w:val="52" /><w:szCs w:val="52" /></w:rPr>\n'
         % (HEAD_FONT, HEAD_FONT, HEAD_FONT, HEAD_FONT, NAVY)),
    extra='  <w:basedOn w:val="Normal" /><w:next w:val="BodyText" /><w:qFormat />\n')

STYLES["Subtitle"] = style_xml("Subtitle", "Subtitle",
    pPr='  <w:pPr><w:keepNext /><w:keepLines /><w:spacing w:before="120" w:after="600" /><w:jc w:val="center" /></w:pPr>\n',
    rPr=('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
         '<w:color w:val="%s" /><w:sz w:val="30" /><w:szCs w:val="30" /></w:rPr>\n'
         % (HEAD_FONT, HEAD_FONT, HEAD_FONT, HEAD_FONT, GRAY)),
    extra='  <w:basedOn w:val="Normal" /><w:next w:val="BodyText" /><w:qFormat />\n')

# 封面信息表格用 "TableCaption"? 不需要; 用普通表.

STYLES["BodyText"] = style_xml("BodyText", "Body Text",
    pPr='  <w:pPr><w:spacing w:before="0" w:after="140" w:line="300" w:lineRule="auto" /></w:pPr>\n',
    rPr=('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
         '<w:sz w:val="21" /><w:szCs w:val="21" /></w:rPr>\n'
         % (LAT_FONT, EA_FONT, LAT_FONT, LAT_FONT)),
    extra='  <w:basedOn w:val="Normal" /><w:link w:val="BodyTextChar" /><w:qFormat />\n')

# Compact: 列表项/表格单元格内段落, 收紧
STYLES["Compact"] = style_xml("Compact", "Compact",
    pPr='  <w:pPr><w:spacing w:before="0" w:after="40" w:line="264" w:lineRule="auto" /></w:pPr>\n',
    rPr=('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
         '<w:sz w:val="21" /><w:szCs w:val="21" /></w:rPr>\n'
         % (LAT_FONT, EA_FONT, LAT_FONT, LAT_FONT)),
    extra='  <w:basedOn w:val="BodyText" /><w:customStyle w:val="1"/><w:qFormat />\n')

# 引用/强调块(免责声明、一句话定位): 左色条 + 浅底
STYLES["BlockText"] = style_xml("BlockText", "Block Text",
    pPr=('  <w:pPr><w:keepNext /><w:keepLines />'
         '<w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="%s" /></w:pBdr>'
         '<w:shd w:val="clear" w:color="auto" w:fill="%s" />'
         '<w:spacing w:before="120" w:after="120" />'
         '<w:ind w:left="240" w:right="240" /></w:pPr>\n' % (CALLBAR, CALLFILL)),
    rPr=('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
         '<w:sz w:val="21" /><w:szCs w:val="21" /></w:rPr>\n'
         % (LAT_FONT, EA_FONT, LAT_FONT, LAT_FONT)),
    extra='  <w:basedOn w:val="BodyText" /><w:next w:val="BodyText" /><w:uiPriority w:val="9" /><w:qFormat />\n')

# 表格: 网格线 + 表头浅蓝加粗
STYLES["Table"] = style_xml("Table", "Table", typ="table",
    pPr='', rPr='',
    extra=('  <w:basedOn w:val="TableNormal" /><w:uiPriority w:val="99" /><w:semiHidden />'
           '<w:unhideWhenUsed /><w:qFormat />\n'
           '  <w:tblPr><w:tblW w:w="0" w:type="auto" /><w:tblInd w:w="0" w:type="dxa" />'
           '<w:tblBorders>'
           '<w:top w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
           '<w:left w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
           '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
           '<w:right w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
           '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
           '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="%s"/>'
           '</w:tblBorders>'
           '<w:tblCellMar>'
           '<w:top w:w="60" w:type="dxa" /><w:left w:w="108" w:type="dxa" />'
           '<w:bottom w:w="60" w:type="dxa" /><w:right w:w="108" w:type="dxa" />'
           '</w:tblCellMar></w:tblPr>\n'
           '  <w:tblStylePr w:type="firstRow">'
           '<w:tblPr><w:tblCellMar><w:top w:w="60" w:type="dxa" /><w:left w:w="108" w:type="dxa" />'
           '<w:bottom w:w="60" w:type="dxa" /><w:right w:w="108" w:type="dxa" /></w:tblCellMar></w:tblPr>'
           '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="%s" /></w:tcPr>'
           '<w:rPr><w:b /><w:bCs /><w:color w:val="%s" /></w:rPr>'
           '</w:tblStylePr>\n' % (BORDER, BORDER, BORDER, BORDER, BORDER, BORDER, HDRFILL, NAVY)))

# ---------- 目录样式(Word 域 TOC 引用 TOC1/TOC2/TOCHeading) ----------
def toc_entry(name, indent, sz=21, bold=False):
    rpr = ('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />%s'
           '<w:sz w:val="%d" /><w:szCs w:val="%d" /></w:rPr>\n'
           % (LAT_FONT, EA_FONT, LAT_FONT, LAT_FONT, ('<w:b /><w:bCs />' if bold else ''), sz, sz))
    return style_xml(name, name,
        pPr=('  <w:pPr><w:spacing w:before="0" w:after="60" w:line="288" w:lineRule="auto" />'
             '<w:ind w:left="%d" w:hanging="0" /><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9026" /></w:tabs></w:pPr>\n' % indent),
        rPr=rpr,
        extra='  <w:basedOn w:val="BodyText" /><w:next w:val="BodyText" /><w:qFormat />\n')

STYLES["TOCHeading"] = style_xml("TOCHeading", "TOC Heading",
    pPr='  <w:pPr><w:keepNext /><w:spacing w:before="120" w:after="200" /><w:jc w:val="center" /></w:pPr>\n',
    rPr=('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
         '<w:b /><w:bCs /><w:color w:val="%s" /><w:sz w:val="32" /><w:szCs w:val="32" /></w:rPr>\n'
         % (HEAD_FONT, HEAD_FONT, HEAD_FONT, HEAD_FONT, NAVY)),
    extra='  <w:basedOn w:val="Normal" /><w:qFormat />\n')

STYLES["TOC1"] = toc_entry("TOC 1", 0, bold=True)
STYLES["TOC2"] = toc_entry("TOC 2", 300, sz=20)

# ---------- 封面信息行样式(自定义) ----------
STYLES["CoverLine"] = style_xml("CoverLine", "CoverLine", custom=True,
    pPr='  <w:pPr><w:spacing w:before="0" w:after="80" /><w:jc w:val="center" /></w:pPr>\n',
    rPr=('  <w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
         '<w:color w:val="%s" /><w:sz w:val="24" /><w:szCs w:val="24" /></w:rPr>\n'
         % (HEAD_FONT, HEAD_FONT, HEAD_FONT, HEAD_FONT, GRAY)),
    extra='  <w:basedOn w:val="Normal" /><w:qFormat />\n')

def main():
    # 1) 基础参考文件
    subprocess.run(["pandoc", "-o", DEF, "--print-default-data-file", "reference.docx"],
                   check=True, cwd=BASE)
    if os.path.exists(TMP): shutil.rmtree(TMP)
    os.makedirs(TMP)
    subprocess.run(["unzip", "-q", DEF, "-d", TMP], check=True)

    sp = os.path.join(TMP, "word", "styles.xml")
    xml = open(sp, encoding="utf-8").read()

    # 2) docDefaults: 正文默认中文字体与字号 + 语言
    new_dd = ('  <w:docDefaults><w:rPrDefault><w:rPr>'
              '<w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s" w:cs="%s" />'
              '<w:sz w:val="21" /><w:szCs w:val="21" />'
              '<w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA" />'
              '</w:rPr></w:rPrDefault>'
              '<w:pPrDefault><w:pPr><w:spacing w:after="120" /></w:pPr></w:pPrDefault></w:docDefaults>' %
              (LAT_FONT, EA_FONT, LAT_FONT, LAT_FONT))
    xml = re.sub(r'<w:docDefaults>.*?</w:docDefaults>', new_dd, xml, flags=re.S)

    # 3) 逐样式替换; 默认模板里没有的(TOC1/TOC2/自定义等)先记下, 最后追加
    missing = []
    for sid, new in STYLES.items():
        pat = r'<w:style\b[^>]*w:styleId="%s"[^>]*>.*?</w:style>' % re.escape(sid)
        if not re.search(pat, xml, flags=re.S):
            missing.append(new)
        else:
            xml = re.sub(pat, new, xml, flags=re.S)

    # 4) 追加缺失样式
    if missing and "</w:styles>" in xml:
        xml = xml.replace("</w:styles>", "\n" + "".join(missing) + "</w:styles>")

    open(sp, "w", encoding="utf-8").write(xml)

    # 5) 重新打包(zipfile, 结构顺序与默认参考一致)
    import zipfile
    if os.path.exists(OUT): os.remove(OUT)
    order = ["[Content_Types].xml", "_rels/.rels", "docProps/core.xml",
             "docProps/app.xml", "word/_rels/document.xml.rels", "word/document.xml",
             "word/styles.xml", "word/numbering.xml", "word/settings.xml",
             "word/fontTable.xml", "word/theme/theme1.xml", "word/webSettings.xml",
             "word/comments.xml", "word/footnotes.xml"]
    present = []
    for rel in order:
        p = os.path.join(TMP, rel.replace("/", os.sep))
        if os.path.isfile(p):
            present.append((rel, p))
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, p in present:
            z.write(p, rel)
    print("生成:", OUT)

if __name__ == "__main__":
    main()
