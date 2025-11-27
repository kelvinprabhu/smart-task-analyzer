import datetime
from collections import defaultdict


class PriorityEngine:
    """
    PriorityEngine V2
    -----------------
    A graph-aware task scoring engine based on WSJF-like logic, dependency influence,
    and network centrality. Produces a single priority score per task.
    """

    # CONFIGURABLE WEIGHTS
    U_MAX = 14          # Max days for urgency relevance
    W_URGENCY = 0.6     # Weight of urgency contribution
    W_IMPORTANCE = 0.4  # Weight of importance contribution
    ALPHA = 0.4         # Weight multiplier for direct dependents
    LAMBDA = 0.15       # Decay factor for graph centrality propagation
    CENTRALITY_ITER = 8 # Iterations for power-centrality calculation

    def __init__(self, tasks):
        self.tasks = tasks
        self.today = datetime.date.today()
    def effort_score(self, task):
        """
        Public-facing effort score used by views/reasons.
        Uses the model's `estimated_hours` field (fallbacks to `effort` if present).
        Returns a bounded score where smaller estimated hours -> larger score.
        """
        # Prefer the canonical `estimated_hours` field on Task
        hours = getattr(task, "estimated_hours", None)
        if hours is None:
            # fallback for older data/models
            hours = getattr(task, "effort", None)

        if hours is None:
            return 0.0

        # Use the same logic as `effort_factor` but scaled for readability
        return float(self.effort_factor(task))

    def dependency_score(self, task):
        """
        Convenience wrapper to compute dependency influence for a single task.
        Counts how many tasks depend on `task` within the engine's task set
        and returns the direct dependency factor.
        """
        # Count dependents among the engine's task queryset/list
        dependents_count = 0
        for t in self.tasks:
            # `dependencies` is a related manager; use .all() to inspect
            if task in t.dependencies.all():
                dependents_count += 1

        return self.direct_dependency_factor(task, {task.id: dependents_count})

    # ------------------------------------------------------------
    # 1. CYCLE DETECTION (Prevents invalid dependency graphs)
    # ------------------------------------------------------------
    def detect_cycles(self):
        visited = set()
        stack = set()
        cyclic_tasks = []

        def dfs(task):
            if task.id in stack:
                return True
            if task.id in visited:
                return False

            visited.add(task.id)
            stack.add(task.id)

            for dep in task.dependencies.all():
                if dfs(dep):
                    return True

            stack.remove(task.id)
            return False

        for task in self.tasks:
            if dfs(task):
                cyclic_tasks.append(task.id)

        return cyclic_tasks

    # ------------------------------------------------------------
    # 2. COMPONENT SCORES
    # ------------------------------------------------------------

    def urgency_score(self, task):
        """
        Urgency based on due date proximity.
        Closer deadlines -> higher urgency.
        Overdue tasks get a fixed high urgency.
        """
        if not task.due_date:
            return 0.0

        delta = (task.due_date - self.today).days

        if delta < 0:
            return 2.0  # Overdue tasks get urgent boost

        # Linear decay up to U_MAX days
        clamped = max(0, self.U_MAX - delta)
        return 1.0 + (clamped / self.U_MAX)

    def importance_score(self, task):
        """ Normalize user-defined importance (1–10) to 0–1 range. """
        return min(max(task.importance / 10.0, 0), 1)

    def effort_factor(self, task):
        """
        Inverse of effort: smaller tasks get boosted (quick wins).
        Capped at minimum 0.5 to avoid extreme values.
        """
        hours = max(task.estimated_hours, 0.5)
        return 1.0 / hours

    def direct_dependency_factor(self, task, dependents_count):
        """
        Tasks that unblock many others get a boost.
        The more tasks depending on this one, the higher the priority.
        """
        dep_count = dependents_count.get(task.id, 0)
        return 1.0 + (self.ALPHA * dep_count)

    # ------------------------------------------------------------
    # 3. GRAPH CENTRALITY CALCULATION
    # ------------------------------------------------------------
    def compute_centrality(self, dependents):
        """
        Katz-like centrality:
        C(task) = β + λ * Σ centrality of direct dependents
        Tasks at the start of long dependency chains get high scores.
        """
        beta = 1.0
        C = {t.id: beta for t in self.tasks}

        for _ in range(self.CENTRALITY_ITER):
            new_C = {}
            for t in self.tasks:
                score = beta
                for child in dependents[t.id]:
                    score += self.LAMBDA * C[child]
                new_C[t.id] = score
            C = new_C

        max_val = max(C.values())
        # Normalize 0–1
        for tid in C:
            C[tid] /= max_val

        return C

    # ------------------------------------------------------------
    # 4. FINAL SCORE
    # ------------------------------------------------------------
    def calculate_score(self, task, dependents_count, centrality_map):
        """
        Final WSJF-like priority score with network awareness.
        """
        urgency = self.urgency_score(task)
        importance = self.importance_score(task)
        effort = self.effort_factor(task)

        # Weighted combination of value components
        value_score = (
            urgency * self.W_URGENCY +
            importance * self.W_IMPORTANCE
        )

        dependency_factor = self.direct_dependency_factor(task, dependents_count)

        centrality_factor = centrality_map.get(task.id, 1.0)

        # WSJF-style: value / effort × influence factors
        final_priority = value_score * dependency_factor * centrality_factor * effort

        return float(final_priority)

    # ------------------------------------------------------------
    # 5. RUN ENGINE
    # ------------------------------------------------------------
    def run(self):
        # Step 1: Detect cycles
        cyclic = self.detect_cycles()

        # Keep only valid (non-cyclic) tasks
        valid_tasks = [t for t in self.tasks if t.id not in cyclic]

        # Step 2: Compute direct dependents count
        dependents_count = defaultdict(int)
        adjacency = defaultdict(list)

        for t in valid_tasks:
            for dep in t.dependencies.all():
                dependents_count[dep.id] += 1
                adjacency[dep.id].append(t.id)

        # Step 3: Compute graph centrality
        centrality_map = self.compute_centrality(adjacency)

        # Step 4: Compute final score for each task
        scored = []
        for task in valid_tasks:
            score = self.calculate_score(task, dependents_count, centrality_map)
            scored.append({
                "task": task,
                "score": score
            })

        # Step 5: Sort high-to-low
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored, cyclic
