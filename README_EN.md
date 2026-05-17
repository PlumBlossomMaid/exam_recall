### README_EN.md（英文）

```markdown
# Exam Recall 📚

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A **personal question bank management system** designed for practicing **public basic knowledge** for the "Three Supports and One Assistance" (San Zhi Yi Fu) exam in China.

Supports manual entry, batch YAML import, intelligent question selection (weighted by error rate), and generates dual-column PDF exams and grading reports.

## ✨ Features

- **📝 Add Questions**: Manual form entry or batch import from YAML files
- **🎲 Smart Selection**: Weighted random selection based on error rate — questions you get wrong more often appear more frequently
- **📄 PDF Generation**: Dual-column exam PDFs + grading report PDFs with Chinese font support (Microsoft YaHei)
- **✅ Auto Grading**: Upload answer sheet YAML, auto-grade and generate detailed feedback
- **🗄️ SQL Management**: Built-in SQL query panel for direct database operations
- **🔐 HTTPS Support**: Built-in self-signed certificate for public access via Sakura Frp etc.

## 🚀 Quick Start

### Requirements

- Python 3.8+
- pip

### Installation

```bash
git clone https://github.com/PlumBlossomMaid/exam_recall.git
cd exam_recall
pip install -r requirements.txt
```

### Configuration

Edit `config.yaml` to change database path, port, etc.

### Start

```bash
python app.py
# or specify config file
python app.py -c config.yaml
# show help
python app.py --help
```

Open `http://127.0.0.1:8964` in browser.

## 🛠️ Tech Stack

- **UI**: Gradio (Ocean theme)
- **Database**: SQLite
- **PDF**: ReportLab
- **YAML**: PyYAML
- **Deployment**: AI Studio + Sakura Frp

## ⚠️ Disclaimer

This is a **personal learning tool**. Please backup your `data/` directory regularly.

## 📝 License

This project is open-sourced under the MIT license. See [LICENSE](LICENSE) for details.