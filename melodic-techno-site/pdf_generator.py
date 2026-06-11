"""
pdf_generator.py — Generate recipe PDF cards using ReportLab.
Each recipe is a styled single-page (or multi-page) PDF.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Palette matching the site's dark theme
BG_COLOR = colors.HexColor("#0a0a0a")
ACCENT = colors.HexColor("#1a6bff")
WHITE = colors.HexColor("#f0f0f0")
LIGHT_GREY = colors.HexColor("#a0a0a0")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "static", "downloads", "recipes")


def _build_styles():
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "RecipeTitle",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=28,
        textColor=WHITE,
        spaceAfter=4 * mm,
        alignment=TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "RecipeSubtitle",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=13,
        textColor=LIGHT_GREY,
        spaceAfter=8 * mm,
        alignment=TA_LEFT,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=ACCENT,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
        alignment=TA_LEFT,
    )
    body_style = ParagraphStyle(
        "RecipeBody",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=11,
        textColor=WHITE,
        leading=16,
        spaceAfter=2 * mm,
        alignment=TA_LEFT,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=LIGHT_GREY,
        alignment=TA_CENTER,
    )
    return title_style, subtitle_style, section_style, body_style, footer_style


def generate_recipe_pdf(recipe: dict) -> str:
    """
    Generate a PDF for a recipe dict and save it to static/downloads/recipes/.
    Returns the path relative to static/ so Flask can serve it.

    Expected recipe keys:
        name        str   — dish name
        description str   — short intro
        ingredients list  — list of ingredient strings
        steps       list  — list of instruction strings
        filename    str   — output filename without extension
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = recipe.get("filename", "recipe") + ".pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    title_s, subtitle_s, section_s, body_s, footer_s = _build_styles()

    story = []

    # Title
    story.append(Paragraph(recipe.get("name", "Recipe"), title_s))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=4 * mm))

    # Description
    if recipe.get("description"):
        story.append(Paragraph(recipe["description"], subtitle_s))

    # Ingredients
    story.append(Paragraph("Ingredients", section_s))
    for ingredient in recipe.get("ingredients", []):
        story.append(Paragraph(f"• {ingredient}", body_s))

    # Steps
    story.append(Paragraph("Method", section_s))
    for i, step in enumerate(recipe.get("steps", []), 1):
        story.append(Paragraph(f"{i}. {step}", body_s))

    story.append(Spacer(1, 12 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GREY))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Downloaded from the artist's website", footer_s))

    # Dark background — draw it on each page via a canvas callback
    def dark_background(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BG_COLOR)
        canvas.rect(0, 0, A4[0], A4[1], fill=True, stroke=False)
        canvas.restoreState()

    doc.build(story, onFirstPage=dark_background, onLaterPages=dark_background)

    # Return the URL path relative to /static/
    return f"downloads/recipes/{filename}"
