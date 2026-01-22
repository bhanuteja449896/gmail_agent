"""Event-driven architecture and pub/sub messaging system."""

import logging
from typing import Any, Dict, List, Optional, Callable, Set
from enum import Enum
from dataclasses import dataclass, field as dataclass_field
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import uuid
import threading
import queue
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types."""
    EMAIL_RECEIVED = "email.received"
    EMAIL_PROCESSED = "email.processed"
    EMAIL_ARCHIVED = "email.archived"
    EMAIL_DELETED = "email.deleted"
    EMAIL_CLASSIFIED = "email.classified"
    FILTER_APPLIED = "filter.applied"
    RULE_TRIGGERED = "rule.triggered"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"
    NOTIFICATION_SENT = "notification.sent"
    ALERT_TRIGGERED = "alert.triggered"
    SYSTEM_HEALTH_CHECK = "system.health_check"


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """Event object."""
    event_type: EventType
    source: str
    data: Dict[str, Any] = dataclass_field(default_factory=dict)
    priority: EventPriority = EventPriority.MEDIUM
    timestamp: datetime = dataclass_field(default_factory=datetime.now)
    event_id: str = dataclass_field(default_factory=lambda: str(uuid.uuid4()))
    parent_event_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = dataclass_field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "priority": self.priority.name,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }


class EventHandler(ABC):
    """Abstract event handler."""
    
    @abstractmethod
    def can_handle(self, event: Event) -> bool:
        """Check if handler can handle event."""
        pass
    
    @abstractmethod
    def handle(self, event: Event) -> bool:
        """Handle event."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get handler priority."""
        pass


class EventListener:
    """Event listener."""
    
    def __init__(self, name: str, callback: Callable, event_types: List[EventType] = None):
        """Initialize listener."""
        self.name = name
        self.callback = callback
        self.event_types = event_types or []
        self.listener_id = str(uuid.uuid4())
        self.enabled = True
        self.invocation_count = 0
        self.last_invocation = None
        self.error_count = 0
    
    def matches(self, event: Event) -> bool:
        """Check if listener matches event."""
        if not self.enabled:
            return False
        if not self.event_types:
            return True
        return event.event_type in self.event_types
    
    async def invoke(self, event: Event) -> bool:
        """Invoke listener."""
        try:
            self.callback(event)
            self.invocation_count += 1
            self.last_invocation = datetime.now()
            return True
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error in listener {self.name}: {e}")
            return False


@dataclass
class EventFilter:
    """Filter events."""
    event_types: Set[EventType] = dataclass_field(default_factory=set)
    sources: Set[str] = dataclass_field(default_factory=set)
    min_priority: EventPriority = EventPriority.LOW
    max_age_seconds: Optional[int] = None
    
    def matches(self, event: Event) -> bool:
        """Check if event matches filter."""
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        if self.sources and event.source not in self.sources:
            return False
        
        if event.priority.value < self.min_priority.value:
            return False
        
        if self.max_age_seconds:
            age = (datetime.now() - event.timestamp).total_seconds()
            if age > self.max_age_seconds:
                return False
        
        return True


@dataclass
class EventTransformer:
    """Transform events."""
    
    def transform(self, event: Event) -> Event:
        """Transform event."""
        return event
    
    def enrich(self, event: Event, enrichment: Dict[str, Any]) -> Event:
        """Enrich event with additional data."""
        event.data.update(enrichment)
        return event


