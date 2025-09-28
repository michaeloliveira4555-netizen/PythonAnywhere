from ..models.database import db
from ..models.school import School
from sqlalchemy.exc import IntegrityError

class SchoolService:
    @staticmethod
    def create_school(name: str):
        """Cria uma nova escola."""
        if not name:
            return False, "O nome da escola não pode estar vazio."

        try:
            new_school = School(nome=name)
            db.session.add(new_school)
            db.session.commit()
            return True, f"Escola '{name}' criada com sucesso."
        except IntegrityError:
            db.session.rollback()
            return False, f"Uma escola com o nome '{name}' já existe."
        except Exception as e:
            db.session.rollback()
            return False, f"Ocorreu um erro inesperado: {e}"
