from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from src.models import SavingsGoal, GoalTransaction

class GoalService:
    def create_goal(
        self,
        db: Session,
        user_id: int,
        name: str,
        target: int,
        deadline: Optional[date] = None,
        description: Optional[str] = None,
    ) -> SavingsGoal:
        if not name or not name.strip():
            raise ValueError("Goal name is required.")
        if target <= 0:
            raise ValueError("Goal target must be greater than zero.")

        goal = SavingsGoal(
            user_id=user_id,
            name=name.strip(),
            target_amount=target,
            deadline=deadline,
            description=description,
            current_amount=0,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal

    def get_goals(self, db: Session, user_id: int) -> List[SavingsGoal]:
        return db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).order_by(SavingsGoal.created_at.desc()).all()

    def add_contribution(self, db: Session, user_id: int, goal_id: int, amount: int) -> SavingsGoal:
        if amount <= 0:
            raise ValueError("Contribution amount must be greater than zero.")

        goal = db.query(SavingsGoal).filter(
            SavingsGoal.id == goal_id,
            SavingsGoal.user_id == user_id,
        ).first()
        if not goal:
            raise ValueError("Goal not found")

        gt = GoalTransaction(
            goal_id=goal_id,
            amount=amount,
            type="contribution",
            date=date.today(),
        )
        db.add(gt)
        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.status = "completed"
        db.commit()
        db.refresh(goal)
        return goal

    def withdraw(self, db: Session, user_id: int, goal_id: int, amount: int) -> SavingsGoal:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be greater than zero.")

        goal = db.query(SavingsGoal).filter(
            SavingsGoal.id == goal_id,
            SavingsGoal.user_id == user_id,
        ).first()
        if not goal:
            raise ValueError("Goal not found")
        if amount > goal.current_amount:
            raise ValueError("Withdrawal cannot exceed the saved amount.")

        db.add(GoalTransaction(
            goal_id=goal_id,
            amount=amount,
            type="withdrawal",
            date=date.today(),
        ))
        goal.current_amount -= amount
        if goal.current_amount < goal.target_amount:
            goal.status = "active"
        db.commit()
        db.refresh(goal)
        return goal
