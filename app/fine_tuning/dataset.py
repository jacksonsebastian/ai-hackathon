"""
Dataset generator for fine-tuning the AI Interviewer Agent System.
Generates synthetic instruction-tuning and multi-turn chat datasets
for technical, behavioral, and coding interview scenarios.
"""

import json
import os
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from pathlib import Path

# Topics for synthetic data generation
TECH_TOPICS = [
    {
        "topic": "Python Advanced Concepts",
        "concepts": ["decorators", "generators", "context managers", "metaclasses", "asyncio", "GIL", "memory management"],
        "difficulty": "medium_hard"
    },
    {
        "topic": "System Design",
        "concepts": ["load balancing", "caching (Redis/Memcached)", "database sharding", "microservices architecture", "event-driven design (Kafka)", "rate limiting", "consistency vs availability (CAP theorem)"],
        "difficulty": "hard"
    },
    {
        "topic": "Relational & Non-Relational Databases",
        "concepts": ["indexing", "transaction isolation levels", "ACID properties", "SQL optimization", "MongoDB vs PostgreSQL", "replication topologies"],
        "difficulty": "medium"
    },
    {
        "topic": "Data Structures & Algorithms",
        "concepts": ["binary trees", "graphs & DFS/BFS", "dynamic programming", "sorting & searching", "hash maps", "sliding window technique", "space-time complexity (Big O)"],
        "difficulty": "medium_hard"
    },
    {
        "topic": "REST APIs & Microservices",
        "concepts": ["gRPC vs REST", "authentication (JWT, OAuth2)", "API gateway pattern", "circuit breaker pattern", "service discovery"],
        "difficulty": "medium"
    }
]

BEHAVIORAL_SCENARIOS = [
    {
        "competency": "Conflict Resolution",
        "situation": "A disagreement with a tech lead or team member about the technical implementation details of a feature.",
        "star_focus": "How did you communicate, compromise, and find a resolution that benefited the project?"
    },
    {
        "competency": "Handling Failure",
        "situation": "A critical system crash or a deployment failure that occurred under your watch.",
        "star_focus": "How did you respond to the emergency, perform post-mortem analysis, and implement preventative measures?"
    },
    {
        "competency": "Prioritization & Deadlines",
        "situation": "Having to deliver a complex project under tight deadlines with resources cut in half.",
        "star_focus": "How did you manage scope creep, prioritize critical path features, and negotiate stakeholders' expectations?"
    },
    {
        "competency": "Leadership & Mentorship",
        "situation": "Helping a junior developer or peer who was struggling to complete their tasks.",
        "star_focus": "How did you identify their blockers, pair program with them, and foster their long-term growth?"
    }
]

