import sqlite3
import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_shell.db")
CREATE_SHELLS_TABLE = """
CREATE TABLE IF NOT EXISTS shells (
    shell_id INTEGER PRIMARY KEY AUTOINCREMENT,
    os_name TEXT NOT NULL,
    shell_name TEXT NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (os_name, shell_name)
);
"""
CREATE_COMMAND_RULES_TABLE = """
CREATE TABLE IF NOT EXISTS command_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shell_id INTEGER NOT NULL,
    command_pattern TEXT NOT NULL,
    risk_level INTEGER NOT NULL CHECK (risk_level >= 1 AND risk_level <= 5),
    description TEXT,
    is_blocked INTEGER DEFAULT 0 CHECK (is_blocked IN (0, 1)),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shell_id) REFERENCES shells(shell_id) ON DELETE CASCADE
);    
"""

CREATE_APPROVED_TEMPLATES_TABLE = """
CREATE TABLE IF NOT EXISTS approved_templates (
    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shell_id INTEGER NOT NULL,
    user_intent TEXT NOT NULL,
    safe_command TEXT NOT NULL,
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shell_id) REFERENCES shells(shell_id) ON DELETE CASCADE
);
"""

CREATE_COMMAND_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS command_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shell_id INTEGER NOT NULL,
    user_input TEXT NOT NULL,
    generated_command TEXT NOT NULL,
    risk_level INTEGER,
    was_approved INTEGER CHECK (was_approved IN (0, 1)),
    was_executed INTEGER CHECK (was_executed IN (0, 1)),
    execution_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shell_id) REFERENCES shells(shell_id) ON DELETE CASCADE
);
"""
CREATE_COMMAND_RULES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_command_pattern 
ON command_rules(command_pattern);
"""
CREATE_HISTORY_TIMESTAMP_INDEX = """
CREATE INDEX IF NOT EXISTS idx_history_timestamp 
ON command_history(execution_timestamp);
"""
SEED_SHELLS = [
    ("Windows", "PowerShell", "Windows PowerShell - default shell for Windows automation", 1),
    ("Windows", "CMD", "Windows Command Prompt - legacy command interpreter", 0),
    ("Linux", "Bash", "Bourne Again Shell - default shell for most Linux distributions", 0),
]
SEED_COMMAND_RULES = [
    ("PowerShell", "Get-ChildItem%", 1, "List directory contents (safe read operation)", 0),
    ("PowerShell", "Get-Location%", 1, "Display current directory path", 0),
    ("PowerShell", "Get-Date%", 1, "Display current date and time", 0),
    ("PowerShell", "Get-Process%", 1, "List running processes (read-only)", 0),
    ("PowerShell", "Get-Service%", 1, "List system services (read-only)", 0),
    ("PowerShell", "Get-Content%", 1, "Read file contents (non-destructive)", 0),
    ("PowerShell", "Get-Help%", 1, "Display help information", 0),
    ("PowerShell", "Get-Command%", 1, "List available commands", 0),
    ("PowerShell", "Get-History%", 1, "Display command history", 0),
    ("PowerShell", "Get-Alias%", 1, "List command aliases", 0),
    ("PowerShell", "pwd%", 1, "Print working directory", 0),
    ("PowerShell", "dir%", 1, "List directory contents (alias)", 0),
    ("PowerShell", "ls%", 1, "List directory contents (alias)", 0),
    ("PowerShell", "cat%", 1, "Display file contents (alias)", 0),
    ("PowerShell", "echo%", 1, "Display text output", 0),
    ("PowerShell", "Write-Output%", 1, "Write to output stream", 0),
    ("PowerShell", "Write-Host%", 1, "Write to console", 0),
    ("PowerShell", "Set-Location%", 2, "Change current directory", 0),
    ("PowerShell", "cd%", 2, "Change directory (alias)", 0),
    ("PowerShell", "New-Item%", 2, "Create new files or directories", 0),
    ("PowerShell", "mkdir%", 2, "Create new directory", 0),
    ("PowerShell", "Copy-Item%", 2, "Copy files or directories", 0),
    ("PowerShell", "cp%", 2, "Copy files (alias)", 0),
    ("PowerShell", "Test-Path%", 2, "Check if path exists", 0),
    ("PowerShell", "Select-Object%", 2, "Select object properties", 0),
    ("PowerShell", "Where-Object%", 2, "Filter objects", 0),
    ("PowerShell", "Sort-Object%", 2, "Sort objects", 0),
    ("PowerShell", "Measure-Object%", 2, "Calculate statistics", 0),
    ("PowerShell", "Move-Item%", 3, "Move/rename files or directories", 0),
    ("PowerShell", "mv%", 3, "Move files (alias)", 0),
    ("PowerShell", "Rename-Item%", 3, "Rename files or directories", 0),
    ("PowerShell", "ren%", 3, "Rename files (alias)", 0),
    ("PowerShell", "Set-Content%", 3, "Write content to file (overwrites)", 0),
    ("PowerShell", "Add-Content%", 3, "Append content to file", 0),
    ("PowerShell", "Out-File%", 3, "Send output to file", 0),
    ("PowerShell", "Start-Process%", 3, "Start a new process", 0),
    ("PowerShell", "Invoke-WebRequest%", 3, "Make web requests", 0),
    ("PowerShell", "Invoke-RestMethod%", 3, "Call REST APIs", 0),
    ("PowerShell", "Remove-Item%", 4, "Delete files or directories - DATA LOSS RISK", 0),
    ("PowerShell", "del%", 4, "Delete files (alias) - DATA LOSS RISK", 0),
    ("PowerShell", "rm%", 4, "Delete files (alias) - DATA LOSS RISK", 0),
    ("PowerShell", "rmdir%", 4, "Remove directory - DATA LOSS RISK", 0),
    ("PowerShell", "Clear-Content%", 4, "Clear file contents - DATA LOSS RISK", 0),
    ("PowerShell", "Stop-Process%", 4, "Terminate a process", 0),
    ("PowerShell", "Stop-Service%", 4, "Stop a system service", 0),
    ("PowerShell", "Restart-Service%", 4, "Restart a system service", 0),
    ("PowerShell", "kill%", 4, "Terminate process (alias)", 0),
    ("PowerShell", "Remove-Item%-Recurse%", 5, "Recursive delete - EXTREME DATA LOSS RISK", 0),
    ("PowerShell", "Format-%", 5, "Format disk - CRITICAL SYSTEM OPERATION", 1),  # Blocked
    ("PowerShell", "Clear-Disk%", 5, "Clear disk - CRITICAL SYSTEM OPERATION", 1),  # Blocked
    ("PowerShell", "Set-ExecutionPolicy%", 5, "Change script execution policy - SECURITY RISK", 0),
    ("PowerShell", "Invoke-Expression%", 5, "Execute arbitrary code - SECURITY RISK", 0),
    ("PowerShell", "iex%", 5, "Execute code (alias) - SECURITY RISK", 0),
    ("PowerShell", "Start-Service%", 5, "Start system service - REQUIRES ADMIN", 0),
    ("PowerShell", "New-Service%", 5, "Create system service - REQUIRES ADMIN", 0),
    ("PowerShell", "Remove-Service%", 5, "Remove system service - REQUIRES ADMIN", 1),  # Blocked
    ("PowerShell", "Restart-Computer%", 5, "Restart the computer - SYSTEM DISRUPTION", 0),
    ("PowerShell", "Stop-Computer%", 5, "Shutdown the computer - SYSTEM DISRUPTION", 0),
    ("PowerShell", "%-Force%", 5, "Force flag detected - bypasses safety prompts", 0),
]
# Pre-approved safe command templates for common intents
SEED_APPROVED_TEMPLATES = [
    # (shell_name, user_intent, safe_command, description)
    ("PowerShell", "list files", "Get-ChildItem", "List files in current directory"),
    ("PowerShell", "show current directory", "Get-Location", "Display current working directory"),
    ("PowerShell", "show running processes", "Get-Process", "List all running processes"),
    ("PowerShell", "show system services", "Get-Service", "List all system services"),
    ("PowerShell", "show current date", "Get-Date", "Display current date and time"),
    ("PowerShell", "show disk space", "Get-PSDrive -PSProvider FileSystem", "Show disk space usage"),
    ("PowerShell", "show environment variables", "Get-ChildItem Env:", "List environment variables"),
    ("PowerShell", "show network adapters", "Get-NetAdapter", "List network adapters"),
    ("PowerShell", "show ip address", "Get-NetIPAddress", "Display IP addresses"),
    ("PowerShell", "clear screen", "Clear-Host", "Clear the terminal screen"),
    # File/folder creation templates
    ("PowerShell", "create file", "New-Item -ItemType File -Name", "Create a new file"),
    ("PowerShell", "create folder", "New-Item -ItemType Directory -Name", "Create a new folder"),
    ("PowerShell", "make directory", "New-Item -ItemType Directory -Name", "Create a new directory"),
]
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Create tables in dependency order
        cursor.execute(CREATE_SHELLS_TABLE)
        cursor.execute(CREATE_COMMAND_RULES_TABLE)
        cursor.execute(CREATE_APPROVED_TEMPLATES_TABLE)
        cursor.execute(CREATE_COMMAND_HISTORY_TABLE)
        # Create indexes for performance
        cursor.execute(CREATE_COMMAND_RULES_INDEX)
        cursor.execute(CREATE_HISTORY_TIMESTAMP_INDEX)
        conn.commit()
        print("[DB] Tables created successfully.")
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to create tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
def seed_shells():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany(
            """
            INSERT OR IGNORE INTO shells (os_name, shell_name, description, is_active)
            VALUES (?, ?, ?, ?)
            """,
            SEED_SHELLS
        )
        conn.commit()
        print(f"[DB] Seeded {cursor.rowcount} shell(s).")
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to seed shells: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
def seed_command_rules():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for shell_name, pattern, risk, desc, blocked in SEED_COMMAND_RULES:
            cursor.execute(
                """
                INSERT OR IGNORE INTO command_rules 
                (shell_id, command_pattern, risk_level, description, is_blocked)
                SELECT shell_id, ?, ?, ?, ?
                FROM shells 
                WHERE shell_name = ?
                """,
                (pattern, risk, desc, blocked, shell_name)
            )
        conn.commit()
        print(f"[DB] Seeded command rules.")
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to seed command rules: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
def seed_approved_templates():
    """
    Insert pre-approved command templates.
    DBMS NOTE: Templates provide a whitelist of known-safe commands
    that can be suggested as alternatives to risky AI-generated commands.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for shell_name, intent, command, desc in SEED_APPROVED_TEMPLATES:
            cursor.execute(
                """
                INSERT OR IGNORE INTO approved_templates 
                (shell_id, user_intent, safe_command, description)
                SELECT shell_id, ?, ?, ?
                FROM shells 
                WHERE shell_name = ?
                """,
                (intent, command, desc, shell_name)
            )
        conn.commit()
        print(f"[DB] Seeded approved templates.")
    except sqlite3.Error as e:
        print(f"[DB ERROR] Failed to seed templates: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
def initialize_database():
    """
    Main initialization function - creates tables and seeds all data.
    Call this once during setup or at application startup.
    """
    print("=" * 60)
    print("AI SHELL - DATABASE INITIALIZATION")
    print("=" * 60)
    print(f"Database path: {DB_PATH}")
    print()
    create_tables()
    seed_shells()
    seed_command_rules()
    seed_approved_templates()
    print()
    print("[DB] Database initialization complete!")
    print("=" * 60)

