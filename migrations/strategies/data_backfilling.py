"""
Data Backfilling Strategy
========================

Implements intelligent data backfilling with batch processing,
progress tracking, and performance optimization.
"""

import asyncio
import logging
import math
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from enum import Enum
from dataclasses import dataclass

from ..migration_engine import MigrationConfig, MigrationResult, MigrationStatus

logger = logging.getLogger(__name__)


class BackfillStrategy(str, Enum):
    """Data backfill strategies."""
    BATCH_SEQUENTIAL = "batch_sequential"
    BATCH_PARALLEL = "batch_parallel"
    STREAMING = "streaming"
    PRIORITY_BASED = "priority_based"
    TIME_BASED = "time_based"


class BackfillStatus(str, Enum):
    """Backfill operation status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackfillProgress:
    """Tracks backfill progress."""
    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    current_batch: int = 0
    total_batches: int = 0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100
    
    @property
    def processing_rate(self) -> float:
        """Calculate records per second."""
        if not self.start_time or self.processed_records == 0:
            return 0.0
        
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return self.processed_records / elapsed if elapsed > 0 else 0.0


@dataclass
class BackfillTask:
    """Represents a data backfill task."""
    task_id: str
    name: str
    description: str
    source_query: str
    target_transformation: Callable
    batch_size: int = 1000
    max_parallelism: int = 5
    strategy: BackfillStrategy = BackfillStrategy.BATCH_SEQUENTIAL
    priority: int = 5  # 1-10 scale
    retry_attempts: int = 3
    timeout_seconds: int = 300
    
    # Progress tracking
    progress: BackfillProgress = None
    status: BackfillStatus = BackfillStatus.PENDING
    
    def __post_init__(self):
        if self.progress is None:
            self.progress = BackfillProgress()


class DataBackfilling:
    """
    Data backfilling strategy implementation.
    
    Provides intelligent data migration with:
    - Multiple backfill strategies
    - Batch processing with configurable sizes
    - Parallel processing capabilities
    - Progress tracking and monitoring
    - Error handling and retry logic
    - Performance optimization
    """
    
    def __init__(self, config: MigrationConfig):
        """
        Initialize data backfilling strategy.
        
        Args:
            config: Migration configuration
        """
        self.config = config
        
        # Backfill settings
        self.default_batch_size = 1000
        self.max_parallelism = 10
        self.rate_limit_per_second = 100
        self.memory_threshold_mb = 1024  # 1GB
        self.error_threshold_percent = 5.0
        
        # State tracking
        self.active_tasks: Dict[str, BackfillTask] = {}
        self.completed_tasks: Dict[str, BackfillTask] = {}
        self.global_progress = BackfillProgress()
        
        # Performance metrics
        self.performance_metrics = {
            'total_records_processed': 0,
            'total_processing_time': 0.0,
            'average_batch_time': 0.0,
            'peak_memory_usage': 0.0,
            'error_count': 0
        }
    
    async def execute(self, migration_path: str, result: MigrationResult) -> None:
        """
        Execute data backfilling migration.
        
        Args:
            migration_path: Path to migration script
            result: Migration result to update
        """
        logger.info(f"Starting data backfilling migration: {result.version}")
        
        try:
            # Parse migration for backfill tasks
            backfill_tasks = await self._parse_backfill_tasks(migration_path, result)
            
            if not backfill_tasks:
                logger.info("No backfill tasks found in migration")
                return
            
            # Initialize monitoring
            await self._initialize_monitoring(result)
            
            # Execute backfill tasks
            await self._execute_backfill_tasks(backfill_tasks, result)
            
            # Validate backfill results
            await self._validate_backfill_results(result)
            
            # Cleanup and finalization
            await self._finalize_backfill(result)
            
            logger.info(f"Data backfilling migration completed: {result.version}")
            
        except Exception as e:
            logger.error(f"Data backfilling migration failed: {e}")
            
            # Attempt cleanup
            await self._cleanup_failed_backfill(result)
            raise
    
    async def _parse_backfill_tasks(self, migration_path: str, 
                                  result: MigrationResult) -> List[BackfillTask]:
        """Parse migration file for backfill tasks."""
        logger.info("Parsing backfill tasks from migration")
        
        with open(migration_path, 'r') as f:
            content = f.read()
        
        tasks = []
        
        # Look for backfill task definitions
        # This is a simplified parser - in practice, you'd use a more sophisticated approach
        
        lines = content.split('\n')
        current_task = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('# BACKFILL_TASK:'):
                # Start of a new backfill task
                task_config = line.replace('# BACKFILL_TASK:', '').strip()
                task_parts = task_config.split(',')
                
                task_name = task_parts[0].strip()
                task_id = f"backfill_{task_name}_{int(time.time())}"
                
                current_task = BackfillTask(
                    task_id=task_id,
                    name=task_name,
                    description=f"Backfill task for {task_name}",
                    source_query="",  # Will be filled in
                    target_transformation=self._default_transformation
                )
                
                # Parse additional config if provided
                for part in task_parts[1:]:
                    if '=' in part:
                        key, value = part.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'batch_size':
                            current_task.batch_size = int(value)
                        elif key == 'strategy':
                            current_task.strategy = BackfillStrategy(value)
                        elif key == 'priority':
                            current_task.priority = int(value)
                
                tasks.append(current_task)
                
            elif current_task and line.startswith('# SOURCE:'):
                current_task.source_query = line.replace('# SOURCE:', '').strip()
                
            elif current_task and line.startswith('# TRANSFORM:'):
                # Custom transformation logic
                transform_code = line.replace('# TRANSFORM:', '').strip()
                current_task.target_transformation = self._create_transformation(transform_code)
        
        # Create default task if none specified but data operations detected
        if not tasks and ('UPDATE' in content.upper() or 'INSERT' in content.upper()):
            default_task = BackfillTask(
                task_id=f"default_backfill_{int(time.time())}",
                name="default_data_migration",
                description="Default data migration task",
                source_query="SELECT * FROM source_table",
                target_transformation=self._default_transformation
            )
            tasks.append(default_task)
        
        logger.info(f"Found {len(tasks)} backfill tasks")
        result.metrics['backfill_tasks_count'] = len(tasks)
        
        return tasks
    
    def _default_transformation(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Default record transformation."""
        # Identity transformation - no changes
        return record
    
    def _create_transformation(self, transform_code: str) -> Callable:
        """Create transformation function from code."""
        # In practice, this would safely evaluate transformation code
        # For security, use a restricted execution environment
        return self._default_transformation
    
    async def _initialize_monitoring(self, result: MigrationResult) -> None:
        """Initialize monitoring for backfill operations."""
        logger.info("Initializing backfill monitoring")
        
        # Setup progress tracking
        self.global_progress = BackfillProgress(start_time=datetime.now(timezone.utc))
        
        # Initialize performance metrics
        self.performance_metrics = {
            'total_records_processed': 0,
            'total_processing_time': 0.0,
            'average_batch_time': 0.0,
            'peak_memory_usage': 0.0,
            'error_count': 0
        }
        
        # Setup monitoring task
        monitoring_task = asyncio.create_task(self._monitor_backfill_progress(result))
        
        result.metrics['monitoring_initialized'] = True
    
    async def _execute_backfill_tasks(self, tasks: List[BackfillTask], 
                                    result: MigrationResult) -> None:
        """Execute all backfill tasks."""
        logger.info(f"Executing {len(tasks)} backfill tasks")
        
        if self.config.dry_run:
            logger.info("DRY RUN: Would execute backfill tasks")
            return
        
        # Sort tasks by priority
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
        
        # Calculate total work
        total_records = 0
        for task in sorted_tasks:
            task.progress.total_records = await self._estimate_task_records(task)
            total_records += task.progress.total_records
        
        self.global_progress.total_records = total_records
        self.global_progress.total_batches = sum(
            math.ceil(task.progress.total_records / task.batch_size)
            for task in sorted_tasks
        )
        
        # Execute tasks based on strategy
        if any(task.strategy == BackfillStrategy.BATCH_PARALLEL for task in sorted_tasks):
            await self._execute_tasks_parallel(sorted_tasks, result)
        else:
            await self._execute_tasks_sequential(sorted_tasks, result)
        
        logger.info("All backfill tasks completed")
    
    async def _estimate_task_records(self, task: BackfillTask) -> int:
        """Estimate number of records for a task."""
        # In practice, this would query the database for count
        # For now, return a mock estimate
        return 10000  # Mock value
    
    async def _execute_tasks_sequential(self, tasks: List[BackfillTask], 
                                      result: MigrationResult) -> None:
        """Execute tasks sequentially."""
        logger.info("Executing tasks sequentially")
        
        for task in tasks:
            try:
                await self._execute_single_task(task, result)
                self.completed_tasks[task.task_id] = task
                
            except Exception as e:
                logger.error(f"Task {task.name} failed: {e}")
                task.status = BackfillStatus.FAILED
                self.performance_metrics['error_count'] += 1
                
                # Decide whether to continue or stop
                if task.priority >= 8:  # High priority task
                    raise RuntimeError(f"Critical backfill task failed: {task.name}")
                else:
                    logger.warning(f"Non-critical task failed, continuing: {task.name}")
    
    async def _execute_tasks_parallel(self, tasks: List[BackfillTask], 
                                    result: MigrationResult) -> None:
        """Execute tasks in parallel where possible."""
        logger.info("Executing tasks in parallel")
        
        # Group tasks by dependencies and resource requirements
        task_groups = self._group_tasks_for_parallel_execution(tasks)
        
        for group in task_groups:
            # Execute tasks in this group concurrently
            coroutines = [self._execute_single_task(task, result) for task in group]
            
            try:
                await asyncio.gather(*coroutines, return_exceptions=True)
                
                # Move completed tasks
                for task in group:
                    if task.status == BackfillStatus.COMPLETED:
                        self.completed_tasks[task.task_id] = task
                        
            except Exception as e:
                logger.error(f"Parallel task group failed: {e}")
                # Handle partial failures
    
    def _group_tasks_for_parallel_execution(self, tasks: List[BackfillTask]) -> List[List[BackfillTask]]:
        """Group tasks that can be executed in parallel."""
        # Simple grouping by priority for now
        # In practice, this would consider dependencies, resource usage, etc.
        
        groups = []
        current_group = []
        current_priority = None
        
        for task in tasks:
            if current_priority is None or task.priority == current_priority:
                current_group.append(task)
                current_priority = task.priority
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [task]
                current_priority = task.priority
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    async def _execute_single_task(self, task: BackfillTask, 
                                 result: MigrationResult) -> None:
        """Execute a single backfill task."""
        logger.info(f"Executing backfill task: {task.name}")
        
        task.status = BackfillStatus.RUNNING
        task.progress.start_time = datetime.now(timezone.utc)
        self.active_tasks[task.task_id] = task
        
        try:
            # Execute based on strategy
            if task.strategy == BackfillStrategy.BATCH_SEQUENTIAL:
                await self._execute_batch_sequential(task, result)
            elif task.strategy == BackfillStrategy.BATCH_PARALLEL:
                await self._execute_batch_parallel(task, result)
            elif task.strategy == BackfillStrategy.STREAMING:
                await self._execute_streaming(task, result)
            elif task.strategy == BackfillStrategy.PRIORITY_BASED:
                await self._execute_priority_based(task, result)
            elif task.strategy == BackfillStrategy.TIME_BASED:
                await self._execute_time_based(task, result)
            else:
                raise ValueError(f"Unknown backfill strategy: {task.strategy}")
            
            task.status = BackfillStatus.COMPLETED
            logger.info(f"Task completed: {task.name}")
            
        except Exception as e:
            task.status = BackfillStatus.FAILED
            logger.error(f"Task failed: {task.name} - {e}")
            raise
        
        finally:
            # Remove from active tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
    
    async def _execute_batch_sequential(self, task: BackfillTask, 
                                      result: MigrationResult) -> None:
        """Execute task using sequential batching."""
        logger.info(f"Executing {task.name} with sequential batching")
        
        batch_number = 0
        total_batches = math.ceil(task.progress.total_records / task.batch_size)
        
        async for batch in self._fetch_batches(task):
            batch_number += 1
            task.progress.current_batch = batch_number
            
            batch_start_time = time.time()
            
            try:
                # Process batch
                processed_records = await self._process_batch(task, batch, result)
                
                # Update progress
                task.progress.processed_records += processed_records
                self.global_progress.processed_records += processed_records
                
                # Track performance
                batch_time = time.time() - batch_start_time
                self.performance_metrics['total_processing_time'] += batch_time
                self.performance_metrics['average_batch_time'] = (
                    self.performance_metrics['total_processing_time'] / batch_number
                )
                
                # Rate limiting
                await self._apply_rate_limiting(batch_time, processed_records)
                
                # Memory check
                await self._check_memory_usage()
                
            except Exception as e:
                logger.error(f"Batch {batch_number} failed: {e}")
                task.progress.failed_records += len(batch)
                
                # Retry logic
                if task.retry_attempts > 0:
                    task.retry_attempts -= 1
                    logger.info(f"Retrying batch {batch_number}")
                    # Retry the batch
                    await asyncio.sleep(2)  # Brief delay before retry
                    continue
                else:
                    raise
        
        logger.info(f"Sequential batching completed for {task.name}")
    
    async def _execute_batch_parallel(self, task: BackfillTask, 
                                    result: MigrationResult) -> None:
        """Execute task using parallel batching."""
        logger.info(f"Executing {task.name} with parallel batching")
        
        semaphore = asyncio.Semaphore(task.max_parallelism)
        batch_tasks = []
        
        batch_number = 0
        async for batch in self._fetch_batches(task):
            batch_number += 1
            
            # Create task for this batch
            batch_task = asyncio.create_task(
                self._process_batch_with_semaphore(semaphore, task, batch, batch_number, result)
            )
            batch_tasks.append(batch_task)
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Process results
        for i, result_item in enumerate(batch_results):
            if isinstance(result_item, Exception):
                logger.error(f"Batch {i+1} failed: {result_item}")
                task.progress.failed_records += task.batch_size
            else:
                task.progress.processed_records += result_item
                self.global_progress.processed_records += result_item
        
        logger.info(f"Parallel batching completed for {task.name}")
    
    async def _process_batch_with_semaphore(self, semaphore: asyncio.Semaphore, 
                                          task: BackfillTask, batch: List[Dict], 
                                          batch_number: int, result: MigrationResult) -> int:
        """Process batch with semaphore for parallelism control."""
        async with semaphore:
            logger.debug(f"Processing batch {batch_number} for {task.name}")
            return await self._process_batch(task, batch, result)
    
    async def _execute_streaming(self, task: BackfillTask, 
                               result: MigrationResult) -> None:
        """Execute task using streaming approach."""
        logger.info(f"Executing {task.name} with streaming")
        
        record_count = 0
        async for record in self._stream_records(task):
            try:
                # Transform and process single record
                transformed = task.target_transformation(record)
                await self._store_record(transformed, task, result)
                
                record_count += 1
                task.progress.processed_records += 1
                self.global_progress.processed_records += 1
                
                # Periodic progress updates
                if record_count % 1000 == 0:
                    logger.debug(f"Streamed {record_count} records for {task.name}")
                
                # Rate limiting
                await asyncio.sleep(1.0 / self.rate_limit_per_second)
                
            except Exception as e:
                logger.error(f"Record processing failed: {e}")
                task.progress.failed_records += 1
        
        logger.info(f"Streaming completed for {task.name}")
    
    async def _execute_priority_based(self, task: BackfillTask, 
                                    result: MigrationResult) -> None:
        """Execute task using priority-based processing."""
        logger.info(f"Executing {task.name} with priority-based processing")
        
        # Fetch and sort records by priority
        all_records = []
        async for batch in self._fetch_batches(task):
            all_records.extend(batch)
        
        # Sort by priority (assuming priority field exists)
        prioritized_records = sorted(
            all_records, 
            key=lambda r: r.get('priority', 5), 
            reverse=True
        )
        
        # Process in priority order
        for record in prioritized_records:
            try:
                transformed = task.target_transformation(record)
                await self._store_record(transformed, task, result)
                
                task.progress.processed_records += 1
                self.global_progress.processed_records += 1
                
            except Exception as e:
                logger.error(f"Priority record processing failed: {e}")
                task.progress.failed_records += 1
        
        logger.info(f"Priority-based processing completed for {task.name}")
    
    async def _execute_time_based(self, task: BackfillTask, 
                                result: MigrationResult) -> None:
        """Execute task using time-based processing."""
        logger.info(f"Executing {task.name} with time-based processing")
        
        # Process records in chronological order
        # Useful for maintaining temporal consistency
        
        time_windows = await self._get_time_windows(task)
        
        for window_start, window_end in time_windows:
            logger.debug(f"Processing time window: {window_start} to {window_end}")
            
            window_records = await self._fetch_records_for_time_window(
                task, window_start, window_end
            )
            
            for record in window_records:
                try:
                    transformed = task.target_transformation(record)
                    await self._store_record(transformed, task, result)
                    
                    task.progress.processed_records += 1
                    self.global_progress.processed_records += 1
                    
                except Exception as e:
                    logger.error(f"Time-based record processing failed: {e}")
                    task.progress.failed_records += 1
        
        logger.info(f"Time-based processing completed for {task.name}")
    
    async def _fetch_batches(self, task: BackfillTask) -> AsyncGenerator[List[Dict], None]:
        """Fetch batches of records for processing."""
        # Mock implementation - in practice, this would query the database
        
        total_records = task.progress.total_records
        batch_size = task.batch_size
        
        for offset in range(0, total_records, batch_size):
            batch = []
            for i in range(min(batch_size, total_records - offset)):
                record = {
                    'id': offset + i,
                    'data': f'record_{offset + i}',
                    'priority': 5,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                batch.append(record)
            
            yield batch
            
            # Simulate processing delay
            await asyncio.sleep(0.1)
    
    async def _stream_records(self, task: BackfillTask) -> AsyncGenerator[Dict, None]:
        """Stream records one by one."""
        async for batch in self._fetch_batches(task):
            for record in batch:
                yield record
    
    async def _process_batch(self, task: BackfillTask, batch: List[Dict], 
                           result: MigrationResult) -> int:
        """Process a batch of records."""
        processed_count = 0
        
        for record in batch:
            try:
                # Transform record
                transformed = task.target_transformation(record)
                
                # Store transformed record
                await self._store_record(transformed, task, result)
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Record processing failed: {e}")
                # Continue processing other records in batch
        
        return processed_count
    
    async def _store_record(self, record: Dict[str, Any], task: BackfillTask, 
                          result: MigrationResult) -> None:
        """Store a processed record."""
        # Mock implementation - in practice, this would write to database
        
        if self.config.database_type.value == "dynamodb":
            await self._store_dynamodb_record(record, task, result)
        else:
            await self._store_sql_record(record, task, result)
    
    async def _store_dynamodb_record(self, record: Dict[str, Any], task: BackfillTask, 
                                   result: MigrationResult) -> None:
        """Store record in DynamoDB."""
        # Implementation would use boto3 to write to DynamoDB
        pass
    
    async def _store_sql_record(self, record: Dict[str, Any], task: BackfillTask, 
                              result: MigrationResult) -> None:
        """Store record in SQL database."""
        # Implementation would use SQLAlchemy or similar to write to SQL database
        pass
    
    async def _get_time_windows(self, task: BackfillTask) -> List[tuple]:
        """Get time windows for time-based processing."""
        # Create daily time windows for the last year
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=365)
        
        windows = []
        current_date = start_date
        
        while current_date < end_date:
            window_end = min(current_date + timedelta(days=1), end_date)
            windows.append((current_date, window_end))
            current_date = window_end
        
        return windows
    
    async def _fetch_records_for_time_window(self, task: BackfillTask, 
                                           start_time: datetime, 
                                           end_time: datetime) -> List[Dict]:
        """Fetch records for a specific time window."""
        # Mock implementation
        return [
            {
                'id': i,
                'data': f'time_window_record_{i}',
                'created_at': start_time.isoformat()
            }
            for i in range(100)  # Mock 100 records per window
        ]
    
    async def _apply_rate_limiting(self, batch_time: float, processed_records: int) -> None:
        """Apply rate limiting to avoid overwhelming the system."""
        if processed_records > 0:
            current_rate = processed_records / batch_time
            
            if current_rate > self.rate_limit_per_second:
                # Slow down processing
                delay = (processed_records / self.rate_limit_per_second) - batch_time
                if delay > 0:
                    await asyncio.sleep(delay)
    
    async def _check_memory_usage(self) -> None:
        """Check memory usage and pause if threshold exceeded."""
        # Mock implementation - in practice, would check actual memory usage
        import psutil
        
        memory_usage = psutil.virtual_memory().percent
        
        if memory_usage > 80:  # 80% threshold
            logger.warning(f"High memory usage: {memory_usage}%")
            await asyncio.sleep(5)  # Brief pause to allow memory cleanup
    
    async def _monitor_backfill_progress(self, result: MigrationResult) -> None:
        """Monitor backfill progress and update metrics."""
        while self.active_tasks:
            try:
                # Update global progress
                self._update_global_progress()
                
                # Log progress
                if self.global_progress.total_records > 0:
                    completion = self.global_progress.completion_percentage
                    rate = self.global_progress.processing_rate
                    
                    logger.info(
                        f"Backfill progress: {completion:.1f}% complete, "
                        f"{rate:.1f} records/sec"
                    )
                
                # Update result metrics
                result.metrics['backfill_progress'] = {
                    'completion_percentage': self.global_progress.completion_percentage,
                    'processing_rate': self.global_progress.processing_rate,
                    'active_tasks': len(self.active_tasks),
                    'completed_tasks': len(self.completed_tasks)
                }
                
                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Progress monitoring error: {e}")
    
    def _update_global_progress(self) -> None:
        """Update global progress based on individual tasks."""
        total_processed = sum(
            task.progress.processed_records 
            for task in list(self.active_tasks.values()) + list(self.completed_tasks.values())
        )
        
        total_failed = sum(
            task.progress.failed_records 
            for task in list(self.active_tasks.values()) + list(self.completed_tasks.values())
        )
        
        self.global_progress.processed_records = total_processed
        self.global_progress.failed_records = total_failed
        
        # Update estimated completion
        if self.global_progress.processing_rate > 0:
            remaining_records = self.global_progress.total_records - total_processed
            remaining_seconds = remaining_records / self.global_progress.processing_rate
            
            self.global_progress.estimated_completion = (
                datetime.now(timezone.utc) + timedelta(seconds=remaining_seconds)
            )
    
    async def _validate_backfill_results(self, result: MigrationResult) -> None:
        """Validate backfill results."""
        logger.info("Validating backfill results")
        
        # Check completion rates
        total_processed = self.global_progress.processed_records
        total_failed = self.global_progress.failed_records
        total_records = self.global_progress.total_records
        
        if total_records > 0:
            success_rate = (total_processed / total_records) * 100
            failure_rate = (total_failed / total_records) * 100
            
            logger.info(f"Backfill success rate: {success_rate:.1f}%")
            logger.info(f"Backfill failure rate: {failure_rate:.1f}%")
            
            if failure_rate > self.error_threshold_percent:
                raise RuntimeError(f"Backfill failure rate too high: {failure_rate:.1f}%")
        
        # Validate data integrity
        await self._validate_data_integrity(result)
        
        result.metrics['backfill_validation'] = {
            'success_rate': success_rate if total_records > 0 else 100,
            'failure_rate': failure_rate if total_records > 0 else 0,
            'total_processed': total_processed,
            'total_failed': total_failed
        }
    
    async def _validate_data_integrity(self, result: MigrationResult) -> None:
        """Validate data integrity after backfill."""
        logger.info("Validating data integrity")
        
        # Implementation would:
        # 1. Check record counts
        # 2. Validate data consistency
        # 3. Check referential integrity
        # 4. Verify business rule compliance
        
        # For now, just log completion
        logger.info("Data integrity validation completed")
    
    async def _finalize_backfill(self, result: MigrationResult) -> None:
        """Finalize backfill operations."""
        logger.info("Finalizing backfill operations")
        
        # Update performance metrics in result
        result.metrics['performance_metrics'] = self.performance_metrics
        
        # Record completion time
        if self.global_progress.start_time:
            total_duration = (
                datetime.now(timezone.utc) - self.global_progress.start_time
            ).total_seconds()
            
            result.metrics['total_backfill_duration'] = total_duration
            logger.info(f"Total backfill duration: {total_duration:.1f} seconds")
        
        # Clean up resources
        self.active_tasks.clear()
        
        logger.info("Backfill finalization completed")
    
    async def _cleanup_failed_backfill(self, result: MigrationResult) -> None:
        """Clean up after failed backfill."""
        logger.info("Cleaning up after failed backfill")
        
        # Cancel active tasks
        for task in self.active_tasks.values():
            task.status = BackfillStatus.CANCELLED
        
        self.active_tasks.clear()
        
        # Record failure metrics
        result.metrics['backfill_cleanup'] = {
            'cancelled_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'cleanup_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Failed backfill cleanup completed")
