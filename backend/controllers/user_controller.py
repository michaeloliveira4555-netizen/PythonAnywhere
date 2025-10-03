# backend/controllers/user_controller.py
from __future__ import annotations

import os
import re
import secrets
from datetime import datetime
from typing import Optional as TypingOptional

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    SelectField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Optional

# ===== DB =====
try:
    from app import db
except Exception:  # pragma: no cover
    from backend.app import db  # type: ignore

def _import_first(paths):
    for p in paths:
        try:
            module_path, name = p.split(":")
            mod = __import__(module_path, fromlist=[name])
            return getattr(mod, name)
        except Exception:
            continue
    return None

User = _import_first([
    "backend.models.user:User",
    "app.models.user:User",
])

Escola = _import_first([
    "backend.models.escola:Escola",
    "app.models.escola:Escola",
])

UserSchool = _import_first([
    "backend.models.user_school:UserSchool",
    "app.models.user_school:UserSchool",
])

user_bp = Blueprint("user", __name__, url_prefix="/user")

# ===== Forms (FORMULÁRIO ATUALIZADO) =====
class MeuPerfilForm(FlaskForm):
    nome_completo = StringField('Nome Completo', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])

    # --- CAMPO ALTERADO PARA SelectField ---
    posto_graduacao = SelectField('Posto/Graduação', choices=[
        ('Soldado', 'Soldado'), ('Cabo', 'Cabo'), ('3º Sargento', '3º Sargento'),
        ('2º Sargento', '2º Sargento'), ('1º Sargento', '1º Sargento'),
        ('Tenente', 'Tenente'), ('Capitão', 'Capitão'), ('Major', 'Major'),
        ('Tenente-Coronel', 'Tenente-Coronel'), ('Coronel', 'Coronel')
    ], validators=[DataRequired()])

    current_password = PasswordField('Senha Atual', validators=[Optional()])
    new_password = PasswordField('Nova Senha', validators=[Optional(), EqualTo('confirm_new_password', message='As senhas não correspondem.')])
    confirm_new_password = PasswordField('Confirmar Nova Senha', validators=[Optional()])
    submit = SubmitField('Salvar Alterações')


# ===== Utils =====
def norm_email(v: Optional[str]) -> Optional[str]:
    return v.strip().lower() if v else None

