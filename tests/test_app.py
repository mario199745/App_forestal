import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


class StreamlitAppTests(unittest.TestCase):
    def test_all_sections_render_without_exceptions(self):
        initial = AppTest.from_file(str(APP), default_timeout=40).run()
        self.assertFalse(initial.exception)
        pages = list(initial.radio[0].options)
        self.assertEqual(
            pages,
            ["Resumen", "Proyecto Tara Ñan", "INIA", "Metodologia"],
        )
        self.assertNotIn("Taninos", pages)
        self.assertNotIn("Comparacion", pages)
        self.assertNotIn("Tara sitios", pages)
        self.assertNotIn("Tara clima", pages)
        self.assertNotIn("Tara suelos", pages)

        for page in pages:
            app = AppTest.from_file(str(APP), default_timeout=40).run()
            if page != pages[0]:
                app.radio[0].set_value(page).run()
            self.assertFalse(app.exception, f"Error en la seccion {page}")

    def test_tara_project_has_metrics_and_selectors(self):
        app = AppTest.from_file(str(APP), default_timeout=40).run()
        app.radio[0].set_value("Proyecto Tara Ñan").run()
        self.assertFalse(app.exception)
        self.assertGreaterEqual(len(app.metric), 4)
        self.assertGreaterEqual(len(app.selectbox), 2)


if __name__ == "__main__":
    unittest.main()