class EventBus:
    """Central event bus for pub/sub."""
    
    def __init__(self, max_queue_size: int = 10000):
        """Initialize event bus."""
        self.listeners: Dict[EventType, List[EventListener]] = defaultdict(list)
        self.global_listeners: List[EventListener] = []
        self.handlers: List[EventHandler] = []
        self.event_history: List[Event] = []
        self.max_history_size = 1000
        self.event_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.filters: List[EventFilter] = []
        self.transformers: List[EventTransformer] = []
        self.event_stats: Dict[EventType, int] = defaultdict(int)
        self.lock = threading.RLock()
    
    def subscribe(self, listener: EventListener, event_type: EventType = None) -> str:
        """Subscribe listener to events."""
        with self.lock:
            if event_type:
                self.listeners[event_type].append(listener)
            else:
                self.global_listeners.append(listener)
            
            logger.info(f"Subscribed listener {listener.name}")
            return listener.listener_id
    
    def unsubscribe(self, listener_id: str) -> bool:
        """Unsubscribe listener."""
        with self.lock:
            for event_type in self.listeners:
                for listener in self.listeners[event_type]:
                    if listener.listener_id == listener_id:
                        self.listeners[event_type].remove(listener)
                        logger.info(f"Unsubscribed listener {listener.name}")
                        return True
            
            for listener in self.global_listeners:
                if listener.listener_id == listener_id:
                    self.global_listeners.remove(listener)
                    return True
            
            return False
    
    def register_handler(self, handler: EventHandler) -> None:
        """Register event handler."""
        with self.lock:
            self.handlers.append(handler)
            self.handlers.sort(key=lambda h: h.get_priority(), reverse=True)
            logger.info(f"Registered event handler")
    
    def add_filter(self, event_filter: EventFilter) -> None:
        """Add event filter."""
        with self.lock:
            self.filters.append(event_filter)
    
    def add_transformer(self, transformer: EventTransformer) -> None:
        """Add event transformer."""
        with self.lock:
            self.transformers.append(transformer)
    
    def publish(self, event: Event) -> bool:
        """Publish event."""
        try:
            with self.lock:
                # Apply filters
                if not self._apply_filters(event):
                    logger.debug(f"Event {event.event_id} filtered out")
                    return False
                
                # Apply transformers
                for transformer in self.transformers:
                    event = transformer.transform(event)
                
                # Record event
                self.event_history.append(event)
                if len(self.event_history) > self.max_history_size:
                    self.event_history.pop(0)
                
                self.event_stats[event.event_type] += 1
                
                # Enqueue event
                self.event_queue.put(event)
                
                logger.info(f"Published event {event.event_id}: {event.event_type.value}")
                return True
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            return False
    
    def _apply_filters(self, event: Event) -> bool:
        """Apply filters to event."""
        for event_filter in self.filters:
            if not event_filter.matches(event):
                return False
        return True
    
    def process_events(self) -> None:
        """Process events from queue."""
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get(block=False)
                self._dispatch_event(event)
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    def _dispatch_event(self, event: Event) -> None:
        """Dispatch event to handlers and listeners."""
        with self.lock:
            # Try handlers first
            for handler in self.handlers:
                if handler.can_handle(event):
                    if handler.handle(event):
                        return
            
            # Then try listeners
            listeners = self.listeners.get(event.event_type, []) + self.global_listeners
            
            for listener in listeners:
                if listener.matches(event):
                    try:
                        listener.callback(event)
                    except Exception as e:
                        logger.error(f"Error in listener {listener.name}: {e}")
    
    def get_event_history(self, event_type: EventType = None, limit: int = 100) -> List[Event]:
        """Get event history."""
        with self.lock:
            history = self.event_history
            if event_type:
                history = [e for e in history if e.event_type == event_type]
            return history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get event statistics."""
        with self.lock:
            return {
                "total_events": sum(self.event_stats.values()),
                "event_types": dict(self.event_stats),
                "listeners": len(self.global_listeners) + sum(len(l) for l in self.listeners.values()),
                "handlers": len(self.handlers),
                "queue_size": self.event_queue.qsize()
            }


class EventChain:
    """Chain events together."""
    
    def __init__(self, event_bus: EventBus):
        """Initialize chain."""
        self.event_bus = event_bus
        self.events: List[Event] = []
        self.conditions: List[Callable] = []
    
    def add_event(self, event: Event) -> 'EventChain':
        """Add event to chain."""
        self.events.append(event)
        return self
    
    def add_condition(self, condition: Callable) -> 'EventChain':
        """Add execution condition."""
        self.conditions.append(condition)
        return self
    
    def execute(self) -> bool:
        """Execute event chain."""
        # Check conditions
        for condition in self.conditions:
            if not condition():
                return False
        
        # Publish events
        for event in self.events:
            if not self.event_bus.publish(event):
                return False
        
        return True


class EventAggregator:
    """Aggregate events for batch processing."""
    
    def __init__(self, timeout_seconds: int = 60, batch_size: int = 100):
        """Initialize aggregator."""
        self.timeout_seconds = timeout_seconds
        self.batch_size = batch_size
        self.batches: Dict[EventType, List[Event]] = defaultdict(list)
        self.batch_timestamps: Dict[EventType, datetime] = {}
    
    def add_event(self, event: Event) -> Optional[List[Event]]:
        """Add event and check if batch ready."""
        event_type = event.event_type
        self.batches[event_type].append(event)
        
        if event_type not in self.batch_timestamps:
            self.batch_timestamps[event_type] = datetime.now()
        
        # Check if batch is ready
        if len(self.batches[event_type]) >= self.batch_size:
            return self._get_batch(event_type)
        
        # Check if timeout reached
        elapsed = (datetime.now() - self.batch_timestamps[event_type]).total_seconds()
        if elapsed >= self.timeout_seconds:
            return self._get_batch(event_type)
        
        return None
    
    def _get_batch(self, event_type: EventType) -> List[Event]:
        """Get batch of events."""
        batch = self.batches[event_type]
        self.batches[event_type] = []
        del self.batch_timestamps[event_type]
        return batch
    
    def get_pending_batches(self) -> Dict[EventType, List[Event]]:
        """Get pending batches."""
        pending = {}
        for event_type in list(self.batches.keys()):
            if self.batches[event_type]:
                pending[event_type] = self._get_batch(event_type)
        return pending


class EventSourceConnector:
    """Connect external event sources."""
    
    def __init__(self, event_bus: EventBus, source_name: str):
        """Initialize connector."""
        self.event_bus = event_bus
        self.source_name = source_name
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to event source."""
        self.connected = True
        logger.info(f"Connected to {self.source_name}")
        return True
    
    def disconnect(self) -> None:
        """Disconnect from event source."""
        self.connected = False
        logger.info(f"Disconnected from {self.source_name}")
    
    def publish_external_event(self, event_data: Dict[str, Any]) -> bool:
        """Publish event from external source."""
        if not self.connected:
            return False
        
        event = Event(
            event_type=EventType.SYSTEM_HEALTH_CHECK,
            source=self.source_name,
            data=event_data
        )
        return self.event_bus.publish(event)


