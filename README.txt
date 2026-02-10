================================================================================
                    AI SHELL (Gemini) — Dual-DBMS Version
================================================================================

OVERVIEW
--------
An intelligent command-line assistant that converts natural language requests 
into Windows PowerShell commands using Google's Gemini AI. Features a dual-
database architecture with SQLite for command validation and MongoDB for 
interaction logging.

FEATURES
--------
✓ Natural Language to PowerShell Command Translation
✓ Risk Assessment & Command Validation System  
✓ Pre-approved Safe Command Templates
✓ Dual Database Architecture (SQLite + MongoDB)
✓ Command History & Session Tracking
✓ Security Rules & Blocked Command Patterns
✓ Real-time Risk Level Analysis
✓ Execution Timing & Performance Metrics


ARCHITECTURE
------------

CORE COMPONENTS:
• flowtest.py      - Main application & user interface
• db_setup.py      - SQLite database initialization & schema
• db_utils.py      - Database queries & command validation
• mongo_utils.py   - MongoDB connection & session management
• .env             - Environment configuration (API keys)

DATABASE STRUCTURE:
• SQLite (ai_shell.db) - Command rules, risk levels, templates, history
• MongoDB           - Session tracking, interaction logs, performance data


FILE DESCRIPTIONS
-----------------

flowtest.py
-----------
Main application entry point. Handles:
- User input collection and processing
- Gemini API integration for command generation  
- Risk validation using database rules
- Command execution with user confirmation
- Session management and logging
- Error handling and user feedback

db_setup.py
-----------
Database initialization and schema management:
- Creates SQLite database tables
- Seeds command validation rules (59 rules across risk levels 1-5)
- Pre-approved command templates (10+ common operations)
- Shell configuration and blocked patterns
- Risk assessment criteria and descriptions

db_utils.py
-----------
Database interaction utilities:
- Command risk assessment queries
- Template matching for common requests
- Command history logging
- Risk statistics and reporting
- Validation rule management

mongo_utils.py
--------------
MongoDB integration for advanced logging:
- Session tracking with unique IDs
- Detailed interaction logging
- Performance metrics (execution timing)
- Query utilities for analytics
- Connection management with error handling


SECURITY SYSTEM
---------------

RISK LEVELS:
1. Very Low  - Safe read operations (Get-ChildItem, Get-Location)
2. Low       - Basic file operations (New-Item, Copy-Item)  
3. Medium    - System queries (Get-Process, Get-Service)
4. High      - Administrative tasks (Stop-Service, Remove-Item)
5. Critical  - Dangerous operations (Format-Disk) - BLOCKED

VALIDATION PROCESS:
1. Check for pre-approved templates (bypass AI if found)
2. Generate command using Gemini AI
3. Query database for matching risk patterns
4. Display risk level and require user confirmation
5. Block execution if command matches blocked patterns
6. Log all attempts to both databases


PRE-APPROVED TEMPLATES
---------------------
• "list files"           → Get-ChildItem
• "show current directory" → Get-Location
• "show running processes" → Get-Process
• "show system services"   → Get-Service
• "show current date"      → Get-Date
• "show disk space"        → Get-PSDrive -PSProvider FileSystem
• "clear screen"           → Clear-Host
• Additional file/folder creation templates


INSTALLATION & SETUP
--------------------

PREREQUISITES:
• Python 3.8+
• Required packages: google-genai, pymongo, python-dotenv
• Google Gemini API key
• MongoDB (optional - app works without it)

SETUP STEPS:
1. Install dependencies:
   pip install google-genai pymongo python-dotenv

2. Create .env file with your API key:
   GEMINI_API_KEY=your_api_key_here

3. Run the application:
   python flowtest.py

4. Database files will be created automatically on first run


USAGE
-----

BASIC COMMANDS:
• Type natural language requests: "create a file called test.txt"
• Use special commands: 'history', 'stats', 'logs', 'help'
• Exit with: 'quit' or 'exit'

EXAMPLE INTERACTIONS:
> list files in current directory
  → Uses pre-approved template (instant execution)

> create a backup of important files  
  → Generates PowerShell command via AI
  → Shows risk assessment
  → Requires user confirmation

> delete all files in C drive
  → High risk command
  → May be blocked by security rules


CONFIGURATION
-------------

GEMINI MODEL:
Current: gemini-2.0-flash-lite (optimized for free tier)
Alternative models available in flowtest.py

DATABASE PATHS:
• SQLite: ./ai_shell.db  
• MongoDB: localhost:27017 (default)

SHELL SUPPORT:
• Primary: PowerShell (Windows)
• Extensible architecture for other shells


SECURITY CONSIDERATIONS
----------------------
• API keys are loaded from .env (never hardcode)
• All commands logged for audit trail
• Risk-based confirmation system prevents accidents
• Critical operations are completely blocked
• User approval required for medium+ risk commands


TROUBLESHOOTING
--------------

COMMON ISSUES:

1. API Quota Exceeded:
   - Wait for quota reset or upgrade API plan
   - Check usage at https://ai.google.dev/

2. Database Connection Errors:
   - Ensure write permissions in application directory
   - MongoDB errors are non-fatal (app continues with SQLite only)

3. Command Not Found Errors:
   - Check if PowerShell is available in system PATH
   - Verify Windows environment compatibility

4. Model Not Found:
   - Update MODEL variable in flowtest.py
   - Use available models from Gemini API


LOGS & MONITORING
----------------

SQLITE LOGS:
• Table: command_history
• Contains: user input, generated commands, risk levels, execution status

MONGODB LOGS:  
• Collection: interactions
• Contains: detailed session data, timing metrics, error logs

ACCESS LOGS:
Use built-in commands:
• 'history' - Recent command history
• 'stats'   - Risk level statistics  
• 'logs'    - Session interaction logs


EXTENDING THE PROJECT
--------------------

ADDING NEW TEMPLATES:
Edit SEED_APPROVED_TEMPLATES in db_setup.py

ADDING RISK RULES:
Edit SEED_COMMAND_RULES in db_setup.py  

SUPPORTING NEW SHELLS:
1. Add shell configuration in db_setup.py
2. Update MODEL prompts in flowtest.py
3. Add shell-specific command patterns

ALTERNATIVE AI MODELS:
Update CLIENT initialization and MODEL variable in flowtest.py


VERSION HISTORY
--------------
Current Version: Dual-DBMS Implementation
- SQLite + MongoDB integration
- Enhanced risk assessment system
- Pre-approved command templates
- Session tracking and performance metrics


AUTHOR & LICENSE
---------------
Educational project demonstrating AI-powered command generation with
database-driven security and validation systems.

For support or contributions, refer to the project documentation.

================================================================================