def norm_idfunc(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    return re.sub(r"\D+", "", v.strip()) or None

def ensure_upload_dir(subdir: str) -> str:
    base = current_app.static_folder
    path = os.path.join(base, subdir)
    os.makedirs(path, exist_ok=True)
    return path

def set_password_hash_on_user(user_obj, plain: str):
    if hasattr(user_obj, "set_password") and callable(getattr(user_obj, "set_password")):
        user_obj.set_password(plain)  # type: ignore
    else:
        if hasattr(user_obj, "password_hash"):
            user_obj.password_hash = generate_password_hash(plain)  # type: ignore
        elif hasattr(user_obj, "senha_hash"):
            user_obj.senha_hash = generate_password_hash(plain)  # type: ignore

def first_row(sql: str, **params):
    return db.session.execute(text(sql), params).first()

def exists_in_users_by(column: str, value: str) -> bool:
    sql = f"SELECT 1 FROM users WHERE {column} = :v LIMIT 1"
    return first_row(sql, v=value) is not None

def generate_unique_username(base: str, max_tries: int = 50) -> str:
    """
    Tenta base, base-1, base-2, ... até encontrar um username livre em users.username.
    """
    base = re.sub(r"[^a-z0-9._-]+", "-", base.lower())
    candidate = base or "user"
    if not exists_in_users_by("username", candidate):
        return candidate
    for i in range(1, max_tries + 1):
        candidate = f"{base}-{i}"
        if not exists_in_users_by("username", candidate):
            return candidate
    # fallback: com token curto
    suffix = secrets.token_hex(2)
    candidate = f"{base}-{suffix}"
    return candidate

def insert_user_school(user_id: int, school_id: int, role: str):
    if UserSchool is not None:
        us = UserSchool(user_id=user_id, school_id=school_id, role=role, created_at=datetime.utcnow())  # type: ignore
        db.session.add(us)
        return
    sql = """
    INSERT INTO user_schools (user_id, school_id, role, created_at)
    VALUES (:user_id, :school_id, :role, :created_at)
    """
    db.session.execute(text(sql), {
        "user_id": user_id,
        "school_id": school_id,
        "role": role,
        "created_at": datetime.utcnow(),
    })

# ===== Meu Perfil (ROTA ATUALIZADA) =====
@user_bp.route("/meu-perfil", methods=["GET", "POST"])
@login_required
def meu_perfil():
    form = MeuPerfilForm(obj=current_user)
    if form.validate_on_submit():
        try:
            current_user.nome_completo = form.nome_completo.data
            # --- ATUALIZAÇÃO DO POSTO/GRADUAÇÃO ---
            current_user.posto_graduacao = form.posto_graduacao.data

            # Verifica se o email foi alterado e se já existe
            if form.email.data != current_user.email:
                if exists_in_users_by("email", form.email.data):
                    flash("Este e-mail já está em uso.", "warning")
                    return redirect(url_for("user.meu_perfil"))
                current_user.email = form.email.data

            # Lógica para alteração de senha
            if form.new_password.data:
                if not current_user.check_password(form.current_password.data):
                    flash("A senha atual está incorreta.", "danger")
                else:
                    set_password_hash_on_user(current_user, form.new_password.data)
                    if hasattr(current_user, "must_change_password"):
                        current_user.must_change_password = False
                    flash("Senha alterada com sucesso.", "success")

            db.session.commit()
            flash("Perfil atualizado com sucesso.", "success")
            return redirect(url_for("user.meu_perfil"))

        except IntegrityError:
            db.session.rollback()
            flash("Não foi possível salvar: dados duplicados no banco.", "danger")
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao salvar Meu Perfil")
            flash("Ocorreu um erro ao salvar seu perfil.", "danger")

    return render_template("meu_perfil.html", user=current_user, form=form)

# ===== Criar Administrador da Escola =====
@user_bp.route("/criar-admin", methods=["GET", "POST"])
@login_required
def criar_admin_escola():
    """
    Cria um admin da MESMA escola do usuário atual.
    Resolve automaticamente conflito de username (baseado no e-mail).
    """
    role_atual = getattr(current_user, "role", None)
    if role_atual not in ("admin_escola", "super_admin", "programador"):
        flash("Você não tem permissão para criar administradores.", "danger")
        return redirect(url_for("main.dashboard"))

    escola_id = getattr(current_user, "school_id", None) or getattr(current_user, "escola_id", None)
    if escola_id is None:
        row = first_row("SELECT school_id FROM user_schools WHERE user_id=:uid LIMIT 1", uid=getattr(current_user, "id", 0))
        if row:
            escola_id = row.school_id

    if request.method == "POST":
        try:
            nome = (request.form.get("nome") or "").strip()
            email = norm_email(request.form.get("email"))
            id_func = norm_idfunc(request.form.get("id_func"))
            telefone = (request.form.get("telefone") or "").strip()

            if not nome:
                flash("Informe o nome completo.", "warning")
                return redirect(url_for("user.criar_admin_escola"))
            if not email:
                flash("Informe um e-mail válido.", "warning")
                return redirect(url_for("user.criar_admin_escola"))
            if not id_func:
                flash("Informe a ID Func (apenas números).", "warning")
                return redirect(url_for("user.criar_admin_escola"))
            if not escola_id:
                flash("Não foi possível identificar a escola do usuário atual.", "danger")
                return redirect(url_for("user.criar_admin_escola"))

            base_username = (email.split("@")[0] if "@" in email else email)
            username = generate_unique_username(base_username)

            # Checagens duras em email / matricula
            if exists_in_users_by("email", email):
                flash("E-mail já está em uso na tabela de usuários.", "warning")
                return redirect(url_for("user.criar_admin_escola"))
            if exists_in_users_by("id_func", id_func):
                flash("ID Func já está em uso na tabela de usuários.", "warning")
                return redirect(url_for("user.criar_admin_escola"))

            temp_pass = secrets.token_urlsafe(8)
            password_hash = generate_password_hash(temp_pass)

            if User is None:
                insert_sql = """
                    INSERT INTO users
                        (id_func, username, email, password_hash, nome_completo, role, is_active, must_change_password)
                    VALUES
                        (:id_func, :username, :email, :password_hash, :nome, :role, 1, 1)
                """
                db.session.execute(text(insert_sql), {
                    "id_func": id_func,
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "nome": nome,
                    "role": "admin_escola",
                })
                new_id = db.session.execute(text("SELECT last_insert_rowid() AS id")).first().id
                insert_user_school(new_id, escola_id, "admin_escola")
                db.session.commit()
                flash(f"Administrador criado com sucesso. Username: {username} • Senha temporária: {temp_pass}", "success")
                return redirect(url_for("user.lista_admins_escola"))

            user = User()
            if hasattr(user, "id_func"):
                user.id_func = id_func
            if hasattr(user, "username"):
                user.username = username
            if hasattr(user, "email"):
                user.email = email
            if hasattr(user, "nome_completo"):
                user.nome_completo = nome
            if hasattr(user, "role"):
                user.role = "admin_escola"
            if hasattr(user, "is_active"):
                user.is_active = True
            if hasattr(user, "must_change_password"):
                user.must_change_password = True

            set_password_hash_on_user(user, temp_pass)

            db.session.add(user)
            db.session.flush()
            insert_user_school(getattr(user, "id"), escola_id, "admin_escola")
            db.session.commit()

            flash(f"Administrador criado com sucesso. Username: {username} • Senha temporária: {temp_pass}", "success")
            return redirect(url_for("user.lista_admins_escola"))

        except IntegrityError as ie:
            db.session.rollback()
            msg = str(ie.orig) if getattr(ie, "orig", None) else str(ie)
            if "email" in msg.lower():
                flash("Conflito: e-mail já cadastrado.", "danger")
            elif "id_func" in msg.lower():
                flash("Conflito: ID Func já cadastrada.", "danger")
            elif "username" in msg.lower():
                flash("Conflito de username. Tente novamente.", "danger")
            else:
                flash(f"Não foi possível criar (UNIQUE/IntegrityError). Detalhe: {msg}", "danger")
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Erro ao criar administrador de escola")
            flash("Ocorreu um erro ao criar o administrador.", "danger")

    return render_template("criar_admin_escola.html")

# ===== Listar Admins da escola =====
@user_bp.route("/admins", methods=["GET"])
@login_required
def lista_admins_escola():
    rows = db.session.execute(text("""
        SELECT u.*
        FROM users u
        JOIN user_schools us ON us.user_id = u.id
        WHERE us.school_id = (
            SELECT school_id FROM user_schools WHERE user_id=:uid LIMIT 1
        )
          AND us.role = 'admin_escola'
        ORDER BY u.nome_completo COLLATE NOCASE
    """), {"uid": getattr(current_user, "id", 0)}).mappings().all()

    return render_template("listar_admins_escola.html", admins=rows)
