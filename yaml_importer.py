# yaml_importer.py
"""
YAML 题目解析模块
用法：
   作为模块: from yaml_importer import parse_file, parse_directory
   命令行:  python yaml_importer.py -p <文件或目录> [-o 输出文件] [--no-strict]
"""

import yaml
import json
import os
import sys
import argparse
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any


# ============================================================================
# 常量：题目预期的字段
# ============================================================================
REQUIRED_FIELDS = {"question", "options", "answer", "explanation"}
CLASS_FIELDS = {"major", "minor"}


# ============================================================================
# 内部函数：生成唯一 ID
# ============================================================================
def generate_id(item: Dict[str, Any]) -> str:
    """根据题目数据生成唯一 ID，追加短哈希防冲突"""
    base_id = None
    
    # 1. 优先使用自定义 id
    if "id" in item and item["id"] is not None:
        base_id = str(item["id"])
    # 2. 如果有 class 信息，生成 "major-minor-id" 格式
    elif "class" in item and item["class"] is not None:
        cls = item["class"]
        if all(k in cls for k in ("major", "minor")) and "id" in item:
            base_id = f"{cls['major']}-{cls['minor']}-{item['id']}"
    
    # 3. 野生题目的 fallback
    if base_id is None:
        import random
        timestamp = int(datetime.now().timestamp())
        random_suffix = random.randint(1000, 9999)
        base_id = f"c_{timestamp}_{random_suffix}"
    
    # 4. 追加短哈希（4位），基于题目内容
    content = f"{item.get('question', '')}{item.get('answer', '')}"
    hash_suffix = hashlib.md5(content.encode()).hexdigest()[:4]
    
    return f"{base_id}-{hash_suffix}"


# ============================================================================
# 内部函数：校验题目
# ============================================================================
def validate_question(item: Dict[str, Any], index: int, strict: bool = True) -> Tuple[bool, Optional[str]]:
    """校验单条题目，返回 (是否有效, 错误信息)"""
    if not isinstance(item, dict):
        return False, f"Item {index}: must be a dict, got {type(item).__name__}"
    
    if not strict:
        return True, None
    
    # 检查 options 类型
    if "options" in item and item["options"] is not None:
        if not isinstance(item["options"], dict):
            return False, f"Item {index}: 'options' must be a dict"
    
    # 检查 class 类型
    if "class" in item and item["class"] is not None:
        if not isinstance(item["class"], dict):
            return False, f"Item {index}: 'class' must be a dict"
    
    # 检查自定义 id 类型
    if "id" in item and item["id"] is not None:
        if not isinstance(item["id"], (str, int)):
            return False, f"Item {index}: 'id' must be str or int, got {type(item['id']).__name__}"
    
    return True, None


# ============================================================================
# 内部函数：标准化题目
# ============================================================================
def normalize_question(item: Dict[str, Any]) -> Dict[str, Any]:
    """将原始题目转换为标准格式"""
    q = {
        "id": generate_id(item),
        "question": item.get("question"),
        "options": item.get("options"),
        "answer": item.get("answer"),
        "explanation": item.get("explanation"),
    }
    
    # 如果有 class 信息，保留 major/minor
    if "class" in item and item["class"] is not None:
        q["major_id"] = item["class"].get("major")
        q["minor_id"] = item["class"].get("minor")
    else:
        q["major_id"] = None
        q["minor_id"] = None
    
    return q


# ============================================================================
# 公开 API
# ============================================================================
def parse_string(content: str, strict: bool = True) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """解析 YAML 字符串，返回标准化题目列表"""
    try:
        raw = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return None, f"Invalid YAML syntax: {e}"
    
    if not isinstance(raw, list):
        return None, "YAML root must be a list/array"
    
    if len(raw) == 0:
        return [], None
    
    questions = []
    for i, item in enumerate(raw, 1):
        valid, err = validate_question(item, i, strict)
        if not valid:
            return None, err
        
        q = normalize_question(item)
        questions.append(q)
    
    return questions, None


def parse_file(filepath: str, strict: bool = True) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """解析单个 YAML 文件"""
    path = Path(filepath)
    if not path.exists():
        return None, f"File not found: {filepath}"
    
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"Cannot read file: {e}"
    
    return parse_string(content, strict)


def parse_files(filepaths: List[str], strict: bool = True) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """解析多个 YAML 文件，合并返回"""
    all_questions = []
    for fp in filepaths:
        questions, err = parse_file(fp, strict)
        if questions is None:
            return None, f"Error in {fp}: {err}"
        all_questions.extend(questions)
    
    return all_questions, None


def parse_directory(dirpath: str, strict: bool = True) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """解析目录下所有 .yaml/.yml 文件"""
    path = Path(dirpath)
    if not path.is_dir():
        return None, f"Not a directory: {dirpath}"
    
    yaml_files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))
    if not yaml_files:
        return None, f"No YAML files found in {dirpath}"
    
    return parse_files([str(f) for f in yaml_files], strict)


# ============================================================================
# 命令行界面
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="YAML 题目解析模块 - 将 YAML 题目文件转换为 JSON 格式"
    )
    parser.add_argument("-p", "--path", required=True, help="YAML 文件或目录路径")
    parser.add_argument("-o", "--output", help="输出 JSON 文件（可选，默认打印到 stdout）")
    parser.add_argument("--no-strict", action="store_true", help="禁用严格字段校验")
    
    args = parser.parse_args()
    strict = not args.no_strict
    
    path = Path(args.path)
    if not path.exists():
        print(f"Error: path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)
    
    if path.is_dir():
        questions, err = parse_directory(str(path), strict)
    else:
        questions, err = parse_file(str(path), strict)
    
    if questions is None:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
    
    json_str = json.dumps(questions, ensure_ascii=False, indent=2)
    
    if args.output:
        Path(args.output).write_text(json_str, encoding="utf-8")
        print(f"Written {len(questions)} questions to {args.output}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()