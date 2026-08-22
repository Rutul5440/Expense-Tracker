from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Friend, SplitTransaction, SplitParticipant, Expense
from backend.schemas import (
    FriendCreate, FriendResponse,
    SplitTransactionCreate, SplitTransactionResponse, ParticipantResponse,
    SettleUpRequest
)
from backend.auth import get_optional_current_user

router = APIRouter(prefix="/api", tags=["Splits & Friends"])


def calculate_friend_net_balance(db: Session, user_id: Optional[int], friend_id: int) -> float:
    """
    Calculates the net balance for a specific friend relative to the logged-in User.
    > 0: Friend owes User
    < 0: User owes Friend
    """
    query = db.query(SplitTransaction)
    if user_id is not None:
        query = query.filter(SplitTransaction.user_id == user_id)
    else:
        query = query.filter(SplitTransaction.user_id.is_(None))

    transactions = query.all()
    net_balance = 0.0

    for tx in transactions:
        if tx.transaction_type == "EXPENSE":
            # If User paid: find friend's share in participants
            if tx.paid_by_user:
                for p in tx.participants:
                    if p.friend_id == friend_id:
                        net_balance += p.share_amount
            # If Friend paid: find user's share in participants
            elif tx.paid_by_friend_id == friend_id:
                for p in tx.participants:
                    if p.is_user:
                        net_balance -= p.share_amount

        elif tx.transaction_type == "DIRECT_LOAN":
            # User gave money to Friend (User paid)
            if tx.paid_by_user:
                for p in tx.participants:
                    if p.friend_id == friend_id:
                        net_balance += p.share_amount
            # Friend gave money to User (Friend paid)
            elif tx.paid_by_friend_id == friend_id:
                for p in tx.participants:
                    if p.is_user:
                        net_balance -= p.share_amount

        elif tx.transaction_type == "SETTLEMENT":
            # User paid Friend to settle User's debt -> Increases Net (reduces negative)
            if tx.paid_by_user:
                for p in tx.participants:
                    if p.friend_id == friend_id:
                        net_balance += p.share_amount
            # Friend paid User to settle Friend's debt -> Decreases Net (reduces positive)
            elif tx.paid_by_friend_id == friend_id:
                for p in tx.participants:
                    if p.is_user:
                        net_balance -= p.share_amount

    return round(net_balance, 2)


# --- Friends Management Endpoints ---

