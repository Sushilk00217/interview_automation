import logging
import uuid
from sqlalchemy import select, literal
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.sql.models.question import Question, CategoryEnum, DifficultyEnum

logger = logging.getLogger(__name__)

async def seed_question_bank(session: AsyncSession):
    """Seed the Question Bank with initial set of questions."""
    logger.info("Seeding Question Bank...")
    
    # No longer skipping if already populated; we want to ensure latest questions are there
    # stmt = select(literal(1)).select_from(Question).limit(1)
    # result = await session.execute(stmt)
    # if result.scalar() is not None:
    #     logger.info("[question_seed] Question bank already populated. Skipping.")
    #     return

    questions_raw = [
        # --- PYTHON ---
        # Easy
        {"text": "What is the difference between a list and a tuple in Python?", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "lists"]},
        {"text": "Explain the use of 'self' in Python classes.", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.EASY, "tags": ["oop", "basics"]},
        {"text": "How do you handle exceptions in Python? Give an example using try-except.", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "error-handling"]},
        {"text": "What are list comprehensions and how are they used?", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "lists"]},
        {"text": "What is the purpose of the '__init__' method in Python?", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.EASY, "tags": ["oop", "basics"]},
        # Medium
        {"text": "Explain the difference between deep copy and shallow copy.", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.MEDIUM, "tags": ["memory-management", "copy"]},
        {"text": "What are decorators in Python and how do they work?", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.MEDIUM, "tags": ["functional-programming", "decorators"]},
        {"text": "Explain Python's Global Interpreter Lock (GIL) and its impact on multi-threading.", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.MEDIUM, "tags": ["concurrency", "parallelism"]},
        {"text": "How does memory management work in Python? Mention garbage collection.", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.MEDIUM, "tags": ["memory-management", "garbage-collection"]},
        {"text": "What are generators in Python and what is the 'yield' keyword?", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.MEDIUM, "tags": ["iterators", "yield"]},
        # Hard
        {"text": "Describe the Method Resolution Order (MRO) in Python and how it works with multiple inheritance.", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.HARD, "tags": ["oop", "advanced"]},
        {"text": "Explain the difference between multiprocessing and multithreading in Python, including when to use each.", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.HARD, "tags": ["concurrency", "parallelism", "performance"]},
        {"text": "How would you profile a Python application to find performance bottlenecks?", "category": CategoryEnum.PYTHON, "difficulty": DifficultyEnum.HARD, "tags": ["performance", "profiling", "optimization"]},

        # --- SQL ---
        # Easy
        {"text": "What is the difference between WHERE and HAVING clauses?", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "filtering"]},
        {"text": "Explain the different types of JOINs in SQL (Inner, Left, Right, Full).", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "joins"]},
        {"text": "What is a Primary Key and how is it different from a Unique Key?", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "keys"]},
        {"text": "What is the purpose of the GROUP BY clause?", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "aggregation"]},
        {"text": "How do you use the LIKE operator for pattern matching?", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "searching"]},
        # Medium
        {"text": "Explain the difference between UNION and UNION ALL.", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.MEDIUM, "tags": ["sets", "performance"]},
        {"text": "What are Window Functions? Give an example like ROW_NUMBER() or RANK().", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.MEDIUM, "tags": ["advanced-sql", "analytics"]},
        {"text": "Describe ACID properties in the context of database transactions.", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.MEDIUM, "tags": ["transactions", "theory"]},
        {"text": "What is an Index in SQL and how does it improve query performance?", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.MEDIUM, "tags": ["performance", "indexing"]},
        {"text": "Explain the concept of Normalization (1NF, 2NF, 3NF).", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.MEDIUM, "tags": ["database-design", "normalization"]},
        # Hard
        {"text": "Describe common strategies for optimizing slow SQL queries.", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.HARD, "tags": ["performance", "optimization", "query-plan"]},
        {"text": "What is Sharding and how does it differ from Horizontal Scaling?", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.HARD, "tags": ["architecture", "scalability", "sharding"]},
        {"text": "Explain the difference between Optimistic and Pessimistic Locking.", "category": CategoryEnum.SQL, "difficulty": DifficultyEnum.HARD, "tags": ["concurrency", "transactions", "locking"]},

        # --- MACHINE LEARNING ---
        # Easy
        {"text": "What is the difference between Supervised and Unsupervised Learning?", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "ml-concepts"]},
        {"text": "Explain the concept of Overfitting and how to prevent it.", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.EASY, "tags": ["regularization", "basics"]},
        {"text": "What is a Confusion Matrix in classification?", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.EASY, "tags": ["evaluation-metrics", "classification"]},
        {"text": "Define Precision and Recall.", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.EASY, "tags": ["evaluation-metrics", "basics"]},
        {"text": "What is Linear Regression and what are its assumptions?", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.EASY, "tags": ["regression", "basics"]},
        # Medium
        {"text": "Explain the Bias-Variance Tradeoff.", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.MEDIUM, "tags": ["model-selection", "theory"]},
        {"text": "How does the Random Forest algorithm work?", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.MEDIUM, "tags": ["ensemble-learning", "trees"]},
        {"text": "What is Cross-Validation and why is it used?", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.MEDIUM, "tags": ["model-evaluation", "validation"]},
        {"text": "Explain Gradient Descent and its variants (Stochastic, Mini-batch).", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.MEDIUM, "tags": ["optimization", "training"]},
        {"text": "What is Feature Engineering and why is it critical in ML projects?", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.MEDIUM, "tags": ["data-preprocessing", "features"]},
        # Hard
        {"text": "Describe how a Transformer architecture works (Attention mechanism).", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.HARD, "tags": ["deep-learning", "nlp", "transformers"]},
        {"text": "Explain the difference between L1 (Lasso) and L2 (Ridge) regularization.", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.HARD, "tags": ["regularization", "optimization"]},
        {"text": "How do you handle class imbalance in a dataset?", "category": CategoryEnum.MACHINE_LEARNING, "difficulty": DifficultyEnum.HARD, "tags": ["data-preprocessing", "classification", "imbalance"]},

        # --- DATA STRUCTURES ---
        # Easy
        {"text": "What is an Array and how does it differ from a Linked List?", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "arrays"]},
        {"text": "Explain the Stack data structure and its LIFO principle.", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "stack"]},
        {"text": "What is a Queue and how does it differ from a Stack?", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "queue"]},
        {"text": "What is a Hash Map/Hash Table and what is it used for?", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "hashing"]},
        {"text": "Explain the concept of Binary Search.", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.EASY, "tags": ["algorithms", "search"]},
        # Medium
        {"text": "Describe the process of inserting a node into a Binary Search Tree (BST).", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.MEDIUM, "tags": ["trees", "bst"]},
        {"text": "What is the time complexity of QuickSort and MergeSort in the average/worst cases?", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.MEDIUM, "tags": ["sorting", "complexity"]},
        {"text": "Explain the difference between Breadth-First Search (BFS) and Depth-First Search (DFS).", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.MEDIUM, "tags": ["graph-algorithms", "traversal"]},
        {"text": "What is a Heap and how is it used in a Priority Queue?", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.MEDIUM, "tags": ["heaps", "priority-queue"]},
        {"text": "Explain the concept of Dynamic Programming with a simple example like Fibonacci.", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.MEDIUM, "tags": ["algorithms", "dp"]},
        # Hard
        {"text": "Describe the implementation and use cases of a Trie (Prefix Tree).", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.HARD, "tags": ["advanced-ds", "strings"]},
        {"text": "How does a Red-Black Tree maintain its balance after insertion?", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.HARD, "tags": ["balanced-trees", "algorithms"]},
        {"text": "Explain Dijkstra's algorithm for finding the shortest path in a graph.", "category": CategoryEnum.DATA_STRUCTURES, "difficulty": DifficultyEnum.HARD, "tags": ["graph-algorithms", "optimization"]},

        # --- SYSTEM DESIGN ---
        # Easy
        {"text": "What is Scalability (Vertical vs Horizontal)?", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "scalability"]},
        {"text": "What is a Load Balancer and where does it sit in an architecture?", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.EASY, "tags": ["networking", "load-balancing"]},
        {"text": "Explain the concept of Caching and why it's used.", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.EASY, "tags": ["performance", "caching"]},
        {"text": "What is a Content Delivery Network (CDN)?", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.EASY, "tags": ["networking", "availability"]},
        {"text": "What is the difference between Monolithic and Microservices architecture?", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.EASY, "tags": ["architecture", "basics"]},
        # Medium
        {"text": "Explain CAP Theorem and its implications for distributed systems.", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.MEDIUM, "tags": ["distributed-systems", "theory"]},
        {"text": "Describe different Load Balancing algorithms (Round Robin, Least Connections).", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.MEDIUM, "tags": ["networking", "load-balancing"]},
        {"text": "How would you design a rate-limiting system for an API?", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.MEDIUM, "tags": ["security", "scalability", "rate-limiting"]},
        {"text": "What is Message Queueing and when should you use it?", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.MEDIUM, "tags": ["asynchronous-processing", "messaging"]},
        {"text": "Describe the difference between SQL (Relational) and NoSQL (Document/Key-Value) databases.", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.MEDIUM, "tags": ["database-design", "storage"]},
        # Hard
        {"text": "How would you design a URL shortening service like Bitly?", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.HARD, "tags": ["architectural-design", "scalability"]},
        {"text": "Explain the concept of Consistent Hashing and its role in distributed caching.", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.HARD, "tags": ["distributed-systems", "hashing"]},
        {"text": "How do you handle data consistency in a distributed microservices environment (Saga pattern)?", "category": CategoryEnum.SYSTEM_DESIGN, "difficulty": DifficultyEnum.HARD, "tags": ["microservices", "consistency", "transactions"]},

        # --- STATISTICS ---
        # Easy
        {"text": "What are Mean, Median, and Mode?", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "descriptive-stats"]},
        {"text": "Explain the concept of Standard Deviation.", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "variance"]},
        {"text": "What is a Normal Distribution (Gaussian)?", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.EASY, "tags": ["probability", "distributions"]},
        {"text": "Define P-value and its significance in hypothesis testing.", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.EASY, "tags": ["hypothesis-testing", "basics"]},
        {"text": "What is the difference between Correlation and Causation?", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.EASY, "tags": ["basics", "correlation"]},
        # Medium
        {"text": "Explain the Central Limit Theorem.", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.MEDIUM, "tags": ["probability", "theory"]},
        {"text": "What is Hypothesis Testing and what are Type I and Type II errors?", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.MEDIUM, "tags": ["inference", "hypothesis-testing"]},
        {"text": "Describe the difference between Bayesian and Frequentist statistics.", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.MEDIUM, "tags": ["theory", "bayesian"]},
        {"text": "What is A/B Testing and how do you determine if results are statistically significant?", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.MEDIUM, "tags": ["experimentation", "testing"]},
        {"text": "Explain Linear Correlation (Pearson) vs Rank Correlation (Spearman).", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.MEDIUM, "tags": ["correlation", "metrics"]},
        # Hard
        {"text": "Explain Power Analysis and its importance in experimental design.", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.HARD, "tags": ["experimental-design", "power"]},
        {"text": "Describe Logistic Regression and how it differs from Linear Regression.", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.HARD, "tags": ["regression", "classification"]},
        {"text": "What is the Law of Large Numbers and how does it relate to probability?", "category": CategoryEnum.STATISTICS, "difficulty": DifficultyEnum.HARD, "tags": ["probability", "theory"]},
    ]

    for q_data in questions_raw:
        # Check if question already exists by text
        stmt = select(Question).where(Question.text == q_data["text"])
        result = await session.execute(stmt)
        existing = result.scalars().first()

        if existing:
            # Update existing
            existing.category = q_data["category"]
            existing.difficulty = q_data["difficulty"]
            existing.tags = q_data["tags"]
        else:
            # Create new
            new_q = Question(**q_data)
            session.add(new_q)
    
    await session.commit()
    logger.info(f"[OK] Seeded/Updated realistic interview questions into the bank.")
