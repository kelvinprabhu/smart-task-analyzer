# Smart Task Analyzer

A Django REST API-based intelligent task prioritization system that uses graph theory and multi-factor scoring to help users decide what to work on next.

## Table of Contents
- [Setup Instructions](#setup-instructions)
- [Algorithm Explanation](#algorithm-explanation)
- [Design Decisions](#design-decisions)
- [Time Breakdown](#time-breakdown)
- [Bonus Challenges Completed](#bonus-challenges-completed)
- [Future Improvements](#future-improvements)
- [API Endpoints](#api-endpoints)

---

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd SMART-TASK-ANALYZER
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Navigate to backend directory**
```bash
cd backend
```

4. **Run migrations**
```bash
python manage.py migrate
```

5. **Start the development server**
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

The font-end will be

Access the frontend at `http://localhost:8080`

### Testing with Postman
Import the provided `Smart Task Analyzer - Complete Test Suite.postman_collection.json` file into Postman to test all API endpoints.

---

## Algorithm Explanation

The Smart Task Analyzer uses a sophisticated **graph-aware priority scoring system** that combines multiple factors to determine task priority. The algorithm is implemented in `priority_engine.py` and consists of several key components:

### Core Scoring Formula

The final priority score for each task is calculated as:

```
score = (urgency × W_urgency + importance × W_importance) 
        × dependency_factor 
        × centrality_factor 
        × effort_factor 
        × depth_discount
```

Then normalized using logarithmic scaling to a 0-100 range.

### Component Breakdown

**1. Urgency Score (Time-Sensitive)**
- Calculates working days remaining until the due date, excluding weekends and Indian holidays
- Tasks with no due date receive a neutral score (0.5)
- Overdue tasks get exponentially higher urgency (2.0-3.0 range)
- Recent deadlines score higher (1.0-2.0 range based on days remaining)

**2. Importance Score**
- User-defined 1-10 scale normalized to 0.0-1.0
- Represents the strategic value or impact of completing the task
- Default value: 5/10 if not specified

**3. Effort Factor**
- Inversely proportional to estimated hours: `1 / estimated_hours`
- Shorter tasks get higher priority (quick wins principle)
- Capped at 10.0 to prevent division issues with very small estimates
- Default: 2.0 hours if not specified

**4. Direct Dependency Boost**
- Tasks that block other tasks receive priority amplification
- Formula: `1 + (α × dependent_count)` where α = 0.6
- Ensures bottleneck tasks are addressed first

**5. Graph Centrality (Katz Propagation)**
- Implements a modified Katz centrality algorithm over 12 iterations
- Measures a task's importance in the overall dependency network
- Tasks that influence many downstream tasks get boosted priority
- Propagates influence through the graph structure using λ = 0.35

**6. Depth Discount (Critical Stability Fix)**
- Calculates how many layers of dependencies exist above a task
- Applies discount: `1 / (1 + depth)`
- Prevents leaf nodes from dominating just because they have many ancestors
- Ensures root tasks (blockers) maintain appropriate priority

### Cycle Detection
The algorithm detects circular dependencies using depth-first search (DFS) with a stack-based approach. Cyclic tasks are:
- Identified and excluded from scoring
- Reported to the user for manual resolution
- Prevents infinite loops in dependency resolution

### Task Blocking Logic
Tasks are classified as:
- **Unblocked**: No dependencies, ready to start
- **Blocked**: Has dependencies that must be completed first
- Unblocked tasks are always shown first regardless of score

### Configurable Weights
The system uses tunable parameters for different organizational priorities:
- `W_URGENCY = 0.7` - How much to prioritize deadlines
- `W_IMPORTANCE = 0.8` - How much to value strategic importance
- `ALPHA = 0.6` - Strength of direct dependency boost
- `LAMBDA = 0.35` - Graph influence propagation strength
- `U_MAX = 10` - Working days threshold for maximum urgency

This multi-dimensional approach ensures tasks are prioritized based on when they're due, how important they are, how much effort they require, and how they fit into the broader project structure.

---

## Design Decisions

### 1. **Graph-Based Architecture**
**Decision**: Used directed acyclic graph (DAG) representation for task dependencies  
**Rationale**: Task relationships are inherently hierarchical. Graph algorithms provide efficient cycle detection and propagation of priority through the network.  
**Trade-off**: More complex than simple list sorting, but handles real-world dependency scenarios correctly.

### 2. **Working Days Calculation**
**Decision**: Implemented `working_days_between()` that excludes weekends and Indian holidays  
**Rationale**: Business tasks operate on working days, not calendar days. Using calendar days would underestimate urgency for tasks due on Mondays.  
**Trade-off**: Requires the `holidays` library dependency, but significantly improves real-world accuracy.

### 3. **Logarithmic Score Normalization**
**Decision**: Applied `log1p()` transformation to final scores before scaling to 0-100  
**Rationale**: Raw scores had extreme outliers. Logarithmic scaling compresses the range while preserving relative ordering.  
**Trade-off**: Scores are less intuitive to interpret, but prevent one factor from dominating the entire calculation.

### 4. **Depth Discount Instead of Depth Boost**
**Decision**: Applied `1/(1+depth)` discount to deeper tasks  
**Rationale**: Initial implementation boosted leaf tasks too aggressively. Discounting ensures blocker tasks at the root maintain priority.  
**Trade-off**: Deep chains of tasks might appear deprioritized, but this reflects the reality that blockers must be handled first.

### 5. **Separate Valid/Invalid Task Handling**
**Decision**: Validator returns detailed error reports but allows partial batch success  
**Rationale**: Users shouldn't lose all valid tasks because one has a typo. Partial success with clear error reporting improves UX.  
**Trade-off**: More complex response structure, but much better user experience.

### 6. **Unblocked Tasks First**
**Decision**: Always display unblocked tasks before blocked ones, regardless of score  
**Rationale**: Users can't start blocked tasks anyway. Showing them first would be misleading.  
**Trade-off**: High-priority blocked tasks might seem "buried," but this accurately reflects what's actionable.

### 7. **Effort as Inverse Factor**
**Decision**: Smaller effort = higher priority (`1/hours`)  
**Rationale**: Encourages "quick wins" and momentum. Aligns with Agile principles.  
**Trade-off**: Very important but time-consuming tasks might rank lower than intended. Importance weight helps balance this.

### 8. **Centrality Iterations = 12**
**Decision**: Fixed 12 iterations for Katz centrality calculation  
**Rationale**: Testing showed convergence typically occurs by iteration 8-10. 12 provides buffer with minimal performance cost.  
**Trade-off**: Slightly slower than 5-6 iterations, but ensures stable scores for complex graphs.

---

## Time Breakdown

| Component | Estimated Time |
|-----------|----------------|
| **Core API Setup** | 1 hours |
| - Django project structure | 30 min |
| - Models and serializers | 45 min |
| **Priority Algorithm Development** | 4 hours |
| - Initial scoring logic | 1.5 hour |
| - Graph theory integration | 1 hours |
| - Cycle detection | 45 min |
| - Testing and refinement | 45 min |
| **Validation System** | 1 hour |
| - TaskValidator class | 30 min |
| - Error handling and reporting | 30 min |
| **Working Days Intelligence** | 30 min |
| - Holidays integration | 20 min |
| - Testing edge cases | 10 min |
| **Eisenhower Matrix View** | 45 min |
| - Dynamic threshold calculation | 25 min |
| - Quadrant assignment logic | 20 min |

| **Frontend Development** | 2 hours |
| - HTML/CSS layout | 45 min |
| - JavaScript API integration | 1 hour |
| - UI polish | 15 min |
| **Testing & Documentation** | 40 hours |
| - Postman collection creation | 10 min |
| - Edge case testing | 45 min |
| - README documentation | 5 min |
| **Total** | **~12 hours** |

---

## Bonus Challenges Completed

### ✅ 1. Date Intelligence: Working Days Calculation (30 min)
**Implementation**: `working_days_between()` function in `priority_engine.py`

- Excludes weekends (Saturday, Sunday)
- Excludes Indian public holidays using the `holidays` library
- Accurately calculates business days for urgency scoring
- Handles edge cases like same-day due dates

**Example**: A task due on Monday with today being Friday is 1 working day away (not 3 calendar days).

### ✅ 2. Eisenhower Matrix View (45 min)
**Endpoint**: `GET /api/eisenhower/`

**Features**:
- Dynamically calculates median urgency and importance across all tasks
- Classifies tasks into four quadrants:
  - **Do**: High urgency, high importance
  - **Plan**: Low urgency, high importance
  - **Delegate**: High urgency, low importance
  - **Delete**: Low urgency, low importance
- Returns normalized urgency/importance scores (0-1 range)
- Includes priority score for tie-breaking within quadrants

**Response Structure**:
```json
{
  "matrix": [
    {
      "id": 1,
      "title": "Fix critical bug",
      "urgency": 0.95,
      "importance": 0.9,
      "score": 87.34,
      "quadrant": "Do"
    }
  ]
}
```

### ✅ 3. Graph Visualization (Bonus) --> Need Improvement -Further Development
**Endpoint**: `GET /api/graph/`

**Features**:
- Renders task dependency graph as PNG image
- Uses NetworkX for graph layout (spring algorithm)
- Color-codes cyclic tasks in red
- Shows dependency arrows with proper directionality
- Returns image directly for embedding in frontend

---




## API Endpoints

### Task Management

**POST** `/api/analyze/`  
Submit tasks for analysis and priority scoring

**GET** `/api/suggest/`  
Get top 3 recommended tasks to work on next

**GET** `/api/list/`  
List all tasks with dependencies

**DELETE** `/api/delete/?id=<task_id>`  
Delete a single task by ID
As well as [ids,...]

**DELETE** `/api/delete/` (with body `{"ids": [1,2,3]}`)  
Delete multiple tasks

**DELETE** `/api/reset/`  
Clear all tasks and reset database

### Analysis Views

**GET** `/api/eisenhower/`  
Get Eisenhower Matrix classification of all tasks

**GET** `/api/graph/`  
Get visual dependency graph (PNG image)

---

## Postman Collection
- export it to postman and text with all the API Endpoints and Test Cases
[Postman colection](<Smart Task Analyzer - Complete Test Suite.postman_collection.json>)
## Project Structure

```
SMART-TASK-ANALYZER/
├── backend/
│   ├── smart_task_analyzer/      # Django project settings
│   │   ├── settings.py
│   │   └── urls.py
│   ├── taskapi/                   # Main API app
│   │   ├── models.py              # Task model
│   │   ├── serializers.py         # DRF serializers
│   │   ├── views.py               # API views
│   │   ├── urls.py                # API routing
│   │   └── scoring/
│   │       └── priority_engine.py # Core algorithm
│   ├── manage.py
│   └── db.sqlite3
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/main.js
├── requirements.txt
├── README.md
└── Smart Task Analyzer - Complete Test Suite.postman_collection.json
```

### Screenshots 
- Smart Task Analyzer - Startup Page
![Smart Task Analyzer - Startup Page](<Screenshot/Smart Task Analyzer - Startup Page.png>)
- Smart Task Analyzer - Initial Analyse
![Smart Task Analyzer - Initial Analyse](<Screenshot/Smart Task Analyzer - Initial Analyse.png>)
-  Task Analyzer - Top Suggestioins
![Smart Task Analyzer - Top Suggestioins](<Screenshot/Smart Task Analyzer - Top Suggestioins.png>)
- Smart Task Analyzer - Validations
![Smart Task Analyzer - Validations](<Screenshot/Smart Task Analyzer - Validations.png>)