import re
import unittest
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from teste_streamlit.auth import (
    AuthenticationError,
    authenticate,
    register_user,
    request_password_reset,
    reset_password,
)
from teste_streamlit.database import initialize_database, make_engine
from teste_streamlit.models import Equipment, Favorite, Folder


class AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = make_engine("sqlite+pysqlite:///:memory:")
        initialize_database(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_registration_assigns_role_from_institutional_domain(self) -> None:
        teacher = register_user(
            self.session, "Docente", "docente@ifc.edu.br", "senha-docente-123"
        )
        student = register_user(
            self.session,
            "Discente",
            "discente@estudantes.ifc.edu.br",
            "senha-discente-123",
            role="student",
        )
        self.session.commit()

        self.assertEqual(teacher.role, "teacher")
        self.assertEqual(student.role, "student")
        self.assertEqual(
            authenticate(self.session, teacher.email, "senha-docente-123").id,
            teacher.id,
        )
        with self.assertRaises(AuthenticationError):
            authenticate(self.session, teacher.email, "senha-incorreta")
        with self.assertRaises(AuthenticationError):
            register_user(
                self.session,
                "Discente",
                "discente@estudantes.ifc.edu.br",
                "senha-discente-123",
                role="teacher",
            )

    def test_registration_rejects_non_institutional_email(self) -> None:
        for email in ("pessoa@example.com", "@ifc.edu.br", "nome com espaço@ifc.edu.br"):
            with self.subTest(email=email), self.assertRaises(AuthenticationError):
                register_user(self.session, "Visitante", email, "senha-segura-123")

    def test_password_reset_token_can_only_be_used_once(self) -> None:
        user = register_user(
            self.session, "Docente", "docente@ifc.edu.br", "senha-docente-123"
        )
        self.session.commit()

        with patch("teste_streamlit.auth._send_email") as send_email:
            self.assertTrue(request_password_reset(self.session, user.email))
            self.session.commit()
        email_body = send_email.call_args.args[2]
        token_match = re.search(r"(?m)^([A-Za-z0-9_-]{40,})$", email_body)
        self.assertIsNotNone(token_match)
        assert token_match is not None

        reset_password(self.session, user.email, token_match.group(1), "nova-senha-123")
        self.session.commit()
        self.assertEqual(
            authenticate(self.session, user.email, "nova-senha-123").id, user.id
        )
        with self.assertRaises(AuthenticationError):
            reset_password(
                self.session, user.email, token_match.group(1), "outra-senha-123"
            )

    def test_deleting_equipment_removes_its_favorites(self) -> None:
        student = register_user(
            self.session,
            "Discente",
            "discente@estudantes.ifc.edu.br",
            "senha-discente-123",
        )
        equipment = Equipment(name="Multímetro")
        folder = Folder(user_id=student.id, name="Eletricidade")
        self.session.add_all((equipment, folder))
        self.session.flush()
        self.session.add(
            Favorite(
                user_id=student.id,
                equipment_id=equipment.id,
                folder_id=folder.id,
            )
        )
        self.session.commit()

        self.session.delete(equipment)
        self.session.commit()
        self.assertIsNone(self.session.scalar(select(Favorite.id)))


if __name__ == "__main__":
    unittest.main()
