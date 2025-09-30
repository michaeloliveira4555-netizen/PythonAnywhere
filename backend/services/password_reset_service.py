import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from flask import current_app
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import joinedload

from ..models.database import db
from ..models.user import User
from ..models.user_school import UserSchool
from ..models.password_reset_token import PasswordResetToken
from ..models.password_reset_request import PasswordResetRequest


class PasswordResetService:
    DEFAULT_EXP_MINUTES = 30

    STATUS_PENDING = PasswordResetRequest.STATUS_PENDING
    STATUS_COMPLETED = PasswordResetRequest.STATUS_COMPLETED
    STATUS_CANCELLED = PasswordResetRequest.STATUS_CANCELLED

    @staticmethod
    def _random_token(length: int = 12) -> str:
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def _get_admins_for_user(user: User) -> List[User]:
        school_links = db.session.scalars(
            select(UserSchool).where(UserSchool.user_id == user.id)
        ).all()
        if not school_links:
            return []

        admin_ids = set()
        admins: List[User] = []
        for link in school_links:
            candidates = db.session.scalars(
                select(User)
                .join(UserSchool, UserSchool.user_id == User.id)
                .where(
                    UserSchool.school_id == link.school_id,
                    User.role == 'admin_escola'
                )
            ).all()
            for admin in candidates:
                if admin.id not in admin_ids:
                    admin_ids.add(admin.id)
                    admins.append(admin)
        return admins

    @staticmethod
    def _get_super_admins() -> List[User]:
        return db.session.scalars(
            select(User).where(User.role.in_(['super_admin', 'programador']))
        ).all()

    @staticmethod
    def request_password_reset(matricula: str) -> Tuple[bool, str]:
        matricula = (matricula or '').strip()
        if not matricula:
            return False, 'Informe uma matrícula válida.'

        user = db.session.execute(
            select(User).filter_by(matricula=matricula)
        ).scalar_one_or_none()

        if not user:
            return True, 'Se a matrícula estiver cadastrada, o administrador receberá o pedido.'

        admins = PasswordResetService._get_admins_for_user(user)
        if not admins:
            admins = PasswordResetService._get_super_admins()

        if not admins:
            current_app.logger.warning('Nenhum administrador encontrado para reset de %s', matricula)
            return False, 'Não foi possível encaminhar a solicitação. Contate o suporte.'

        created = 0
        for admin in admins:
            existing = db.session.scalar(
                select(PasswordResetRequest)
                .where(
                    PasswordResetRequest.user_id == user.id,
                    PasswordResetRequest.admin_id == (admin.id if admin else None),
                    PasswordResetRequest.status == PasswordResetService.STATUS_PENDING
                )
            )
            if existing:
                continue

            req = PasswordResetRequest(
                user_id=user.id,
                admin_id=admin.id if admin else None,
                status=PasswordResetService.STATUS_PENDING
            )
            db.session.add(req)
            created += 1

        if created:
            db.session.commit()
        else:
            db.session.rollback()

        return True, 'Solicitação registrada. O administrador entrará em contato com uma senha temporária.'

    @staticmethod
    def get_requests_for_admin(admin_user: User, status: str = STATUS_PENDING) -> list[PasswordResetRequest]:
        query = (
            select(PasswordResetRequest)
            .options(
                joinedload(PasswordResetRequest.user).joinedload(User.user_schools).joinedload(UserSchool.school),
                joinedload(PasswordResetRequest.admin),
                joinedload(PasswordResetRequest.processed_by_admin)
            )
            .order_by(PasswordResetRequest.created_at.desc())
        )

        if status in {PasswordResetService.STATUS_PENDING, PasswordResetService.STATUS_COMPLETED, PasswordResetService.STATUS_CANCELLED}:
            query = query.where(PasswordResetRequest.status == status)

        if admin_user.role in ['super_admin', 'programador']:
            return db.session.scalars(query).unique().all()

        school_ids = [link.school_id for link in admin_user.user_schools]
        conditions = [PasswordResetRequest.admin_id == admin_user.id]

        if school_ids:
            subquery = select(UserSchool.user_id).where(UserSchool.school_id.in_(school_ids))
            conditions.append(
                and_(
                    PasswordResetRequest.admin_id.is_(None),
                    PasswordResetRequest.user_id.in_(subquery)
                )
            )

        query = query.where(or_(*conditions))
        return db.session.scalars(query).unique().all()

    @staticmethod
    def process_request(request_id: int, admin_user: User) -> Tuple[bool, str, Optional[str]]:
        request = db.session.get(PasswordResetRequest, request_id)
        if not request:
            return False, 'Solicitação não encontrada.', None

        if request.status != PasswordResetService.STATUS_PENDING:
            return False, 'A solicitação já foi processada.', None

        if request.admin_id and request.admin_id != admin_user.id and admin_user.role not in ['super_admin', 'programador']:
            return False, 'Você não possui permissão para processar esta solicitação.', None

        user = request.user
        if not user:
            request.mark_cancelled(admin_user.id)
            db.session.commit()
            return False, 'Usuário associado não encontrado.', None

        temp_password = PasswordResetService._random_token(10)
        user.set_password(temp_password)
        user.must_change_password = True

        if not request.admin_id:
            request.admin_id = admin_user.id
        request.mark_completed(admin_user.id)

        PasswordResetService._cancel_other_pending_requests(user.id, request.id, admin_user.id)

        db.session.commit()
        return True, 'Senha temporária gerada com sucesso!', temp_password

    @staticmethod
    def cancel_request(request_id: int, admin_user: User) -> Tuple[bool, str]:
        request = db.session.get(PasswordResetRequest, request_id)
        if not request:
            return False, 'Solicitação não encontrada.'

        if request.status != PasswordResetService.STATUS_PENDING:
            return False, 'A solicitação já foi processada.'

        if request.admin_id and request.admin_id != admin_user.id and admin_user.role not in ['super_admin', 'programador']:
            return False, 'Você não possui permissão para cancelar esta solicitação.'

        request.mark_cancelled(admin_user.id)
        db.session.commit()
        return True, 'Solicitação cancelada com sucesso.'

    @staticmethod
    def _cancel_other_pending_requests(user_id: int, current_request_id: int, admin_id: int) -> None:
        others = db.session.scalars(
            select(PasswordResetRequest)
            .where(
                PasswordResetRequest.user_id == user_id,
                PasswordResetRequest.status == PasswordResetService.STATUS_PENDING,
                PasswordResetRequest.id != current_request_id
            )
        ).all()
        for req in others:
            req.mark_cancelled(admin_id)

    # Métodos legados mantidos para compatibilidade interna --------------------------------
    @staticmethod
    def generate_token_for_user(user_id: int, admin_id: int | None = None, exp_minutes: int | None = None) -> str:
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError('Usuário não encontrado.')

        minutes = exp_minutes or int(os.environ.get('PASSWORD_RESET_TOKEN_EXP_MIN', PasswordResetService.DEFAULT_EXP_MINUTES))
        raw = PasswordResetService._random_token()
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=PasswordResetToken.hash_token(raw),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
            created_by_admin_id=admin_id
        )
        db.session.add(token)
        db.session.commit()
        return raw

    @staticmethod
    def consume_with_user_and_raw_token(matricula: str, raw_token: str) -> Optional[User]:
        user = db.session.execute(db.select(User).filter_by(matricula=matricula)).scalar_one_or_none()
        if not user:
            return None

        token = db.session.execute(
            db.select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id)
            .order_by(PasswordResetToken.created_at.desc())
        ).scalars().first()

        if not token or not token.is_usable():
            return None

        if not token.verify_token(raw_token):
            token.attempts += 1
            db.session.commit()
            return None

        token.used_at = datetime.now(timezone.utc)
        db.session.commit()
        return user


