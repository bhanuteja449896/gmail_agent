"""Authentication and authorization system."""

import logging
import hashlib
import hmac
import secrets
import time
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import jwt
import json

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Permission types."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_LOGS = "view_logs"
    EXPORT = "export"
    IMPORT = "import"


class Role(Enum):
    """User roles."""
    GUEST = "guest"
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


@dataclass
class TokenData:
    """Token data."""
    user_id: str
    token_type: str
    issued_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = None
    permissions: List[Permission] = field(default_factory=list)
    claims: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass
class User:
    """User data class."""
    id: str
    username: str
    email: str
    password_hash: str
    role: Role = Role.USER
    permissions: Set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    active: bool = True
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions],
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "active": self.active,
            "mfa_enabled": self.mfa_enabled
        }


class PasswordHasher:
    """Hash and verify passwords."""
    
    ALGORITHM = "sha256"
    ITERATIONS = 100000
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple:
        """Hash password with salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        
        key = hashlib.pbkdf2_hmac(
            PasswordHasher.ALGORITHM,
            password.encode(),
            salt.encode(),
            PasswordHasher.ITERATIONS
        )
        
        return salt + key.hex(), salt
    
    @staticmethod
    def verify_password(password: str, hash_with_salt: str) -> bool:
        """Verify password."""
        try:
            salt = hash_with_salt[:32]
            stored_hash = hash_with_salt[32:]
            
            _, computed_hash = PasswordHasher.hash_password(password, salt)
            _, computed_hash_hex = PasswordHasher.hash_password(password, salt)
            
            return hmac.compare_digest(stored_hash, computed_hash_hex[32:])
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False


class TokenManager:
    """Manage authentication tokens."""
    
    def __init__(self, secret_key: str = "secret", algorithm: str = "HS256"):
        """Initialize token manager."""
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_blacklist: Set[str] = set()
        self.token_cache: Dict[str, TokenData] = {}
    
    def generate_token(self, user_id: str, duration_hours: int = 24,
                      permissions: List[Permission] = None,
                      claims: Dict[str, Any] = None) -> str:
        """Generate JWT token."""
        now = datetime.utcnow()
        expires = now + timedelta(hours=duration_hours)
        
        payload = {
            "user_id": user_id,
            "iat": now.timestamp(),
            "exp": expires.timestamp(),
            "permissions": [p.value for p in (permissions or [])],
            "claims": claims or {}
        }
        
        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Generated token for user: {user_id}")
            return token
        except Exception as e:
            logger.error(f"Token generation error: {e}")
            raise
    
    def verify_token(self, token: str) -> bool:
        """Verify token."""
        if token in self.token_blacklist:
            logger.warning("Token is blacklisted")
            return False
        
        try:
            jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return True
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return False
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return False
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """Decode token."""
        if not self.verify_token(token):
            return None
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            return None
    
    def refresh_token(self, token: str, duration_hours: int = 24) -> Optional[str]:
        """Refresh token."""
        payload = self.decode_token(token)
        if not payload:
            return None
        
        user_id = payload.get("user_id")
        permissions = [Permission(p) for p in payload.get("permissions", [])]
        claims = payload.get("claims", {})
        
        return self.generate_token(user_id, duration_hours, permissions, claims)
    
    def revoke_token(self, token: str) -> None:
        """Revoke token."""
        self.token_blacklist.add(token)
        logger.info("Token revoked")
    
    def get_token_info(self, token: str) -> Optional[Dict]:
        """Get token information."""
        return self.decode_token(token)


class RoleManager:
    """Manage roles and permissions."""
    
    def __init__(self):
        """Initialize role manager."""
        self.role_permissions: Dict[Role, Set[Permission]] = self._default_permissions()
    
    def _default_permissions(self) -> Dict[Role, Set[Permission]]:
        """Get default role permissions."""
        return {
            Role.GUEST: {Permission.READ},
            Role.USER: {Permission.READ, Permission.WRITE},
            Role.MODERATOR: {
                Permission.READ, Permission.WRITE, Permission.DELETE,
                Permission.VIEW_LOGS
            },
            Role.ADMIN: set(Permission),
            Role.SUPERADMIN: set(Permission)
        }
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get permissions for role."""
        return self.role_permissions.get(role, set()).copy()
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check if role has permission."""
        return permission in self.get_role_permissions(role)
    
    def add_permission_to_role(self, role: Role, permission: Permission) -> None:
        """Add permission to role."""
        if role not in self.role_permissions:
            self.role_permissions[role] = set()
        self.role_permissions[role].add(permission)
    
    def remove_permission_from_role(self, role: Role, permission: Permission) -> None:
        """Remove permission from role."""
        if role in self.role_permissions:
            self.role_permissions[role].discard(permission)


class UserManager:
    """Manage users."""
    
    def __init__(self, role_manager: RoleManager):
        """Initialize user manager."""
        self.users: Dict[str, User] = {}
        self.role_manager = role_manager
    
    def create_user(self, user_id: str, username: str, email: str,
                   password: str, role: Role = Role.USER) -> User:
        """Create user."""
        if user_id in self.users:
            raise ValueError(f"User already exists: {user_id}")
        
        password_hash, _ = PasswordHasher.hash_password(password)
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            permissions=self.role_manager.get_role_permissions(role)
        )
        
        self.users[user_id] = user
        logger.info(f"Created user: {user_id}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user."""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        for user in self.users.values():
            if user.email == email:
                return user
        return None
    
    def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """Update user."""
        user = self.get_user(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        logger.info(f"Updated user: {user_id}")
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        if user_id in self.users:
            del self.users[user_id]
            logger.info(f"Deleted user: {user_id}")
            return True
        return False
    
    def verify_password(self, user_id: str, password: str) -> bool:
        """Verify user password."""
        user = self.get_user(user_id)
        if not user:
            return False
        
        return PasswordHasher.verify_password(password, user.password_hash)
    
    def change_password(self, user_id: str, new_password: str) -> bool:
        """Change user password."""
        user = self.get_user(user_id)
        if not user:
            return False
        
        password_hash, _ = PasswordHasher.hash_password(new_password)
        user.password_hash = password_hash
        logger.info(f"Changed password for user: {user_id}")
        return True
    
    def list_users(self) -> List[User]:
        """List all users."""
        return list(self.users.values())


class Session:
    """User session."""
    
    def __init__(self, session_id: str, user_id: str, token: str):
        """Initialize session."""
        self.session_id = session_id
        self.user_id = user_id
        self.token = token
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.active = True
    
    def is_valid(self, timeout_minutes: int = 30) -> bool:
        """Check if session is valid."""
        if not self.active:
            return False
        
        elapsed = (datetime.now() - self.last_activity).total_seconds() / 60
        return elapsed < timeout_minutes
    
    def update_activity(self) -> None:
        """Update last activity."""
        self.last_activity = datetime.now()


class SessionManager:
    """Manage user sessions."""
    
    def __init__(self, timeout_minutes: int = 30):
        """Initialize session manager."""
        self.sessions: Dict[str, Session] = {}
        self.timeout_minutes = timeout_minutes
    
    def create_session(self, user_id: str, token: str) -> Session:
        """Create session."""
        session_id = secrets.token_hex(16)
        session = Session(session_id, user_id, token)
        self.sessions[session_id] = session
        logger.info(f"Created session for user: {user_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session."""
        session = self.sessions.get(session_id)
        if session and session.is_valid(self.timeout_minutes):
            session.update_activity()
            return session
        return None
    
    def end_session(self, session_id: str) -> None:
        """End session."""
        if session_id in self.sessions:
            self.sessions[session_id].active = False
            logger.info(f"Ended session: {session_id}")
    
    def end_user_sessions(self, user_id: str) -> None:
        """End all sessions for user."""
        for session in self.sessions.values():
            if session.user_id == user_id:
                session.active = False
        logger.info(f"Ended all sessions for user: {user_id}")
    
    def cleanup_expired(self) -> int:
        """Clean up expired sessions."""
        expired_ids = [
            sid for sid, session in self.sessions.items()
            if not session.is_valid(self.timeout_minutes)
        ]
        
        for sid in expired_ids:
            del self.sessions[sid]
        
        logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
        return len(expired_ids)


class AuditLog:
    """Audit log entry."""
    
    def __init__(self, user_id: str, action: str, resource: str,
                 details: Dict[str, Any] = None):
        """Initialize audit log."""
        self.id = secrets.token_hex(8)
        self.user_id = user_id
        self.action = action
        self.resource = resource
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class AuditLogManager:
    """Manage audit logs."""
    
    def __init__(self, max_logs: int = 10000):
        """Initialize audit log manager."""
        self.logs: List[AuditLog] = []
        self.max_logs = max_logs
    
    def log_action(self, user_id: str, action: str, resource: str,
                  details: Dict[str, Any] = None) -> AuditLog:
        """Log action."""
        log = AuditLog(user_id, action, resource, details)
        self.logs.append(log)
        
        # Keep only recent logs
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        logger.debug(f"Logged action: {action} on {resource} by {user_id}")
        return log
    
    def get_logs(self, user_id: str = None, action: str = None) -> List[AuditLog]:
        """Get logs."""
        logs = self.logs
        
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]
        
        if action:
            logs = [l for l in logs if l.action == action]
        
        return logs
    
    def clear_logs(self) -> None:
        """Clear logs."""
        self.logs.clear()


class AuthenticationService:
    """Main authentication service."""
    
    def __init__(self, secret_key: str = "secret"):
        """Initialize service."""
        self.token_manager = TokenManager(secret_key)
        self.role_manager = RoleManager()
        self.user_manager = UserManager(self.role_manager)
        self.session_manager = SessionManager()
        self.audit_log = AuditLogManager()
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user."""
        user = self.user_manager.get_user_by_username(username)
        
        if not user or not user.active:
            self.audit_log.log_action("unknown", "login_failed", "auth", 
                                     {"reason": "user_not_found"})
            return None
        
        if not self.user_manager.verify_password(user.id, password):
            self.audit_log.log_action(user.id, "login_failed", "auth",
                                     {"reason": "invalid_password"})
            return None
        
        # Generate token
        permissions = self.role_manager.get_role_permissions(user.role)
        token = self.token_manager.generate_token(user.id, permissions=list(permissions))
        
        # Create session
        session = self.session_manager.create_session(user.id, token)
        
        # Update last login
        user.last_login = datetime.now()
        
        # Log action
        self.audit_log.log_action(user.id, "login_success", "auth")
        
        logger.info(f"User authenticated: {user.id}")
        return token
    
    def logout(self, token: str, user_id: str) -> None:
        """Logout user."""
        self.token_manager.revoke_token(token)
        self.session_manager.end_user_sessions(user_id)
        self.audit_log.log_action(user_id, "logout", "auth")
        logger.info(f"User logged out: {user_id}")
    
    def verify_authorization(self, token: str, required_permission: Permission) -> bool:
        """Verify user is authorized."""
        payload = self.token_manager.decode_token(token)
        if not payload:
            return False
        
        permissions = [Permission(p) for p in payload.get("permissions", [])]
        return required_permission in permissions
