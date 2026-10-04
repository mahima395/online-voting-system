# Online Voting System

## About the Project

This is a web-based voting application built with Python, Flask and MySQL as a college project. Registered voters can log in, view the candidates and cast a single vote. An administrator can add, edit and delete candidates and view the voting results.

The main logic is written in Python. HTML and CSS handle the pages, and a small JavaScript file is used only for confirmation messages and a password-match check.

## Features

Voter side:
- Registration with validation and duplicate username/email checks
- Login with username or email, and logout
- Dashboard showing voting status and election information
- Candidate list
- Voting page with a confirmation message before the vote is submitted
- One vote per voter, checked on the server and enforced by a UNIQUE key in MySQL

Admin side:
- Separate admin login
- Dashboard with total registered voters, total votes cast and total candidates
- Add, edit and delete candidates
- Results page with votes and percentage for each candidate

Security basics:
- Passwords stored as hashes (Werkzeug)
- Session-based login and protected routes for voters and admin
- Parameterized SQL queries
- CSRF token on every POST form
- Temporary lock after repeated failed logins
- Secrets and database settings read from environment variables

## Technologies Used

- Python 3 and Flask
- MySQL and SQL
- HTML and CSS
- JavaScript (minimal frontend enhancement)
- Libraries: mysql-connector-python, python-dotenv, Werkzeug

## Project Structure

```
online-voting-system/
├── app.py              Flask routes, validation, login and CSRF handling
├── models.py           Database classes (Database, UserModel, AdminModel, CandidateModel, VoteModel)
├── create_admin.py     Script to create an admin account
├── schema.sql          MySQL database and tables
├── requirements.txt    Python packages
├── .env.example        Template for environment variables
├── .gitignore
├── README.md
├── static/
│   ├── css/style.css
│   └── js/script.js
└── templates/          Jinja2 HTML templates (base.html is the shared layout)
```

## Requirements

- Python 3.9 or newer
- MySQL Server 8.0 or newer

## Installation

1. Download or clone the repository and open the folder in a terminal.
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate it. On Windows:
   ```
   venv\Scripts\activate
   ```
   On Linux or macOS:
   ```
   source venv/bin/activate
   ```
4. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Create the database (see Database Setup below).
6. Create the `.env` file (see Environment Variables below).
7. Create an admin account (see Default Admin Setup below).
8. Run the application and open http://127.0.0.1:5000 in the browser.

## Database Setup

Import `schema.sql` from the project folder:

```
mysql -u root -p < schema.sql
```

On Windows, if the `mysql` command is not recognised, open "MySQL Command Line Client" and run:

```
SOURCE C:/path/to/online-voting-system/schema.sql;
```

This creates the `voting_system` database with the tables `users`, `admins`, `candidates` and `votes`.

Optionally, create a separate MySQL user for the application instead of using root:

```sql
CREATE USER 'voting_user'@'localhost' IDENTIFIED BY 'your_own_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON voting_system.* TO 'voting_user'@'localhost';
```

## Environment Variables

Copy `.env.example` to `.env` (on Windows: `copy .env.example .env`) and fill in your values:

| Variable | Purpose |
|---|---|
| SECRET_KEY | Signs the session cookie. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| MYSQL_HOST | Usually `localhost` |
| MYSQL_PORT | Usually `3306` |
| MYSQL_USER | Your MySQL username |
| MYSQL_PASSWORD | Your MySQL password |
| MYSQL_DATABASE | `voting_system` |
| FLASK_DEBUG | `0` normally, `1` only while developing locally |

The `.env` file is listed in `.gitignore`, so it is not uploaded to GitHub.

## Running the Application

```
python app.py
```

Then open http://127.0.0.1:5000 in the browser.

## Default Admin Setup

No admin account is stored in the repository. After importing the schema and creating `.env`, run:

```
python create_admin.py
```

Enter a username and a password when asked. The password is hashed before it is saved. Then log in at `/admin/login`.

## Future Improvements

- Election start and end dates, so voting can be opened and closed by the admin
- Email verification during registration
- Password reset
- Exporting results as a CSV file
- Automated tests
