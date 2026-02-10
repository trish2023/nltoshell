"""
================================================================================
AI SHELL - DATABASE UTILITIES MODULE
================================================================================
This module provides database query and validation functions for the AI Shell.

DBMS CONCEPTS DEMONSTRATED:
- Parameterized queries (SQL injection prevention)
- SELECT queries with JOINs and WHERE clauses
- Pattern matching with LIKE operator
- Aggregate functions (MAX, COUNT)
- Transaction handling

Author: AI Shell Project
================================================================================
"""

import sqlite3
import os
from typing import Optional, Tuple, List, Dict

# Import database path from setup module
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_shell.db")


# ==============================================================================
# DATABASE CONNECTION
# ==============================================================================

def get_connection():
    """
    Create and return a database connection with foreign key support.
    
    DBMS NOTE: Each function gets its own connection to ensure thread safety
    and proper resource cleanup.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


# ==============================================================================
# RISK ASSESSMENT FUNCTIONS
# ==============================================================================

def get_command_risk_level(command: str, shell_name: str = "PowerShell") -> Tuple[int, str, bool]:
    """
    Query the database to determine the risk level of a command.
    
    DBMS CONCEPTS:
    - JOIN operation: Links command_rules with shells table
    - LIKE operator: Pattern matching for flexible command matching
    - Parameterized query: Prevents SQL injection attacks
    - ORDER BY + LIMIT: Gets the highest matching risk level
    
    Args:
        command: The command string to evaluate
        shell_name: The shell type (default: PowerShell)
    
    Returns:
        Tuple of (risk_level, description, is_blocked)
        Returns (0, "Unknown command", False) if no matching rule found
    
    ALGORITHM:
    1. Extract the first word/cmdlet from the command
    2. Query for rules where the command LIKE pattern matches
    3. Return the HIGHEST risk level found (conservative approach)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Query for matching command rules
        # Uses LIKE for pattern matching: command matches pattern
        # Example: "Remove-Item test.txt" LIKE "Remove-Item%"
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
            # No matching rule found - return unknown
            return (0, "Command not found in rules database", False)
            
    except sqlite3.Error as e:
        print(f"[DB ERROR] Risk assessment failed: {e}")
        return (0, f"Database error: {e}", False)
    finally:
        conn.close()


def get_all_matching_rules(command: str, shell_name: str = "PowerShell") -> List[Dict]:
    """
    Get ALL matching rules for a command, not just the highest risk.
    Useful for displaying detailed information to the user.
    
    DBMS CONCEPTS:
    - Multiple row retrieval with fetchall()
    - Converting Row objects to dictionaries
    """
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
        print(f"[DB ERROR] Rule lookup failed: {e}")
        return []
    finally:
        conn.close()


# ==============================================================================
# APPROVED TEMPLATES FUNCTIONS
# ==============================================================================