CODING_PROBLEMS = [
    {
        "title": "Reverse Linked List",
        "difficulty": "Easy",
        "description": "Given the head of a singly linked list, reverse the list, and return its reversed list.",
        "solution": "def reverseList(head):\n    prev = None\n    curr = head\n    while curr:\n        next_node = curr.next\n        curr.next = prev\n        prev = curr\n        curr = next_node\n    return prev",
        "complexity": "Time Complexity: O(n) | Space Complexity: O(1)"
    },
    {
        "title": "Two Sum",
        "difficulty": "Easy",
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
        "solution": "def twoSum(nums, target):\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []",
        "complexity": "Time Complexity: O(n) | Space Complexity: O(n)"
    },
    {
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "Medium",
        "description": "Given a string s, find the length of the longest substring without repeating characters.",
        "solution": "def lengthOfLongestSubstring(s):\n    char_map = {}\n    max_len = 0\n    start = 0\n    for i, char in enumerate(s):\n        if char in char_map and char_map[char] >= start:\n            start = char_map[char] + 1\n        char_map[char] = i\n        max_len = max(max_len, i - start + 1)\n    return max_len",
        "complexity": "Time Complexity: O(n) | Space Complexity: O(min(m, n)) where m is size of alphabet"
    },
    {
        "title": "LRU Cache",
        "difficulty": "Hard",
        "description": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.",
        "solution": "class Node:\n    def __init__(self, key=0, val=0):\n        self.key = key\n        self.val = val\n        self.prev = None\n        self.next = None\n\nclass LRUCache:\n    def __init__(self, capacity: int):\n        self.cap = capacity\n        self.cache = {}\n        self.head = Node()\n        self.tail = Node()\n        self.head.next = self.tail\n        self.tail.prev = self.head\n        \n    def _remove(self, node):\n        p, n = node.prev, node.next\n        p.next, n.prev = n, p\n        \n    def _add(self, node):\n        p = self.tail.prev\n        p.next = node\n        node.prev = p\n        node.next = self.tail\n        self.tail.prev = node\n        \n    def get(self, key: int) -> int:\n        if key in self.cache:\n            node = self.cache[key]\n            self._remove(node)\n            self._add(node)\n            return node.val\n        return -1\n        \n    def put(self, key: int, value: int) -> None:\n        if key in self.cache:\n            self._remove(self.cache[key])\n        node = Node(key, value)\n        self.cache[key] = node\n        self._add(node)\n        if len(self.cache) > self.cap:\n            lru = self.head.next\n            self._remove(lru)\n            del self.cache[lru.key]",
        "complexity": "Time Complexity: O(1) get/put | Space Complexity: O(capacity)"
    }
]


@dataclass
class ConversationSample:
    """Structure of an individual sample formatted for ChatML / instruction tuning."""
    messages: List[Dict[str, str]]


