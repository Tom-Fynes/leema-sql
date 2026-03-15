# Leema SQL

> An agile, multi-engine Terminal User Interface (TUI) SQL IDE for fast connections to popular database engines.

![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-alpha-orange)

---

## Overview

Leema SQL is a keyboard-driven SQL IDE that runs entirely in your terminal. It lets you connect to multiple database engines, browse schemas, write and execute queries, and inspect execution plans — all without leaving the command line.

### Key Features

- **Multi-engine support** — connect to PostgreSQL, MySQL, SQL Server, DuckDB, Trino, and Snowflake from a single tool
- **Schema browser ("The Burrow")** — lazy-loading sidebar that lets you navigate databases, schemas, and tables at a glance
- **SQL editor ("The Workspace")** — syntax-highlighted editor with query formatting powered by sqlparse and Pygments
- **Results & execution plans** — tabbed output pane showing query results alongside visual execution plan information
- **Secure credential storage** — passwords are never written to disk; they are stored in your system keyring
- **Profile-based configuration** — maintain separate connection profiles for development, staging, and production environments
- **XDG-compliant config** — configuration lives in `~/.config/leema/config.yaml` by default, respecting `$XDG_CONFIG_HOME`

### Supported Databases

| Engine | Extra install required? |
|--------|------------------------|
| DuckDB (local / in-memory) | No — included by default |
| PostgreSQL | `pip install "leema-sql[postgres]"` |
| MySQL | `pip install "leema-sql[mysql]"` |
| SQL Server (MSSQL) | `pip install "leema-sql[mssql]"` |
| Trino | `pip install "leema-sql[trino]"` |
| Snowflake | `pip install "leema-sql[snowflake]"` |

---

## Quick Start

### Prerequisites

- Python **3.12** or newer
- `pip` (comes with Python)

### Installation

**Install with DuckDB support only (default):**

```bash
pip install leema-sql
```

**Install with all database drivers:**

```bash
pip install "leema-sql[all]"
```

**Install with specific drivers:**

```bash
pip install "leema-sql[postgres,mysql]"
```

**Install from source for development:**

```bash
git clone https://github.com/Tom-Fynes/leema-sql.git
cd leema-sql
pip install -e ".[all]"
```

### Configuration

Run the interactive configuration wizard to create your first connection profile:

```bash
leema configure
```

The wizard will prompt you for the database engine, host, port, database name, and username. Your password is stored securely in your system keyring and is never written to the config file.

Configuration is saved to `~/.config/leema/config.yaml`. A typical file looks like this:

```yaml
default_profile: dev
profiles:
  dev:
    engine: postgres
    host: localhost
    port: 5432
    database: myapp_dev
    username: dev_user
    ssl: false
  prod:
    engine: postgres
    host: prod.example.com
    port: 5432
    database: myapp_prod
    username: prod_user
    ssl: true
    options:
      sslmode: require
```

### Running Leema SQL

**Launch with the default profile:**

```bash
leema run
```

**Launch with a specific profile:**

```bash
leema run --profile prod
```

**Launch with a custom config file:**

```bash
leema run --config /path/to/config.yaml
```

### Other CLI Commands

```bash
leema list-drivers   # Show all available database drivers
leema version        # Print the installed version
leema --help         # Full help text
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+E` | Execute the current query |
| `Ctrl+F` | Format / pretty-print SQL |
| `Ctrl+Q` | Quit the application |
| `Tab` | Move focus between panes |

---

## Contributing

Contributions are welcome and appreciated! Please follow the steps below to set up a development environment and submit your changes.

### Development Setup

1. **Fork** the repository on GitHub and clone your fork:

   ```bash
   git clone https://github.com/<your-username>/leema-sql.git
   cd leema-sql
   ```

2. **Create a virtual environment** and install all dependencies including optional drivers:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[all]"
   ```

3. **Create a feature branch** from `main`:

   ```bash
   git checkout -b feature/my-new-feature
   ```

### Running the Tests

The test suite uses **pytest**. Run all tests from the project root:

```bash
pytest
```

Run a specific test file:

```bash
pytest tests/test_drivers.py -v
```

Run with coverage:

```bash
pytest --cov=src
```

### Adding a New Database Driver

1. Create a new file in `src/drivers/` (e.g. `src/drivers/mydb.py`).
2. Subclass `BaseEngine` from `src/drivers/base.py` and implement all abstract methods:
   - `connect()`
   - `execute(query, params)`
   - `get_schema()`
   - `get_columns(schema, table)`
   - `get_explain_plan(query)`
   - `close()`
   - `is_connected()`
3. Register your driver in `src/drivers/__init__.py`.
4. Add a corresponding optional dependency in `pyproject.toml`.
5. Write tests in `tests/test_drivers.py`.

### Submitting Changes

1. Ensure all tests pass (`pytest`).
2. Push your branch and open a **Pull Request** against `main`.
3. Describe what your change does and reference any related issues.

### Reporting Bugs & Requesting Features

Please open an [issue](https://github.com/Tom-Fynes/leema-sql/issues) and use one of the available templates. Include as much detail as possible — OS, Python version, database engine and version, and steps to reproduce.

---

## License

This project is licensed under the [MIT License](LICENSE).
