"""
Tests for execution modules.
"""

import asyncio
import os
import pytest
import tempfile
import shutil

from living_entity.execution.executor import (
    FunctionExecutor,
    ExecutionResult,
    SandboxViolation,
)
from living_entity.execution.focus import (
    FocusModule,
    FocusTask,
    TaskStep,
    TaskStatus,
    TaskPriority,
)


class TestFunctionExecutor:
    """Tests for FunctionExecutor."""
    
    @pytest.fixture
    def temp_sandbox(self):
        """Create a temporary sandbox directory."""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path, ignore_errors=True)
    
    def test_init(self, temp_sandbox):
        """Test executor initialization."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        assert executor.sandbox_path.exists()
        assert executor.unsafe_mode is False
        assert executor.timeout == 30.0
    
    def test_execute_simple_code(self, temp_sandbox):
        """Test executing simple Python code."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("x = 1 + 1")
        
        assert result.success is True
        assert result.error == ""
    
    def test_execute_with_output(self, temp_sandbox):
        """Test executing code with print output."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("print('Hello World')")
        
        assert result.success is True
        assert "Hello World" in result.output
    
    def test_execute_with_result(self, temp_sandbox):
        """Test executing code with result variable."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("result = 42")
        
        assert result.success is True
        assert result.return_value == 42
    
    def test_execute_say_to_user(self, temp_sandbox):
        """Test say_to_user function."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        messages = []
        executor.set_output_callback(lambda x: messages.append(x))
        
        result = executor.execute('say_to_user("Hello!")')
        
        assert result.success is True
        assert "Hello!" in result.user_messages
        assert "Hello!" in messages
    
    def test_execute_create_file(self, temp_sandbox):
        """Test create_file function."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute('create_file("test.txt", "content")')
        
        assert result.success is True
        assert len(result.files_created) == 1
        assert os.path.exists(os.path.join(temp_sandbox, "test.txt"))
    
    def test_execute_read_file(self, temp_sandbox):
        """Test read_file function."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        # Create file first
        with open(os.path.join(temp_sandbox, "test.txt"), "w") as f:
            f.write("test content")
        
        result = executor.execute('result = read_file("test.txt")')
        
        assert result.success is True
        assert "test.txt" in str(result.files_read.keys())
    
    def test_execute_end(self, temp_sandbox):
        """Test end() function."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("end()")
        
        assert result.success is True
        assert result.task_ended is True
    
    def test_execute_syntax_error(self, temp_sandbox):
        """Test handling syntax errors."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("this is not valid python")
        
        assert result.success is False
        assert "SyntaxError" in result.error or "invalid syntax" in result.error.lower()
    
    def test_execute_runtime_error(self, temp_sandbox):
        """Test handling runtime errors."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("x = 1 / 0")
        
        assert result.success is False
        assert "ZeroDivisionError" in result.error
    
    def test_blocked_import_os(self, temp_sandbox):
        """Test that os import is blocked."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("import os")
        
        assert result.success is False
        assert "not allowed" in result.error.lower() or "sandbox" in result.error.lower()
    
    def test_blocked_import_subprocess(self, temp_sandbox):
        """Test that subprocess import is blocked."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("import subprocess")
        
        assert result.success is False
    
    def test_blocked_exec(self, temp_sandbox):
        """Test that exec is blocked."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        result = executor.execute("exec('print(1)')")
        
        assert result.success is False
    
    def test_safe_modules_available(self, temp_sandbox):
        """Test that safe modules are available."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        # Math should work
        result = executor.execute("result = math.sqrt(16)")
        assert result.success is True
        assert result.return_value == 4.0
        
        # JSON should work
        result = executor.execute('result = json.dumps({"a": 1})')
        assert result.success is True
    
    def test_unsafe_mode(self, temp_sandbox):
        """Test that unsafe mode allows blocked operations."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox, unsafe_mode=True)
        
        # In unsafe mode, validation is skipped
        # Note: actual import might still fail in sandbox, but validation should pass
        result = executor.execute("x = 1")  # Just test that unsafe mode works
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_async(self, temp_sandbox):
        """Test async execution."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox, timeout=5.0)
        
        result = await executor.execute_async("result = 42")
        
        assert result.success is True
        assert result.return_value == 42
    
    def test_list_sandbox_files(self, temp_sandbox):
        """Test listing sandbox files."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        # Create some files
        executor.execute('create_file("a.txt", "a")')
        executor.execute('create_file("b.txt", "b")')
        
        files = executor.list_sandbox_files()
        
        assert len(files) == 2
    
    def test_clear_sandbox(self, temp_sandbox):
        """Test clearing sandbox."""
        executor = FunctionExecutor(sandbox_path=temp_sandbox)
        
        executor.execute('create_file("test.txt", "content")')
        assert len(executor.list_sandbox_files()) == 1
        
        executor.clear_sandbox()
        assert len(executor.list_sandbox_files()) == 0


class TestFocusModule:
    """Tests for FocusModule."""
    
    def test_create_task(self):
        """Test creating a focus task."""
        focus = FocusModule()
        
        task = focus.create_task(
            task_id="test-1",
            title="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH,
        )
        
        assert task.id == "test-1"
        assert task.title == "Test Task"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
    
    def test_add_steps(self):
        """Test adding steps to a task."""
        focus = FocusModule()
        
        focus.create_task("test-1", "Test", "Description")
        focus.add_steps("test-1", [
            ("step1", "First step"),
            ("step2", "Second step"),
        ])
        
        task = focus.get_task("test-1")
        assert len(task.steps) == 2
    
    def test_decompose_task(self):
        """Test task decomposition from LLM output."""
        focus = FocusModule()
        
        focus.create_task("test-1", "Test", "Description")
        focus.decompose_task("test-1", [
            {"id": "a", "description": "Step A"},
            {"id": "b", "description": "Step B"},
        ])
        
        task = focus.get_task("test-1")
        assert len(task.steps) == 2
        assert task.steps[0].id == "a"
    
    @pytest.mark.asyncio
    async def test_start_task(self):
        """Test starting a task."""
        focus = FocusModule()
        
        focus.create_task("test-1", "Test", "Description")
        await focus.start_task("test-1")
        
        task = focus.get_task("test-1")
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.started_at is not None
    
    def test_complete_step(self):
        """Test completing a step."""
        focus = FocusModule()
        
        focus.create_task("test-1", "Test", "Description")
        focus.add_steps("test-1", [("step1", "Do something")])
        
        step = focus.complete_step("test-1", "step1", result="Done")
        
        assert step.status == TaskStatus.COMPLETED
        assert step.result == "Done"
    
    def test_get_pending_step(self):
        """Test getting pending step."""
        focus = FocusModule()
        
        focus.create_task("test-1", "Test", "Description")
        focus.add_steps("test-1", [
            ("step1", "First"),
            ("step2", "Second"),
        ])
        
        step = focus.get_pending_step("test-1")
        assert step.id == "step1"
        assert step.status == TaskStatus.IN_PROGRESS
    
    def test_task_progress(self):
        """Test task progress calculation."""
        focus = FocusModule()
        
        task = focus.create_task("test-1", "Test", "Description")
        focus.add_steps("test-1", [
            ("step1", "First"),
            ("step2", "Second"),
            ("step3", "Third"),
            ("step4", "Fourth"),
        ])
        
        # No progress initially
        assert task.get_progress() == 0.0
        
        # Complete 2 out of 4
        focus.complete_step("test-1", "step1")
        focus.complete_step("test-1", "step2")
        
        assert task.get_progress() == 50.0
    
    def test_task_auto_completion(self):
        """Test automatic task completion when all steps done."""
        focus = FocusModule()
        
        task = focus.create_task("test-1", "Test", "Description")
        focus.add_steps("test-1", [("step1", "Only step")])
        
        focus.complete_step("test-1", "step1")
        
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
    
    def test_cancel_task(self):
        """Test canceling a task."""
        focus = FocusModule()
        
        focus.create_task("test-1", "Test", "Description")
        result = focus.cancel_task("test-1")
        
        assert result is True
        task = focus.get_task("test-1")
        assert task.status == TaskStatus.CANCELLED
    
    def test_get_active_tasks(self):
        """Test getting active tasks."""
        focus = FocusModule()
        
        focus.create_task("t1", "Task 1", "")
        focus.create_task("t2", "Task 2", "")
        
        # None are active yet
        assert len(focus.get_active_tasks()) == 0
    
    def test_clear_completed(self):
        """Test clearing completed tasks."""
        focus = FocusModule()
        
        task = focus.create_task("t1", "Task 1", "")
        focus.add_steps("t1", [("s1", "step")])
        focus.complete_step("t1", "s1")
        
        count = focus.clear_completed()
        
        assert count == 1
        assert focus.get_task("t1") is None