class DatasetGenerator:
    """Generates synthetic interview dataset for fine-tuning LLMs."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_technical_sample(self, topic: Dict[str, Any]) -> ConversationSample:
        """Generates a structured chat exchange for a technical question."""
        concept = random.choice(topic["concepts"])
        
        system_prompt = (
            "You are an expert Technical Interviewer Agent. Ask direct, challenging questions "
            "evaluating coding practices, system design principles, and core computer science concepts."
        )
        
        # Scenario questions & answers
        questions = [
            f"Can you explain how {concept} works in production systems, and what are some common pitfalls developers face?",
            f"How does {concept} affect scalability or memory usage in high-throughput applications?",
            f"If you had to optimize a system experiencing performance bottlenecks related to {concept}, what would be your step-by-step strategy?"
        ]
        
        answers_good = [
            f"In production, {concept} is critical. For instance, when designing high-concurrency architectures, misconfiguring it can lead to "
            f"severe bottlenecking, memory leaks, or thread starvation. A common pitfall is ignoring the default behaviors (like blocking operations "
            f"or cache eviction policies). I usually mitigate this by setting up connection pools, profiling memory, and monitoring usage.",
            
            f"Regarding scalability, {concept} introduces resource overhead if not handled carefully. For memory, it might lead to garbage collection pressure "
            f"or excessive memory fragmentation. We must balance CPU cycles with memory allocations, implementing pooling or buffering structures "
            f"to reuse objects and keep tail latencies under control.",
            
            f"First, I would gather telemetry data using APM tools to profile the hot paths. Then, I would isolate the code executing {concept} and run "
            f"microbenchmarks. Next, I'd apply targeted optimizations (such as introducing asynchronous processing, batching DB queries, or introducing "
            f"an in-memory caching tier), and finally, run load tests to verify the throughput improvements under synthetic pressure."
        ]
        
        q = random.choice(questions)
        a = random.choice(answers_good)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Hi, I'm ready for the technical questions. Topic: {topic['topic']}"},
            {"role": "assistant", "content": f"Great! Let's start with {topic['topic']}. {q}"},
            {"role": "user", "content": a},
            {"role": "assistant", "content": "Excellent response. You've clearly outlined the production pitfalls, memory characteristics, and optimization pathways."}
        ]
        
        return ConversationSample(messages=messages)

    def generate_behavioral_sample(self, scenario: Dict[str, Any]) -> ConversationSample:
        """Generates a structured behavioral STAR interview exchange."""
        system_prompt = (
            "You are a Senior HR Behavioral Interviewer. Assess candidate's soft skills, conflict resolution, "
            "leadership capability, and growth mindset using the STAR methodology."
        )
        
        q = f"Describe a situation where you had to deal with: {scenario['situation']}. {scenario['star_focus']}"
        
        a = (
            "In my previous role, we had a major challenge with a critical system component. [SITUATION] During a peak traffic window, the main payment gateway "
            "underwent connection dropouts, causing 15% of transactions to fail. [TASK] As the senior engineer, my task was to lead the team to resolve the issue "
            "immediately and restructure the integration. [ACTION] I organized a war room, isolated the API timeout issue, and implemented an exponential backoff "
            "and circuit breaker pattern using Redis to queue failed attempts. I also coordinated communications between frontend developers, customer support, "
            "and the third-party provider. [RESULT] This reduced transaction failures to 0.05% within 2 hours, saved approximately $50k in potential revenue losses, "
            "and we established a robust failover architecture that eliminated this vulnerability entirely."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "I'm ready for the behavioral interview portion."},
            {"role": "assistant", "content": f"Let's focus on {scenario['competency']}. {q}"},
            {"role": "user", "content": a},
            {"role": "assistant", "content": "Thank you for the detailed breakdown. You clearly defined the context (STAR) and showcased ownership, collaboration, and high-impact resolution."}
        ]
        
        return ConversationSample(messages=messages)

    def generate_coding_sample(self, problem: Dict[str, Any]) -> ConversationSample:
        """Generates a coding assessment exchange."""
        system_prompt = (
            "You are an expert Coding Evaluator. Provide algorithmic challenges, evaluate coding syntax, "
            "and perform time/space complexity analysis."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Let's proceed with the coding round."},
            {"role": "assistant", "content": f"Here is your coding challenge: **{problem['title']}** ({problem['difficulty']}).\nDescription: {problem['description']}\n\nPlease write your solution and explain its complexity."},
            {"role": "user", "content": f"Here is my solution:\n```python\n{problem['solution']}\n```\n{problem['complexity']}"},
            {"role": "assistant", "content": f"Perfect. Your solution for {problem['title']} is correct. It complies with optimal complexity bounds: {problem['complexity']}."}
        ]
        
        return ConversationSample(messages=messages)

    def generate_dataset(self, num_samples: int = 500) -> List[ConversationSample]:
        """Generates a mixture of technical, behavioral, and coding samples."""
        dataset = []
        
        for _ in range(num_samples):
            rand_val = random.random()
            if rand_val < 0.50:
                # 50% Technical
                topic = random.choice(TECH_TOPICS)
                sample = self.generate_technical_sample(topic)
            elif rand_val < 0.80:
                # 30% Behavioral
                scenario = random.choice(BEHAVIORAL_SCENARIOS)
                sample = self.generate_behavioral_sample(scenario)
            else:
                # 20% Coding
                problem = random.choice(CODING_PROBLEMS)
                sample = self.generate_coding_sample(problem)
                
            dataset.append(sample)
            
        return dataset

    def save_dataset(self, dataset: List[ConversationSample], file_name: str = "train.jsonl"):
        """Saves the generated dataset to a JSONL file."""
        output_path = self.output_dir / file_name
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in dataset:
                f.write(json.dumps(asdict(sample)) + "\n")
        print(f"Generated {len(dataset)} samples and saved to {output_path}")


if __name__ == "__main__":
    # Generate default training and evaluation sets
    generator = DatasetGenerator(Path("data/fine_tuning"))
    train_set = generator.generate_dataset(num_samples=400)
    generator.save_dataset(train_set, "train.jsonl")
    
    val_set = generator.generate_dataset(num_samples=100)
    generator.save_dataset(val_set, "val.jsonl")
