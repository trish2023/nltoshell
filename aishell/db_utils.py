import sqlite3
import os
from typing import Optional, Tuple, List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_shell.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def get_command_risk_level(command: str, shell_name: str = "PowerShell") -> Tuple[int, str, bool]:
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT cr.risk_level, cr.description, cr.is_blocked
            FROM command_rules cr
            JOIN shells s ON cr.shell_id = s.shell_id
            WHERE s.shell_name = ?
              AND ? LIKE cr.command_pattern
            ORDER BY cr.risk_level DESC
            LIMIT 1
            """,
            (shell_name, command)
        )
        
        result = cursor.fetchone()
        
        if result:
            return (result['risk_level'], result['description'], bool(result['is_blocked']))
        else:
            return (0, "Command not found in rules database", False)
            
    except sqlite3.Error as e:
        print(f"[DB ERROR] Risk assessment failed: {e}")
        return (0, f"Database error: {e}", False)
    finally:
        conn.close()

def get_all_matching_rules(command: str, shell_name: str = "PowerShell") -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT cr.rule_id, cr.command_pattern, cr.risk_level, 
                   cr.description, cr.is_blocked
            FROM command_rules cr
            JOIN shells s ON cr.shell_id = s.shell_id
            WHERE s.shell_name = ?
              AND ? LIKE cr.command_pattern
            ORDER BY cr.risk_level DESC
            """,
            (shell_name, command)
        )
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to get matching rules: {e}")
        return []
    finally:
        conn.close()

def find_approved_template(user_intent: str, shell_name: str = "PowerShell") -> Optional[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT at.template_id, at.user_intent, at.safe_command, 
                   at.description, at.usage_count
            FROM approved_templates at
            JOIN shells s ON at.shell_id = s.shell_id
            WHERE s.shell_name = ?
              AND LOWER(?) LIKE LOWER('%' || at.user_intent || '%')
            ORDER BY at.usage_count DESC
            LIMIT 1
            """,
            (shell_name, user_intent)
        )
        
        result = cursor.fetchone()
        return dict(result) if result else None
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Template search failed: {e}")
        return None
    finally:
        conn.close()

def log_command_history(user_input: str, generated_command: str, risk_level: int, 
                       was_approved: bool, was_executed: bool, shell_name: str = "PowerShell"):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO command_history 
            (shell_id, user_input, generated_command, risk_level, was_approved, was_executed)
            SELECT shell_id, ?, ?, ?, ?, ?
            FROM shells 
            WHERE shell_name = ?
            """,
            (user_input, generated_command, risk_level, was_approved, was_executed, shell_name)
        )
        
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to log command history: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_recent_history(limit: int = 10, shell_name: str = "PowerShell") -> List[Dict]:
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT ch.user_input, ch.generated_command, ch.risk_level,
                   ch.was_approved, ch.was_executed, ch.execution_timestamp
            FROM command_history ch
            JOIN shells s ON ch.shell_id = s.shell_id
            WHERE s.shell_name = ?
            ORDER BY ch.execution_timestamp DESC
            LIMIT ?
            """,
            (shell_name, limit)
        )
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to get command history: {e}")
        return []
    finally:
        conn.close()

def get_risk_statistics(shell_name: str = "PowerShell") -> Dict:
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_rules,
                SUM(CASE WHEN is_blocked = 1 THEN 1 ELSE 0 END) as blocked_commands,
                COUNT(DISTINCT risk_level) as risk_levels
            FROM command_rules cr
            JOIN shells s ON cr.shell_id = s.shell_id
            WHERE s.shell_name = ?
            """,
            (shell_name,)
        )
        
        result = cursor.fetchone()
        
        cursor.execute(
            """
            SELECT COUNT(*) as approved_templates
            FROM approved_templates at
            JOIN shells s ON at.shell_id = s.shell_id
            WHERE s.shell_name = ?
            """,
            (shell_name,)
        )
        
        templates = cursor.fetchone()
        
        return {
            'total_rules': result['total_rules'],
            'blocked_commands': result['blocked_commands'],
            'risk_levels': result['risk_levels'],
            'approved_templates': templates['approved_templates'],
            'risk_distribution': {}
        }
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to get statistics: {e}")
        return {}
    finally:
        conn.close()

def get_active_shell() -> str:
    return "PowerShell"

RISK_LABELS = {
    0: "Unknown",
    1: "Very Low",
    2: "Low", 
    3: "Medium",
    4: "High",
    5: "Critical"
}

def get_risk_level_color(risk_level: int) -> str:
    colors = {
        0: "dim",
        1: "green",
        2: "blue",
        3: "yellow",
        4: "red",
        5: "bold red"
    }
    return colors.get(risk_level, "white")

def get_risk_level_label(risk_level: int) -> str:
    return RISK_LABELS.get(risk_level, "Unknown")

def format_risk_display(risk_level: int) -> str:
    label = get_risk_level_label(risk_level)
    color = get_risk_level_color(risk_level)
    
    if risk_level == 5:
        return f"[{color}]🚨 CRITICAL RISK: This command can cause irreversible damage![/{color}]"
    elif risk_level == 4:
        return f"[{color}]⚠️  HIGH RISK: This command may cause data loss or system changes![/{color}]"
    elif risk_level == 3:
        return f"[{color}]⚡ MEDIUM RISK: This command will modify files or system state.[/{color}]"
    elif risk_level == 2:
        return f"[{color}]🟡 LOW RISK: This command may make minor system changes.[/{color}]"
    else:
        return f"[{color}]🟢 VERY LOW RISK: This is a safe, read-only command.[/{color}]"

def validate_command(command: str, shell_name: str = "PowerShell") -> Dict:
    risk_level, description, is_blocked = get_command_risk_level(command, shell_name)
    matching_rules = get_all_matching_rules(command, shell_name)
    
    is_allowed = not is_blocked
    risk_label = get_risk_level_label(risk_level)
    warning_message = format_risk_display(risk_level) if risk_level > 2 else None
    requires_confirmation = risk_level >= 3
    requires_double_confirmation = risk_level >= 5
    
    result = {
        'risk_level': risk_level,
        'risk_label': risk_label,
        'is_blocked': is_blocked,
        'is_allowed': is_allowed,
        'description': description,
        'requires_confirmation': requires_confirmation,
        'requires_double_confirmation': requires_double_confirmation,
        'warning_message': warning_message,
        'matching_rules': matching_rules
    }
    
    return result