# SQL vs. Graph Database: The "Friends of Friends" Benchmark

This project compares the performance of a **Relational Database (PostgreSQL)** and a **Graph Database (Neo4j)**.

It is created as a Blog Post Project (BPP) for the **BBM467 Data Intensive Applications** course.

## 🎯 The Goal
In social networks, finding "friends of friends" is a common task.
* **SQL (PostgreSQL)** uses `JOIN` operations to connect tables. As relationships get deeper, this becomes very slow.
* **Graph (Neo4j)** uses "Index-Free Adjacency". It simply "walks" from one node to another. This is very fast.

We created this benchmark to prove that **Neo4j is significantly faster** than SQL for connected data queries.

## 🚀 Technologies Used
* **Language:** Python 3.x
* **Databases:** PostgreSQL 15, Neo4j 5.12
* **Infrastructure:** Docker & Docker Compose
* **Libraries:** `psycopg2-binary`, `neo4j` driver

## ⚙️ Prerequisites
Before running this project, make sure you have:
1.  **Docker Desktop** installed and running.
2.  **Python 3** installed.

## 📦 How to Run

Follow these steps to set up the environment and run the benchmark.

### 1. Clone the Repository
Download this repository to your computer.
```bash
git clone <your-repo-url>
cd <your-repo-folder>
```

### 2. Start Databases with Docker Compose

We use Docker Compose to set up PostgreSQL and Neo4j automatically. You do not need to install databases manually.

Run this command in the project folder:

```bash
docker-compose up -d
```

### 3. Install Python Dependencies

Install the required Python libraries listed in requirements.txt. This includes the drivers for Neo4j and PostgreSQL.

```bash
pip install -r requirements.txt
```

### 4. Run the Benchmark

Run the Python script to generate data and test performance.

```bash
python benchmark.py
```

The script performs the following steps:

Data Generation: It creates 10,000 users and assigns ~50 friends to each user randomly (Total ~500,000 connections).

PostgreSQL Test:

1. Inserts data into tables (Users, Friendships).

2. Creates Indexes for fair comparison.

3. Runs a query to find friends at Depth 2 and Depth 3.

Neo4j Test:

1. Inserts data as Nodes (Person) and Relationships (FRIEND).

2. Runs the same query using Graph Traversal.

3. Comparison: It prints a scoreboard showing the execution time of both databases

## 👥 Authors
* **Hayrullah Alper** (2220356108)
* **Barışcan Tekin** (2200356023)
* **Mehmet Yılmaz Erdem** (2210765036)