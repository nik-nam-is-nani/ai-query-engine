-- AI SQL Studio Demo Database Setup

-- Create database
CREATE DATABASE IF NOT EXISTS ai_sql_demo;
USE ai_sql_demo;

-- Employees table
CREATE TABLE IF NOT EXISTS employees (
    emp_id INT PRIMARY KEY AUTO_INCREMENT,
    emp_name VARCHAR(100) NOT NULL,
    dept_id INT,
    join_date DATE,
    status VARCHAR(20) DEFAULT 'active'
);

-- Departments table
CREATE TABLE IF NOT EXISTS departments (
    dept_id INT PRIMARY KEY AUTO_INCREMENT,
    dept_name VARCHAR(100) NOT NULL
);

-- Salaries table
CREATE TABLE IF NOT EXISTS salaries (
    id INT PRIMARY KEY AUTO_INCREMENT,
    emp_id INT,
    basic_salary DECIMAL(10,2),
    effective_date DATE,
    FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
);

-- Bonuses table
CREATE TABLE IF NOT EXISTS bonuses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    emp_id INT,
    amount DECIMAL(10,2),
    bonus_date DATE,
    FOREIGN KEY (emp_id) REFERENCES employees(emp_id)
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    project_id INT PRIMARY KEY AUTO_INCREMENT,
    project_name VARCHAR(100) NOT NULL,
    dept_id INT,
    budget DECIMAL(12,2)
);

-- Students table (for college plugin)
CREATE TABLE IF NOT EXISTS students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    dept VARCHAR(50),
    year INT
);

-- Marks table (for college plugin)
CREATE TABLE IF NOT EXISTS marks (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    subject VARCHAR(50),
    marks INT,
    FOREIGN KEY (student_id) REFERENCES students(id)
);

-- Products table (for shop plugin)
CREATE TABLE IF NOT EXISTS products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2),
    stock_quantity INT,
    category VARCHAR(50)
);

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    cust_id INT PRIMARY KEY AUTO_INCREMENT,
    cust_name VARCHAR(100) NOT NULL
);

-- Sales table
CREATE TABLE IF NOT EXISTS sales (
    sale_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    cust_id INT,
    quantity INT,
    total_amount DECIMAL(10,2),
    sale_date DATE
);

-- Insert sample data into employees
INSERT INTO employees (emp_name, dept_id, join_date, status) VALUES
('Alice Johnson', 1, '2020-01-15', 'active'),
('Bob Smith', 1, '2019-03-22', 'active'),
('Charlie Brown', 2, '2021-06-10', 'active'),
('Diana Prince', 2, '2018-11-05', 'inactive'),
('Eve Adams', 3, '2022-02-28', 'active'),
('Frank Miller', 1, '2020-08-14', 'active'),
('Grace Lee', 3, '2021-01-20', 'active');

-- Insert sample departments
INSERT INTO departments (dept_id, dept_name) VALUES
(1, 'Engineering'),
(2, 'Marketing'),
(3, 'Sales');

-- Insert sample salaries
INSERT INTO salaries (emp_id, basic_salary, effective_date) VALUES
(1, 75000.00, '2024-01-01'),
(2, 65000.00, '2024-01-01'),
(3, 55000.00, '2024-01-01'),
(4, 50000.00, '2024-01-01'),
(5, 80000.00, '2024-01-01'),
(6, 70000.00, '2024-01-01'),
(7, 60000.00, '2024-01-01');

-- Insert sample bonuses
INSERT INTO bonuses (emp_id, amount, bonus_date) VALUES
(1, 5000.00, '2024-06-01'),
(2, 3000.00, '2024-06-01'),
(5, 7000.00, '2024-06-01');

-- Insert sample projects
INSERT INTO projects (project_name, dept_id, budget) VALUES
('Website Redesign', 1, 100000.00),
('SEO Campaign', 2, 50000.00),
('Sales Pipeline', 3, 75000.00);

-- Insert sample students
INSERT INTO students (name, dept, year) VALUES
('John Doe', 'cse', 2),
('Jane Smith', 'ece', 3),
('Mike Ross', 'cse', 1),
('Sara Connor', 'mech', 2),
('Tom Hardy', 'civil', 3);

-- Insert sample marks
INSERT INTO marks (student_id, subject, marks) VALUES
(1, 'maths', 95),
(1, 'physics', 88),
(1, 'chemistry', 92),
(2, 'maths', 78),
(2, 'physics', 85),
(2, 'chemistry', 80),
(3, 'maths', 90),
(3, 'physics', 92),
(3, 'chemistry', 88),
(4, 'maths', 65),
(4, 'physics', 70),
(4, 'chemistry', 72),
(5, 'maths', 82),
(5, 'physics', 78),
(5, 'chemistry', 85);

-- Insert sample products
INSERT INTO products (product_name, price, stock_quantity, category) VALUES
('Laptop', 999.99, 50, 'Electronics'),
('Mouse', 29.99, 200, 'Electronics'),
('Keyboard', 79.99, 150, 'Electronics'),
('Monitor', 349.99, 80, 'Electronics'),
('Desk Chair', 249.99, 60, 'Furniture'),
('Standing Desk', 599.99, 30, 'Furniture');

-- Insert sample customers
INSERT INTO customers (cust_name) VALUES
('Acme Corp'),
('Tech Solutions'),
('Global Industries'),
('Startup Hub'),
('Enterprise Ltd');

-- Insert sample sales
INSERT INTO sales (product_id, cust_id, quantity, total_amount, sale_date) VALUES
(1, 1, 5, 4999.95, '2024-03-15'),
(2, 1, 20, 599.80, '2024-03-15'),
(3, 2, 10, 799.90, '2024-04-01'),
(1, 3, 3, 2999.97, '2024-04-10'),
(4, 4, 2, 699.98, '2024-05-01'),
(5, 5, 4, 999.96, '2024-05-10'),
(6, 1, 1, 599.99, '2024-05-12');

SELECT 'Database setup complete!' AS status;