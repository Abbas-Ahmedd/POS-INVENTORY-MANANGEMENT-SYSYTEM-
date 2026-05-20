# NexaPOS — Point of Sale & Inventory Management System

A full-featured POS and Inventory Management web application built with Flask, Bootstrap 5, and MySQL.

## Features
- 🔐 **Login System** — Admin & Cashier roles
- 🛒 **POS Terminal** — Fast checkout with product grid, cart, discounts & tax
- 💳 **Payment Methods** — Cash, Card, JazzCash, EasyPaisa
- 📦 **Inventory Management** — Add/edit/remove products, categories, stock adjustments
- 🧾 **Invoice Generation** — Printable invoices per sale
- 📊 **Reports & Analytics** — Daily/monthly revenue, top products, payment breakdown, inventory status
- 👥 **User Management** — Add/deactivate users, reset passwords (Admin only)
- 👤 **Profile** — Update name and password

## Requirements
- Python 3.9+
- MySQL 5.7+ or MariaDB 10+

## Setup Instructions

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up MySQL database
```bash
mysql -u root -p < schema.sql
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your MySQL credentials
```

### 4. Create admin account
Visit `http://localhost:5000/setup` to create your first admin account.

### 5. Run the app
```bash
python app.py
```

Then open `http://localhost:5000` in your browser.

## Default Credentials
After running setup at `/setup`, use the admin account you created.

## Project Structure
```
pos_system/
├── app.py              ← Flask application (all routes)
├── schema.sql          ← MySQL database schema
├── requirements.txt    ← Python dependencies
├── .env.example        ← Environment variables template
├── templates/          ← Jinja2 HTML templates
│   ├── base.html       ← Layout with sidebar & topbar
│   ├── login.html
│   ├── dashboard.html
│   ├── pos.html        ← POS terminal
│   ├── inventory.html
│   ├── product_form.html
│   ├── categories.html
│   ├── sales.html
│   ├── reports.html
│   ├── users.html
│   ├── invoice.html
│   └── profile.html
└── static/
    └── css/
        └── style.css   ← Custom styles
```

## Notes
- All prices are in PKR (Pakistani Rupees)
- GST options: 5%, 10%, 17%
- Stock is auto-deducted on each sale
- Invoice pages are print-ready
