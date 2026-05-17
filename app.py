# app.py
"""
题库管理系统 - Gradio 主界面
Tab 1: 练习模式（录题、组卷、批改、批量导入）
Tab 2: 数据管理（SQL 查询）

用法:
    python app.py                    # 使用默认 config.yaml
    python app.py -c my_config.yaml  # 指定配置文件
    python app.py --help             # 显示帮助
"""

import yaml
import json
import argparse
import sys
import gradio as gr
from datetime import datetime
from pathlib import Path

from db import QuestionDB
from selector import select_questions
from pdf_generator import PDFGenerator, generate_grade_report
from grading import grade_paper, render_feedback_html
from yaml_importer import parse_file


# ============================================================================
# 命令行参数解析
# ============================================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Exam Recall - 个人题库管理系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python app.py                          # 使用默认配置
    python app.py -c /path/to/config.yaml  # 指定配置文件
        """
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)"
    )
    return parser.parse_args()


# ============================================================================
# 加载配置
# ============================================================================
def load_config(config_path: str) -> dict:
    """加载 YAML 配置文件，对缺失字段填充默认值"""
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        config = {}

    # 递归设置默认值
    config.setdefault("server", {})
    config.setdefault("database", {})
    config.setdefault("output", {})
    config.setdefault("ui", {})
    config.setdefault("ssl", {})
    config.setdefault("selector", {})
    config.setdefault("font", {})

    config["server"].setdefault("host", "127.0.0.1")
    config["server"].setdefault("port", 8964)
    config["database"].setdefault("path", "data/szyf.db")
    config["output"].setdefault("dir", "output")
    config["ui"].setdefault("theme", "Ocean")
    config["ui"].setdefault("title", "题库管理系统")
    config["ssl"].setdefault("certfile", None)
    config["ssl"].setdefault("keyfile", None)
    config["selector"].setdefault("default_count", 20)
    config["selector"].setdefault("min_count", 5)
    config["selector"].setdefault("max_count", 200)
    config["font"].setdefault("path", "msyh.ttc")
    config["font"].setdefault("name", "MicrosoftYaHei")

    return config


# ============================================================================
# 全局配置初始化
# ============================================================================
args = parse_args()
CONFIG = load_config(args.config)

DB_PATH = CONFIG["database"]["path"]
OUTPUT_DIR = Path(CONFIG["output"]["dir"])
OUTPUT_DIR.mkdir(exist_ok=True)

SERVER_HOST = CONFIG["server"]["host"]
SERVER_PORT = CONFIG["server"]["port"]
UI_THEME = CONFIG["ui"]["theme"]
UI_TITLE = CONFIG["ui"]["title"]
SSL_CERTFILE = CONFIG["ssl"]["certfile"]
SSL_KEYFILE = CONFIG["ssl"]["keyfile"]
FONT_PATH = CONFIG["font"]["path"]
FONT_NAME = CONFIG["font"]["name"]
SELECTOR_MIN = CONFIG["selector"]["min_count"]
SELECTOR_MAX = CONFIG["selector"]["max_count"]
SELECTOR_DEFAULT = CONFIG["selector"]["default_count"]

# 初始化数据库
db = QuestionDB(DB_PATH)


# ============================================================================
# 辅助函数
# ============================================================================
def get_major_options():
    result = db.execute_sql(
        "SELECT DISTINCT major_id FROM questions WHERE major_id IS NOT NULL ORDER BY major_id"
    )
    if result[0] and result[1]:
        return [str(row["major_id"]) for row in result[1]]
    return ["1", "2", "3"]


def get_minor_options():
    result = db.execute_sql(
        "SELECT DISTINCT minor_id FROM questions WHERE minor_id IS NOT NULL ORDER BY minor_id"
    )
    if result[0] and result[1]:
        return [str(row["minor_id"]) for row in result[1]]
    return ["1", "2", "3"]


def generate_answer_sheet_yaml(questions, paper_id):
    sheet = {
        "paper_id": paper_id,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ids": [q["id"] for q in questions],
        "answers": ["~"] * len(questions),
    }
    yaml_path = OUTPUT_DIR / f"answer_sheet_{paper_id}.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(sheet, f, allow_unicode=True, default_flow_style=False)
    return str(yaml_path)


def render_paper_html(questions):
    if not questions:
        return "<p>暂无题目，请先录题或调整筛选条件。</p>"

    html = "<div style='font-family: Microsoft YaHei, SimHei, sans-serif; max-height: 500px; overflow-y: auto;'>"
    for i, q in enumerate(questions, 1):
        answer = q.get("answer", "")
        q_type = "[多选]" if len(answer) > 1 else "[单选]"
        html += f"<p><b>{i}. {q['question']}</b> <span style='color:gray; font-size:0.9em'>(ID: {q['id']} {q_type})</span></p>"
        opts = q.get("options", {})
        if opts:
            for opt in ["A", "B", "C", "D", "E", "F"]:
                if opt in opts:
                    html += f"<p style='margin-left:20px;'>{opt}. {opts[opt]}</p>"
        html += "<br>"
    html += "</div>"
    return html


# ============================================================================
# 事件处理函数
# ============================================================================

def on_import_yaml(files):
    if not files:
        return "❌ 请先选择 YAML 文件"

    all_questions = []
    errors = []

    for f in files:
        questions, err = parse_file(f.name)
        if questions:
            all_questions.extend(questions)
        else:
            errors.append(f"❌ {Path(f.name).name}: {err}")

    if not all_questions and errors:
        return "导入失败:\n" + "\n".join(errors)

    count = db.insert_questions(all_questions)

    msg = f"✅ 成功导入 {count} 道题目"
    if errors:
        msg += "\n\n部分失败:\n" + "\n".join(errors)
    return msg


def on_save_question(major, minor, question, options_str, answer, explanation):
    if not question or not answer:
        return "❌ 题目和答案不能为空"

    try:
        options = json.loads(options_str) if options_str else None
    except Exception:
        return "❌ 选项格式错误，请输入有效的 JSON 格式"

    import random

    timestamp = int(datetime.now().timestamp())
    random_suffix = random.randint(1000, 9999)
    qid = f"custom_{timestamp}_{random_suffix}"

    q = {
        "id": qid,
        "major_id": int(major) if major else None,
        "minor_id": int(minor) if minor else None,
        "question": question,
        "options": options,
        "answer": answer.strip().upper(),
        "explanation": explanation,
    }

    success = db.insert_question(q)
    if success:
        return f"✅ 题目保存成功！ID: {qid}"
    return "❌ 保存失败，可能 ID 已存在"


def on_generate_paper(major, minor, count):
    major_id = int(major) if major and major.strip() else None
    minor_id = int(minor) if minor and minor.strip() else None
    count = int(count)

    questions = select_questions(db, major_id=major_id, minor_id=minor_id, count=count)
    if not questions:
        return "<p>没有符合条件的题目</p>", None, None

    paper_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    pdf_path = OUTPUT_DIR / f"paper_{paper_id}.pdf"
    pdf_gen = PDFGenerator(str(pdf_path), font_path=FONT_PATH, font_name=FONT_NAME)
    pdf_gen.generate(questions)

    yaml_path = generate_answer_sheet_yaml(questions, paper_id)
    html = render_paper_html(questions)

    return html, str(pdf_path), yaml_path


def on_grade_paper(yaml_file):
    if yaml_file is None:
        return "", "<p style='color:red'>请先上传答题卡文件</p>", None

    result = grade_paper(yaml_file.name, db)

    if result["success"]:
        score_text = f"{result['score']} / {result['total']}"
        html = render_feedback_html(result)

        paper_id = result.get("paper_id") or datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = OUTPUT_DIR / f"grade_report_{paper_id}.pdf"
        generate_grade_report(result, paper_id, str(report_path), font_path=FONT_PATH, font_name=FONT_NAME)

        return score_text, html, str(report_path)
    return "", f"<p style='color:red'>{result['error']}</p>", None


def on_execute_sql(sql):
    if not sql.strip():
        return "请输入 SQL 语句", ""

    success, result = db.execute_sql(sql)
    if success:
        if isinstance(result, list):
            if result:
                output = json.dumps(result, ensure_ascii=False, indent=2)
                return output, ""
            return "查询成功，但无返回结果", ""
        return str(result), ""
    return f"❌ SQL 错误: {result}", ""


def refresh_major_dropdown():
    options = get_major_options()
    return gr.Dropdown(choices=options, value=options[0] if options else None)


def refresh_minor_dropdown():
    options = get_minor_options()
    return gr.Dropdown(choices=options, value=options[0] if options else None)


# ============================================================================
# Gradio 界面
# ============================================================================
def create_app():
    with gr.Blocks(title=UI_TITLE) as app:
        gr.Markdown("# 📚 题库管理系统")

        with gr.Tab("📝 练习模式"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 录题")
                    major_input = gr.Dropdown(
                        label="大类", choices=get_major_options(), allow_custom_value=True
                    )
                    minor_input = gr.Dropdown(
                        label="小类", choices=get_minor_options(), allow_custom_value=True
                    )
                    question_input = gr.Textbox(label="题目", lines=3, placeholder="输入题目内容")
                    options_input = gr.Textbox(
                        label="选项 (JSON格式)",
                        lines=4,
                        placeholder='{"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"}',
                    )
                    answer_input = gr.Textbox(label="答案", placeholder="例如: C 或 AB")
                    explanation_input = gr.Textbox(label="解析", lines=2, placeholder="输入答案解析")
                    save_btn = gr.Button("保存题目", variant="primary")
                    save_status = gr.Markdown("")

                    gr.Markdown("---")
                    gr.Markdown("### 快捷操作")
                    with gr.Row():
                        refresh_major_btn = gr.Button("刷新大类", size="sm")
                        refresh_minor_btn = gr.Button("刷新小类", size="sm")

                    gr.Markdown("---")
                    gr.Markdown("### 批量导入 YAML")
                    yaml_files = gr.File(
                        label="选择 YAML 文件",
                        file_count="multiple",
                        file_types=[".yaml", ".yml"],
                    )
                    import_btn = gr.Button("开始导入", variant="secondary")
                    import_status = gr.Markdown("")

                with gr.Column(scale=2):
                    gr.Markdown("### 组卷")
                    with gr.Row():
                        paper_major = gr.Dropdown(
                            label="大类（留空则全题库）",
                            choices=[""] + get_major_options(),
                            value="",
                            allow_custom_value=True,
                        )
                        paper_minor = gr.Dropdown(
                            label="小类（可选）",
                            choices=[""] + get_minor_options(),
                            value="",
                            allow_custom_value=True,
                        )
                        paper_count = gr.Slider(
                            SELECTOR_MIN, SELECTOR_MAX, value=SELECTOR_DEFAULT, step=1, label="题目数量"
                        )
                    gen_btn = gr.Button("生成试卷", variant="primary")

                    paper_html = gr.HTML(label="试卷预览", value="<p>点击「生成试卷」开始</p>")

                    with gr.Row():
                        pdf_download = gr.File(label="📥 下载 PDF 试卷")
                        yaml_download = gr.File(label="📥 下载答题卡 (YAML)")

                    gr.Markdown("---")
                    gr.Markdown("### 批改")
                    yaml_upload = gr.File(label="上传答题卡", file_types=[".yaml", ".yml"])
                    grade_btn = gr.Button("提交批改", variant="primary")
                    score_display = gr.Textbox(label="得分")
                    feedback_html = gr.HTML(label="批改详情", value="<p>上传答题卡后点击「提交批改」</p>")
                    grade_pdf_download = gr.File(label="📥 下载批改报告 (PDF)")

        with gr.Tab("🗄️ 数据管理"):
            gr.Markdown("### SQL 查询")
            gr.Markdown("直接输入 SQL 语句操作数据库（支持 SELECT/INSERT/UPDATE/DELETE）")

            sql_input = gr.Textbox(
                label="SQL 语句", lines=5, placeholder="SELECT * FROM questions LIMIT 10;"
            )
            sql_btn = gr.Button("执行查询", variant="primary")
            sql_output = gr.Textbox(label="查询结果", lines=10)
            sql_error = gr.Markdown("")

        # 事件绑定
        import_btn.click(on_import_yaml, yaml_files, import_status)

        save_btn.click(
            on_save_question,
            [major_input, minor_input, question_input, options_input, answer_input, explanation_input],
            save_status,
        ).then(
            lambda: ("", "", "", ""),
            None,
            [question_input, options_input, answer_input, explanation_input],
        )

        refresh_major_btn.click(refresh_major_dropdown, None, major_input)
        refresh_minor_btn.click(refresh_minor_dropdown, None, minor_input)

        gen_btn.click(
            on_generate_paper,
            [paper_major, paper_minor, paper_count],
            [paper_html, pdf_download, yaml_download],
        )

        grade_btn.click(
            on_grade_paper,
            yaml_upload,
            [score_display, feedback_html, grade_pdf_download],
        )

        sql_btn.click(on_execute_sql, sql_input, [sql_output, sql_error])

    return app


# ============================================================================
# 启动
# ============================================================================
if __name__ == "__main__":
    app = create_app()

    launch_kwargs = {
        "server_name": SERVER_HOST,
        "server_port": SERVER_PORT,
        "share": False,
        "theme": UI_THEME,
    }
    if SSL_CERTFILE and SSL_KEYFILE:
        launch_kwargs["ssl_certfile"] = SSL_CERTFILE
        launch_kwargs["ssl_keyfile"] = SSL_KEYFILE
        launch_kwargs["ssl_verify"] = False

    app.launch(**launch_kwargs)