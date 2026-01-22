"""Tests for storage module."""

import pytest
import sys
sys.path.insert(0, '/workspaces/gmail_agent/high_score_version')

from src.storage import (
    InMemoryStorage, FileStorage, StorageManager,
    EmailArchive, BackupManager, DataMigration
)


class TestInMemoryStorage:
    """Test suite for InMemoryStorage."""
    
    @pytest.fixture
    def storage(self):
        """Create in-memory storage."""
        return InMemoryStorage()
    
    def test_storage_initialization(self, storage):
        """Test storage initialization."""
        assert len(storage.emails) == 0
        assert len(storage.indexes) > 0
    
    def test_save_and_load_email(self, storage):
        """Test saving and loading email."""
        email = {
            "id": "msg_1",
            "subject": "Test",
            "from": "sender@example.com"
        }
        
        assert storage.save_email(email) is True
        loaded = storage.load_email("msg_1")
        assert loaded is not None
        assert loaded["subject"] == "Test"
    
    def test_delete_email(self, storage):
        """Test deleting email."""
        email = {"id": "msg_1", "subject": "Test"}
        storage.save_email(email)
        
        assert storage.delete_email("msg_1") is True
        assert storage.load_email("msg_1") is None
    
    def test_query_emails(self, storage):
        """Test querying emails."""
        emails = [
            {"id": "msg_1", "from": "alice@example.com", "subject": "Meeting"},
            {"id": "msg_2", "from": "bob@example.com", "subject": "Report"}
        ]
        
        for email in emails:
            storage.save_email(email)
        
        results = storage.query_emails({"from": "alice@example.com"})
        assert len(results) == 1


class TestFileStorage:
    """Test suite for FileStorage."""
    
    @pytest.fixture
    def storage(self):
        """Create file storage."""
        return FileStorage()
    
    def test_file_storage_initialization(self, storage):
        """Test file storage initialization."""
        assert storage.base_path is not None


class TestStorageManager:
    """Test suite for StorageManager."""
    
    @pytest.fixture
    def manager(self):
        """Create storage manager."""
        return StorageManager(InMemoryStorage())
    
    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.backend is not None
        assert manager.cache_enabled is True
    
    def test_save_and_load(self, manager):
        """Test saving and loading."""
        email = {"id": "msg_1", "subject": "Test"}
        assert manager.save_email(email) is True
        
        loaded = manager.load_email("msg_1")
        assert loaded is not None
    
    def test_batch_save(self, manager):
        """Test batch save."""
        emails = [
            {"id": f"msg_{i}", "subject": f"Email {i}"}
            for i in range(5)
        ]
        
        count = manager.batch_save(emails)
        assert count == 5
    
    def test_cache_operations(self, manager):
        """Test cache operations."""
        email = {"id": "msg_1", "subject": "Test"}
        manager.save_email(email)
        
        # Load from cache
        loaded = manager.load_email("msg_1")
        assert loaded is not None
        
        # Clear cache
        manager.clear_cache()
        assert len(manager.cache) == 0
    
    def test_get_statistics(self, manager):
        """Test getting statistics."""
        stats = manager.get_statistics()
        assert "backend_type" in stats
        assert "cache_size" in stats


class TestEmailArchive:
    """Test suite for EmailArchive."""
    
    @pytest.fixture
    def archive(self):
        """Create email archive."""
        manager = StorageManager(InMemoryStorage())
        return EmailArchive(manager)
    
    def test_archive_email(self, archive):
        """Test archiving email."""
        email = {"id": "msg_1", "subject": "Test"}
        archive.storage.save_email(email)
        
        assert archive.archive_email("msg_1") is True
        assert archive.get_archived_count() == 1
    
    def test_restore_email(self, archive):
        """Test restoring email."""
        email = {"id": "msg_1", "subject": "Test"}
        archive.storage.save_email(email)
        archive.archive_email("msg_1")
        
        assert archive.restore_email("msg_1") is True
        assert archive.get_archived_count() == 0


class TestBackupManager:
    """Test suite for BackupManager."""
    
    @pytest.fixture
    def backup_mgr(self):
        """Create backup manager."""
        manager = StorageManager(InMemoryStorage())
        return BackupManager(manager)
    
    def test_create_backup(self, backup_mgr):
        """Test creating backup."""
        assert backup_mgr.create_backup("backup_1") is True
        assert "backup_1" in backup_mgr.backups
    
    def test_list_backups(self, backup_mgr):
        """Test listing backups."""
        backup_mgr.create_backup("backup_1")
        backup_mgr.create_backup("backup_2")
        
        backups = backup_mgr.list_backups()
        assert len(backups) == 2
    
    def test_schedule_backup(self, backup_mgr):
        """Test scheduling backup."""
        backup_mgr.schedule_backup("backup_1", "daily")
        assert len(backup_mgr.backup_schedule) == 1


class TestDataMigration:
    """Test suite for DataMigration."""
    
    def test_migration_initialization(self):
        """Test migration initialization."""
        source = InMemoryStorage()
        dest = InMemoryStorage()
        migration = DataMigration(source, dest)
        
        assert migration.source is not None
        assert migration.destination is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
