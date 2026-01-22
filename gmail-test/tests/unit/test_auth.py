"""Tests for authentication and authorization."""

import pytest
import time
from datetime import datetime, timedelta
from src.auth import (
    Permission, Role, User, PasswordHasher, TokenManager, RoleManager,
    UserManager, Session, SessionManager, AuditLog, AuditLogManager,
    AuthenticationService, TokenData
)


class TestPermission:
    """Test Permission enum."""
    
    def test_permissions(self):
        """Test permission values."""
        assert Permission.READ.value == "read"
        assert Permission.WRITE.value == "write"
        assert Permission.ADMIN.value == "admin"


class TestRole:
    """Test Role enum."""
    
    def test_roles(self):
        """Test role values."""
        assert Role.GUEST.value == "guest"
        assert Role.USER.value == "user"
        assert Role.ADMIN.value == "admin"


class TestTokenData:
    """Test TokenData."""
    
    def test_creation(self):
        """Test token data creation."""
        token_data = TokenData(user_id="user1", token_type="access")
        assert token_data.user_id == "user1"
        assert token_data.token_type == "access"
    
    def test_is_expired(self):
        """Test expiry check."""
        token_data = TokenData(user_id="user1", token_type="access")
        assert token_data.is_expired() is False
        
        token_data.expires_at = datetime.now() - timedelta(hours=1)
        assert token_data.is_expired() is True


class TestUser:
    """Test User class."""
    
    def test_creation(self):
        """Test user creation."""
        user = User(
            id="user1",
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            role=Role.USER
        )
        assert user.id == "user1"
        assert user.username == "testuser"
        assert user.active is True
    
    def test_to_dict(self):
        """Test converting to dict."""
        user = User(
            id="user1",
            username="testuser",
            email="test@example.com",
            password_hash="hash",
            role=Role.USER
        )
        data = user.to_dict()
        assert data["id"] == "user1"
        assert data["username"] == "testuser"


