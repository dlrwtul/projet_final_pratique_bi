"""Outils Word du rapport.

  python docx/docx_tools.py reference SORTIE.docx   crée le modèle de styles passé à pandoc
  python docx/docx_tools.py finish RAPPORT.docx      ajoute la page de garde et la mise à jour des champs
"""
import subprocess
import sys

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ACCENT = RGBColor(0x0B, 0x6E, 0x99)
INK = RGBColor(0x0F, 0x1B, 0x2D)
MUTED = RGBColor(0x5A, 0x66, 0x78)
BODY_FONT, CODE_FONT = "Calibri", "Consolas"
YEAR = "2025–2026"


def _font(style, size=None, color=None, bold=None, name=BODY_FONT):
    style.font.name = name
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        fonts.attrib.pop(qn(attr), None)
    if size:
        style.font.size = Pt(size)
    if color is not None:
        style.font.color.rgb = color
    if bold is not None:
        style.font.bold = bold


def _shade(style, fill):
    ppr = style.element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    ppr.append(shd)


def reference(path):
    subprocess.run(["pandoc", "-o", path, "--print-default-data-file", "reference.docx"], check=True)
    doc = Document(path)
    for section in doc.sections:
        section.page_height, section.page_width = Cm(29.7), Cm(21)
        for side in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
            setattr(section, side, Cm(2.5))
    # styles[...] traduit « Heading 1 » en « heading 1 », que le modèle de pandoc ne connaît pas.
    styles = {style.name: style for style in doc.styles}
    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        if name in styles:
            _font(styles[name], 11, INK)
            styles[name].paragraph_format.line_spacing = 1.15
            styles[name].paragraph_format.space_after = Pt(6)
    headings = {"Title": (26, INK), "Heading 1": (22, INK), "Heading 2": (15, ACCENT),
                "Heading 3": (12.5, INK), "TOC Heading": (22, INK)}
    for name, (size, color) in headings.items():
        if name in styles:
            _font(styles[name], size, color, bold=True)
            styles[name].font.italic = False
    styles["Heading 1"].paragraph_format.page_break_before = True
    styles["Heading 1"].paragraph_format.space_after = Pt(18)
    styles["Heading 2"].paragraph_format.space_before = Pt(18)
    for name in ("Image Caption", "Table Caption", "Caption"):
        if name in styles:
            _font(styles[name], 9, MUTED, bold=False)
            styles[name].font.italic = False
    for name in ("Source Code", "Verbatim Char"):
        if name in styles:
            _font(styles[name], 9, INK, name=CODE_FONT)
    if "Source Code" in styles:
        _shade(styles["Source Code"], "F3F5F8")
    if "Hyperlink" in styles:
        styles["Hyperlink"].font.color.rgb = ACCENT
    doc.save(path)


def _para(body, anchor, text="", size=11, color=INK, bold=False, space_after=4):
    p = body.add_paragraph()
    anchor.addprevious(p._p)
    if text:
        run = p.add_run(text)
        run.font.size, run.font.color.rgb, run.font.bold = Pt(size), color, bold
        run.font.name = BODY_FONT
    p.paragraph_format.space_after = Pt(space_after)
    return p


def finish(path):
    doc = Document(path)
    first = doc.paragraphs[0]._p
    body = doc
    logo = _para(body, first, space_after=6)
    logo.add_run().add_picture("figures/ucad_emblem.png", width=Cm(2.1))
    _para(body, first, "Université Cheikh Anta Diop de Dakar", 13, INK, True, 0)
    _para(body, first, "Faculté des Sciences et Techniques", 10.5, MUTED, space_after=0)
    _para(body, first, "Département de Mathématiques et Informatique, section Informatique", 10.5, MUTED)
    for _ in range(7):
        _para(body, first, space_after=0)
    _para(body, first, "RAPPORT DE PROJET · MASTER 2 BUSINESS INTELLIGENCE", 9.5, ACCENT, True, 10)
    _para(body, first, "Conception d’une Modern Data Platform avec architecture Médaillon "
                       "et application Text-to-SQL basée sur l’IA", 24, INK, True, 12)
    _para(body, first, "Wide World Importers · SQL Server, DLT, dbt, Dagster, Snowflake, Streamlit", 13, MUTED)
    for _ in range(9):
        _para(body, first, space_after=0)
    for label, value in (("Réalisé par", "Ibrahima Lang Diop"), ("Encadrant", "Dr. Jean Gane Sarr"),
                         ("Année universitaire", YEAR)):
        _para(body, first, label, 9, MUTED, space_after=0)
        _para(body, first, value, 11.5, INK, True, 8)
    _para(body, first).add_run().add_break(WD_BREAK.PAGE)

    # Word met à jour la table des matières à l'ouverture.
    settings = doc.settings.element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)
    doc.save(path)


if __name__ == "__main__":
    {"reference": reference, "finish": finish}[sys.argv[1]](sys.argv[2])
