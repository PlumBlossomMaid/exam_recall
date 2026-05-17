# count_questions.py
"""
统计目录下所有 YAML 文件中的题目总数
用法: python count_questions.py <目录路径>
"""

import sys
from pathlib import Path
from yaml_importer import parse_file

def count_questions_in_dir(dirpath):
    path = Path(dirpath)
    if not path.is_dir():
        print(f"错误: {dirpath} 不是目录")
        return
    
    yaml_files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))
    if not yaml_files:
        print("没有找到 YAML 文件")
        return
    
    total = 0
    print("=" * 60)
    print(f"{'文件名':<40} {'题目数':>10}")
    print("=" * 60)
    
    for f in sorted(yaml_files):
        questions, err = parse_file(str(f))
        if questions is not None:
            count = len(questions)
            total += count
            print(f"{f.name:<40} {count:>10}")
        else:
            print(f"{f.name:<40} {'解析失败':>10}")
            print(f"  错误: {err}")
    
    print("=" * 60)
    print(f"{'总计':<40} {total:>10}")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python count_questions.py <目录路径>")
        sys.exit(1)
    
    count_questions_in_dir(sys.argv[1])