Start new task by retrieving a new step via calling get_next_step using MCP tool "step_orchestrator".
Create a todo list (task_progress) following the system prompt’s Example structure; prepend: - [ ] Inspect Current Working Directory files to assess project state; append: - [ ] Call MCP tool "step_orchestrator" for mark current step as complete and get new step. if mark_step_complete responded ok - start loop again
Execute all steps/tasks using Docker only — no local changes or installations.
Call get_step_task, agent task is never completed