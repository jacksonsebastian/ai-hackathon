"""
Knowledge base management for interview domain knowledge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.config import settings
from app.rag.chunking import chunk_knowledge_doc, Chunk
from app.rag.vector_store import get_vector_store
from app.utils.helpers import generate_id
from app.utils.logger import get_rag_logger

logger = get_rag_logger()

# Built-in interview knowledge for bootstrapping
INTERVIEW_KNOWLEDGE = {
    "dsa_topics": """
Data Structures and Algorithms Interview Topics:
- Arrays and Strings: Two pointers, sliding window, prefix sums
- Linked Lists: Reversal, cycle detection, merge operations
- Trees and Graphs: BFS, DFS, BST operations, shortest paths
- Dynamic Programming: Memoization, tabulation, common patterns
- Sorting and Searching: QuickSort, MergeSort, Binary Search variants
- Stacks and Queues: Monotonic stack, BFS with queue
- Hash Tables: Design, collision handling, applications
- Heaps: Priority queues, top-K problems, median finding
""",
    "system_design": """
System Design Interview Topics:
- Scalability: Horizontal vs vertical scaling, load balancing
- Database Design: SQL vs NoSQL, sharding, replication, indexing
- Caching: Redis, Memcached, CDN, cache invalidation strategies
- Message Queues: Kafka, RabbitMQ, async processing patterns
- API Design: REST, GraphQL, gRPC, rate limiting, versioning
- Microservices: Service discovery, circuit breakers, saga pattern
- Storage: Blob storage, file systems, data lakes
- Monitoring: Logging, metrics, alerting, distributed tracing
""",
    "behavioral_framework": """
Behavioral Interview Framework (STAR Method):
- Situation: Describe the context and background
- Task: Explain your responsibility or goal
- Action: Detail the specific steps you took
- Result: Share the outcome and what you learned

Key Behavioral Competencies:
- Leadership: Initiative, decision-making, mentoring
- Teamwork: Collaboration, conflict resolution, communication
- Problem Solving: Analytical thinking, creativity, persistence
- Adaptability: Learning agility, handling change, resilience
- Communication: Clarity, active listening, presentation skills
""",
}


def load_knowledge_base():
    """Load and index all knowledge base documents."""
    store = get_vector_store()
    
    # Index built-in knowledge
    all_chunks = []
    for topic_id, content in INTERVIEW_KNOWLEDGE.items():
        chunks = chunk_knowledge_doc(content, doc_id=topic_id, doc_type="knowledge_base")
        all_chunks.extend(chunks)

    # Load custom knowledge from files
    kb_path = Path(settings.rag.knowledge_base_path)
    if kb_path.exists():
        for file_path in kb_path.glob("*.txt"):
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            if text.strip():
                chunks = chunk_knowledge_doc(
                    text, doc_id=file_path.stem, doc_type="knowledge_base"
                )
                all_chunks.extend(chunks)
                logger.info(f"Loaded knowledge file: {file_path.name} ({len(chunks)} chunks)")

        for file_path in kb_path.glob("*.json"):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    text = json.dumps(data, indent=2)
                    chunks = chunk_knowledge_doc(
                        text, doc_id=file_path.stem, doc_type="company_data"
                    )
                    all_chunks.extend(chunks)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in knowledge file: {file_path.name}")

    if all_chunks:
        store.add(all_chunks)
        logger.info(f"Knowledge base indexed: {len(all_chunks)} total chunks")

    return len(all_chunks)
