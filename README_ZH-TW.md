# Exam Recall 📚

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一個**個人題庫管理系統**，專為**三支一扶公共基礎知識**刷題而設計。

支援手動錄題、批量匯入 YAML、智慧抽題（基於錯誤率權重）、生成雙欄 PDF 試卷與批改報告。

## ✨ 功能特性

- **📝 錄題**：手動填寫表單，或批量匯入 YAML 格式的題目檔案
- **🎲 智慧組卷**：基於錯誤率的權重隨機抽題，錯得越多越容易被抽中
- **📄 PDF 生成**：雙欄排版的試卷 PDF + 批改報告 PDF，支援中文（微軟正黑體）
- **✅ 自動批改**：上傳答題卡 YAML，自動批改並生成解析報告
- **🗄️ SQL 管理**：內建 SQL 查詢面板，可直接操作資料庫
- **🔐 HTTPS 支援**：內建自簽名憑證，可透過 Sakura Frp 等工具公開存取

## 🚀 快速開始

### 環境要求

- Python 3.8+
- pip

### 安裝

```bash
git clone https://github.com/PlumBlossomMaid/exam_recall.git
cd exam_recall
pip install -r requirements.txt
```

### 配置

編輯 `config.yaml`，修改資料庫路徑、埠號等配置。

### 啟動

```bash
python app.py
# 或指定配置檔
python app.py -c config.yaml
# 檢視幫助
python app.py --help
```

瀏覽器開啟 `http://127.0.0.1:8964`。

## 🛠️ 技術棧

- **UI**: Gradio (Ocean 主題)
- **資料庫**: SQLite
- **PDF 生成**: ReportLab
- **YAML 解析**: PyYAML
- **部署**: AI Studio + Sakura Frp

## ⚠️ 免責聲明

本專案為**個人學習工具**，不保證資料安全。請定期備份 `data/` 目錄下的資料庫檔案。

## 📝 License

本專案基於 MIT 協議開源，詳見 [LICENSE](LICENSE) 檔案。
