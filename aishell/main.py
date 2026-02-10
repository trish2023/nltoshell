import subprocess
import sys
import os
import time
import re
from google import genai
from dotenv import load_dotenv
from datetime import datetime

# Rich Library - Custom Terminal UI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.prompt import Prompt, Confirm
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.padding import Padding
from rich import box

# Load .env from the same directory as this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(SCRIPT_DIR, '.env')
load_dotenv(env_path)

# Import SQLite database utilities (validation, rules)
from .db_utils import (
    validate_command,
    log_command_history,
    find_approved_template,
    format_risk_display,
    get_risk_statistics,
    get_recent_history,
    get_active_shell
)
from .db_setup import initialize_database, DB_PATH

# Import MongoDB utilities (logging, session tracking)
from .mongo_utils import (
    initialize_mongodb,
    close_mongodb,
    is_mongodb_available,
    get_session_id,
    log_interaction,
    get_session_interactions,
    get_all_interactions,
    get_interaction_statistics,
    ExecutionTimer
)

# Initialize Rich Console
console = Console()


# =============================================================================
# CUSTOM TERMINAL UI FUNCTIONS
# =============================================================================

def show_splash_screen():
    """Display animated splash screen on startup"""
    console.clear()
    
    logo = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     █████╗ ██╗    ███████╗██╗  ██╗███████╗██╗     ██╗        ║
    ║    ██╔══██╗██║    ██╔════╝██║  ██║██╔════╝██║     ██║        ║
    ║    ███████║██║    ███████╗███████║█████╗  ██║     ██║        ║
    ║    ██╔══██║██║    ╚════██║██╔══██║██╔══╝  ██║     ██║        ║
    ║    ██║  ██║██║    ███████║██║  ██║███████╗███████╗███████╗   ║
    ║    ╚═╝  ╚═╝╚═╝    ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝   ║
    ║                                                               ║
    ║           Intelligent Command Shell • Dual-DBMS               ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(logo, style="bold cyan")
    time.sleep(0.5)


def show_header():
    """Display the main terminal header with system info"""
    console.clear()
    
    # Title bar
    title = Text()
    title.append("  AI SHELL ", style="bold white on blue")
    title.append(" v2.0 ", style="bold yellow on blue")
    title.append(" Dual-DBMS Terminal ", style="white on blue")
    
    console.print(Panel(
        title,
        box=box.DOUBLE,
        style="blue",
        padding=(0, 2)
    ))
    
    # System status panel
    status_table = Table(show_header=False, box=None, padding=(0, 2))
    status_table.add_column("Label", style="dim", width=20)
    status_table.add_column("Value", style="white")
    
    stats = get_risk_statistics()
    mongo_stats = get_interaction_statistics()
    
    status_table.add_row("🗄️  SQLite", f"[green]Active[/green] • {DB_PATH}")
    status_table.add_row(
        "🍃 MongoDB", 
        f"[green]Connected ✓[/green]" if mongo_stats.get('mongodb_available') else "[red]Offline ✗[/red]"
    )
    if mongo_stats.get('mongodb_available'):
        status_table.add_row("🔑 Session", f"{get_session_id()[:8]}...")
    status_table.add_row("🤖 AI Model", MODEL)
    status_table.add_row("🔐 API Key", f"{API_KEY[:8]}...{API_KEY[-4:]}")
    status_table.add_row("🛡️  Security Rules", f"{sum(stats.get('risk_distribution', {}).values())} rules loaded")
    status_table.add_row("🚫 Blocked Patterns", str(stats.get('blocked_commands', 0)))
    status_table.add_row("✅ Safe Templates", str(stats.get('approved_templates', 0)))
    
    console.print(Panel(
        status_table,
        title="[bold]⚙️  System Status[/bold]",
        box=box.ROUNDED,
        border_style="dim cyan",
        padding=(1, 1)
    ))
    
    # Commands quick reference
    cmd_table = Table(show_header=False, box=None, padding=(0, 1))
    cmd_table.add_column("Cmd", style="bold yellow", width=12)
    cmd_table.add_column("Description", style="dim")
    
    cmd_table.add_row("help", "Show all commands")
    cmd_table.add_row("stats", "Database statistics")
    cmd_table.add_row("history", "Command history (SQLite)")
    cmd_table.add_row("logs", "Session logs (MongoDB)")
    cmd_table.add_row("alllogs", "All logs across sessions")
    cmd_table.add_row("manual", "Direct PowerShell mode")
    cmd_table.add_row("clear", "Clear screen")
    cmd_table.add_row("exit", "Quit application")
    
    console.print(Panel(
        cmd_table,
        title="[bold]📋 Quick Reference[/bold]",
        box=box.ROUNDED,
        border_style="dim yellow",
        padding=(0, 1)
    ))
    console.print()


