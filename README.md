# AI SQL Studio 🚀

A powerful AI-powered Natural Language to SQL Database System that converts plain English queries into executable SQL queries. Features a modern glassmorphism web dashboard interface.

![Python](https://img.shields.io/badge/Python-3.7+-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-green)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### Core Features
- **Natural Language to SQL**: Convert plain English queries to SQL
- **AI-Powered**: Uses advanced LLMs for intelligent query generation
- **Multi-Database Support**: Works with MySQL databases
- **Plugin System**: Extensible architecture with domain-specific plugins
- **SQL Guardrails**: Validates and fixes generated SQL queries

### Web Dashboard
- **Modern UI**: Glassmorphism dark theme design
- **Interactive Tables**: DataTables.js with sorting, filtering, pagination
- **Dynamic Charts**: Chart.js with bar, line, pie, doughnut charts
- **Real-time Results**: Instant query execution and visualization
- **Query History**: Track and re-run previous queries
- **Export**: Download results as CSV

### Backend Features
- **REST API**: Clean API endpoints for all operations
- **Connection Management**: Secure database connections
- **Error Handling**: Graceful error messages and validation

## 📁 Project Structure

```
ai_DB_project/
├── api_server.py          # Flask API server
├── main.py                # CLI entry point
├── api_nl2sql.py         # AI API integration
├── sql_guard.py           # SQL validation layer
├── nlp_preprocessor.py    # Query preprocessing
├── nl2sql_universal.py    # Core NL2SQL engine
├── requirements.txt       # Python dependencies
├── API_datamanager/
│   └── API_key.txt       # API key storage
├── plugin/                # Domain plugins
│   ├── company_plugin.py
│   ├── hospital_plugin.py
│   ├── shop_plugin.py
│   └── college_plugin.py
└── dashboard/             # Web frontend
    ├── index.html
    └── app.js
```

## 🛠️ Installation

### Prerequisites
- Python 3.7+
- MySQL 8.0+
- API Key (OpenRouter or OpenAI)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/nik-nam-is-nani/ai-query-engine.git
cd ai-query-engine
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Database**
Update database credentials in `nl2sql_universal.py`:
```python
def get_connection(db_name):
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_password",  # Change this
        database=db_name
    )
```

4. **Add API Key**
Put your OpenRouter API key in `API_datamanager/API_key.txt`

5. **Run the Server**
```bash
python api_server.py
```

6. **Open Dashboard**
Navigate to `http://localhost:5000`

## 🎯 Usage

### Web Dashboard
1. Select a database from the dropdown
2. Wait for connection (green indicator)
3. Browse tables in sidebar
4. Click a table to view data
5. Or type a natural language query:
   - "Show all employees from department 2"
   - "List products with price above 100"
   - "Count total orders"

### CLI Mode
```bash
python main.py
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/databases` | List all databases |
| GET | `/api/connect?db=<name>` | Connect to database |
| GET | `/api/tables` | Get table list |
| GET | `/api/table-data?name=<table>` | Get table data |
| POST | `/api/generate-sql` | Generate SQL from NL |
| POST | `/api/run-query` | Execute SQL query |

## 🧩 Architecture

### Flow Diagram
```
User Query
    ↓
[AI API] or [Plugin] or [Universal Engine]
    ↓
SQL Guardrail (Validates constraints)
    ↓
MySQL Database
    ↓
Results → Dashboard (Table/Chart/JSON)
```

### Components

1. **API Integration** (`api_nl2sql.py`)
   - Connects to AI API
   - Sends natural language with database schema
   - Parses SQL from response

2. **SQL Guardrails** (`sql_guard.py`)
   - Enforces user constraints (LIMIT, WHERE, etc.)
   - Fixes missing filters
   - Validates SQL before execution

3. **Plugin System** (`plugin/`)
   - Company: Employee, Department, Salary queries
   - Hospital: Patient, Doctor, Appointment queries
   - Shop: Product, Order, Customer queries
   - College: Student, Course, Enrollment queries

4. **Universal Engine** (`nl2sql_universal.py`)
   - Fallback for generic queries
   - COUNT, LIST, FILTER operations

## 🎨 Tech Stack

- **Backend**: Flask, Python
- **Database**: MySQL
- **AI**: OpenRouter API (arcee-ai/trinity-large-preview)
- **Frontend**: 
  - TailwindCSS
  - DataTables.js
  - Chart.js
  - CodeMirror

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - feel free to use this project!

## 👨‍💻 Author

- **Nik Nam** - [GitHub](https://github.com/nik-nam-is-nani)

---

<p align="center">Made with ❤️ for AI-Powered Database Queries</p>
