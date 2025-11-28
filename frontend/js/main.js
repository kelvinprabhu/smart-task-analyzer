        let taskQueue = [];
        let currentResults = null;
        let graphDotData = null;

        // Set default date to today
        document.getElementById('dueDate').valueAsDate = new Date();

        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            if (tab === 'form') {
                document.querySelector('.tab-btn:first-child').classList.add('active');
                document.getElementById('form-tab').classList.add('active');
            } else {
                document.querySelector('.tab-btn:last-child').classList.add('active');
                document.getElementById('bulk-tab').classList.add('active');
            }
        }

        function addTask() {
            const title = document.getElementById('title').value;
            const dueDate = document.getElementById('dueDate').value;
            const estimatedHours = parseFloat(document.getElementById('estimatedHours').value);
            const importance = parseInt(document.getElementById('importance').value);
            const depsInput = document.getElementById('dependencies').value;

            const dependencies = depsInput ? depsInput.split(',').map(d => parseInt(d.trim())).filter(d => !isNaN(d)) : [];

            if (!title || !dueDate || isNaN(estimatedHours) || isNaN(importance)) {
                alert('Please fill all required fields');
                return;
            }

            const task = {
                title,
                due_date: dueDate,
                estimated_hours: estimatedHours,
                importance,
                dependencies
            };

            taskQueue.push(task);
            updateTaskQueue();

            // Clear form
            document.getElementById('singleTaskForm').reset();
            document.getElementById('dueDate').valueAsDate = new Date();
        }

        function updateTaskQueue() {
            const queueDiv = document.getElementById('taskQueue');
            if (taskQueue.length === 0) {
                queueDiv.innerHTML = '';
                return;
            }

            queueDiv.innerHTML = `
                <h4 style="margin-bottom: 10px;">Tasks in Queue (${taskQueue.length})</h4>
                ${taskQueue.map((task, index) => `
                    <div style="padding: 8px; background: #f0f0f0; margin-bottom: 5px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
                        <span>${task.title}</span>
                        <button onclick="removeTask(${index})" style="background: #5f282dff; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">Remove</button>
                    </div>
                `).join('')}
            `;
        }

        function removeTask(index) {
            taskQueue.splice(index, 1);
            updateTaskQueue();
        }

        async function analyzeTasks() {
            const apiUrl = document.getElementById('apiUrl').value;
            let tasksToAnalyze = [];

            if (document.getElementById('form-tab').classList.contains('active')) {
                if (taskQueue.length === 0) {
                    alert('Please add at least one task');
                    return;
                }
                tasksToAnalyze = taskQueue;
            } else {
                const bulkJson = document.getElementById('bulkJson').value;
                if (!bulkJson.trim()) {
                    alert('Please paste JSON data');
                    return;
                }
                try {
                    tasksToAnalyze = JSON.parse(bulkJson);
                } catch (e) {
                    alert('Invalid JSON format');
                    return;
                }
            }

            showLoading();

            try {
                const response = await fetch(`${apiUrl}/api/tasks/analyze/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(tasksToAnalyze)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                currentResults = data;
                displayResults(data);
                displayStats(data.stats);
                await loadEisenhowerMatrix();
                await loadDependencyGraph();

                // Clear queue after successful analysis
                taskQueue = [];
                updateTaskQueue();

            } catch (error) {
                showError('Failed to analyze tasks: ' + error.message);
            }
        }

        function showLoading() {
            document.getElementById('results').innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing your tasks...</p>
                </div>
            `;
        }

        function showError(message) {
            document.getElementById('results').innerHTML = `
                <div class="error">
                    <strong>Error:</strong> ${message}
                </div>
            `;
        }

        function displayResults(data) {
            const resultsDiv = document.getElementById('results');

            if (!data.scored_tasks || data.scored_tasks.length === 0) {
                resultsDiv.innerHTML = `
                    <div class="empty-state">
                        <h3>No valid tasks found</h3>
                        <p>Please check your input and try again</p>
                    </div>
                `;
                return;
            }

            const tasksHtml = data.scored_tasks.map(task => {
                const priorityClass = task.score > 0.6 ? 'high-priority' : task.score > 0.3 ? 'medium-priority' : 'low-priority';
                const scoreColor = task.score > 0.6 ? '#5f282dff' : task.score > 0.3 ? '#ffc107' : '#184122ff';

                return `
                    <div class="task-item ${priorityClass}">
                        <div class="task-header">
                            <div>
                                <span class="task-title">${task.title}</span>
                                ${task.blocked ? '<span class="blocked-badge">BLOCKED DUE TO DEPENDENCIES</span>' : ''}
                            </div>
                            <span class="task-score" style="color: ${scoreColor}">${task.score.toFixed(3)}</span>
                        </div>
                        
                        <div class="task-details">
                            <div class="detail-item">
                                <span class="detail-label">Urgency:</span>
                                <span>${task.urgency.toFixed(2)}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Importance:</span>
                                <span>${task.importance.toFixed(2)}</span>
                            </div>
                            <div class="detail-item">
                                <span class="detail-label">Effort:</span>
                                <span>${task.effort_factor.toFixed(2)}</span>
                            </div>
                        </div>

                        ${task.blocked ? `
                            <div style="margin-top: 10px; padding: 8px; background: #fff3cd; border-radius: 4px; font-size: 0.9em;">
                                <strong>Blocked by tasks:</strong> ${task.blocked_by.join(', ')}
                            </div>
                        ` : ''}
                        
                        <div class="task-reason">
                            <div class="reason-title">Priority Explanation:</div>
                            ${generateExplanation(task)}
                        </div>
                    </div>
                `;
            }).join('');

            resultsDiv.innerHTML = tasksHtml;
        }

        function generateExplanation(task) {
            let explanation = [];

            if (task.urgency > 1.5) {
                explanation.push('<strong>High urgency</strong> due to approaching deadline');
            }
            if (task.importance > 0.7) {
                explanation.push('<strong>Very important</strong> task with high business value');
            }
            if (task.effort_factor > 0.5) {
                explanation.push('<strong>Quick win</strong> - low effort required');
            }
            if (task.blocked) {
                explanation.push('Currently blocked by other tasks - complete dependencies first');
            }
            if (!task.blocked && task.score > 0.6) {
                explanation.push('<strong>Top priority</strong> - Start this task immediately!');
            }

            return explanation.length > 0 ? explanation.join('<br>') : 'Standard priority task';
        }

        function displayStats(stats) {
            const statsCard = document.getElementById('statsCard');
            statsCard.style.display = 'block';

            statsCard.innerHTML = `
                <div class="stats-card">
                    <h2>Analysis Statistics</h2>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-value">${stats.total_submitted}</span>
                            <span class="stat-label">Total Submitted</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${stats.valid_tasks}</span>
                            <span class="stat-label">Valid Tasks</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${stats.invalid_tasks}</span>
                            <span class="stat-label">Invalid Tasks</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${stats.blocked_tasks}</span>
                            <span class="stat-label">Blocked Tasks</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${stats.cyclic_tasks}</span>
                            <span class="stat-label">Cyclic Dependencies</span>
                        </div>
                    </div>
                </div>
            `;
        }

        async function loadEisenhowerMatrix() {
            const apiUrl = document.getElementById('apiUrl').value;

            try {
                const response = await fetch(`${apiUrl}/api/tasks/eisenhower/`);
                const data = await response.json();

                displayEisenhowerMatrix(data.matrix);
            } catch (error) {
                console.error('Failed to load Eisenhower matrix:', error);
            }
        }

        function displayEisenhowerMatrix(matrix) {
            const card = document.getElementById('eisenhowerCard');
            const matrixDiv = document.getElementById('eisenhowerMatrix');

            card.style.display = 'block';

            const quadrants = {
                'Do': { tasks: [], color: 'do' },
                'Schedule': { tasks: [], color: 'schedule' },
                'Delegate': { tasks: [], color: 'delegate' },
                'Eliminate': { tasks: [], color: 'eliminate' }
            };

            matrix.forEach(task => {
                if (quadrants[task.quadrant]) {
                    quadrants[task.quadrant].tasks.push(task);
                }
            });

            matrixDiv.innerHTML = Object.entries(quadrants).map(([name, data]) => `
                <div class="quadrant quadrant-${data.color}">
                    <h3>${name} (${data.tasks.length})</h3>
                    ${data.tasks.map(task => `
                        <div class="quadrant-task">
                            <strong>${task.title}</strong>
                            <div style="margin-top: 5px; font-size: 0.85em; color: #666;">
                                Urgency: ${task.urgency.toFixed(2)} | Importance: ${task.importance.toFixed(2)}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `).join('');
        }

        function applySortingStrategy() {
            if (!currentResults) return;

            const strategy = document.getElementById('strategy').value;
            let sortedTasks = [...currentResults.scored_tasks];

            switch (strategy) {
                case 'fastest':
                    sortedTasks.sort((a, b) => b.effort_factor - a.effort_factor);
                    break;
                case 'impact':
                    sortedTasks.sort((a, b) => b.importance - a.importance);
                    break;
                case 'deadline':
                    sortedTasks.sort((a, b) => b.urgency - a.urgency);
                    break;
                case 'smart':
                default:
                    sortedTasks.sort((a, b) => b.score - a.score);
                    break;
            }

            displayResults({ ...currentResults, scored_tasks: sortedTasks });
        }

        async function resetDatabase() {
            if (!confirm('Are you sure you want to reset the database? This will delete all tasks.')) {
                return;
            }

            const apiUrl = document.getElementById('apiUrl').value;

            try {
                const response = await fetch(`${apiUrl}/api/tasks/reset/`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    throw new Error('Failed to reset database');
                }

                alert('Database reset successfully!');

                // Clear UI
                document.getElementById('results').innerHTML = `
                    <div class="empty-state">
                        <h3>Database Reset</h3>
                        <p>All tasks have been cleared</p>
                    </div>
                `;
                document.getElementById('statsCard').style.display = 'none';
                document.getElementById('eisenhowerCard').style.display = 'none';
                currentResults = null;

            } catch (error) {
                alert('Error resetting database: ' + error.message);
            }
        }

        async function loadTopSuggestions() {
            const apiUrl = document.getElementById('apiUrl').value;

            try {
                const response = await fetch(`${apiUrl}/api/tasks/suggest/`);

                if (!response.ok) {
                    throw new Error('Failed to load suggestions');
                }

                const data = await response.json();
                displayTopSuggestions(data);

            } catch (error) {
                alert('Error loading suggestions: ' + error.message);
            }
        }

        function displayTopSuggestions(data) {
            const card = document.getElementById('suggestCard');
            const resultsDiv = document.getElementById('suggestResults');

            card.style.display = 'block';

            if (!data.top_tasks || data.top_tasks.length === 0) {
                resultsDiv.innerHTML = `
                    <div class="empty-state">
                        <h3>No suggestions available</h3>
                        <p>Analyze some tasks first to get recommendations</p>
                    </div>
                `;
                return;
            }

            const suggestionsHtml = data.top_tasks.map((task, index) => {
                const isTopPick = index === 0;
                const rankNum = index + 1;

                return `
                    <div class="suggest-item ${isTopPick ? 'top-pick' : ''}">
                        <div style="display: flex; align-items: center; margin-bottom: 15px;">
                            <span class="suggest-rank">${rankNum}</span>
                            <div style="flex: 1;">
                                <h3 style="margin: 0; color: #333;">${task.title}</h3>
                                <div style="margin-top: 5px; font-size: 0.9em; color: #666;">
                                    Priority Score: <strong style="color: #1b213bff; font-size: 1.2em;">${task.score.toFixed(3)}</strong>
                                    ${task.blocked ? '<span class="blocked-badge" style="margin-left: 10px;">BLOCKED</span>' : '<span style="margin-left: 10px; color: #214d2bff; font-weight: 600;">Ready to Start</span>'}
                                </div>
                            </div>
                        </div>

                        ${task.blocked ? `
                            <div style="padding: 10px; background: #fff3cd; border-radius: 6px; margin-bottom: 15px;">
                                <strong>Blocked by tasks:</strong> ${task.blocked_by.join(', ')}
                            </div>
                        ` : ''}

                        <div class="reason-grid">
                            <div class="reason-metric">
                                <span class="reason-metric-value">${task.reason.urgency.toFixed(2)}</span>
                                <span class="reason-metric-label">Urgency</span>
                            </div>
                            <div class="reason-metric">
                                <span class="reason-metric-value">${task.reason.importance.toFixed(2)}</span>
                                <span class="reason-metric-label">Importance</span>
                            </div>
                            <div class="reason-metric">
                                <span class="reason-metric-value">${task.reason.effort.toFixed(2)}</span>
                                <span class="reason-metric-label">Effort Factor</span>
                            </div>
                            <div class="reason-metric">
                                <span class="reason-metric-value">${task.reason.dependency.toFixed(2)}</span>
                                <span class="reason-metric-label">Dependency</span>
                            </div>
                        </div>

                        ${isTopPick && !task.blocked ? `
                            <div style="margin-top: 15px; padding: 12px; background: linear-gradient(135deg, #194624ff 0%, #094130ff 100%); color: white; border-radius: 8px; text-align: center; font-weight: 600;">
                                RECOMMENDED: Start this task now for maximum productivity!
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');

            resultsDiv.innerHTML = `
                <div style="margin-bottom: 20px; padding: 15px; background: #e8f4f8; border-radius: 8px; border-left: 4px solid #1b213bff;">
                    <strong>Analysis Summary:</strong> ${data.total_available} tasks analyzed
                    ${data.cyclic_task_ids && data.cyclic_task_ids.length > 0 ? `<br><span style="color: #532327ff;">${data.cyclic_task_ids.length} cyclic dependencies detected: ${data.cyclic_task_ids.join(', ')}</span>` : ''}
                </div>
                ${suggestionsHtml}
            `;
        }

        async function loadDependencyGraph() {
            const apiUrl = document.getElementById('apiUrl').value;

            try {
                const response = await fetch(`${apiUrl}/api/tasks/list/`);

                if (!response.ok) {
                    throw new Error('Failed to load task list for graph');
                }

                const data = await response.json();

                // Generate DOT format from task list
                graphDotData = generateDotFromTasks(data.tasks);
                displayDependencyGraph();

            } catch (error) {
                console.error('Error loading dependency graph:', error);
            }
        }

        function generateDotFromTasks(tasks) {
            let dot = 'digraph {\n';
            dot += '  rankdir=TB;\n';
            dot += '  node [shape=box, style="rounded,filled", fillcolor="#e8f4f8", fontname="Arial"];\n';
            dot += '  edge [color="#1b213bff", penwidth=2];\n\n';

            tasks.forEach(task => {
                const label = task.title.replace(/"/g, '\\"');
                dot += `  ${task.id} [label="${label}"];\n`;
            });

            dot += '\n';

            tasks.forEach(task => {
                if (task.dependencies && task.dependencies.length > 0) {
                    task.dependencies.forEach(depId => {
                        dot += `  ${depId} -> ${task.id};\n`;
                    });
                }
            });

            dot += '}\n';
            return dot;
        }

        function displayDependencyGraph() {
            const card = document.getElementById('graphCard');
            const dotSource = document.getElementById('dotSource');

            card.style.display = 'block';

            if (graphDotData) {
                dotSource.textContent = graphDotData;
            }
        }

        function renderGraph() {
            const viz = document.getElementById('graphVisualization');

            if (!graphDotData) {
                viz.innerHTML = '<p style="text-align: center; color: #5f282dff;">No graph data available. Please analyze tasks first.</p>';
                return;
            }

            viz.innerHTML = '<div style="text-align: center; padding: 40px;"><div class="spinner" style="margin: 0 auto 20px;"></div><p>Rendering graph visualization...</p></div>';

            // Try to use Viz.js if available, otherwise show instructions
            if (typeof Viz !== 'undefined') {
                try {
                    const viz = new Viz();
                    viz.renderSVGElement(graphDotData)
                        .then(element => {
                            const container = document.getElementById('graphVisualization');
                            container.innerHTML = '';
                            container.appendChild(element);
                        })
                        .catch(error => {
                            showGraphError(error);
                        });
                } catch (error) {
                    showGraphError(error);
                }
            } else {
                // Show alternative visualization using simple HTML/CSS
                renderSimpleGraph();
            }
        }

        function renderSimpleGraph() {
            const viz = document.getElementById('graphVisualization');

            viz.innerHTML = `
                <div style="text-align: center; padding: 20px;">
                    <h3 style="color: #1b213bff; margin-bottom: 15px;">Simplified Dependency View</h3>
                    <p style="color: #666; margin-bottom: 20px;">For full graph visualization, use the DOT format below with Graphviz Online:</p>
                    <a href="https://dreampuf.github.io/GraphvizOnline/" target="_blank" class="btn btn-primary" style="display: inline-block; text-decoration: none;">
                        Open Graphviz Online Viewer
                    </a>
                    <p style="color: #666; margin-top: 15px; font-size: 0.9em;">Copy the DOT format below and paste it in the online viewer</p>
                </div>
            `;
        }

        function showGraphError(error) {
            const viz = document.getElementById('graphVisualization');
            viz.innerHTML = `
                <div style="padding: 20px; text-align: center;">
                    <p style="color: #5f282dff; margin-bottom: 15px;">Could not render graph: ${error.message}</p>
                    <p style="color: #666; margin-bottom: 15px;">Use an external tool to visualize the DOT format:</p>
                    <a href="https://dreampuf.github.io/GraphvizOnline/" target="_blank" class="btn btn-primary" style="display: inline-block; text-decoration: none;">
                        Open Graphviz Online Viewer
                    </a>
                </div>
            `;
        }

        function downloadGraphDot() {
            if (!graphDotData) {
                alert('No graph data available. Please analyze tasks first.');
                return;
            }

            const blob = new Blob([graphDotData], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'dependency_graph.dot';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }