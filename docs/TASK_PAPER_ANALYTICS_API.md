# Task Paper Analytics API Documentation

## Endpoint
`GET /api/task-paper-analytics/`

## Query Parameters
- `startDate` (required): Start date in YYYY-MM-DD format
- `endDate` (required): End date in YYYY-MM-DD format

## Response Structure

The API returns a comprehensive response designed for easy frontend filtering:

```json
{
  "summary": {
    "total_tasks_in_range": 45,
    "total_papers_in_range": 1500,
    "tasks_with_papers": 30,
    "top_20_tasks_count": 20,
    "top_papers_count": 100
  },
  "task_distribution": [
    {
      "id": 1,
      "name": "Natural Language Processing",
      "description": "Tasks related to NLP",
      "paper_count": 25,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "papers_with_tasks": [
    {
      "id": "paper-uuid",
      "title": "Paper Title",
      "abstract": "Paper abstract...",
      "tasks": [
        {
          "id": 1,
          "name": "Natural Language Processing",
          "description": "Tasks related to NLP"
        }
      ],
      "task_ids": [1, 2, 3]
    }
  ],
  "papers_grouped_by_task": [
    {
      "task_id": 1,
      "task_name": "Natural Language Processing",
      "task_description": "Tasks related to NLP",
      "paper_count": 15,
      "papers": [
        {
          "id": "paper-uuid",
          "title": "Paper Title",
          "abstract": "Paper abstract..."
        }
      ]
    }
  ],
  "task_lookup": {
    "1": {
      "id": 1,
      "name": "Natural Language Processing",
      "description": "Tasks related to NLP",
      "paper_count": 25,
      "created_at": "2024-01-01T00:00:00Z"
    }
  },
  "date_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }
}
```

## Frontend Usage Examples

### 1. Filter Papers by Specific Task

```javascript
// Get papers for a specific task
function filterPapersByTask(apiResponse, taskId) {
  return apiResponse.papers_with_tasks.filter(paper => 
    paper.task_ids.includes(taskId)
  );
}

// Usage
const nlpPapers = filterPapersByTask(apiResponse, 1);
```

### 2. Get Papers Grouped by Task

```javascript
// Already provided in the response
const groupedPapers = apiResponse.papers_grouped_by_task;

// Display papers by task
groupedPapers.forEach(taskGroup => {
  console.log(`Task: ${taskGroup.task_name} (${taskGroup.paper_count} papers)`);
  taskGroup.papers.forEach(paper => {
    console.log(`  - ${paper.title}`);
  });
});
```

### 3. Filter Papers by Multiple Tasks

```javascript
function filterPapersByMultipleTasks(apiResponse, taskIds) {
  return apiResponse.papers_with_tasks.filter(paper => 
    taskIds.some(taskId => paper.task_ids.includes(taskId))
  );
}

// Usage - get papers that belong to either NLP or Computer Vision
const multiTaskPapers = filterPapersByMultipleTasks(apiResponse, [1, 2]);
```

### 4. Get Task Information

```javascript
// Get task info quickly using task_lookup
function getTaskInfo(apiResponse, taskId) {
  return apiResponse.task_lookup[taskId];
}

// Usage
const taskInfo = getTaskInfo(apiResponse, 1);
console.log(`Task: ${taskInfo.name} - ${taskInfo.description}`);
```

### 5. Create Filter Dropdown

```javascript
function createTaskFilterDropdown(apiResponse) {
  const dropdown = document.createElement('select');
  dropdown.innerHTML = '<option value="">All Tasks</option>';
  
  apiResponse.task_distribution.forEach(task => {
    const option = document.createElement('option');
    option.value = task.id;
    option.textContent = `${task.name} (${task.paper_count} papers)`;
    dropdown.appendChild(option);
  });
  
  return dropdown;
}
```

### 6. Filter with Search and Task Combination

```javascript
function filterPapersAdvanced(apiResponse, searchTerm = '', taskIds = []) {
  let filtered = apiResponse.papers_with_tasks;
  
  // Filter by tasks if specified
  if (taskIds.length > 0) {
    filtered = filtered.filter(paper => 
      taskIds.some(taskId => paper.task_ids.includes(taskId))
    );
  }
  
  // Filter by search term if specified
  if (searchTerm) {
    filtered = filtered.filter(paper => 
      paper.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      paper.abstract.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }
  
  return filtered;
}

// Usage
const results = filterPapersAdvanced(apiResponse, 'neural network', [1, 2]);
```

## Key Benefits for Frontend

1. **papers_with_tasks**: Each paper includes task information, making it easy to filter
2. **papers_grouped_by_task**: Papers are pre-grouped by task for immediate display
3. **task_lookup**: Quick task information retrieval by ID
4. **task_ids**: Simple array for fast filtering operations
5. **summary**: Overview statistics for UI display

## Performance Tips

- Use `task_ids` array for fast filtering operations
- Use `papers_grouped_by_task` when you need to display papers organized by task
- Use `task_lookup` for quick task information retrieval
- Cache the API response and perform filtering on the client side for better performance 