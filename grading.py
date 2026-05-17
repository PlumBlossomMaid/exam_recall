# grading.py
"""
批改模块
负责解析答题卡 YAML、规范化答案、比对、更新统计、生成批改报告
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


def normalize_answer(ans: str) -> str:
    """
    规范化答案字符串
    
    规则：
    - None 或 "~" 视为未作答
    - 去除首尾空格
    - 统一转为小写
    - 多选题（长度>1且全为字母）按字母顺序排序
    """
    if ans is None or ans == "~":
        return "~"
    
    ans = ans.strip().lower()
    
    # 多选题：排序字母
    if len(ans) > 1 and ans.isalpha():
        ans = "".join(sorted(ans))
    
    return ans


def parse_answer_sheet(yaml_path: str) -> Tuple[Optional[List[str]], Optional[List[str]], Optional[str]]:
    """
    解析答题卡 YAML 文件
    
    参数:
        yaml_path: 答题卡 YAML 文件路径
    
    返回:
        (ids, answers, paper_id) 或 (None, None, error_msg)
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            sheet = yaml.safe_load(f)
    except FileNotFoundError:
        return None, None, f"文件不存在: {yaml_path}"
    except yaml.YAMLError as e:
        return None, None, f"YAML 解析错误: {e}"
    
    if not isinstance(sheet, dict):
        return None, None, "答题卡格式错误：根节点必须是字典"
    
    ids = sheet.get("ids")
    answers = sheet.get("answers")
    paper_id = sheet.get("paper_id")
    
    if ids is None:
        return None, None, "答题卡缺少 'ids' 字段"
    if answers is None:
        return None, None, "答题卡缺少 'answers' 字段"
    if not isinstance(ids, list) or not isinstance(answers, list):
        return None, None, "'ids' 和 'answers' 必须是数组"
    if len(ids) != len(answers):
        return None, None, f"'ids' 和 'answers' 长度不一致 ({len(ids)} vs {len(answers)})"
    
    return ids, answers, paper_id


def grade_paper(
    yaml_path: str,
    db,
    normalize: bool = True
) -> Dict[str, Any]:
    """
    批改试卷主函数
    
    参数:
        yaml_path: 答题卡 YAML 文件路径
        db: QuestionDB 实例
        normalize: 是否规范化答案（默认 True）
    
    返回:
        {
            "success": True/False,
            "error": "错误信息" (仅当 success=False),
            "paper_id": "20260413_153000",
            "score": 85,
            "total": 20,
            "results": [
                {
                    "index": 1,
                    "id": "2-1-3",
                    "user_answer": "C",
                    "correct_answer": "C",
                    "is_correct": True,
                    "question": "题目文本",
                    "explanation": "解析文本"
                },
                ...
            ]
        }
    """
    # 1. 解析答题卡
    ids, answers, paper_id = parse_answer_sheet(yaml_path)
    if ids is None:
        return {
            "success": False,
            "error": answers  # answers 此时是错误信息
        }
    
    total = len(ids)
    correct_count = 0
    results = []
    
    # 2. 逐题批改
    for i, (qid, user_ans) in enumerate(zip(ids, answers), 1):
        # 规范化用户答案
        if normalize:
            user_ans = normalize_answer(user_ans)
        
        # 从数据库查原题
        q = db.get_question(qid)
        if q is None:
            return {
                "success": False,
                "error": f"题目 ID 不存在: {qid}"
            }
        
        correct_ans = q["answer"]
        if normalize:
            correct_ans = normalize_answer(correct_ans)
        
        is_correct = (user_ans == correct_ans)
        if is_correct:
            correct_count += 1
        
        # 更新数据库统计
        db.update_stats(qid, is_correct)
        
        # 记录结果
        results.append({
            "index": i,
            "id": qid,
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "question": q["question"],
            "explanation": q.get("explanation", "")
        })
    
    # 3. 返回批改报告
    return {
        "success": True,
        "paper_id": paper_id,
        "score": correct_count,
        "total": total,
        "results": results
    }