def find_approved_template(user_intent: str, shell_name: str = "PowerShell") -> Optional[Dict]:
    """
    Search for a pre-approved command template matching the user's intent.
    
    DBMS CONCEPTS:
    - LIKE with wildcards for fuzzy matching
    - LOWER() function for case-insensitive search
    
    Args:
        user_intent: The user's natural language request
        shell_name: The shell type
    
    Returns:
        Dictionary with template info or None if not found
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Case-insensitive search for matching intent
        cursor.execute(
            """
            SELECT at.template_id, at.user_intent, at.safe_command, at.description
            FROM approved_templates at
            JOIN shells s ON at.shell_id = s.shell_id
            WHERE s.shell_name = ?
              AND LOWER(?) LIKE '%' || LOWER(at.user_intent) || '%'
            LIMIT 1
            """,
            (shell_name, user_intent)
        )
        
        result = cursor.fetchone()
        return dict(result) if result else None
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Template lookup failed: {e}")
        return None
    finally:
        conn.close()


def increment_template_usage(template_id: int) -> None:
    """
    Increment the usage counter for a template.
    
    DBMS CONCEPTS:
    - UPDATE statement with arithmetic operation
    - Tracking usage statistics
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            UPDATE approved_templates 
            SET usage_count = usage_count + 1
            WHERE template_id = ?
            """,
            (template_id,)
        )
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Usage update failed: {e}")
        conn.rollback()
    finally:
        conn.close()


# ==============================================================================
# COMMAND HISTORY FUNCTIONS
# ==============================================================================

def log_command_history(
    user_input: str,
    generated_command: str,
    risk_level: int,
    was_approved: bool,
    was_executed: bool,
    shell_name: str = "PowerShell"
) -> Optional[int]:
    """
    Log a command to the history table for auditing.
    
    DBMS CONCEPTS:
    - INSERT with subquery for foreign key resolution
    - Returning the auto-generated primary key
    - Boolean to integer conversion for SQLite
    
    Returns:
        The history_id of the inserted record, or None on failure
    """
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
            (user_input, generated_command, risk_level, 
             1 if was_approved else 0, 1 if was_executed else 0, shell_name)
        )
        conn.commit()
        return cursor.lastrowid
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] History logging failed: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_recent_history(limit: int = 10) -> List[Dict]:
    """
    Retrieve recent command history entries.
    
    DBMS CONCEPTS:
    - ORDER BY with DESC for reverse chronological order
    - LIMIT clause for pagination
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT ch.history_id, ch.user_input, ch.generated_command,
                   ch.risk_level, ch.was_approved, ch.was_executed,
                   ch.execution_timestamp, s.shell_name
            FROM command_history ch
            JOIN shells s ON ch.shell_id = s.shell_id
            ORDER BY ch.execution_timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] History retrieval failed: {e}")
        return []
    finally:
        conn.close()


# ==============================================================================
# SHELL FUNCTIONS
# ==============================================================================

def get_active_shell() -> Optional[Dict]:
    """
    Get the currently active shell configuration.
    
    DBMS CONCEPTS:
    - SELECT with WHERE clause for filtering
    - Single row retrieval
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT shell_id, os_name, shell_name, description
            FROM shells
            WHERE is_active = 1
            LIMIT 1
            """
        )
        
        result = cursor.fetchone()
        return dict(result) if result else None
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Shell lookup failed: {e}")
        return None
    finally:
        conn.close()


# ==============================================================================
# STATISTICS FUNCTIONS
# ==============================================================================

