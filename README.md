# NexaPOS — Point of Sale & Inventory Management System

## Group Number
**Group 14** 

---

## Group Members

| Name | Roll Number |
|------|-------------|
| Abbas Ahmed | 24P-0693 |
| Ahmed Bilal | 24P-0741 |

---

## Project Title & Description

**NexaPOS** is a full-stack web-based Point of Sale (POS) and Inventory Management System built with Flask and MySQL. It allows businesses to manage products, process sales transactions, track inventory levels, generate reports, and manage staff accounts — all through a clean, modern browser-based interface.

---

## GitHub Repository

[https://github.com/Abbas-Ahmedd/pos-inventory-management-system)

---

## Technologies Used

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Database | MySQL |
| ORM / DB Connector | flask-mysqldb |
| Authentication | Werkzeug (password hashing) |
| Frontend | HTML5, CSS3, Bootstrap 5 |
| Icons | Font Awesome 6 |
| Fonts | Plus Jakarta Sans, JetBrains Mono |
| Environment Config | python-dotenv |
| Templating | Jinja2 |

---

## CRUD Operations Implemented

| Operation | Where Used |
|-----------|-----------|
| **Create** | Add products, add categories, create sales, register users |
| **Read** | View inventory, dashboard stats, sales history, reports |
| **Update** | Edit products, adjust stock, update user profiles, reset passwords |
| **Delete** | Soft-delete products (deactivate), delete categories, deactivate users |

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- MySQL Server
- pip

### Step 1 — Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### Step 2 — Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

### Step 3 — Install Dependencies
```bash
pip install flask flask-mysqldb werkzeug python-dotenv
```

### Step 4 — Set Up the Database
Open MySQL and run the schema file:
```bash
mysql -u root -p < schema.sql
```

### Step 5 — Configure the App
Open `app.py` and update your MySQL password:
```python
app.config['MYSQL_PASSWORD'] = 'abbas12345'
```

Or create a `.env` file in the project root:
```
SECRET_KEY=your_secret_key
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=pos_db
```

### Step 6 — Set the Admin Password
Generate a proper password hash and update the database:
```bash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('admin123'))"
```
Then in MySQL:
```sql
USE pos_db;
UPDATE users SET password_hash = '<output from above>' WHERE username = 'admin';
```

### Step 7 — Run the Application
```bash
python3 app.py
```

Visit: [http://localhost:5000](http://localhost:5000)

### Default Login Credentials
```
Username: admin
Password: admin123
```

---

## Key Features

- **Dashboard** — Real-time sales stats, weekly revenue chart, top products
- **POS Terminal** — Fast checkout with cart, discount, tax, and multiple payment methods (Cash, Card, JazzCash, EasyPaisa)
- **Inventory Management** — Add, edit, remove products with low-stock alerts
- **Categories** — Organize products by category
- **Sales History** — Filter and view all transactions with invoice generation
- **Reports** — Monthly revenue, top-selling products, payment breakdown, stock status
- **User Management** — Admin can create cashier accounts, reset passwords, activate/deactivate users
- **Role-Based Access** — Admin vs Cashier permissions enforced throughout