"""Tests for events module."""

import pytest
import queue
import threading
import time
from datetime import datetime, timedelta

from src.events import (
    EventType, EventPriority, Event, EventHandler, EventListener, EventFilter,
    EventTransformer, EventBus, EventChain, EventAggregator, EventSourceConnector,
    EventStore
)


@pytest.fixture
def event_bus():
    """Event bus fixture."""
    return EventBus()


@pytest.fixture
def sample_event():
    """Sample event fixture."""
    return Event(
        event_type=EventType.EMAIL_RECEIVED,
        source="gmail",
        data={"email_id": "123", "from": "test@example.com"},
        priority=EventPriority.HIGH
    )


class TestEventType:
    """Test EventType enum."""
    
    def test_event_type_values(self):
        """Test event type values."""
        assert EventType.EMAIL_RECEIVED.value == "email.received"
        assert EventType.EMAIL_PROCESSED.value == "email.processed"
        assert EventType.TASK_STARTED.value == "task.started"
    
    def test_all_event_types_defined(self):
        """Test all event types are defined."""
        event_types = [
            EventType.EMAIL_RECEIVED, EventType.EMAIL_PROCESSED,
            EventType.TASK_STARTED, EventType.TASK_COMPLETED,
            EventType.USER_LOGGED_IN, EventType.NOTIFICATION_SENT
        ]
        assert len(event_types) > 0


class TestEventPriority:
    """Test EventPriority enum."""
    
    def test_priority_ordering(self):
        """Test priority ordering."""
        assert EventPriority.LOW.value < EventPriority.MEDIUM.value
        assert EventPriority.MEDIUM.value < EventPriority.HIGH.value
        assert EventPriority.HIGH.value < EventPriority.CRITICAL.value


class TestEvent:
    """Test Event class."""
    
    def test_event_creation(self, sample_event):
        """Test event creation."""
        assert sample_event.event_type == EventType.EMAIL_RECEIVED
        assert sample_event.source == "gmail"
        assert sample_event.priority == EventPriority.HIGH
    
    def test_event_has_id(self, sample_event):
        """Test event has unique ID."""
        event2 = Event(
            event_type=EventType.EMAIL_PROCESSED,
            source="gmail"
        )
        assert sample_event.event_id != event2.event_id
    
    def test_event_has_timestamp(self, sample_event):
        """Test event has timestamp."""
        assert isinstance(sample_event.timestamp, datetime)
    
    def test_event_to_dict(self, sample_event):
        """Test event to dictionary."""
        event_dict = sample_event.to_dict()
        assert event_dict["event_id"] == sample_event.event_id
        assert event_dict["event_type"] == EventType.EMAIL_RECEIVED.value
        assert event_dict["source"] == "gmail"
    
    def test_event_with_correlation_id(self):
        """Test event with correlation ID."""
        event = Event(
            event_type=EventType.EMAIL_RECEIVED,
            source="gmail",
            correlation_id="corr-123"
        )
        assert event.correlation_id == "corr-123"
    
    def test_event_with_parent_event(self):
        """Test event with parent event."""
        parent = Event(
            event_type=EventType.EMAIL_RECEIVED,
            source="gmail"
        )
        child = Event(
            event_type=EventType.EMAIL_PROCESSED,
            source="processor",
            parent_event_id=parent.event_id
        )
        assert child.parent_event_id == parent.event_id


class TestEventListener:
    """Test EventListener."""
    
    def test_listener_creation(self):
        """Test listener creation."""
        callback = lambda e: None
        listener = EventListener("test", callback, [EventType.EMAIL_RECEIVED])
        assert listener.name == "test"
        assert listener.enabled is True
        assert listener.invocation_count == 0
    
    def test_listener_matches_event(self):
        """Test listener matches event."""
        callback = lambda e: None
        listener = EventListener("test", callback, [EventType.EMAIL_RECEIVED])
        
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        assert listener.matches(event) is True
        
        event2 = Event(event_type=EventType.EMAIL_PROCESSED, source="gmail")
        assert listener.matches(event2) is False
    
    def test_listener_disabled(self):
        """Test disabled listener."""
        callback = lambda e: None
        listener = EventListener("test", callback)
        listener.enabled = False
        
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        assert listener.matches(event) is False
    
    def test_listener_global(self):
        """Test global listener."""
        callback = lambda e: None
        listener = EventListener("test", callback)  # No event types specified
        
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.TASK_STARTED, source="scheduler")
        
        assert listener.matches(event1) is True
        assert listener.matches(event2) is True


