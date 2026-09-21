from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class

    def get_by_id(self, db: Session, id: int) -> Optional[T]:
        return db.query(self.model_class).filter(self.model_class.id == id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[T]:
        return db.query(self.model_class).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: dict) -> T:
        db_obj = self.model_class(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: T, obj_in: dict) -> T:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> bool:
        obj = self.get_by_id(db, id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False
