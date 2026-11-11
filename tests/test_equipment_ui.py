import os
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from streamlit.testing.v1 import AppTest

from teste_streamlit.database import get_engine, initialize_database, make_engine
from teste_streamlit.models import Equipment, Favorite, User


class EquipmentPageTests(unittest.TestCase):
    def setUp(self) -> None:
        get_engine.clear()
        self.previous_database_url = os.environ.get("DATABASE_URL")
        file_descriptor, self.database_path = tempfile.mkstemp(suffix=".db")
        os.close(file_descriptor)
        os.environ["DATABASE_URL"] = (
            "sqlite+pysqlite:///" + self.database_path.replace("\\", "/")
        )

        engine = make_engine(os.environ["DATABASE_URL"])
        initialize_database(engine)
        with Session(engine) as session:
            teacher = User(
                email="docente@ifc.edu.br",
                full_name="Docente",
                role="teacher",
                password_hash="unused",
            )
            student = User(
                email="discente@estudantes.ifc.edu.br",
                full_name="Discente",
                role="student",
                password_hash="unused",
            )
            session.add_all((teacher, student))
            session.flush()
            equipment = Equipment(name="Scale", category="Medicao")
            session.add(equipment)
            session.flush()
            session.add(Favorite(user_id=student.id, equipment_id=equipment.id))
            session.commit()
            self.teacher_id = teacher.id
            self.student_id = student.id
            self.original_equipment_id = equipment.id
        engine.dispose()

        app_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "teste_streamlit"
            / "app.py"
        )
        self.app = AppTest.from_file(str(app_path))
        self.app.session_state["user_id"] = self.teacher_id
        self.app.run()
        self._navigate(self.app, "Equipamentos")

    def tearDown(self) -> None:
        get_engine().dispose()
        get_engine.clear()
        if self.previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.previous_database_url
        try:
            os.remove(self.database_path)
        except FileNotFoundError:
            pass

    @staticmethod
    def _navigate(app: AppTest, page: str) -> None:
        next(widget for widget in app.radio if widget.label.startswith("Navega")).set_value(
            page
        ).run()

    def _fill_equipment_form(self) -> None:
        values = {
            "Nome do equipamento": "Thermometer",
            "Categoria": "Temperatura",
            "Bancada": "Bench 3",
        }
        for label, value in values.items():
            next(widget for widget in self.app.text_input if widget.label == label).set_value(
                value
            )

    def test_create_clears_form_duplicate_is_blocked_and_delete_cascades(self) -> None:
        self._fill_equipment_form()
        next(
            button
            for button in self.app.button
            if button.label == "Cadastrar equipamento"
        ).click().run()
        self.assertTrue(
            any("cadastrado com sucesso" in item.value for item in self.app.success)
        )
        self.assertEqual(
            next(
                widget
                for widget in self.app.text_input
                if widget.label == "Nome do equipamento"
            ).value,
            "",
        )

        self._fill_equipment_form()
        next(
            button
            for button in self.app.button
            if button.label == "Cadastrar equipamento"
        ).click().run()
        self.assertTrue(
            any("cadastrado nesse local" in item.value for item in self.app.error)
        )

        with Session(get_engine()) as session:
            self.assertEqual(
                len(
                    session.scalars(
                        select(Equipment).where(Equipment.name == "Thermometer")
                    ).all()
                ),
                1,
            )

        next(
            checkbox
            for checkbox in self.app.checkbox
            if checkbox.label.endswith("Scale")
        ).set_value(True)
        next(
            button for button in self.app.button if button.label == "Excluir equipamento"
        ).click().run()
        with Session(get_engine()) as session:
            self.assertIsNone(
                session.get(Equipment, self.original_equipment_id)
            )
            self.assertIsNone(session.scalar(select(Favorite.id)))
        self.assertFalse(self.app.exception)

    def test_student_can_view_but_not_manage_equipment_or_experiments(self) -> None:
        app_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "teste_streamlit"
            / "app.py"
        )
        app = AppTest.from_file(str(app_path))
        app.session_state["user_id"] = self.student_id
        app.run()

        self._navigate(app, "Equipamentos")
        self.assertFalse(any(button.label == "Cadastrar equipamento" for button in app.button))
        self.assertFalse(any(button.label == "Excluir equipamento" for button in app.button))
        self._navigate(app, "Experimentos")
        self.assertFalse(any(button.label == "Cadastrar experimento" for button in app.button))
        self.assertFalse(any(button.label == "Excluir experimento" for button in app.button))
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