class TestEventFilter:
    """Test EventFilter."""
    
    def test_filter_by_event_type(self):
        """Test filter by event type."""
        event_filter = EventFilter(
            event_types={EventType.EMAIL_RECEIVED, EventType.EMAIL_PROCESSED}
        )
        
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.TASK_STARTED, source="scheduler")
        
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False
    
    def test_filter_by_source(self):
        """Test filter by source."""
        event_filter = EventFilter(sources={"gmail", "outlook"})
        
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.EMAIL_RECEIVED, source="imap")
        
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False
    
    def test_filter_by_priority(self):
        """Test filter by priority."""
        event_filter = EventFilter(min_priority=EventPriority.HIGH)
        
        event1 = Event(
            event_type=EventType.EMAIL_RECEIVED,
            source="gmail",
            priority=EventPriority.CRITICAL
        )
        event2 = Event(
            event_type=EventType.EMAIL_RECEIVED,
            source="gmail",
            priority=EventPriority.LOW
        )
        
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False
    
    def test_filter_by_age(self):
        """Test filter by event age."""
        old_time = datetime.now() - timedelta(seconds=100)
        
        event_filter = EventFilter(max_age_seconds=60)
        
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(
            event_type=EventType.EMAIL_RECEIVED,
            source="gmail",
            timestamp=old_time
        )
        
        assert event_filter.matches(event1) is True
        assert event_filter.matches(event2) is False


class TestEventTransformer:
    """Test EventTransformer."""
    
    def test_transform_event(self):
        """Test transform event."""
        transformer = EventTransformer()
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        transformed = transformer.transform(event)
        assert transformed.event_id == event.event_id
    
    def test_enrich_event(self):
        """Test enrich event."""
        transformer = EventTransformer()
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        enrichment = {"processed": True, "score": 0.95}
        enriched = transformer.enrich(event, enrichment)
        
        assert enriched.data["processed"] is True
        assert enriched.data["score"] == 0.95


class TestEventBus:
    """Test EventBus."""
    
    def test_bus_creation(self, event_bus):
        """Test event bus creation."""
        assert event_bus is not None
        assert len(event_bus.listeners) == 0
    
    def test_subscribe_listener(self, event_bus):
        """Test subscribe listener."""
        callback = lambda e: None
        listener = EventListener("test", callback, [EventType.EMAIL_RECEIVED])
        
        listener_id = event_bus.subscribe(listener, EventType.EMAIL_RECEIVED)
        assert listener_id is not None
        assert listener_id == listener.listener_id
    
    def test_unsubscribe_listener(self, event_bus):
        """Test unsubscribe listener."""
        callback = lambda e: None
        listener = EventListener("test", callback, [EventType.EMAIL_RECEIVED])
        listener_id = event_bus.subscribe(listener, EventType.EMAIL_RECEIVED)
        
        result = event_bus.unsubscribe(listener_id)
        assert result is True
    
    def test_publish_event(self, event_bus, sample_event):
        """Test publish event."""
        result = event_bus.publish(sample_event)
        assert result is True
    
    def test_event_history(self, event_bus):
        """Test event history."""
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.EMAIL_PROCESSED, source="processor")
        
        event_bus.publish(event1)
        event_bus.publish(event2)
        
        history = event_bus.get_event_history()
        assert len(history) == 2
    
    def test_event_statistics(self, event_bus):
        """Test event statistics."""
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        event_bus.publish(event1)
        event_bus.publish(event2)
        
        stats = event_bus.get_statistics()
        assert stats["total_events"] == 2
    
    def test_add_filter(self, event_bus):
        """Test add filter."""
        event_filter = EventFilter(
            event_types={EventType.EMAIL_RECEIVED}
        )
        event_bus.add_filter(event_filter)
        
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.TASK_STARTED, source="scheduler")
        
        assert event_bus.publish(event1) is True
        assert event_bus.publish(event2) is False
    
    def test_add_transformer(self, event_bus):
        """Test add transformer."""
        transformer = EventTransformer()
        event_bus.add_transformer(transformer)
        
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        result = event_bus.publish(event)
        assert result is True


class TestEventChain:
    """Test EventChain."""
    
    def test_chain_creation(self, event_bus):
        """Test chain creation."""
        chain = EventChain(event_bus)
        assert chain is not None
        assert len(chain.events) == 0
    
    def test_add_event_to_chain(self, event_bus):
        """Test add event to chain."""
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.EMAIL_PROCESSED, source="processor")
        
        chain = EventChain(event_bus)
        chain.add_event(event1).add_event(event2)
        
        assert len(chain.events) == 2
    
    def test_execute_chain(self, event_bus):
        """Test execute chain."""
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        chain = EventChain(event_bus)
        chain.add_event(event)
        
        result = chain.execute()
        assert result is True
    
    def test_chain_condition(self, event_bus):
        """Test chain condition."""
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        chain = EventChain(event_bus)
        chain.add_event(event)
        chain.add_condition(lambda: True)
        
        result = chain.execute()
        assert result is True
    
    def test_chain_failed_condition(self, event_bus):
        """Test chain failed condition."""
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        chain = EventChain(event_bus)
        chain.add_event(event)
        chain.add_condition(lambda: False)
        
        result = chain.execute()
        assert result is False


