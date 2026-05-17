# Exam Recall 📚

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个**个人题库管理系统**，专为**三支一扶公共基础知识**刷题而设计。

支持手动录题、批量导入 YAML、智能抽题（基于错误率权重）、生成双栏 PDF 试卷和批改报告。

## ✨ 功能特性

- **📝 录题**：手动填写表单，或批量导入 YAML 格式的题目文件
- **🎲 智能组卷**：基于错误率的权重随机抽题，错得越多越容易被抽中
- **📄 PDF 生成**：双栏排版的试卷 PDF + 批改报告 PDF，支持中文（微软雅黑）
- **✅ 自动批改**：上传答题卡 YAML，自动批改并生成解析报告
- **🗄️ SQL 管理**：内置 SQL 查询面板，可直接操作数据库
- **🔐 HTTPS 支持**：内置自签名证书，可通过 Sakura Frp 等工具公网访问

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装

```bash
git clone https://github.com/PlumBlossomMaid/exam_recall.git
cd exam_recall
pip install -r requirements.txt
```

### 配置

编辑 `config.yaml`，修改数据库路径、端口等配置：

```yaml
server:
  port: 8964
database:
  path: "data/szyf.db"
font:
  path: "msyh.ttc"
  name: "MicrosoftYaHei"
```

### 启动

```bash
python app.py
# 或指定配置文件
python app.py -c config.yaml
# 查看帮助
python app.py --help
```

浏览器打开 `http://127.0.0.1:8964`。

### 启用 HTTPS

```bash
# 生成自签名证书
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 3650
# 编辑 config.yaml 中 ssl 部分
# 启动后访问 https://127.0.0.1:8964
```

## 📁 项目结构

```
exam_recall/
├── app.py                 # Gradio 主界面
├── config.yaml            # 配置文件
├── db.py                  # SQLite 数据库操作
├── selector.py            # 智能抽题算法
├── pdf_generator.py       # PDF 试卷生成
├── grading.py             # 批改模块
├── yaml_importer.py       # YAML 批量导入
├── count_questions.py     # 题目数量统计工具
├── requirements.txt       # 依赖列表
├── msyh.ttc               # 微软雅黑字体文件
├── data/                  # 数据库目录
└── output/                # 生成的 PDF/YAML 输出目录
```

## 🛠️ 技术栈

- **UI**: Gradio (Ocean 主题)
- **数据库**: SQLite
- **PDF 生成**: ReportLab
- **YAML 解析**: PyYAML
- **部署**: AI Studio + Sakura Frp

## ⚠️ 免责声明

本项目为**个人学习工具**，不保证数据安全。请定期备份 `data/` 目录下的数据库文件。

## 📝 License

本项目基于 MIT 协议开源，详见 [LICENSE](LICENSE) 文件。