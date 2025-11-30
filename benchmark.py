import psycopg2
import time
import random
from neo4j import GraphDatabase

# --- CONFIGURATION ---
USER_COUNT = 10000
FRIENDS_PER_USER = 50
TARGET_USER_ID = 1

PG_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "social_network",
    "user": "admin",
    "password": "password123"
}

NEO_CONFIG = {
    "uri": "bolt://localhost:7687",
    "auth": ("neo4j", "password123")
}

print(f"--- BENCHMARK STARTING: {USER_COUNT} Users / ~{FRIENDS_PER_USER} friends each ---")

# ---------------------------------------------------------
# 1. DATA GENERATION
# ---------------------------------------------------------
print("1. Generating data in memory...")
users = [(i, f"User_{i}") for i in range(1, USER_COUNT + 1)]
friendships = []

for user_id in range(1, USER_COUNT + 1):
    potential = list(range(1, USER_COUNT + 1))
    potential.remove(user_id)
    friends = random.sample(potential, FRIENDS_PER_USER)
    for friend_id in friends:
        friendships.append((user_id, friend_id))

print(f"   -> Generated {len(friendships)} connections.")

# ---------------------------------------------------------
# 2. POSTGRESQL SETUP & BENCHMARK
# ---------------------------------------------------------
print("\n2. PostgreSQL Benchmark...")
pg_results = {}

try:
    pg_conn = psycopg2.connect(**PG_CONFIG)
    pg_cursor = pg_conn.cursor()

    # Setup Schema
    pg_cursor.execute("DROP TABLE IF EXISTS friendships")
    pg_cursor.execute("DROP TABLE IF EXISTS users")
    pg_cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(50))")
    pg_cursor.execute("CREATE TABLE friendships (user_id INTEGER, friend_id INTEGER)")

    # Batch Insert
    print("   -> Inserting data...")
    batch_size = 10000
    for i in range(0, len(users), batch_size):
        pg_cursor.executemany("INSERT INTO users VALUES (%s, %s)", users[i:i + batch_size])
    for i in range(0, len(friendships), batch_size):
        pg_cursor.executemany("INSERT INTO friendships VALUES (%s, %s)", friendships[i:i + batch_size])

    # Indexing
    print("   -> Creating indexes...")
    pg_cursor.execute("CREATE INDEX idx_user ON friendships (user_id)")
    pg_cursor.execute("CREATE INDEX idx_friend ON friendships (friend_id)")
    pg_conn.commit()


    def run_postgres_query(depth):
        start_time = time.time()

        if depth == 2:
            # Depth 2: User -> Friend -> Friend (1 Join)
            query = """
            SELECT DISTINCT t2.friend_id
            FROM friendships t1
            JOIN friendships t2 ON t1.friend_id = t2.user_id
            WHERE t1.user_id = %s
            """
        elif depth == 3:
            # Depth 3: User -> Friend -> Friend -> Friend (2 Joins)
            query = """
            SELECT DISTINCT t3.friend_id
            FROM friendships t1
            JOIN friendships t2 ON t1.friend_id = t2.user_id
            JOIN friendships t3 ON t2.friend_id = t3.user_id
            WHERE t1.user_id = %s
            """

        pg_cursor.execute(query, (TARGET_USER_ID,))
        results = pg_cursor.fetchall()
        duration = (time.time() - start_time) * 1000
        return duration, len(results)


    # Run Tests
    print("   -> Running Depth 2 Query...")
    t2, c2 = run_postgres_query(2)
    pg_results[2] = t2
    print(f"      Depth 2: {t2:.2f} ms | Count: {c2}")

    print("   -> Running Depth 3 Query...")
    t3, c3 = run_postgres_query(3)
    pg_results[3] = t3
    print(f"      Depth 3: {t3:.2f} ms | Count: {c3}")

    pg_cursor.close()
    pg_conn.close()

except Exception as e:
    print(f"Postgres Error: {e}")

# ---------------------------------------------------------
# 3. NEO4J SETUP & BENCHMARK
# ---------------------------------------------------------
print("\n3. Neo4j Benchmark...")
driver = GraphDatabase.driver(NEO_CONFIG["uri"], auth=NEO_CONFIG["auth"])
neo_results = {}


def insert_data_batch(tx, users_data, friendships_data):
    batch_size = 5000
    for i in range(0, len(users_data), batch_size):
        tx.run("UNWIND $batch AS u CREATE (:Person {id: u[0], name: u[1]})", batch=users_data[i:i + batch_size])
    for i in range(0, len(friendships_data), batch_size):
        tx.run("""
        UNWIND $batch AS f
        MATCH (u:Person {id: f[0]}), (target:Person {id: f[1]})
        MERGE (u)-[:FRIEND]->(target)
        """, batch=friendships_data[i:i + batch_size])


def run_traversal_query(tx, user_id, depth):
    start_time = time.time()
    # Dynamic Cypher Query based on depth
    query = f"""
    MATCH (p:Person {{id: $id}})-[:FRIEND*{depth}]->(fof)
    RETURN count(distinct fof) AS count
    """
    result = tx.run(query, id=user_id)
    count = result.single()["count"]
    return (time.time() - start_time) * 1000, count


with driver.session() as session:
    # Cleanup & Schema
    print("   -> Cleaning & Indexing...")
    session.run("MATCH (n) DETACH DELETE n")
    try:
        session.run("DROP INDEX person_id_index IF EXISTS")
    except:
        pass
    session.run("CREATE INDEX person_id_index IF NOT EXISTS FOR (p:Person) ON (p.id)")

    # Insert Data
    print("   -> Inserting data...")
    session.execute_write(insert_data_batch, users, friendships)

    # Warm-up (Important to ignore compilation time)
    print("   -> Warming up...")
    session.execute_read(run_traversal_query, TARGET_USER_ID, 2)

    # Run Tests
    print("   -> Running Depth 2 Query...")
    t2, c2 = session.execute_read(run_traversal_query, TARGET_USER_ID, 2)
    neo_results[2] = t2
    print(f"      Depth 2: {t2:.2f} ms | Count: {c2}")

    print("   -> Running Depth 3 Query...")
    t3, c3 = session.execute_read(run_traversal_query, TARGET_USER_ID, 3)
    neo_results[3] = t3
    print(f"      Depth 3: {t3:.2f} ms | Count: {c3}")

driver.close()

# ---------------------------------------------------------
# FINAL COMPARISON TABLE
# ---------------------------------------------------------
print(f"\n{'=' * 70}")
print(f"{'METRIC':<15} | {'POSTGRES (ms)':<15} | {'NEO4J (ms)':<15} | {'SPEEDUP':<10}")
print(f"{'-' * 70}")

# Depth 2 Comparison
pg_d2 = pg_results.get(2, 0)
neo_d2 = neo_results.get(2, 0)
speedup_2 = pg_d2 / neo_d2 if neo_d2 > 0 else 0
print(f"{'Depth 2':<15} | {pg_d2:<15.2f} | {neo_d2:<15.2f} | {speedup_2:.1f}x")

# Depth 3 Comparison
pg_d3 = pg_results.get(3, 0)
neo_d3 = neo_results.get(3, 0)
speedup_3 = pg_d3 / neo_d3 if neo_d3 > 0 else 0
print(f"{'Depth 3':<15} | {pg_d3:<15.2f} | {neo_d3:<15.2f} | {speedup_3:.1f}x")
print(f"{'=' * 70}")