def show_help():
    """Display help panel"""
    help_table = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
    help_table.add_column("Command", style="bold yellow", width=15)
    help_table.add_column("Description", style="white")
    help_table.add_column("Database", style="dim", width=10)
    
    help_table.add_row("(any text)", "Natural language → PowerShell command", "Both")
    help_table.add_row("manual", "Enter direct PowerShell mode", "Both")
    help_table.add_row("stats", "Show database statistics", "Both")
    help_table.add_row("history", "Show recent command history", "SQLite")
    help_table.add_row("logs", "Show current session logs", "MongoDB")
    help_table.add_row("alllogs", "Show all logs across sessions", "MongoDB")
    help_table.add_row("clear", "Clear terminal screen", "—")
    help_table.add_row("exit / quit", "Exit the application", "Both")
    
    console.print(Panel(
        help_table,
        title="[bold]📖 AI Shell Help[/bold]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    
    # Risk level guide
    risk_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    risk_table.add_column("Level", width=8, justify="center")
    risk_table.add_column("Label", width=12)
    risk_table.add_column("Action", width=20)
    risk_table.add_column("Example")
    
    risk_table.add_row("[green]1[/green]", "[green]Very Low[/green]", "Auto-approve", "Get-ChildItem")
    risk_table.add_row("[blue]2[/blue]", "[blue]Low[/blue]", "Single confirm", "New-Item")
    risk_table.add_row("[yellow]3[/yellow]", "[yellow]Medium[/yellow]", "Confirm + warning", "Stop-Process")
    risk_table.add_row("[red]4[/red]", "[red]High[/red]", "Double confirm", "Remove-Item -Recurse")
    risk_table.add_row("[bold red]5[/bold red]", "[bold red]Critical[/bold red]", "🚫 BLOCKED", "Format-Disk")
    
    console.print(Panel(
        risk_table,
        title="[bold]⚠️  Risk Levels[/bold]",
        box=box.ROUNDED,
        border_style="yellow"
    ))


def show_stats():
    """Display database statistics in rich panels"""
    stats = get_risk_statistics()
    
    # SQLite Statistics
    sqlite_table = Table(box=box.SIMPLE, show_header=True, header_style="bold green")
    sqlite_table.add_column("Metric", style="white")
    sqlite_table.add_column("Value", justify="right", style="bold")
    
    risk_dist = stats.get('risk_distribution', {})
    risk_labels = {1: "Very Low", 2: "Low", 3: "Medium", 4: "High", 5: "Critical"}
    risk_colors = {1: "green", 2: "blue", 3: "yellow", 4: "red", 5: "bold red"}
    
    for level, count in sorted(risk_dist.items()):
        label = risk_labels.get(level, f"Level {level}")
        color = risk_colors.get(level, "white")
        sqlite_table.add_row(f"[{color}]Risk {level} ({label})[/{color}]", str(count))
    
    sqlite_table.add_row("─" * 25, "─" * 5)
    sqlite_table.add_row("Total Rules", str(sum(risk_dist.values())))
    sqlite_table.add_row("Blocked Patterns", str(stats.get('blocked_commands', 0)))
    sqlite_table.add_row("Approved Templates", str(stats.get('approved_templates', 0)))
    
    # MongoDB Statistics
    mongo_stats = get_interaction_statistics()
    mongo_table = Table(box=box.SIMPLE, show_header=True, header_style="bold green")
    mongo_table.add_column("Metric", style="white")
    mongo_table.add_column("Value", justify="right", style="bold")
    
    if mongo_stats.get('mongodb_available'):
        mongo_table.add_row("Session ID", mongo_stats.get('session_id', 'N/A'))
        mongo_table.add_row("Total Interactions", str(mongo_stats.get('total_interactions', 0)))
        mongo_table.add_row("[green]Executed[/green]", str(mongo_stats.get('executed', 0)))
        mongo_table.add_row("[red]Blocked[/red]", str(mongo_stats.get('blocked', 0)))
        mongo_table.add_row("[yellow]Cancelled[/yellow]", str(mongo_stats.get('cancelled', 0)))
    else:
        mongo_table.add_row("Status", "[red]Offline[/red]")
    
    # Display side by side
    left = Panel(sqlite_table, title="[bold]🗄️  SQLite Database[/bold]", box=box.ROUNDED, border_style="cyan")
    right = Panel(mongo_table, title="[bold]🍃 MongoDB Analytics[/bold]", box=box.ROUNDED, border_style="green")
    
    console.print(Columns([left, right], equal=True))


def show_history(history_items):
    """Display command history in a rich table"""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan", title="📜 Command History (SQLite)")
    table.add_column("#", width=3, justify="center")
    table.add_column("Status", width=8, justify="center")
    table.add_column("Risk", width=6, justify="center")
    table.add_column("Command", style="white")
    
    for i, h in enumerate(history_items, 1):
        status = "[green]✓[/green]" if h['was_executed'] else "[red]✗[/red]"
        risk = h['risk_level']
        risk_colors = {1: "green", 2: "blue", 3: "yellow", 4: "red", 5: "bold red"}
        risk_style = risk_colors.get(risk, "white")
        table.add_row(str(i), status, f"[{risk_style}]{risk}[/{risk_style}]", h['generated_command'][:60])
    
    console.print(table)


def show_logs(logs, title="Session Logs (MongoDB)"):
    """Display MongoDB logs in a rich table"""
    table = Table(
        box=box.ROUNDED, show_header=True, header_style="bold green",
        title=f"📋 {title}"
    )
    table.add_column("Time", width=20)
    table.add_column("Status", width=8, justify="center")
    table.add_column("Risk", width=6, justify="center")
    table.add_column("User Input", style="cyan", width=25)
    table.add_column("Command", style="white")
    
    for log in logs:
        status = "[green]✓[/green]" if log.get('was_executed') else "[red]✗[/red]"
        risk = log.get('risk_level', '—')
        risk_colors = {1: "green", 2: "blue", 3: "yellow", 4: "red", 5: "bold red"}
        risk_style = risk_colors.get(risk, "dim") if isinstance(risk, int) else "dim"
        
        ts = log.get('timestamp', '').strftime('%Y-%m-%d %H:%M:%S') if log.get('timestamp') else '—'
        user_input = (log.get('user_input', 'N/A') or 'N/A')[:25]
        cmd = log.get('generated_command') or log.get('execution_error', 'N/A')
        if cmd:
            cmd = cmd[:40]
        else:
            cmd = 'N/A'
        
        risk_display = f"[{risk_style}]{risk}[/{risk_style}]" if isinstance(risk, int) else str(risk)
        table.add_row(ts, status, risk_display, user_input, cmd)
    
    console.print(table)


def show_command_result(command, explanation, risk_level, risk_label, description):
    """Display the AI-generated command in a formatted panel"""
    result = Table(show_header=False, box=None, padding=(0, 1))
    result.add_column("Field", style="dim", width=15)
    result.add_column("Value")
    
    result.add_row("💻 Command:", f"[bold white]{command}[/bold white]")
    result.add_row("📖 Explanation:", f"[italic]{explanation}[/italic]")
    
    risk_colors = {1: "green", 2: "blue", 3: "yellow", 4: "red", 5: "bold red"}
    risk_icons = {1: "🟢", 2: "🔵", 3: "🟡", 4: "🔴", 5: "⛔"}
    color = risk_colors.get(risk_level, "white")
    icon = risk_icons.get(risk_level, "❓")
    
    result.add_row("⚠️  Risk Level:", f"[{color}]{icon} {risk_level}/5 — {risk_label}[/{color}]")
    result.add_row("📝 Details:", f"[dim]{description}[/dim]")
    
    border_color = risk_colors.get(risk_level, "white")
    console.print(Panel(
        result,
        title="[bold]🤖 AI Generated Command[/bold]",
        box=box.ROUNDED,
        border_style=border_color
    ))


def show_template_match(command, description):
    """Display a matched template"""
    result = Table(show_header=False, box=None, padding=(0, 1))
    result.add_column("Field", style="dim", width=15)
    result.add_column("Value")
    result.add_row("💻 Command:", f"[bold white]{command}[/bold white]")
    result.add_row("📖 Description:", f"[italic]{description}[/italic]")
    result.add_row("🛡️  Risk Level:", "[green]🟢 1/5 — Very Low (Pre-approved)[/green]")
    
    console.print(Panel(
        result,
        title="[bold green]✅ Approved Template Found[/bold green]",
        box=box.ROUNDED,
        border_style="green"
    ))


def show_execution_output(success=True, error_msg=None, duration_ms=None):
    """Show execution result"""
    if success:
        msg = Text()
        msg.append("✅ Command executed successfully", style="bold green")
        if duration_ms:
            msg.append(f"  ({duration_ms:.0f}ms)", style="dim")
        console.print(msg)
    else:
        console.print(Panel(
            f"[red]{error_msg}[/red]",
            title="[red]❌ Execution Error[/red]",
            box=box.ROUNDED,
            border_style="red"
        ))


def show_blocked():
    """Show blocked command message"""
    console.print(Panel(
        "[bold red]This command has been BLOCKED by the database security policy.\n"
        "An administrator has restricted this command type.[/bold red]",
        title="[bold red]⛔ EXECUTION BLOCKED[/bold red]",
        box=box.HEAVY,
        border_style="red"
    ))


def show_api_error(error_msg):
    """Display API error in a formatted panel"""
    error_table = Table(show_header=False, box=None, padding=(0, 1))
    error_table.add_column("Field", style="dim", width=12)
    error_table.add_column("Value")
    
    if "429" in error_msg and "RESOURCE_EXHAUSTED" in error_msg:
        error_table.add_row("Type:", "[yellow]Quota Exceeded[/yellow]")
        error_table.add_row("Fix 1:", "Wait a few minutes and retry")
        error_table.add_row("Fix 2:", "Enable billing in Google Cloud")
        error_table.add_row("Fix 3:", "Create new Cloud project + API key")
    elif "403" in error_msg or "PERMISSION_DENIED" in error_msg:
        error_table.add_row("Type:", "[yellow]Permission Denied[/yellow]")
        error_table.add_row("Fix:", "Create new API key at aistudio.google.com")
    elif "404" in error_msg or "NOT_FOUND" in error_msg:
        error_table.add_row("Type:", "[yellow]Model Not Found[/yellow]")
        error_table.add_row("Fix:", f"Model '{MODEL}' may not be available")
    else:
        error_table.add_row("Type:", "[yellow]Unknown Error[/yellow]")
    
    error_table.add_row("Raw:", f"[dim]{error_msg[:200]}[/dim]")
    
    console.print(Panel(
        error_table,
        title="[bold red]⚠️  API Error[/bold red]",
        box=box.ROUNDED,
        border_style="red"
    ))


def main():
    """Main entry point for AI Shell"""
    # Make MODEL accessible in UI functions via global
    global MODEL, API_KEY

    # -----------------------------
    # CONFIG
    # -----------------------------
    API_KEY = os.getenv("GEMINI_API_KEY")

    # Validate API key is loaded
    if not API_KEY:
        console.print(Panel(
            "[red]GEMINI_API_KEY not found in .env file![/red]\n"
            f"[yellow]Looking for .env at: {env_path}[/yellow]\n"
            "[yellow]Please ensure your .env file contains: GEMINI_API_KEY=your_key_here[/yellow]",
            title="[bold red]❌ Configuration Error[/bold red]",
            box=box.ROUNDED,
            border_style="red"
        ))
        sys.exit(1)

    # gemini-2.0-flash-lite has more generous free tier limits
    MODEL = "gemini-2.0-flash-lite"
    SHELL_NAME = "PowerShell"  # Current shell for database queries


    # -----------------------------
    # DATABASE INITIALIZATION
    # -----------------------------
    def ensure_database():
        if not os.path.exists(DB_PATH):
            console.print("[cyan][SETUP] Initializing database for first run...[/cyan]")
            initialize_database()
        return True


    # -----------------------------
    # INIT GEMINI
    # -----------------------------
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        console.print(f"[bold red]ERROR: Failed to initialize Gemini client: {e}[/bold red]")
        sys.exit(1)


    # =============================================================================
    # STARTUP SEQUENCE
    # =============================================================================
    ensure_database()
    mongo_connected = initialize_mongodb()

    # Show splash and header
    show_splash_screen()
    show_header()


    # =============================================================================
    # MAIN LOOP
    # =============================================================================
    while True:
        try:
            # Custom prompt
            user_prompt = Prompt.ask("\n[bold cyan]AI-Shell[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Use 'exit' to quit properly[/yellow]")
            continue

        if not user_prompt:
            console.print("[dim]No input given. Type 'help' for commands.[/dim]")
            continue

        # -------------------------
        # EXIT
        # -------------------------
        if user_prompt.lower() in ["exit", "quit"]:
            close_mongodb()
            console.print(Panel(
                "[bold magenta]Goodbye! All commands have been logged to the databases.[/bold magenta]",
                box=box.ROUNDED,
                border_style="magenta"
            ))
            break

        # -------------------------
        # CLEAR
        # -------------------------
        if user_prompt.lower() == "clear":
            show_header()
            continue

        # -------------------------
        # HELP
        # -------------------------
        if user_prompt.lower() == "help":
            show_help()
            continue

        # -------------------------
        # STATS
        # -------------------------
        if user_prompt.lower() == "stats":
            show_stats()
            continue

        # -------------------------
        # HISTORY
        # -------------------------
        if user_prompt.lower() == "history":
            history = get_recent_history(10)
            if not history:
                console.print("[dim]No command history yet.[/dim]")
            else:
                show_history(history)
            continue

        # -------------------------
        # LOGS
        # -------------------------
        if user_prompt.lower() == "logs":
            logs = get_session_interactions(10)
            if logs:
                show_logs(logs, "Current Session Logs")
            else:
                console.print("[dim]No logs in current session. Showing recent logs from all sessions...[/dim]")
                logs = get_all_interactions(10)
                if logs:
                    show_logs(logs, "Recent Logs (All Sessions)")
                else:
                    console.print("[dim]No logs found in MongoDB.[/dim]")
            continue

        # -------------------------
        # ALL LOGS
        # -------------------------
        if user_prompt.lower() == "alllogs":
            logs = get_all_interactions(20)
            if logs:
                show_logs(logs, "All Logs Across Sessions")
            else:
                console.print("[dim]No logs found in MongoDB.[/dim]")
            continue

        # -------------------------
        # MANUAL MODE
        # -------------------------
        if user_prompt.lower() == "manual":
            console.print(Panel(
                "[yellow]Type PowerShell commands directly. AI generation disabled.\n"
                "Type 'back' to return to AI mode.[/yellow]",
                title="[bold]🔧 Manual Mode[/bold]",
                box=box.ROUNDED,
                border_style="yellow"
            ))

            while True:
                try:
                    manual_cmd = Prompt.ask("[bold green]PS>[/bold green]").strip()
                except (KeyboardInterrupt, EOFError):
                    console.print("[yellow]Type 'back' to exit manual mode[/yellow]")
                    continue

                if manual_cmd.lower() in ['exit', 'quit', 'back']:
                    console.print("[cyan]Returning to AI mode...[/cyan]\n")
                    break
                if not manual_cmd:
                    continue

                validation = validate_command(manual_cmd, f"Manual: {manual_cmd}")
                risk_level = validation.get('risk_level', 3)
                risk_label = validation.get('label', 'Medium')
                is_blocked = validation.get('blocked', False)

                console.print(f"\n[yellow]Command:[/yellow] {manual_cmd}")
                console.print(format_risk_display(risk_level, risk_label, is_blocked))

                if is_blocked:
                    show_blocked()
                    log_command_history(f"Manual: {manual_cmd}", manual_cmd, risk_level, False, False, SHELL_NAME)
                    log_interaction(
                        user_input=f"Manual: {manual_cmd}",
                        generated_command=manual_cmd,
                        risk_level=risk_level,
                        risk_label=risk_label,
                        is_blocked=True,
                        user_approved=False,
                        was_executed=False
                    )
                    continue

                if not Confirm.ask("[cyan]Execute this command?[/cyan]"):
                    console.print("[dim]Command cancelled.[/dim]")
                    log_command_history(f"Manual: {manual_cmd}", manual_cmd, risk_level, False, False, SHELL_NAME)
                    log_interaction(
                        user_input=f"Manual: {manual_cmd}",
                        generated_command=manual_cmd,
                        risk_level=risk_level,
                        risk_label=risk_label,
                        is_blocked=False,
                        user_approved=False,
                        was_executed=False
                    )
                    continue

                console.print("[green]Executing...[/green]\n")
                log_command_history(f"Manual: {manual_cmd}", manual_cmd, risk_level, True, True, SHELL_NAME)

                with ExecutionTimer() as timer:
                    try:
                        subprocess.run(["powershell", "-Command", manual_cmd], check=False)
                        exec_error = None
                    except Exception as e:
                        exec_error = str(e)

                show_execution_output(exec_error is None, exec_error, timer.duration_ms)
                log_interaction(
                    user_input=f"Manual: {manual_cmd}",
                    generated_command=manual_cmd,
                    risk_level=risk_level,
                    risk_label=risk_label,
                    is_blocked=False,
                    user_approved=True,
                    was_executed=True,
                    execution_error=exec_error,
                    execution_duration_ms=timer.duration_ms
                )
            continue


        # =========================================================================
        # CHECK FOR APPROVED TEMPLATE
        # =========================================================================
        template = find_approved_template(user_prompt, SHELL_NAME)
        if template:
            show_template_match(template['safe_command'], template['description'])

            if Confirm.ask("[cyan]Use this safe command?[/cyan]"):
                command = template['safe_command']
                explanation = template['description']
                risk_level = 1

                console.print("\n[green]Running approved command...[/green]\n")
                log_command_history(user_prompt, command, risk_level, True, True, SHELL_NAME)

                with ExecutionTimer() as timer:
                    try:
                        subprocess.run(["powershell", "-Command", command], check=False)
                        exec_error = None
                    except Exception as e:
                        exec_error = str(e)

                show_execution_output(exec_error is None, exec_error, timer.duration_ms)
                log_interaction(
                    user_input=user_prompt,
                    generated_command=command,
                    risk_level=risk_level,
                    risk_label="Very Low",
                    is_blocked=False,
                    user_approved=True,
                    was_executed=True,
                    execution_error=exec_error,
                    execution_duration_ms=timer.duration_ms,
                    used_template=True,
                    template_name=template.get('user_intent')
                )
                continue


        # =========================================================================
        # PROMPT GEMINI AI
        # =========================================================================
        system_instruction = """You are an assistant that converts natural language into Windows PowerShell commands.

    Rules:
    - ONLY generate PowerShell commands (Windows)
    - DO NOT use Linux commands like ls, grep, awk, sed
    - DO NOT add markdown or code blocks
    - Output must be EXACTLY in this format:

    Command:
    <single line command>

    Explanation:
    <one sentence explanation>"""

        console.print("[dim]🤖 Generating command...[/dim]")

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config={
                    "system_instruction": system_instruction
                }
            )
            output = response.text.strip()
        except Exception as e:
            error_msg = str(e)
            show_api_error(error_msg)
            log_interaction(
                user_input=user_prompt,
                generated_command=None,
                risk_level=None,
                risk_label=None,
                is_blocked=False,
                user_approved=False,
                was_executed=False,
                execution_error=f"API_ERROR: {error_msg[:500]}",
                extra_metadata={"error_type": "api_call_failed", "model": MODEL}
            )
            continue


        # =========================================================================
        # PARSE RESPONSE
        # =========================================================================
        try:
            command = output.split("Command:")[1].split("Explanation:")[0].strip()
            explanation = output.split("Explanation:")[1].strip()
        except Exception:
            console.print(Panel(
                f"[red]Failed to parse AI response:[/red]\n{output}",
                title="[red]Parse Error[/red]",
                box=box.ROUNDED,
                border_style="red"
            ))
            continue


        # =========================================================================
        # DATABASE VALIDATION & DISPLAY
        # =========================================================================
        validation = validate_command(command, user_prompt)

        show_command_result(
            command, explanation,
            validation['risk_level'],
            validation.get('risk_label', 'Unknown'),
            validation['description']
        )

        # Warning messages
        if validation['warning_message']:
            if validation['risk_level'] >= 4:
                console.print(f"[bold red]⚠️  {validation['warning_message']}[/bold red]")
            elif validation['risk_level'] >= 3:
                console.print(f"[yellow]⚠️  {validation['warning_message']}[/yellow]")

        # =========================================================================
        # BLOCKED CHECK
        # =========================================================================
        if not validation['is_allowed']:
            show_blocked()
            log_command_history(user_prompt, command, validation['risk_level'], False, False, SHELL_NAME)
            log_interaction(
                user_input=user_prompt,
                generated_command=command,
                risk_level=validation['risk_level'],
                risk_label=validation['risk_label'],
                is_blocked=True,
                user_approved=False,
                was_executed=False,
                ai_response_raw=output
            )
            continue

        # =========================================================================
        # CONFIRMATION BASED ON RISK
        # =========================================================================
        approved = False

        if validation['requires_double_confirmation']:
            console.print("[bold red]⚠️  This is a HIGH-RISK command![/bold red]")
            if Confirm.ask("[red]Are you SURE you want to proceed?[/red]"):
                confirm_text = Prompt.ask("[red]Type 'CONFIRM' to execute[/red]")
                if confirm_text == "CONFIRM":
                    approved = True
                else:
                    console.print("[red]Confirmation not received. Command cancelled.[/red]")
            else:
                console.print("[red]Command cancelled.[/red]")

        elif validation['requires_confirmation']:
            approved = Confirm.ask("[yellow]Run this command?[/yellow]")
            if not approved:
                console.print("[dim]Command cancelled.[/dim]")

        else:
            approved = Confirm.ask("[cyan]Run this command?[/cyan]")
            if not approved:
                console.print("[dim]Command cancelled.[/dim]")

        if not approved:
            log_command_history(user_prompt, command, validation['risk_level'], False, False, SHELL_NAME)
            log_interaction(
                user_input=user_prompt,
                generated_command=command,
                risk_level=validation['risk_level'],
                risk_label=validation['risk_label'],
                is_blocked=False,
                user_approved=False,
                was_executed=False,
                ai_response_raw=output
            )
            continue


        # =========================================================================
        # EXECUTE COMMAND
        # =========================================================================
        console.print("\n[bold green]▶ Running command...[/bold green]\n")

        log_command_history(user_prompt, command, validation['risk_level'], True, True, SHELL_NAME)

        exec_error = None
        with ExecutionTimer() as timer:
            try:
                subprocess.run(["powershell", "-Command", command], check=False)
            except Exception as e:
                exec_error = str(e)

        show_execution_output(exec_error is None, exec_error, timer.duration_ms)

        log_interaction(
            user_input=user_prompt,
            generated_command=command,
            risk_level=validation['risk_level'],
            risk_label=validation['risk_label'],
            is_blocked=False,
            user_approved=True,
            was_executed=True,
            execution_error=exec_error,
            execution_duration_ms=timer.duration_ms,
            ai_response_raw=output,
            extra_metadata={
                "matching_rules_count": len(validation.get('matching_rules', []))
            }
        )

if __name__ == "__main__":
    main()
