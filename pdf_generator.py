# pdf_generator.py
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import Paragraph, Frame, PageTemplate, BaseDocTemplate, Spacer
from reportlab.lib.colors import black, gray, red

# 页面配置常量
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 8 * mm
COLUMN_GAP = 6 * mm
COLUMN_WIDTH = (PAGE_WIDTH - 2 * MARGIN - COLUMN_GAP) / 2

# 默认字体（模块级 fallback）
_DEFAULT_FONT_PATH = "msyh.ttc"
_DEFAULT_FONT_NAME = "MicrosoftYaHei"


def _register_font(font_path: str, font_name: str) -> str:
    """注册字体，返回实际使用的字体名称"""
    path = Path(font_path)
    if path.exists():
        pdfmetrics.registerFont(TTFont(font_name, str(path)))
        return font_name
    # fallback
    for fallback in ("simsun.ttc", "C:/Windows/Fonts/simsun.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(fallback).exists():
            pdfmetrics.registerFont(TTFont(font_name, fallback))
            return font_name
    raise FileNotFoundError(f"字体文件不存在: {font_path}")


def generate_title():
    return f"{datetime.now().strftime('%b %d %Y %H:%M:%S')} paper {str(uuid.uuid4())[:8]}"


def format_id_list(ids: List[str]) -> str:
    return json.dumps(ids, ensure_ascii=False)


class NumberedCanvas(pdf_canvas.Canvas):
    def __init__(self, *args, font_name: str = _DEFAULT_FONT_NAME, **kwargs):
        super().__init__(*args, **kwargs)
        self._font_name = font_name

    def showPage(self):
        self.saveState()
        self.setStrokeColor(gray)
        self.setLineWidth(0.5)
        x = MARGIN + COLUMN_WIDTH + COLUMN_GAP / 2
        self.line(x, MARGIN, x, PAGE_HEIGHT - MARGIN)
        self.setFont(self._font_name, 9)
        self.setFillColor(gray)
        self.drawCentredString(PAGE_WIDTH / 2, 11, str(self.getPageNumber()))
        self.restoreState()
        pdf_canvas.Canvas.showPage(self)


class PDFGenerator:
    def __init__(
        self,
        output_path: str,
        font_path: Optional[str] = None,
        font_name: Optional[str] = None,
    ):
        self.output_path = output_path
        font_path = font_path or _DEFAULT_FONT_PATH
        font_name = font_name or _DEFAULT_FONT_NAME
        self.font_name = _register_font(font_path, font_name)

        # 动态创建样式
        self.title_style = ParagraphStyle(
            "Title", fontName=self.font_name, fontSize=12, leading=16,
            textColor=black, alignment=TA_LEFT, bold=True, spaceAfter=4,
        )
        self.id_list_style = ParagraphStyle(
            "IDList", fontName=self.font_name, fontSize=8, leading=11,
            textColor=black, alignment=TA_LEFT, spaceAfter=6,
        )
        self.question_style = ParagraphStyle(
            "Question", fontName=self.font_name, fontSize=10, leading=14,
            textColor=black, alignment=TA_LEFT, spaceAfter=4, leftIndent=0,
        )
        self.option_style = ParagraphStyle(
            "Option", fontName=self.font_name, fontSize=10, leading=14,
            textColor=black, alignment=TA_LEFT, leftIndent=12, spaceAfter=2,
        )
        self.id_style = ParagraphStyle(
            "ID", fontName=self.font_name, fontSize=8, leading=11,
            textColor=gray, alignment=TA_LEFT, spaceAfter=2,
        )
        self.answer_style = ParagraphStyle(
            "Answer", fontName=self.font_name, fontSize=10, leading=14,
            textColor=black, alignment=TA_LEFT, leftIndent=12, spaceAfter=2,
        )
        self.wrong_answer_style = ParagraphStyle(
            "WrongAnswer", fontName=self.font_name, fontSize=10, leading=14,
            textColor=red, alignment=TA_LEFT, leftIndent=12, spaceAfter=2,
        )
        self.explanation_style = ParagraphStyle(
            "Explanation", fontName=self.font_name, fontSize=10, leading=14,
            textColor=black, alignment=TA_LEFT, leftIndent=12, spaceAfter=2,
        )
        self.divider_style = ParagraphStyle(
            "Divider", fontName=self.font_name, fontSize=8, leading=2,
        )

        bottom_margin = MARGIN + 10
        frame_left = Frame(MARGIN, bottom_margin, COLUMN_WIDTH, PAGE_HEIGHT - MARGIN - bottom_margin, id="left")
        frame_right = Frame(MARGIN + COLUMN_WIDTH + COLUMN_GAP, bottom_margin, COLUMN_WIDTH, PAGE_HEIGHT - MARGIN - bottom_margin, id="right")
        template = PageTemplate(id="TwoColumn", frames=[frame_left, frame_right])
        self.doc = BaseDocTemplate(
            output_path, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=bottom_margin,
        )
        self.doc.addPageTemplates([template])

    def _canvas_factory(self):
        """返回一个适配 BaseDocTemplate 的 canvas 工厂函数"""
        font_name = self.font_name
        return lambda *args, **kwargs: NumberedCanvas(*args, font_name=font_name, **kwargs)

    def format_question(self, q: Dict, index: int) -> List:
        paragraphs = []
        answer = q.get("answer", "")
        question_type = "[多选]" if len(answer) > 1 else "[单选]"
        paragraphs.append(Paragraph(f"ID: {q['id']} {question_type}", self.id_style))
        paragraphs.append(Paragraph(f"<b>{index}.</b> {q['question']}", self.question_style))
        options = q.get("options")
        if options and isinstance(options, dict):
            for opt_key in ["A", "B", "C", "D", "E", "F"]:
                if opt_key in options:
                    paragraphs.append(Paragraph(f"{opt_key}. {options[opt_key]}", self.option_style))
        paragraphs.append(Spacer(1, 6))
        return paragraphs

    def format_grade_item(self, result: Dict, index: int) -> List:
        paragraphs = []
        icon = "\u2713" if result["is_correct"] else "\u2717"
        correct_ans = result.get("correct_answer", "")
        q_type = "[多选]" if len(correct_ans) > 1 else "[单选]"
        paragraphs.append(Paragraph(f"ID: {result['id']} {q_type} {icon}", self.id_style))
        paragraphs.append(Paragraph(f"<b>{index}.</b> {result['question']}", self.question_style))
        opts = result.get("options")
        if opts and isinstance(opts, dict):
            for opt_key in ["A", "B", "C", "D", "E", "F"]:
                if opt_key in opts:
                    paragraphs.append(Paragraph(f"{opt_key}. {opts[opt_key]}", self.option_style))
        user_ans = result.get("user_answer", "~")
        paragraphs.append(Paragraph(f"你的答案: {user_ans}", self.answer_style))
        if not result["is_correct"]:
            paragraphs.append(Paragraph(f"正确答案: {correct_ans}", self.wrong_answer_style))
        explanation = result.get("explanation", "无解析")
        paragraphs.append(Paragraph(f"解析: {explanation}", self.explanation_style))
        paragraphs.append(Spacer(1, 8))
        return paragraphs

    def generate(self, questions: List[Dict]) -> str:
        story = []
        story.append(Paragraph(f"<b>{generate_title()}</b>", self.title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"ID LIST: {format_id_list([q['id'] for q in questions])}", self.id_list_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("<hr width='100%' size='0.5' color='gray' />", self.divider_style))
        story.append(Spacer(1, 6))
        for i, q in enumerate(questions, 1):
            story.extend(self.format_question(q, i))
        self.doc.build(story, canvasmaker=self._canvas_factory())
        return self.output_path


def generate_grade_report(
    grade_result: Dict[str, Any],
    paper_id: str,
    output_path: str,
    font_path: Optional[str] = None,
    font_name: Optional[str] = None,
) -> str:
    generator = PDFGenerator(output_path, font_path=font_path, font_name=font_name)
    title = f"{datetime.now().strftime('%b %d %Y %H:%M:%S')} paper {paper_id} [批改报告]"
    score_line = f"得分: {grade_result['score']} / {grade_result['total']}"
    results = grade_result["results"]
    ids = [r["id"] for r in results]

    story = []
    story.append(Paragraph(f"<b>{title}</b>", generator.title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(f"ID LIST: {format_id_list(ids)}", generator.id_list_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(f"<b>{score_line}</b>", generator.question_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<hr width='100%' size='0.5' color='gray' />", generator.divider_style))
    story.append(Spacer(1, 6))
    for i, r in enumerate(results, 1):
        story.extend(generator.format_grade_item(r, i))
    generator.doc.build(story, canvasmaker=generator._canvas_factory())
    return output_path


def main():
    print("=" * 60)
    print("PDF Generator 测试")
    print("=" * 60)
    mock_questions = []
    for i in range(1, 31):
        mock_questions.append({
            "id": f"2-1-{i}",
            "question": f"第 {i} 题：这是测试题目，请选出正确选项。" if i % 3 != 0 else f"第 {i} 题：多选题测试。",
            "options": {"A": f"选项A-{i}", "B": f"选项B-{i}", "C": f"选项C-{i}", "D": f"选项D-{i}"},
            "answer": "C" if i % 3 != 0 else "AB",
            "explanation": f"第 {i} 题解析。",
        })
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"test_paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    generator = PDFGenerator(str(output_path))
    result_path = generator.generate(mock_questions)
    print(f"✅ PDF 已生成: {result_path}")
    print(f"📄 文件大小: {Path(result_path).stat().st_size / 1024:.2f} KB")

    print("\n测试批改报告生成...")
    mock_grade_result = {
        "score": 25,
        "total": 30,
        "results": [
            {
                "id": f"2-1-{i}",
                "question": mock_questions[i - 1]["question"],
                "options": mock_questions[i - 1]["options"],
                "user_answer": "C" if i % 2 == 0 else "A",
                "correct_answer": mock_questions[i - 1]["answer"],
                "is_correct": (i % 2 == 0),
                "explanation": mock_questions[i - 1]["explanation"],
            }
            for i in range(1, 6)
        ],
    }
    report_path = output_dir / f"test_grade_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    generate_grade_report(mock_grade_result, "test_paper_001", str(report_path))
    print(f"✅ 批改报告已生成: {report_path}")

    try:
        os.startfile(result_path)
    except Exception:
        pass


if __name__ == "__main__":
    main()
