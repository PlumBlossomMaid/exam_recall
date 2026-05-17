# selector.py
"""
抽题算法模块
基于错误率权重的随机抽取
"""

import random
import sqlite3
from typing import List, Dict, Optional, Tuple


def calculate_weight(query_count: int, error_count: int) -> float:
    """
    计算单道题的权重
    
    规则：
    - 未被抽过（query_count == 0）：初始权重 2.0
    - 已被抽过：1.0 + (错误率 × 10)
    
    错误率 = error_count / query_count
    """
    if query_count == 0:
        return 2.0
    else:
        error_rate = error_count / query_count
        return 1.0 + error_rate * 10.0


def weighted_random_choice(questions: List[Dict], count: int) -> List[Dict]:
    """
    从题目列表中按权重随机抽取指定数量的题目（不重复）
    
    算法：使用累积权重 + 随机数，每次抽中后移除该题，重新计算累积权重
    """
    if count >= len(questions):
        return questions.copy()
    
    selected = []
    remaining = questions.copy()
    
    for _ in range(count):
        # 计算累积权重
        weights = [q["_weight"] for q in remaining]
        total_weight = sum(weights)
        
        # 随机抽取
        r = random.random() * total_weight
        cumulative = 0
        chosen_idx = 0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                chosen_idx = i
                break
        
        selected.append(remaining.pop(chosen_idx))
    
    return selected


def select_questions(
    db,
    major_id: Optional[int] = None,
    count: int = 20,
    minor_id: Optional[int] = None
) -> List[Dict]:
    """
    从数据库按条件抽取题目
    
    参数：
    - db: QuestionDB 实例
    - major_id: 大类 ID，如果为 None 则不限制
    - count: 抽取数量
    - minor_id: 小类 ID（可选）
    
    返回：题目列表
    """
    # 1. 查询符合条件的题目
    questions = db.get_questions_by_filter(
        major_id=major_id,
        minor_id=minor_id
    )
    
    if len(questions) == 0:
        return []
    
    # 2. 为每道题计算权重
    for q in questions:
        q["_weight"] = calculate_weight(
            q.get("query_count", 0),
            q.get("error_count", 0)
        )
    
    # 3. 按权重抽取
    count = min(count, len(questions))
    selected = weighted_random_choice(questions, count)
    
    # 4. 清理临时权重字段
    for q in selected:
        del q["_weight"]
    
    return selected


def select_questions_custom(questions: List[Dict], count: int) -> List[Dict]:
    """
    从给定的题目列表中按权重抽取（不依赖数据库）
    
    适用场景：已经查询出题目列表，需要二次筛选
    """
    if count >= len(questions):
        return questions.copy()
    
    # 为每道题计算权重（如果还没有 _weight）
    for q in questions:
        if "_weight" not in q:
            q["_weight"] = calculate_weight(
                q.get("query_count", 0),
                q.get("error_count", 0)
            )
    
    selected = weighted_random_choice(questions, count)
    
    # 清理临时权重字段
    for q in selected:
        if "_weight" in q:
            del q["_weight"]
    
    return selected


# ============================================================================
# 测试代码
# ============================================================================
if __name__ == "__main__":
    # 模拟数据
    mock_questions = [
        {"id": "1", "query_count": 0, "error_count": 0, "question": "新题1"},
        {"id": "2", "query_count": 10, "error_count": 8, "question": "高错误率"},
        {"id": "3", "query_count": 10, "error_count": 2, "question": "低错误率"},
        {"id": "4", "query_count": 5, "error_count": 0, "question": "全对"},
        {"id": "5", "query_count": 0, "error_count": 0, "question": "新题2"},
    ]
    
    # 计算权重并打印
    print("权重分布：")
    for q in mock_questions:
        w = calculate_weight(q["query_count"], q["error_count"])
        print(f"  {q['question']}: {w:.2f}")
    
    print("\n抽取 3 道题（模拟 1000 次）：")
    
    # 统计抽取频率
    freq = {q["id"]: 0 for q in mock_questions}
    for _ in range(1000):
        selected = select_questions_custom(mock_questions, 3)
        for q in selected:
            freq[q["id"]] += 1
    
    for q in mock_questions:
        print(f"  {q['question']}: {freq[q['id']]} 次")
        print(f"  {q['question']}: {freq[q['id']]} 次")