@router.get("/friends", response_model=List[FriendResponse])
def get_friends(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    query = db.query(Friend)
    if user_id is not None:
        query = query.filter(Friend.user_id == user_id)
    else:
        query = query.filter(Friend.user_id.is_(None))

    friends = query.all()
    response = []
    for f in friends:
        net_bal = calculate_friend_net_balance(db, user_id, f.id)
        f_resp = FriendResponse(
            id=f.id,
            user_id=f.user_id,
            name=f.name,
            email=f.email,
            phone=f.phone,
            created_at=f.created_at,
            net_balance=net_bal
        )
        response.append(f_resp)

    return response


@router.post("/friends", response_model=FriendResponse, status_code=status.HTTP_201_CREATED)
def create_friend(
    payload: FriendCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    friend = Friend(
        name=payload.name.strip(),
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        user_id=user_id
    )
    db.add(friend)
    db.commit()
    db.refresh(friend)

    return FriendResponse(
        id=friend.id,
        user_id=friend.user_id,
        name=friend.name,
        email=friend.email,
        phone=friend.phone,
        created_at=friend.created_at,
        net_balance=0.0
    )


@router.delete("/friends/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_friend(
    friend_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    query = db.query(Friend).filter(Friend.id == friend_id)
    if user_id is not None:
        query = query.filter(Friend.user_id == user_id)

    friend = query.first()
    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found")

    db.delete(friend)
    db.commit()
    return None


# --- Split Transactions Endpoints ---

@router.get("/splits", response_model=List[SplitTransactionResponse])
def get_splits(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    query = db.query(SplitTransaction)
    if user_id is not None:
        query = query.filter(SplitTransaction.user_id == user_id)
    else:
        query = query.filter(SplitTransaction.user_id.is_(None))

    transactions = query.order_by(SplitTransaction.date.desc(), SplitTransaction.id.desc()).all()
    
    result = []
    for tx in transactions:
        paid_by_name = "You" if tx.paid_by_user else (tx.paid_by_friend.name if tx.paid_by_friend else "Unknown")
        participants_resp = []
        for p in tx.participants:
            friend_name = "You" if p.is_user else (p.friend.name if p.friend else "Unknown")
            participants_resp.append(ParticipantResponse(
                id=p.id,
                friend_id=p.friend_id,
                friend_name=friend_name,
                is_user=p.is_user,
                share_amount=round(p.share_amount, 2)
            ))
        
        result.append(SplitTransactionResponse(
            id=tx.id,
            title=tx.title,
            total_amount=round(tx.total_amount, 2),
            transaction_type=tx.transaction_type,
            paid_by_user=tx.paid_by_user,
            paid_by_friend_id=tx.paid_by_friend_id,
            paid_by_name=paid_by_name,
            date=tx.date,
            notes=tx.notes,
            created_at=tx.created_at,
            participants=participants_resp
        ))

    return result


@router.post("/splits", response_model=SplitTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_split_transaction(
    payload: SplitTransactionCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user else None

    # Validate payer
    if not payload.paid_by_user and not payload.paid_by_friend_id:
        raise HTTPException(status_code=400, detail="Must specify who paid (User or Friend)")

    if payload.paid_by_friend_id:
        f_query = db.query(Friend).filter(Friend.id == payload.paid_by_friend_id)
        if user_id is not None:
            f_query = f_query.filter(Friend.user_id == user_id)
        if not f_query.first():
            raise HTTPException(status_code=404, detail="Payer friend not found")

    # Validate participants
    if not payload.participants:
        raise HTTPException(status_code=400, detail="At least one participant is required")

    # Calculate equal share if share_amount not provided
    num_participants = len(payload.participants)
    equal_share = round(payload.total_amount / num_participants, 2)

    split_tx = SplitTransaction(
        user_id=user_id,
        title=payload.title.strip(),
        total_amount=payload.total_amount,
        transaction_type=payload.transaction_type,
        paid_by_user=payload.paid_by_user,
        paid_by_friend_id=payload.paid_by_friend_id,
        date=payload.date,
        notes=payload.notes.strip() if payload.notes else None
    )
    db.add(split_tx)
    db.flush()  # assign split_tx.id

    participants_resp = []
    user_share_amount = 0.0

    for p in payload.participants:
        share = p.share_amount if p.share_amount is not None else equal_share
        participant_model = SplitParticipant(
            transaction_id=split_tx.id,
            is_user=p.is_user,
            friend_id=p.friend_id,
            share_amount=share
        )
        db.add(participant_model)
        db.flush()

        friend_name = "You" if p.is_user else None
        if p.friend_id and not p.is_user:
            fr = db.query(Friend).filter(Friend.id == p.friend_id).first()
            if fr:
                friend_name = fr.name

        if p.is_user:
            user_share_amount = share

        participants_resp.append(ParticipantResponse(
            id=participant_model.id,
            friend_id=p.friend_id,
            friend_name=friend_name or "Unknown",
            is_user=p.is_user,
            share_amount=share
        ))

    # Optional: Log user's share into personal expense tracker
    if payload.log_as_personal_expense and payload.category_id and user_share_amount > 0:
        exp = Expense(
            amount=user_share_amount,
            category_id=payload.category_id,
            user_id=user_id,
            description=f"[Split] {payload.title}",
            date=payload.date
        )
        db.add(exp)

    db.commit()
    db.refresh(split_tx)

    paid_by_name = "You" if split_tx.paid_by_user else (
        split_tx.paid_by_friend.name if split_tx.paid_by_friend else "Unknown"
    )

    return SplitTransactionResponse(
        id=split_tx.id,
        title=split_tx.title,
        total_amount=split_tx.total_amount,
        transaction_type=split_tx.transaction_type,
        paid_by_user=split_tx.paid_by_user,
        paid_by_friend_id=split_tx.paid_by_friend_id,
        paid_by_name=paid_by_name,
        date=split_tx.date,
        notes=split_tx.notes,
        created_at=split_tx.created_at,
        participants=participants_resp
    )


@router.post("/splits/settle", response_model=SplitTransactionResponse, status_code=status.HTTP_201_CREATED)
def settle_up(
    payload: SettleUpRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user else None

    # Check friend exists
    friend_query = db.query(Friend).filter(Friend.id == payload.friend_id)
    if user_id is not None:
        friend_query = friend_query.filter(Friend.user_id == user_id)
    friend = friend_query.first()
    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found")

    # Determine direction of settlement based on current net balance
    net_bal = calculate_friend_net_balance(db, user_id, payload.friend_id)

    # If Net > 0 (Friend owes User), Friend is paying User to settle.
    # If Net < 0 (User owes Friend), User is paying Friend to settle.
    # Default to User paying if net balance is 0 or negative.
    if net_bal > 0:
        paid_by_user = False
        paid_by_friend_id = payload.friend_id
        participant_is_user = True
        participant_friend_id = None
    else:
        paid_by_user = True
        paid_by_friend_id = None
        participant_is_user = False
        participant_friend_id = payload.friend_id

    split_tx = SplitTransaction(
        user_id=user_id,
        title=f"Settlement with {friend.name}",
        total_amount=payload.amount,
        transaction_type="SETTLEMENT",
        paid_by_user=paid_by_user,
        paid_by_friend_id=paid_by_friend_id,
        date=date.today(),
        notes=payload.notes
    )
    db.add(split_tx)
    db.flush()

    participant = SplitParticipant(
        transaction_id=split_tx.id,
        is_user=participant_is_user,
        friend_id=participant_friend_id,
        share_amount=payload.amount
    )
    db.add(participant)
    db.commit()
    db.refresh(split_tx)

    paid_by_name = "You" if split_tx.paid_by_user else friend.name
    participant_name = "You" if participant.is_user else friend.name

    return SplitTransactionResponse(
        id=split_tx.id,
        title=split_tx.title,
        total_amount=split_tx.total_amount,
        transaction_type=split_tx.transaction_type,
        paid_by_user=split_tx.paid_by_user,
        paid_by_friend_id=split_tx.paid_by_friend_id,
        paid_by_name=paid_by_name,
        date=split_tx.date,
        notes=split_tx.notes,
        created_at=split_tx.created_at,
        participants=[
            ParticipantResponse(
                id=participant.id,
                friend_id=participant.friend_id,
                friend_name=participant_name,
                is_user=participant.is_user,
                share_amount=participant.share_amount
            )
        ]
    )


@router.delete("/splits/{split_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_split_transaction(
    split_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    query = db.query(SplitTransaction).filter(SplitTransaction.id == split_id)
    if user_id is not None:
        query = query.filter(SplitTransaction.user_id == user_id)

    tx = query.first()
    if not tx:
        raise HTTPException(status_code=404, detail="Split transaction not found")

    db.delete(tx)
    db.commit()
    return None