class EventStore:
    """Persistent event storage."""
    
    def __init__(self, retention_days: int = 30):
        """Initialize event store."""
        self.events: List[Event] = []
        self.retention_days = retention_days
        self.indices: Dict[str, Dict[str, List[Event]]] = {
            "event_type": defaultdict(list),
            "source": defaultdict(list),
            "correlation_id": defaultdict(list)
        }
    
    def store(self, event: Event) -> bool:
        """Store event."""
        self.events.append(event)
        
        # Update indices
        self.indices["event_type"][event.event_type.value].append(event)
        self.indices["source"][event.source].append(event)
        if event.correlation_id:
            self.indices["correlation_id"][event.correlation_id].append(event)
        
        return True
    
    def query_by_type(self, event_type: EventType) -> List[Event]:
        """Query events by type."""
        return self.indices["event_type"][event_type.value]
    
    def query_by_source(self, source: str) -> List[Event]:
        """Query events by source."""
        return self.indices["source"][source]
    
    def query_by_correlation_id(self, correlation_id: str) -> List[Event]:
        """Query events by correlation ID."""
        return self.indices["correlation_id"][correlation_id]
    
    def cleanup_old_events(self) -> int:
        """Remove old events."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        
        original_count = len(self.events)
        self.events = [e for e in self.events if e.timestamp > cutoff]
        
        return original_count - len(self.events)
    
    def get_all_events(self) -> List[Event]:
        """Get all stored events."""
        return self.events.copy()
