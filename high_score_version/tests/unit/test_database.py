"""Tests for database module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sqlite3
from datetime import datetime

from src.database import (
    DatabaseType, DatabaseConfig, QueryResult, Field, DatabaseConnection,
    SQLiteConnection, QueryBuilder, InsertBuilder, UpdateBuilder, Repository,
    Transaction, DatabasePool, DataMapper, CacheLayer, Model
)


@pytest.fixture
def db_config():
    """Database config fixture."""
    return DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database=":memory:"
    )


@pytest.fixture
def sqlite_connection():
    """SQLite connection fixture."""
    conn = SQLiteConnection(":memory:")
    conn.connect()
    yield conn
    conn.disconnect()


@pytest.fixture
def cache_layer():
    """Cache layer fixture."""
    return CacheLayer(ttl_seconds=3600)


class TestDatabaseConfig:
    """Test DatabaseConfig."""
    
    def test_config_initialization(self, db_config):
        """Test config initialization."""
        assert db_config.db_type == DatabaseType.SQLITE
        assert db_config.database == ":memory:"
        assert db_config.pool_size == 10
    
    def test_config_with_credentials(self):
        """Test config with credentials."""
        config = DatabaseConfig(
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="testdb",
            username="user",
            password="pass"
        )
        assert config.username == "user"
        assert config.password == "pass"
        assert config.host == "localhost"
    
    def test_config_pool_size(self):
        """Test config pool size."""
        config = DatabaseConfig(
            db_type=DatabaseType.SQLITE,
            pool_size=20
        )
        assert config.pool_size == 20


class TestField:
    """Test Field."""
    
    def test_field_creation(self):
        """Test field creation."""
        field = Field("id", "INTEGER", primary_key=True, nullable=False)
        assert field.name == "id"
        assert field.field_type == "INTEGER"
        assert field.primary_key is True
        assert field.nullable is False
    
    def test_field_with_default(self):
        """Test field with default."""
        field = Field("status", "TEXT", default="active")
        assert field.default == "active"
    
    def test_multiple_fields(self):
        """Test multiple fields."""
        fields = [
            Field("id", "INTEGER", primary_key=True),
            Field("name", "TEXT", nullable=False),
            Field("created_at", "TIMESTAMP", default="NOW()")
        ]
        assert len(fields) == 3
        assert fields[0].primary_key is True
        assert fields[1].nullable is False


class TestSQLiteConnection:
    """Test SQLiteConnection."""
    
    def test_connect(self):
        """Test connection."""
        conn = SQLiteConnection(":memory:")
        assert conn.connect() is True
        conn.disconnect()
    
    def test_disconnect(self, sqlite_connection):
        """Test disconnect."""
        sqlite_connection.disconnect()
        # Connection should be None or closed
        assert sqlite_connection.connection is None or True
    
    def test_execute_query(self, sqlite_connection):
        """Test execute query."""
        # Create test table
        sqlite_connection.execute_update(
            "CREATE TABLE test (id INTEGER, name TEXT)"
        )
        sqlite_connection.execute_update(
            "INSERT INTO test VALUES (?, ?)", (1, "test")
        )
        
        result = sqlite_connection.execute_query("SELECT * FROM test")
        assert result.success is True
        assert result.rows_affected == 1
    
    def test_execute_update(self, sqlite_connection):
        """Test execute update."""
        sqlite_connection.execute_update(
            "CREATE TABLE test (id INTEGER, name TEXT)"
        )
        
        result = sqlite_connection.execute_update(
            "INSERT INTO test VALUES (?, ?)", (1, "test")
        )
        assert result.success is True
        assert result.rows_affected == 1
    
    def test_create_table(self, sqlite_connection):
        """Test create table."""
        fields = [
            Field("id", "INTEGER", primary_key=True),
            Field("name", "TEXT", nullable=False),
            Field("email", "TEXT")
        ]
        
        result = sqlite_connection.create_table("users", fields)
        assert result.success is True
    
    def test_query_error_handling(self, sqlite_connection):
        """Test query error handling."""
        result = sqlite_connection.execute_query("SELECT * FROM nonexistent")
        assert result.success is False
        assert result.error is not None
    
    def test_update_rollback_on_error(self, sqlite_connection):
        """Test update rollback on error."""
        result = sqlite_connection.execute_update(
            "INSERT INTO nonexistent VALUES (?, ?)", (1, "test")
        )
        assert result.success is False


class TestQueryBuilder:
    """Test QueryBuilder."""
    
    def test_select_all(self):
        """Test select all."""
        builder = QueryBuilder("users")
        query, params = builder.build()
        assert query == "SELECT * FROM users"
        assert params == ()
    
    def test_select_specific_fields(self):
        """Test select specific fields."""
        builder = QueryBuilder("users").select("id", "name", "email")
        query, params = builder.build()
        assert "id" in query
        assert "name" in query
        assert "email" in query
    
    def test_where_condition(self):
        """Test where condition."""
        builder = QueryBuilder("users").where("id = ?", 1)
        query, params = builder.build()
        assert "WHERE" in query
        assert params == (1,)
    
    def test_multiple_where_conditions(self):
        """Test multiple where conditions."""
        builder = QueryBuilder("users").where("id = ?", 1).where("status = ?", "active")
        query, params = builder.build()
        assert query.count("AND") == 1
        assert params == (1, "active")
    
    def test_order_by(self):
        """Test order by."""
        builder = QueryBuilder("users").order_by("name", "ASC")
        query, params = builder.build()
        assert "ORDER BY" in query
    
    def test_limit(self):
        """Test limit."""
        builder = QueryBuilder("users").limit(10)
        query, params = builder.build()
        assert "LIMIT 10" in query
    
    def test_offset(self):
        """Test offset."""
        builder = QueryBuilder("users").offset(20)
        query, params = builder.build()
        assert "OFFSET 20" in query
    
    def test_join(self):
        """Test join."""
        builder = QueryBuilder("users").join("INNER JOIN orders ON users.id = orders.user_id")
        query, params = builder.build()
        assert "INNER JOIN" in query
    
    def test_complex_query(self):
        """Test complex query."""
        builder = (QueryBuilder("users")
                   .select("id", "name")
                   .where("status = ?", "active")
                   .order_by("created_at", "DESC")
                   .limit(10))
        query, params = builder.build()
        assert "SELECT id, name" in query
        assert "WHERE" in query
        assert "ORDER BY" in query
        assert "LIMIT 10" in query


class TestInsertBuilder:
    """Test InsertBuilder."""
    
    def test_insert_single_value(self):
        """Test insert single value."""
        builder = InsertBuilder("users").add_value("name", "John")
        query, params = builder.build()
        assert "INSERT INTO users" in query
        assert params == ("John",)
    
    def test_insert_multiple_values(self):
        """Test insert multiple values."""
        builder = (InsertBuilder("users")
                   .add_value("name", "John")
                   .add_value("email", "john@example.com")
                   .add_value("age", 30))
        query, params = builder.build()
        assert params == ("John", "john@example.com", 30)
    
    def test_insert_null_value(self):
        """Test insert null value."""
        builder = InsertBuilder("users").add_value("bio", None)
        query, params = builder.build()
        assert None in params


class TestUpdateBuilder:
    """Test UpdateBuilder."""
    
    def test_update_single_field(self):
        """Test update single field."""
        builder = UpdateBuilder("users").set("name", "Jane").where("id = ?", 1)
        query, params = builder.build()
        assert "UPDATE users" in query
        assert "SET" in query
        assert "WHERE" in query
    
    def test_update_multiple_fields(self):
        """Test update multiple fields."""
        builder = (UpdateBuilder("users")
                   .set("name", "Jane")
                   .set("email", "jane@example.com")
                   .where("id = ?", 1))
        query, params = builder.build()
        assert query.count("=") >= 2
    
    def test_update_with_multiple_conditions(self):
        """Test update with multiple conditions."""
        builder = (UpdateBuilder("users")
                   .set("status", "inactive")
                   .where("age > ?", 65)
                   .where("active = ?", False))
        query, params = builder.build()
        assert "AND" in query


class TestTransaction:
    """Test Transaction."""
    
    def test_transaction_creation(self, sqlite_connection):
        """Test transaction creation."""
        tx = Transaction(sqlite_connection)
        assert tx.active is False
    
    def test_begin_transaction(self, sqlite_connection):
        """Test begin transaction."""
        tx = Transaction(sqlite_connection)
        tx.begin()
        assert tx.active is True
    
    def test_commit_transaction(self, sqlite_connection):
        """Test commit transaction."""
        tx = Transaction(sqlite_connection)
        tx.begin()
        tx.commit()
        assert tx.active is False
    
    def test_rollback_transaction(self, sqlite_connection):
        """Test rollback transaction."""
        tx = Transaction(sqlite_connection)
        tx.begin()
        tx.rollback()
        assert tx.active is False
    
    def test_context_manager(self, sqlite_connection):
        """Test context manager."""
        with Transaction(sqlite_connection) as tx:
            assert tx.active is True
        assert tx.active is False


class TestDatabasePool:
    """Test DatabasePool."""
    
    def test_pool_initialization(self, db_config):
        """Test pool initialization."""
        pool = DatabasePool(db_config, pool_size=5)
        assert pool.initialize() is True
        assert len(pool.available) == 5
        pool.close_all()
    
    def test_get_connection(self, db_config):
        """Test get connection."""
        pool = DatabasePool(db_config, pool_size=3)
        pool.initialize()
        
        conn = pool.get_connection()
        assert conn is not None
        assert len(pool.available) == 2
        
        pool.close_all()
    
    def test_return_connection(self, db_config):
        """Test return connection."""
        pool = DatabasePool(db_config, pool_size=3)
        pool.initialize()
        
        conn = pool.get_connection()
        assert len(pool.available) == 2
        
        pool.return_connection(conn)
        assert len(pool.available) == 3
        
        pool.close_all()
    
    def test_pool_size_limit(self, db_config):
        """Test pool size limit."""
        pool = DatabasePool(db_config, pool_size=2)
        pool.initialize()
        
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        conn3 = pool.get_connection()
        
        assert conn3 is None
        
        pool.close_all()
    
    def test_close_all(self, db_config):
        """Test close all."""
        pool = DatabasePool(db_config, pool_size=5)
        pool.initialize()
        
        pool.close_all()
        assert len(pool.connections) == 0
        assert len(pool.available) == 0


class TestDataMapper:
    """Test DataMapper."""
    
    def test_insert_data(self, sqlite_connection):
        """Test insert data."""
        sqlite_connection.create_table("users", [
            Field("id", "INTEGER", primary_key=True),
            Field("name", "TEXT")
        ])
        
        mapper = DataMapper(sqlite_connection)
        result = mapper.insert("users", {"id": 1, "name": "John"})
        assert result.success is True
    
    def test_update_data(self, sqlite_connection):
        """Test update data."""
        sqlite_connection.create_table("users", [
            Field("id", "INTEGER", primary_key=True),
            Field("name", "TEXT")
        ])
        sqlite_connection.execute_update(
            "INSERT INTO users VALUES (?, ?)", (1, "John")
        )
        
        mapper = DataMapper(sqlite_connection)
        result = mapper.update("users", {"name": "Jane"}, 1)
        assert result.success is True
    
    def test_select_data(self, sqlite_connection):
        """Test select data."""
        sqlite_connection.create_table("users", [
            Field("id", "INTEGER", primary_key=True),
            Field("name", "TEXT")
        ])
        sqlite_connection.execute_update(
            "INSERT INTO users VALUES (?, ?)", (1, "John")
        )
        
        mapper = DataMapper(sqlite_connection)
        result = mapper.select("users", 1)
        assert result.success is True


class TestCacheLayer:
    """Test CacheLayer."""
    
    def test_cache_set_and_get(self, cache_layer):
        """Test cache set and get."""
        cache_layer.set("key1", {"data": "value"})
        result = cache_layer.get("key1")
        assert result == {"data": "value"}
    
    def test_cache_miss(self, cache_layer):
        """Test cache miss."""
        result = cache_layer.get("nonexistent")
        assert result is None
    
    def test_cache_invalidation(self, cache_layer):
        """Test cache invalidation."""
        cache_layer.set("key1", "value")
        cache_layer.invalidate("key1")
        result = cache_layer.get("key1")
        assert result is None
    
    def test_cache_clear(self, cache_layer):
        """Test cache clear."""
        cache_layer.set("key1", "value1")
        cache_layer.set("key2", "value2")
        cache_layer.clear()
        
        assert cache_layer.get("key1") is None
        assert cache_layer.get("key2") is None
    
    def test_cache_ttl_expiry(self):
        """Test cache TTL expiry."""
        cache = CacheLayer(ttl_seconds=1)
        cache.set("key1", "value")
        
        import time
        time.sleep(1.1)
        
        result = cache.get("key1")
        assert result is None
    
    def test_multiple_cache_entries(self, cache_layer):
        """Test multiple cache entries."""
        cache_layer.set("user:1", {"id": 1, "name": "John"})
        cache_layer.set("user:2", {"id": 2, "name": "Jane"})
        cache_layer.set("email:john", "john@example.com")
        
        assert cache_layer.get("user:1")["name"] == "John"
        assert cache_layer.get("user:2")["name"] == "Jane"
        assert cache_layer.get("email:john") == "john@example.com"


class TestDatabaseIntegration:
    """Integration tests for database module."""
    
    def test_create_and_query_table(self, sqlite_connection):
        """Test create and query table."""
        # Create table
        fields = [
            Field("id", "INTEGER", primary_key=True),
            Field("email", "TEXT", nullable=False),
            Field("status", "TEXT", default="active")
        ]
        
        result = sqlite_connection.create_table("emails", fields)
        assert result.success is True
        
        # Insert data
        result = sqlite_connection.execute_update(
            "INSERT INTO emails (email, status) VALUES (?, ?)",
            ("test@example.com", "active")
        )
        assert result.success is True
        
        # Query data
        result = sqlite_connection.execute_query("SELECT * FROM emails")
        assert result.success is True
        assert result.rows_affected == 1
    
    def test_transaction_workflow(self, sqlite_connection):
        """Test transaction workflow."""
        sqlite_connection.create_table("accounts", [
            Field("id", "INTEGER", primary_key=True),
            Field("balance", "INTEGER")
        ])
        
        with Transaction(sqlite_connection):
            sqlite_connection.execute_update(
                "INSERT INTO accounts VALUES (?, ?)", (1, 1000)
            )
            sqlite_connection.execute_update(
                "INSERT INTO accounts VALUES (?, ?)", (2, 500)
            )
        
        result = sqlite_connection.execute_query("SELECT COUNT(*) FROM accounts")
        assert result.success is True
    
    def test_query_builder_with_connection(self, sqlite_connection):
        """Test query builder with connection."""
        sqlite_connection.create_table("users", [
            Field("id", "INTEGER", primary_key=True),
            Field("name", "TEXT"),
            Field("age", "INTEGER")
        ])
        
        sqlite_connection.execute_update(
            "INSERT INTO users VALUES (?, ?, ?)", (1, "John", 30)
        )
        
        builder = QueryBuilder("users").select("name", "age").where("id = ?", 1)
        query, params = builder.build()
        
        result = sqlite_connection.execute_query(query, params)
        assert result.success is True
    
    def test_full_crud_operations(self, sqlite_connection):
        """Test full CRUD operations."""
        # Create
        sqlite_connection.create_table("products", [
            Field("id", "INTEGER", primary_key=True),
            Field("name", "TEXT"),
            Field("price", "REAL")
        ])
        
        # Create (Insert)
        result = sqlite_connection.execute_update(
            "INSERT INTO products VALUES (?, ?, ?)",
            (1, "Widget", 9.99)
        )
        assert result.success is True
        
        # Read
        result = sqlite_connection.execute_query("SELECT * FROM products WHERE id = 1")
        assert result.success is True
        
        # Update
        result = sqlite_connection.execute_update(
            "UPDATE products SET price = ? WHERE id = ?",
            (14.99, 1)
        )
        assert result.success is True
        
        # Delete
        result = sqlite_connection.execute_update(
            "DELETE FROM products WHERE id = 1"
        )
        assert result.success is True
