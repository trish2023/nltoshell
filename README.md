# 🤖 AI Shell

**Natural Language to PowerShell Command Generator**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-blue)](https://ai.google.dev/)

A sophisticated AI-powered command-line interface that converts natural language requests into Windows PowerShell commands using Google's Gemini AI, featuring dual-database architecture for security and session management.

![AI Shell Demo](https://via.placeholder.com/800x400/1a1a1a/ffffff?text=🤖+AI+Shell+Demo)

## ✨ Features

### 🧠 **Intelligent Command Generation**
- **Natural Language Processing**: Convert plain English to PowerShell commands
- **Google Gemini AI Integration**: Powered by state-of-the-art language models
- **Context-Aware**: Understands complex, multi-step operations

### 🛡️ **Advanced Security System**
- **5-Level Risk Assessment**: Automatic command safety evaluation
- **Database-Driven Validation**: Configurable security rules and patterns  
- **Pre-approved Templates**: Whitelist of verified safe commands
- **User Confirmation**: Interactive approval for risky operations
- **Blocked Commands**: Prevent execution of dangerous operations

### 🗄️ **Dual-Database Architecture**
- **SQLite**: Command rules, risk levels, templates, and history
- **MongoDB**: Session logging, interaction tracking, and analytics
- **Audit Trail**: Complete command execution history
- **Performance Metrics**: Execution timing and success tracking

### 🎨 **Beautiful Terminal Interface**
- **Rich UI**: Colorful, formatted terminal output using Rich library
- **Interactive Prompts**: User-friendly command confirmation
- **System Dashboard**: Real-time status of databases and AI connection
- **Progress Indicators**: Visual feedback for command generation

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Windows OS** (PowerShell commands)
- **Google Gemini API Key** ([Get yours here](https://ai.google.dev/))
- **MongoDB** (optional, for session logging)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/trish2023/nltoshell.git
   cd nltoshell
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # Or using the package
   pip install -e .
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

4. **Initialize database**
   ```bash
   python -m aishell.db_setup
   ```

### 🎯 Usage

#### **Method 1: Direct Script**
```bash
python flowtest.py
```

#### **Method 2: Package Command**
```bash
aishell
```

#### **Example Session**
```
AI-Shell: create a directory called projects
🤖 Generating command...

💻 Command: New-Item -ItemType Directory -Name projects  
📖 Explanation: Creates a new directory named 'projects'
🛡️ Risk: 2/5 - Low Risk

Execute this command? [y/n]: y
✅ Command completed successfully (245ms)
```

## 🛠️ Configuration

### **Environment Variables** (`.env`)
```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional MongoDB (for session logging)
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=ai_shell_logs
```

### **Database Setup**
The application automatically creates and initializes SQLite databases with:
- **Security rules** (50+ built-in patterns)
- **Risk levels** (1-5 scale)
- **Safe templates** (common operations)
- **Command history** tracking

## 💡 Advanced Features

### **Built-in Commands**
| Command | Description |
|---------|-------------|
| `help` | Show all available commands |
| `stats` | Display database statistics |
| `history` | View recent command history (SQLite) |
| `logs` | View current session logs (MongoDB) |
| `manual` | Direct PowerShell execution mode |
| `clear` | Clear screen |
| `exit` | Quit application |

### **Risk Assessment Levels**
- 🟢 **Level 1-2**: Safe read operations (Get-ChildItem, Get-Process)
- 🟡 **Level 3**: Medium risk operations (New-Item, Set-Location)  
- 🔴 **Level 4**: High risk operations (Remove-Item, Stop-Process)
- 🚨 **Level 5**: Critical operations (Format-Volume, Set-ExecutionPolicy)

### **Security Features**
- **Blocked Patterns**: Commands like `Format-*`, `Clear-Disk` are blocked
- **Double Confirmation**: Critical commands require typing "CONFIRM"
- **Audit Logging**: All commands logged with timestamps and results
- **Session Tracking**: MongoDB integration for analytics

## 🏗️ Project Structure

```
nltoshell/
├── 📄 README.md              # This file
├── 🤖 flowtest.py            # Main AI Shell application
├── ⚙️ pyproject.toml         # Package configuration
├── 📦 aishell/               # Core package
│   ├── __init__.py           # Package initialization
│   ├── main.py               # Package entry point  
│   ├── db_setup.py           # Database schema & initialization
│   ├── db_utils.py           # Database utilities & validation
│   ├── mongo_utils.py        # MongoDB integration
│   └── ai_shell.db           # SQLite database file
├── 🔐 .env.example           # Environment template
└── 📁 .git/                  # Git repository
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### **Development Setup**
```bash
# Clone your fork
git clone https://github.com/yourusername/nltoshell.git
cd nltoshell

# Install in development mode
pip install -e .

# Run tests
python -m pytest

# Check code quality
python -m flake8 aishell/
```

## 🐛 Troubleshooting

### **Common Issues**

**🔸 "ModuleNotFoundError: No module named 'aishell'"**
```bash
# Install in editable mode
pip install -e .
```

**🔸 "API Key Error"**
```bash
# Check your .env file
cat .env
# Ensure GEMINI_API_KEY is set correctly
```

**🔸 "MongoDB Connection Failed"**
```bash
# MongoDB is optional - AI Shell works without it
# To use MongoDB, ensure it's running:
mongod --dbpath /your/data/path
```

**🔸 "Database Lock Error"**
```bash
# Remove lock file if SQLite database is locked
rm aishell/ai_shell.db-wal
rm aishell/ai_shell.db-shm
```

## 📊 Performance

- **Command Generation**: ~1-3 seconds (depends on Gemini API)
- **Risk Assessment**: <100ms (local SQLite lookup)
- **Database Operations**: <50ms average
- **Memory Usage**: ~50MB typical
- **Startup Time**: ~2 seconds (including database initialization)

## 🔒 Security & Privacy

- **Local Processing**: All validation happens locally
- **No Command Storage**: Only metadata logged, not actual commands
- **Encrypted Transit**: HTTPS communication with Gemini API
- **User Control**: All commands require explicit user approval
- **Audit Trail**: Complete history for security review

## 📚 Educational Use

This project demonstrates:
- **Database Design**: Relational (SQLite) vs Document (MongoDB)
- **API Integration**: RESTful services and authentication
- **Security Patterns**: Input validation and risk assessment
- **Terminal UI**: Rich formatting and user interaction
- **Package Development**: Python project structure and distribution

## 🙏 Acknowledgments

- **Google Gemini AI** for natural language processing
- **Rich Library** for beautiful terminal interfaces  
- **MongoDB** for flexible session data storage
- **SQLite** for reliable relational data management
- **Python Community** for excellent libraries and tools

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Support

Found this project helpful? Give it a ⭐ on GitHub!

**Questions or Issues?** 
- 📧 Open an [Issue](https://github.com/trish2023/nltoshell/issues)
- 💬 Start a [Discussion](https://github.com/trish2023/nltoshell/discussions)
- 🐛 Report bugs with detailed reproduction steps

---

<div align="center">
  <strong>Built with ❤️ using Python, Google Gemini AI, and lots of ☕</strong>
  <br><br>
  <a href="https://github.com/trish2023/nltoshell">🏠 Home</a> •
  <a href="https://github.com/trish2023/nltoshell/issues">🐛 Issues</a> •
  <a href="https://github.com/trish2023/nltoshell/pulls">🔄 Pull Requests</a>
</div>