def get_risk_statistics() -> Dict:
    """
    Get statistics about command risk levels in the database.
    
    DBMS CONCEPTS:
    - Aggregate functions: COUNT, GROUP BY
    - Multiple queries for comprehensive statistics
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Count rules by risk level
        cursor.execute(
            """
            SELECT risk_level, COUNT(*) as count
            FROM command_rules
            GROUP BY risk_level
            ORDER BY risk_level
            """
        )
        
        risk_counts = {row['risk_level']: row['count'] for row in cursor.fetchall()}
        
        # Count blocked commands
        cursor.execute("SELECT COUNT(*) FROM command_rules WHERE is_blocked = 1")
        blocked_count = cursor.fetchone()[0]
        
        # Count approved templates
        cursor.execute("SELECT COUNT(*) FROM approved_templates")
        template_count = cursor.fetchone()[0]
        
        return {
            'risk_distribution': risk_counts,
            'blocked_commands': blocked_count,
            'approved_templates': template_count
        }
        
    except sqlite3.Error as e:
        print(f"[DB ERROR] Statistics retrieval failed: {e}")
        return {}
    finally:
        conn.close()


# ==============================================================================
# RISK LEVEL HELPERS
# ==============================================================================

RISK_LABELS = {
    0: "Unknown",
    1: "Very Low",
    2: "Low", 
    3: "Medium",
    4: "High",
    5: "Critical"
}

RISK_COLORS = {
    0: "\033[90m",   # Gray
    1: "\033[92m",   # Green
    2: "\033[92m",   # Green
    3: "\033[93m",   # Yellow
    4: "\033[91m",   # Red
    5: "\033[95m",   # Magenta/Purple (for critical)
}

RESET_COLOR = "\033[0m"


def get_risk_label(risk_level: int) -> str:
    """Get human-readable label for a risk level."""
    return RISK_LABELS.get(risk_level, "Unknown")


def get_risk_color(risk_level: int) -> str:
    """Get ANSI color code for a risk level."""
    return RISK_COLORS.get(risk_level, RISK_COLORS[0])


def format_risk_display(risk_level: int) -> str:
    """Format risk level with color for terminal display."""
    color = get_risk_color(risk_level)
    label = get_risk_label(risk_level)
    return f"{color}[Risk: {risk_level}/5 - {label}]{RESET_COLOR}"


# ==============================================================================
# VALIDATION FUNCTION (MAIN ENTRY POINT)
# ==============================================================================

def validate_command(command: str, user_input: str = "") -> Dict:
    """
    Main validation function - checks command against database rules.
    
    This is the primary function called by the AI Shell to validate commands.
    
    Args:
        command: The generated command to validate
        user_input: Original user request (for logging)
    
    Returns:
        Dictionary containing:
        - is_allowed: Boolean, whether command can proceed
        - risk_level: Integer 0-5
        - risk_label: Human-readable risk label
        - description: Rule description or warning message
        - requires_confirmation: Boolean, needs extra confirmation
        - warning_message: Optional warning to display
        - matching_rules: List of all matching rules
    """
    # Get risk assessment from database
    risk_level, description, is_blocked = get_command_risk_level(command)
    
    # Get all matching rules for detailed info
    matching_rules = get_all_matching_rules(command)
    
    # Determine validation result
    result = {
        'is_allowed': not is_blocked,
        'risk_level': risk_level,
        'risk_label': get_risk_label(risk_level),
        'description': description,
        'requires_confirmation': risk_level >= 3,
        'requires_double_confirmation': risk_level >= 4,
        'warning_message': None,
        'matching_rules': matching_rules
    }
    
    # Generate appropriate warning messages
    if is_blocked:
        result['warning_message'] = f"⛔ BLOCKED: This command type is blocked by security policy."
    elif risk_level >= 5:
        result['warning_message'] = (
            "🚨 CRITICAL RISK: This command can cause irreversible damage!\n"
            "   Data loss, system instability, or security compromise may occur."
        )
    elif risk_level >= 4:
        result['warning_message'] = (
            "⚠️  HIGH RISK: This command may cause data loss or system changes!\n"
            "   Please review carefully before proceeding."
        )
    elif risk_level >= 3:
        result['warning_message'] = (
            "⚡ MEDIUM RISK: This command will modify files or system state.\n"
            "   Make sure you understand what it does."
        )
    elif risk_level == 0:
        result['warning_message'] = (
            "❓ UNKNOWN: This command is not in the rules database.\n"
            "   Exercise caution - risk cannot be assessed."
        )
    
    return result


# ==============================================================================
# TEST FUNCTION
# ==============================================================================

def test_validation():
    """Test the validation functions with sample commands."""
    print("\n" + "=" * 60)
    print("DATABASE VALIDATION TESTS")
    print("=" * 60)
    
    test_commands = [
        "Get-ChildItem",
        "Get-Process | Select-Object Name",
        "Remove-Item test.txt",
        "Remove-Item -Recurse folder",
        "Format-Volume",
        "random-unknown-command",
        "Get-Content file.txt",
        "Set-Location C:\\Users",
    ]
    
    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        result = validate_command(cmd)
        print(f"  {format_risk_display(result['risk_level'])}")
        print(f"  Allowed: {result['is_allowed']}")
        print(f"  Description: {result['description']}")
        if result['warning_message']:
            print(f"  Warning: {result['warning_message'].split(chr(10))[0]}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    """Run tests when executed directly."""
    test_validation()
