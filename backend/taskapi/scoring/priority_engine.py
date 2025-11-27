import datetime
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class PriorityEngine:
    """
    PriorityEngine V3 - Hardened Edition
    -------------------------------------
    Graph-aware task scoring with comprehensive validation and error handling.
    """

    # CONFIGURABLE WEIGHTS
    U_MAX = 14
    W_URGENCY = 0.6
    W_IMPORTANCE = 0.4
    ALPHA = 0.4
    LAMBDA = 0.15
    CENTRALITY_ITER = 8

    def __init__(self, tasks):
        self.tasks = tasks
        self.today = datetime.date.today()

    def effort_score(self, task):
        """Public-facing effort score for API responses."""
        hours = getattr(task, "estimated_hours", None)
        if hours is None:
            hours = getattr(task, "effort", None)
        if hours is None or hours <= 0:
            return 0.0
        return float(self.effort_factor(task))

    def dependency_score(self, task):
        """Compute dependency influence for a single task."""
        dependents_count = 0
        for t in self.tasks:
            if task in t.dependencies.all():
                dependents_count += 1
        return self.direct_dependency_factor(task, {task.id: dependents_count})

    # ============================================================
    # CYCLE DETECTION
    # ============================================================
    def detect_cycles(self):
        """Detects circular dependencies using DFS."""
        visited = set()
        stack = set()
        cyclic_tasks = set()

        def dfs(task):
            if task.id in stack:
                cyclic_tasks.add(task.id)
                return True
            if task.id in visited:
                return False

            visited.add(task.id)
            stack.add(task.id)

            for dep in task.dependencies.all():
                if dfs(dep):
                    cyclic_tasks.add(task.id)

            stack.remove(task.id)
            return False

        for task in self.tasks:
            if task.id not in visited:
                dfs(task)

        return list(cyclic_tasks)

    # ============================================================
    # COMPONENT SCORES WITH SAFE DEFAULTS
    # ============================================================
    def urgency_score(self, task):
        """Urgency based on due date. Safe for None/past dates."""
        if not task.due_date:
            return 0.5  # Neutral score for tasks without due date

        delta = (task.due_date - self.today).days

        if delta < 0:
            # Overdue: scale by how overdue (more overdue = more urgent)
            overdue_days = abs(delta)
            return 2.0 + min(overdue_days / 7.0, 1.0)  # Cap at 3.0

        # Future tasks: linear decay
        clamped = max(0, self.U_MAX - delta)
        return 1.0 + (clamped / self.U_MAX)

    def importance_score(self, task):
        """Normalize importance (1-10) with bounds checking."""
        importance = getattr(task, "importance", 5)  # Default to 5 if missing
        if importance is None:
            importance = 5
        # Clamp to valid range
        importance = max(1, min(10, importance))
        return importance / 10.0

    def effort_factor(self, task):
        """Inverse effort with safe lower bound."""
        hours = getattr(task, "estimated_hours", None)
        if hours is None:
            hours = getattr(task, "effort", 2.0)  # Default 2 hours
        
        # Handle invalid values
        if hours is None or hours <= 0:
            hours = 1.0  # Default to 1 hour for invalid data
        
        hours = max(hours, 0.1)  # Minimum 0.1 to avoid division issues
        return min(1.0 / hours, 10.0)  # Cap at 10x boost

    def direct_dependency_factor(self, task, dependents_count):
        """Boost for tasks that unblock others."""
        dep_count = dependents_count.get(task.id, 0)
        return 1.0 + (self.ALPHA * dep_count)

    # ============================================================
    # GRAPH CENTRALITY
    # ============================================================
    def compute_centrality(self, dependents):
        """Katz-like centrality for dependency graph."""
        if not self.tasks:
            return {}

        beta = 1.0
        C = {t.id: beta for t in self.tasks}

        for _ in range(self.CENTRALITY_ITER):
            new_C = {}
            for t in self.tasks:
                score = beta
                for child in dependents.get(t.id, []):
                    score += self.LAMBDA * C.get(child, beta)
                new_C[t.id] = score
            C = new_C

        max_val = max(C.values()) if C else 1.0
        if max_val > 0:
            for tid in C:
                C[tid] /= max_val

        return C

    # ============================================================
    # FINAL SCORE CALCULATION
    # ============================================================
    def calculate_score(self, task, dependents_count, centrality_map):
        """WSJF-like priority score with network awareness."""
        urgency = self.urgency_score(task)
        importance = self.importance_score(task)
        effort = self.effort_factor(task)

        value_score = (
            urgency * self.W_URGENCY +
            importance * self.W_IMPORTANCE
        )

        dependency_factor = self.direct_dependency_factor(task, dependents_count)
        centrality_factor = centrality_map.get(task.id, 1.0)

        final_priority = value_score * dependency_factor * centrality_factor * effort
        return float(final_priority)

    # ============================================================
    # RUN ENGINE
    # ============================================================
    def run(self):
        """Execute scoring with cycle detection and validation."""
        if not self.tasks:
            return [], []

        # Detect cycles
        cyclic = self.detect_cycles()
        valid_tasks = [t for t in self.tasks if t.id not in cyclic]

        if not valid_tasks:
            return [], cyclic

        # Build dependency graph
        dependents_count = defaultdict(int)
        adjacency = defaultdict(list)

        for t in valid_tasks:
            for dep in t.dependencies.all():
                if dep.id not in cyclic:  # Only count valid dependencies
                    dependents_count[dep.id] += 1
                    adjacency[dep.id].append(t.id)

        # Compute centrality
        centrality_map = self.compute_centrality(adjacency)

        # Score all tasks
        scored = []
        for task in valid_tasks:
            score = self.calculate_score(task, dependents_count, centrality_map)
            scored.append({
                "task": task,
                "score": score
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored, cyclic


# ============================================================
# VALIDATION UTILITIES
# ============================================================
class TaskValidator:
    """Validates and sanitizes task input data."""
    
    @staticmethod
    def validate_task_data(data):
        """
        Validates a single task dict. Returns (is_valid, cleaned_data, errors).
        """
        errors = []
        cleaned = {}
        
        # Required: title
        title = data.get("title", "").strip()
        if not title:
            errors.append("Title is required and cannot be empty")
            return False, cleaned, errors
        else:
            cleaned["title"] = title
        
        # Optional: due_date (REJECT past dates)
        due_date = data.get("due_date")
        if due_date:
            try:
                if isinstance(due_date, str):
                    parsed = datetime.datetime.strptime(due_date, "%Y-%m-%d").date()
                else:
                    parsed = due_date
                
                # Check if date is in the past
                today = datetime.date.today()
                if parsed < today:
                    errors.append(f"due_date cannot be in the past: {parsed}")
                    return False, cleaned, errors
                
                cleaned["due_date"] = parsed
            except (ValueError, TypeError):
                errors.append(f"Invalid due_date format: {due_date}. Expected YYYY-MM-DD")
                return False, cleaned, errors
        
        # Optional: estimated_hours (REJECT negative or zero)
        hours = data.get("estimated_hours")
        if hours is not None:
            try:
                hours_float = float(hours)
                if hours_float < 0:
                    errors.append(f"estimated_hours cannot be negative: {hours}")
                    return False, cleaned, errors
                elif hours_float == 0:
                    errors.append("estimated_hours cannot be zero")
                    return False, cleaned, errors
                else:
                    cleaned["estimated_hours"] = hours_float
            except (ValueError, TypeError):
                errors.append(f"Invalid estimated_hours: {hours}")
                return False, cleaned, errors
        else:
            cleaned["estimated_hours"] = 2.0  # Default if missing
        
        # Optional: importance (REJECT out of range)
        importance = data.get("importance")
        if importance is not None:
            try:
                imp_int = int(importance)
                if imp_int < 1 or imp_int > 10:
                    errors.append(f"importance must be between 1-10, got: {imp_int}")
                    return False, cleaned, errors
                cleaned["importance"] = imp_int
            except (ValueError, TypeError):
                errors.append(f"Invalid importance: {importance}")
                return False, cleaned, errors
        else:
            cleaned["importance"] = 5  # Default
        
        # Dependencies (will be resolved later)
        deps = data.get("dependencies", [])
        if not isinstance(deps, list):
            errors.append(f"dependencies must be a list, got: {type(deps)}")
            return False, cleaned, errors
        else:
            cleaned["dependencies"] = deps
        
        is_valid = len(errors) == 0
        return is_valid, cleaned, errors