def grade_from_dict(
    ids: List[str],
    answers: List[str],
    db,
    normalize: bool = True
) -> Dict[str, Any]:
    """
    直接从 ID 和答案列表批改（无需 YAML 文件）
    
    适用于前端直接传递答案数组的场景
    
    参数:
        ids: 题目 ID 列表
        answers: 用户答案列表
        db: QuestionDB 实例
        normalize: 是否规范化答案
    
    返回:
        同 grade_paper()
    """
    if len(ids) != len(answers):
        return {
            "success": False,
            "error": f"ID 和答案数量不一致 ({len(ids)} vs {len(answers)})"
        }
    
    total = len(ids)
    correct_count = 0
    results = []
    
    for i, (qid, user_ans) in enumerate(zip(ids, answers), 1):
        if normalize:
            user_ans = normalize_answer(user_ans)
        
        q = db.get_question(qid)
        if q is None:
            return {
                "success": False,
                "error": f"题目 ID 不存在: {qid}"
            }
        
        correct_ans = q["answer"]
        if normalize:
            correct_ans = normalize_answer(correct_ans)
        
        is_correct = (user_ans == correct_ans)
        if is_correct:
            correct_count += 1
        
        db.update_stats(qid, is_correct)
        
        results.append({
            "index": i,
            "id": qid,
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "question": q["question"],
            "explanation": q.get("explanation", "")
        })
    
    return {
        "success": True,
        "paper_id": None,
        "score": correct_count,
        "total": total,
        "results": results
    }


def render_feedback_html(grade_result: Dict[str, Any]) -> str:
    """
    将批改结果渲染为 HTML（用于 Gradio 展示）
    
    参数:
        grade_result: grade_paper() 或 grade_from_dict() 的返回值
    
    返回:
        HTML 字符串
    """
    if not grade_result.get("success"):
        return f"<p style='color:red'>批改失败: {grade_result.get('error')}</p>"
    
    score = grade_result["score"]
    total = grade_result["total"]
    results = grade_result["results"]
    
    html = f"<h2>得分: {score} / {total}</h2>"
    html += "<hr>"
    
    for r in results:
        icon = "✅" if r["is_correct"] else "❌"
        html += f"<h3>{icon} 第 {r['index']} 题 (ID: {r['id']})</h3>"
        
        if not r["is_correct"]:
            html += f"<p><strong>你的答案: {r['user_answer']}，正确答案: {r['correct_answer']}</strong></p>"
        
        html += f"<p><strong>📖 解析:</strong> {r['explanation']}</p>"
        html += "<hr>"
    
    return html


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == "__main__":
    import tempfile
    from db import QuestionDB
    
    print("=" * 60)
    print("Grading 模块测试")
    print("=" * 60)
    
    # 创建临时数据库和答题卡
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = QuestionDB(str(db_path))
        
        # 插入测试题目
        test_questions = [
            {
                "id": "test-1",
                "major_id": 1,
                "minor_id": 1,
                "question": "1+1=?",
                "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
                "answer": "B",
                "explanation": "基础数学"
            },
            {
                "id": "test-2",
                "major_id": 1,
                "minor_id": 1,
                "question": "下列哪些是水果？",
                "options": {"A": "苹果", "B": "香蕉", "C": "胡萝卜", "D": "土豆"},
                "answer": "AB",
                "explanation": "苹果和香蕉是水果"
            }
        ]
        db.insert_questions(test_questions)
        
        # 测试 normalize_answer
        print("\n测试答案规范化:")
        print(f"  'C' -> '{normalize_answer('C')}'")
        print(f"  ' c ' -> '{normalize_answer(' c ')}'")
        print(f"  'BA' -> '{normalize_answer('BA')}'")
        print(f"  '~' -> '{normalize_answer('~')}'")
        
        # 测试 grade_from_dict
        print("\n测试批改:")
        result = grade_from_dict(
            ids=["test-1", "test-2"],
            answers=["B", "BA"],  # 第二题故意用 BA，测试排序
            db=db
        )
        
        if result["success"]:
            print(f"  得分: {result['score']}/{result['total']}")
            for r in result["results"]:
                status = "✅" if r["is_correct"] else "❌"
                print(f"  {status} 第{r['index']}题: {r['user_answer']} vs {r['correct_answer']}")
        else:
            print(f"  批改失败: {result['error']}")
        
        # 验证统计更新
        print("\n验证统计更新:")
        q1 = db.get_question("test-1")
        q2 = db.get_question("test-2")
        print(f"  test-1: query_count={q1['query_count']}, error_count={q1['error_count']}")
        print(f"  test-2: query_count={q2['query_count']}, error_count={q2['error_count']}")
        
        db.close()
    
    print("=" * 60)