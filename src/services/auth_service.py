from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from src.models import User
from src.core.security import hash_password, verify_password, validate_password

MAX_FAILED_LOGIN_ATTEMPTS = 5

class AuthService:
    def __init__(self):
        self.current_user: Optional[User] = None

    def register(self, db: Session, username: str, email: str, password: str, display_name: str = "") -> Tuple[bool, str]:
        try:
            validate_password(password)
        except ValueError as exc:
            return False, str(exc)
        if db.query(User).filter(User.username == username).first():
            return False, "Username already exists."
        if db.query(User).filter(User.email == email).first():
            return False, "Email already exists."
        
        hashed = hash_password(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed,
            display_name=display_name
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create default account
        from src.models import Account, Category
        default_acc = Account(user_id=new_user.id, name="Cash", account_type="Cash", currency="UGX", opening_balance=0, current_balance=0)
        db.add(default_acc)
        
        # Create default categories
        categories = [
            ("Food", "expense", "#FF8A65"),
            ("Transport", "expense", "#64B5F6"),
            ("Rent", "expense", "#81C784"),
            ("Utilities", "expense", "#FFD54F"),
            ("Salary", "income", "#4DB6AC"),
            ("Other", "expense", "#E0E0E0")
        ]
        for name, ctype, color in categories:
            db.add(Category(user_id=new_user.id, name=name, type=ctype, color=color))
            
        db.commit()
        return True, "Registration successful."

    def login(self, db: Session, identifier: str, password: str) -> Tuple[bool, str]:
        # Identifier can be email or username
        user = db.query(User).filter((User.username == identifier) | (User.email == identifier)).first()
        
        if not user:
            return False, "Invalid credentials."
        
        if not user.is_active:
            return False, "Account is disabled."
        if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            return False, "Account temporarily locked after repeated failed logins."
            
        if verify_password(user.password_hash, password):
            user.last_login = datetime.now()
            user.failed_login_attempts = 0
            db.commit()
            self.current_user = user
            return True, "Login successful."
        else:
            user.failed_login_attempts += 1
            db.commit()
            return False, "Invalid credentials."

    def logout(self):
        self.current_user = None

    def is_authenticated(self) -> bool:
        return self.current_user is not None
        
    def get_current_user(self) -> Optional[User]:
        return self.current_user
        
auth_service = AuthService() # Singleton instance for session management