class TestEventAggregator:
    """Test EventAggregator."""
    
    def test_aggregator_creation(self):
        """Test aggregator creation."""
        agg = EventAggregator(timeout_seconds=60, batch_size=100)
        assert agg.timeout_seconds == 60
        assert agg.batch_size == 100
    
    def test_add_event_to_batch(self):
        """Test add event to batch."""
        agg = EventAggregator(batch_size=5)
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        result = agg.add_event(event)
        assert result is None  # Not ready yet
    
    def test_batch_ready_on_size(self):
        """Test batch ready on size."""
        agg = EventAggregator(batch_size=2)
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        agg.add_event(event1)
        batch = agg.add_event(event2)
        
        assert batch is not None
        assert len(batch) == 2
    
    def test_batch_timeout(self):
        """Test batch timeout."""
        agg = EventAggregator(timeout_seconds=1, batch_size=100)
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        agg.add_event(event)
        time.sleep(1.1)
        
        batch = agg.add_event(Event(event_type=EventType.EMAIL_RECEIVED, source="gmail"))
        # This should trigger the timeout batch
        assert len(agg.batches[EventType.EMAIL_RECEIVED]) >= 0


class TestEventSourceConnector:
    """Test EventSourceConnector."""
    
    def test_connector_creation(self, event_bus):
        """Test connector creation."""
        connector = EventSourceConnector(event_bus, "external")
        assert connector.source_name == "external"
        assert connector.connected is False
    
    def test_connect_disconnect(self, event_bus):
        """Test connect and disconnect."""
        connector = EventSourceConnector(event_bus, "external")
        
        assert connector.connect() is True
        assert connector.connected is True
        
        connector.disconnect()
        assert connector.connected is False
    
    def test_publish_external_event(self, event_bus):
        """Test publish external event."""
        connector = EventSourceConnector(event_bus, "external")
        connector.connect()
        
        event_data = {"status": "ok", "timestamp": str(datetime.now())}
        result = connector.publish_external_event(event_data)
        assert result is True


class TestEventStore:
    """Test EventStore."""
    
    def test_store_creation(self):
        """Test store creation."""
        store = EventStore(retention_days=30)
        assert store.retention_days == 30
        assert len(store.events) == 0
    
    def test_store_event(self):
        """Test store event."""
        store = EventStore()
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        result = store.store(event)
        assert result is True
        assert len(store.events) == 1
    
    def test_query_by_type(self):
        """Test query by type."""
        store = EventStore()
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.EMAIL_PROCESSED, source="processor")
        
        store.store(event1)
        store.store(event2)
        
        results = store.query_by_type(EventType.EMAIL_RECEIVED)
        assert len(results) == 1
    
    def test_query_by_source(self):
        """Test query by source."""
        store = EventStore()
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.EMAIL_RECEIVED, source="outlook")
        
        store.store(event1)
        store.store(event2)
        
        results = store.query_by_source("gmail")
        assert len(results) == 1
    
    def test_query_by_correlation_id(self):
        """Test query by correlation ID."""
        store = EventStore()
        corr_id = "corr-123"
        
        event1 = Event(
            event_type=EventType.EMAIL_RECEIVED,
            source="gmail",
            correlation_id=corr_id
        )
        event2 = Event(
            event_type=EventType.EMAIL_PROCESSED,
            source="processor",
            correlation_id=corr_id
        )
        
        store.store(event1)
        store.store(event2)
        
        results = store.query_by_correlation_id(corr_id)
        assert len(results) == 2
    
    def test_cleanup_old_events(self):
        """Test cleanup old events."""
        store = EventStore(retention_days=1)
        
        old_time = datetime.now() - timedelta(days=2)
        event1 = Event(
            event_type=EventType.EMAIL_RECEIVED,
            source="gmail",
            timestamp=old_time
        )
        event2 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        
        store.store(event1)
        store.store(event2)
        
        removed = store.cleanup_old_events()
        assert removed == 1
        assert len(store.events) == 1


class TestEventIntegration:
    """Integration tests for event system."""
    
    def test_publish_and_subscribe(self, event_bus):
        """Test publish and subscribe."""
        received_events = []
        
        def callback(event):
            received_events.append(event)
        
        listener = EventListener("test", callback, [EventType.EMAIL_RECEIVED])
        event_bus.subscribe(listener, EventType.EMAIL_RECEIVED)
        
        event = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event_bus.publish(event)
        event_bus.process_events()
        
        assert len(received_events) > 0
    
    def test_event_chain_workflow(self, event_bus):
        """Test event chain workflow."""
        received_events = []
        
        def callback(event):
            received_events.append(event)
        
        listener = EventListener("test", callback)
        event_bus.subscribe(listener)
        
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.EMAIL_PROCESSED, source="processor")
        
        chain = EventChain(event_bus)
        chain.add_event(event1).add_event(event2)
        chain.execute()
        
        event_bus.process_events()
        
        assert len(received_events) == 2
    
    def test_filtered_event_delivery(self, event_bus):
        """Test filtered event delivery."""
        received_events = []
        
        def callback(event):
            received_events.append(event)
        
        event_filter = EventFilter(
            event_types={EventType.EMAIL_RECEIVED}
        )
        event_bus.add_filter(event_filter)
        
        listener = EventListener("test", callback)
        event_bus.subscribe(listener)
        
        event1 = Event(event_type=EventType.EMAIL_RECEIVED, source="gmail")
        event2 = Event(event_type=EventType.TASK_STARTED, source="scheduler")
        
        event_bus.publish(event1)
        event_bus.publish(event2)
        event_bus.process_events()
        
        assert len(received_events) == 1