class TestPasswordHasher:
    """Test PasswordHasher."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password"
        hash_result, salt = PasswordHasher.hash_password(password)
        
        assert hash_result is not None
        assert salt is not None
    
    def test_hash_different_outputs(self):
        """Test different hashes for same password."""
        password = "test_password"
        hash1, _ = PasswordHasher.hash_password(password)
        hash2, _ = PasswordHasher.hash_password(password)
        
        # Different salts should produce different hashes
        assert hash1 != hash2
    
    def test_verify_password_success(self):
        """Test successful password verification."""
        password = "test_password"
        hash_result, _ = PasswordHasher.hash_password(password)
        
        result = PasswordHasher.verify_password(password, hash_result)
        assert result is True
    
    def test_verify_password_failure(self):
        """Test failed password verification."""
        password = "test_password"
        wrong_password = "wrong_password"
        hash_result, _ = PasswordHasher.hash_password(password)
        
        result = PasswordHasher.verify_password(wrong_password, hash_result)
        assert result is False


class TestTokenManager:
    """Test TokenManager."""
    
    def test_generate_token(self):
        """Test token generation."""
        manager = TokenManager(secret_key="test_secret")
        token = manager.generate_token("user1", duration_hours=24)
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_valid_token(self):
        """Test verifying valid token."""
        manager = TokenManager(secret_key="test_secret")
        token = manager.generate_token("user1")
        
        result = manager.verify_token(token)
        assert result is True
    
    def test_verify_invalid_token(self):
        """Test verifying invalid token."""
        manager = TokenManager(secret_key="test_secret")
        result = manager.verify_token("invalid_token")
        
        assert result is False
    
    def test_decode_token(self):
        """Test decoding token."""
        manager = TokenManager(secret_key="test_secret")
        token = manager.generate_token("user1")
        
        payload = manager.decode_token(token)
        assert payload is not None
        assert payload["user_id"] == "user1"
    
    def test_refresh_token(self):
        """Test refreshing token."""
        manager = TokenManager(secret_key="test_secret")
        original_token = manager.generate_token("user1")
        
        refreshed_token = manager.refresh_token(original_token)
        assert refreshed_token is not None
        assert refreshed_token != original_token
    
    def test_revoke_token(self):
        """Test revoking token."""
        manager = TokenManager(secret_key="test_secret")
        token = manager.generate_token("user1")
        
        manager.revoke_token(token)
        result = manager.verify_token(token)
        assert result is False


class TestRoleManager:
    """Test RoleManager."""
    
    def test_get_role_permissions(self):
        """Test getting role permissions."""
        manager = RoleManager()
        permissions = manager.get_role_permissions(Role.USER)
        
        assert Permission.READ in permissions
        assert Permission.WRITE in permissions
    
    def test_has_permission(self):
        """Test permission check."""
        manager = RoleManager()
        
        assert manager.has_permission(Role.USER, Permission.READ) is True
        assert manager.has_permission(Role.GUEST, Permission.WRITE) is False
    
    def test_add_permission_to_role(self):
        """Test adding permission to role."""
        manager = RoleManager()
        manager.add_permission_to_role(Role.GUEST, Permission.WRITE)
        
        assert manager.has_permission(Role.GUEST, Permission.WRITE) is True
    
    def test_remove_permission_from_role(self):
        """Test removing permission from role."""
        manager = RoleManager()
        manager.remove_permission_from_role(Role.USER, Permission.WRITE)
        
        assert manager.has_permission(Role.USER, Permission.WRITE) is False


class TestUserManager:
    """Test UserManager."""
    
    def test_create_user(self):
        """Test creating user."""
        role_manager = RoleManager()
        manager = UserManager(role_manager)
        
        user = manager.create_user("user1", "testuser", "test@example.com", "password")
        assert user.id == "user1"
        assert user.active is True
    
    def test_get_user(self):
        """Test getting user."""
        role_manager = RoleManager()
        manager = UserManager(role_manager)
        
        manager.create_user("user1", "testuser", "test@example.com", "password")
        user = manager.get_user("user1")
        
        assert user is not None
        assert user.id == "user1"
    
    def test_get_user_by_username(self):
        """Test getting user by username."""
        role_manager = RoleManager()
        manager = UserManager(role_manager)
        
        manager.create_user("user1", "testuser", "test@example.com", "password")
        user = manager.get_user_by_username("testuser")
        
        assert user is not None
        assert user.username == "testuser"
    
    def test_get_user_by_email(self):
        """Test getting user by email."""
        role_manager = RoleManager()
        manager = UserManager(role_manager)
        
        manager.create_user("user1", "testuser", "test@example.com", "password")
        user = manager.get_user_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"
    
    def test_update_user(self):
        """Test updating user."""
        role_manager = RoleManager()
        manager = UserManager(role_manager)
        
        manager.create_user("user1", "testuser", "test@example.com", "password")
        updated = manager.update_user("user1", active=False)
        
        assert updated.active is False
    
    def test_delete_user(self):
        """Test deleting user."""
        role_manager = RoleManager()
        manager = UserManager(role_manager)
        
        manager.create_user("user1", "testuser", "test@example.com", "password")
        result = manager.delete_user("user1")
        
        assert result is True
        assert manager.get_user("user1") is None
    
    def test_verify_password(self):
        """Test password verification."""
        role_manager = RoleManager()
        manager = UserManager(role_manager)
        
        manager.create_user("user1", "testuser", "test@example.com", "password")
        result = manager.verify_password("user1", "password")
        
        assert result is True
    
    def test_change_password(self):
        """Test changing password."""
        role_manager = RoleManager()
        manager = UserManager(role_manager)
        
        manager.create_user("user1", "testuser", "test@example.com", "password")
        manager.change_password("user1", "new_password")
        
        assert manager.verify_password("user1", "new_password") is True
        assert manager.verify_password("user1", "password") is False


class TestSession:
    """Test Session."""
    
    def test_creation(self):
        """Test session creation."""
        session = Session("sess1", "user1", "token123")
        assert session.session_id == "sess1"
        assert session.user_id == "user1"
        assert session.active is True
    
    def test_is_valid(self):
        """Test session validity."""
        session = Session("sess1", "user1", "token123")
        assert session.is_valid() is True
    
    def test_is_valid_expired(self):
        """Test expired session."""
        session = Session("sess1", "user1", "token123")
        session.last_activity = datetime.now() - timedelta(hours=1)
        
        assert session.is_valid(timeout_minutes=30) is False
    
    def test_update_activity(self):
        """Test updating activity."""
        session = Session("sess1", "user1", "token123")
        old_time = session.last_activity
        
        time.sleep(0.01)  # Small delay
        session.update_activity()
        
        assert session.last_activity > old_time


class TestSessionManager:
    """Test SessionManager."""
    
    def test_create_session(self):
        """Test creating session."""
        manager = SessionManager()
        session = manager.create_session("user1", "token123")
        
        assert session.user_id == "user1"
        assert session.active is True
    
    def test_get_session(self):
        """Test getting session."""
        manager = SessionManager()
        created_session = manager.create_session("user1", "token123")
        
        retrieved = manager.get_session(created_session.session_id)
        assert retrieved is not None
        assert retrieved.user_id == "user1"
    
    def test_end_session(self):
        """Test ending session."""
        manager = SessionManager()
        session = manager.create_session("user1", "token123")
        
        manager.end_session(session.session_id)
        retrieved = manager.get_session(session.session_id)
        
        assert retrieved is None
    
    def test_cleanup_expired(self):
        """Test cleaning up expired sessions."""
        manager = SessionManager(timeout_minutes=0)
        session = manager.create_session("user1", "token123")
        
        time.sleep(0.01)
        count = manager.cleanup_expired()
        
        assert count > 0


class TestAuditLog:
    """Test AuditLog."""
    
    def test_creation(self):
        """Test audit log creation."""
        log = AuditLog("user1", "login", "auth")
        assert log.user_id == "user1"
        assert log.action == "login"
    
    def test_to_dict(self):
        """Test converting to dict."""
        log = AuditLog("user1", "login", "auth", {"ip": "127.0.0.1"})
        data = log.to_dict()
        
        assert data["user_id"] == "user1"
        assert data["action"] == "login"
        assert data["details"]["ip"] == "127.0.0.1"


class TestAuditLogManager:
    """Test AuditLogManager."""
    
    def test_log_action(self):
        """Test logging action."""
        manager = AuditLogManager()
        log = manager.log_action("user1", "login", "auth")
        
        assert log is not None
        assert log.user_id == "user1"
    
    def test_get_logs(self):
        """Test getting logs."""
        manager = AuditLogManager()
        manager.log_action("user1", "login", "auth")
        manager.log_action("user2", "logout", "auth")
        
        logs = manager.get_logs()
        assert len(logs) == 2
    
    def test_get_logs_by_user(self):
        """Test getting logs by user."""
        manager = AuditLogManager()
        manager.log_action("user1", "login", "auth")
        manager.log_action("user2", "logout", "auth")
        
        logs = manager.get_logs(user_id="user1")
        assert len(logs) == 1
        assert logs[0].user_id == "user1"
    
    def test_get_logs_by_action(self):
        """Test getting logs by action."""
        manager = AuditLogManager()
        manager.log_action("user1", "login", "auth")
        manager.log_action("user2", "login", "auth")
        
        logs = manager.get_logs(action="login")
        assert len(logs) == 2


class TestAuthenticationService:
    """Test AuthenticationService."""
    
    def test_authenticate_success(self):
        """Test successful authentication."""
        service = AuthenticationService(secret_key="test_secret")
        service.user_manager.create_user("user1", "testuser", "test@example.com", "password")
        
        token = service.authenticate("testuser", "password")
        assert token is not None
    
    def test_authenticate_wrong_password(self):
        """Test authentication with wrong password."""
        service = AuthenticationService(secret_key="test_secret")
        service.user_manager.create_user("user1", "testuser", "test@example.com", "password")
        
        token = service.authenticate("testuser", "wrongpassword")
        assert token is None
    
    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user."""
        service = AuthenticationService(secret_key="test_secret")
        
        token = service.authenticate("nonexistent", "password")
        assert token is None
    
    def test_logout(self):
        """Test logout."""
        service = AuthenticationService(secret_key="test_secret")
        service.user_manager.create_user("user1", "testuser", "test@example.com", "password")
        
        token = service.authenticate("testuser", "password")
        service.logout(token, "user1")
        
        # Token should be revoked
        assert service.token_manager.verify_token(token) is False
    
    def test_verify_authorization(self):
        """Test authorization verification."""
        service = AuthenticationService(secret_key="test_secret")
        service.user_manager.create_user("user1", "testuser", "test@example.com", "password", role=Role.ADMIN)
        
        token = service.authenticate("testuser", "password")
        result = service.verify_authorization(token, Permission.ADMIN)
        
        assert result is True


class TestAuthIntegration:
    """Integration tests for authentication."""
    
    def test_full_auth_workflow(self):
        """Test complete authentication workflow."""
        service = AuthenticationService(secret_key="test_secret")
        
        # Create user
        service.user_manager.create_user("user1", "testuser", "test@example.com", "password")
        
        # Authenticate
        token = service.authenticate("testuser", "password")
        assert token is not None
        
        # Verify token
        assert service.token_manager.verify_token(token) is True
        
        # Logout
        service.logout(token, "user1")
        assert service.token_manager.verify_token(token) is False
