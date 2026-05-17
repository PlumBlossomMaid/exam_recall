# db.py
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple


class QuestionDB:
    def __init__(self, db_path: str = "data/questions.db"):
        """初始化数据库连接，自动创建表和目录"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 返回字典式行
        self._init_tables()
    
    def _init_tables(self):
        """创建表结构"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                major_id INTEGER,
                minor_id INTEGER,
                question TEXT NOT NULL,
                options TEXT,
                answer TEXT NOT NULL,
                explanation TEXT,
                query_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    # ========================================================================
    # 插入操作
    # ========================================================================
    
    def insert_question(self, q: Dict[str, Any], replace: bool = False) -> bool:
        """插入单条题目，如果 ID 已存在且 replace=False 则忽略"""
        try:
            options_json = json.dumps(q.get("options"), ensure_ascii=False) if q.get("options") else None
            
            if replace:
                sql = """
                    INSERT OR REPLACE INTO questions 
                    (id, major_id, minor_id, question, options, answer, explanation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
            else:
                sql = """
                    INSERT OR IGNORE INTO questions 
                    (id, major_id, minor_id, question, options, answer, explanation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
            
            cursor = self.conn.cursor()
            cursor.execute(sql, (
                q["id"],
                q.get("major_id"),
                q.get("minor_id"),
                q["question"],
                options_json,
                q["answer"],
                q.get("explanation")
            ))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Insert error: {e}")
            return False
    
    def insert_questions(self, questions: List[Dict], replace: bool = False) -> int:
        """批量插入题目，返回成功插入的数量"""
        count = 0
        for q in questions:
            if self.insert_question(q, replace):
                count += 1
        return count
    
    # ========================================================================
    # 查询操作
    # ========================================================================
    
    def get_question(self, qid: str) -> Optional[Dict]:
        """按 ID 查询单题"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM questions WHERE id = ?", (qid,))
        row = cursor.fetchone()
        if row:
            return self._row_to_dict(row)
        return None
    
    def get_questions_by_major(self, major_id: int, limit: Optional[int] = None) -> List[Dict]:
        """按大类查询题目"""
        cursor = self.conn.cursor()
        if limit:
            cursor.execute(
                "SELECT * FROM questions WHERE major_id = ? LIMIT ?",
                (major_id, limit)
            )
        else:
            cursor.execute("SELECT * FROM questions WHERE major_id = ?", (major_id,))
        
        return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_questions_by_filter(
        self,
        major_id: Optional[int] = None,
        minor_id: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """多条件查询题目"""
        conditions = []
        params = []
        
        if major_id is not None:
            conditions.append("major_id = ?")
            params.append(major_id)
        if minor_id is not None:
            conditions.append("minor_id = ?")
            params.append(minor_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM questions WHERE {where_clause}"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_all_questions(self) -> List[Dict]:
        """获取所有题目"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM questions ORDER BY major_id, minor_id, id")
        return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # 统计更新
    # ========================================================================
    
    def update_stats(self, qid: str, is_correct: bool):
        """更新做题统计：query_count +1，如果错误则 error_count +1"""
        cursor = self.conn.cursor()
        if is_correct:
            cursor.execute(
                "UPDATE questions SET query_count = query_count + 1 WHERE id = ?",
                (qid,)
            )
        else:
            cursor.execute(
                "UPDATE questions SET query_count = query_count + 1, error_count = error_count + 1 WHERE id = ?",
                (qid,)
            )
        self.conn.commit()
    
    # ========================================================================
    # 自定义 SQL
    # ========================================================================
    
    def execute_sql(self, sql: str) -> Tuple[bool, Any]:
        """执行自定义 SQL，返回 (是否成功, 结果/错误信息)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            
            # 判断是查询还是修改
            if sql.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                # 转换为字典列表
                if rows:
                    columns = [desc[0] for desc in cursor.description]
                    result = [dict(zip(columns, row)) for row in rows]
                    return True, result
                return True, []
            else:
                self.conn.commit()
                return True, f"Affected rows: {cursor.rowcount}"
        except Exception as e:
            return False, str(e)
    
    # ========================================================================
    # 辅助函数
    # ========================================================================
    
    def _row_to_dict(self, row) -> Dict:
        """将 sqlite3.Row 转换为普通字典，并解析 options JSON"""
        d = dict(row)
        if d.get("options"):
            try:
                d["options"] = json.loads(d["options"])
            except json.JSONDecodeError:
                pass  # 保持原字符串
        return d
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()