"""
Task Classification Engine for T AI Operating System.
Categorizes user queries and intent to inform intelligent model routing decisions.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from brain.logging.logger import get_logger

log = get_logger("core.task_classifier")


@dataclass
class TaskClassification:
    type: str  # "coding" | "reasoning" | "fast_response" | "local" | "general"
    complexity: str  # "low" | "medium" | "high"
    context_required: str  # "small" | "large"
    privacy: str  # "normal" | "local_only"
    latency_preference: str  # "fast" | "normal"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "complexity": self.complexity,
            "contextRequired": self.context_required,
            "privacy": self.privacy,
            "latencyPreference": self.latency_preference,
        }


class TaskClassifier:
    """Classifies incoming AI requests using rule heuristics and metadata analysis."""

    CODING_KEYWORDS = {
        "code", "python", "javascript", "typescript", "html", "css", "sql", "bug", "fix",
        "refactor", "function", "class", "def", "import", "const", "let", "var", "git",
        "regex", "async", "await", "api", "json", "endpoint", "stacktrace", "error"
    }

    REASONING_KEYWORDS = {
        "why", "explain", "analyze", "reason", "evaluate", "compare", "strategy",
        "math", "proof", "derive", "logic", "conclude", "plan", "solve", "deep"
    }

    LOCAL_KEYWORDS = {
        "private", "local", "offline", "sensitive", "confidential", "secret", "my pc", "my device"
    }

    FAST_KEYWORDS = {
        "hi", "hello", "hey", "thanks", "thank you", "status", "time", "date", "ping", "test"
    }

    def classify(self, messages: List[Dict[str, str]]) -> TaskClassification:
        if not messages:
            return TaskClassification(
                type="general", complexity="low", context_required="small", privacy="normal", latency_preference="normal"
            )

        last_user_msg = ""
        total_length = 0

        for msg in messages:
            content = msg.get("content", "")
            total_length += len(content)
            if msg.get("role") == "user":
                last_user_msg = content

        text_lower = last_user_msg.lower()
        words = set(text_lower.split())

        # Check local / privacy first
        if any(kw in text_lower for kw in self.LOCAL_KEYWORDS):
            return TaskClassification(
                type="local",
                complexity="medium",
                context_required="large" if total_length > 3000 else "small",
                privacy="local_only",
                latency_preference="normal",
            )

        # Check coding
        if any(kw in words or kw in text_lower for kw in self.CODING_KEYWORDS) or "```" in last_user_msg:
            return TaskClassification(
                type="coding",
                complexity="high" if len(last_user_msg) > 300 or "```" in last_user_msg else "medium",
                context_required="large" if total_length > 2000 else "small",
                privacy="normal",
                latency_preference="normal",
            )

        # Check reasoning
        if any(kw in words or kw in text_lower for kw in self.REASONING_KEYWORDS):
            return TaskClassification(
                type="reasoning",
                complexity="high" if len(last_user_msg) > 200 else "medium",
                context_required="large" if total_length > 3000 else "small",
                privacy="normal",
                latency_preference="normal",
            )

        # Check fast / simple request
        if len(last_user_msg) < 30 and (text_lower.strip() in self.FAST_KEYWORDS or any(w in words for w in self.FAST_KEYWORDS)):
            return TaskClassification(
                type="fast_response",
                complexity="low",
                context_required="small",
                privacy="normal",
                latency_preference="fast",
            )

        # Default general chat
        return TaskClassification(
            type="general",
            complexity="high" if total_length > 4000 else "medium" if total_length > 1000 else "low",
            context_required="large" if total_length > 3000 else "small",
            privacy="normal",
            latency_preference="normal",
        )


task_classifier = TaskClassifier()
