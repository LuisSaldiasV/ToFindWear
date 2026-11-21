"""Pruebas del filtro de estilo: correr con  python test_estilo.py

Cada caso es un titulo real (o tipico) y el grupo donde deberia caer (None = fuera).
Si cambias config.json y algo de aqui falla, el filtro empezo a dejar pasar (o a sacar)
algo que antes estaba bien. Agrega aqui los casos nuevos que se te cuelen.
"""
import unittest

import comparador as c

CFG = c.cargar_cfg()
G = list(c.GRUPOS)

# (titulo, grupo esperado) para tiendas generales (Falabella, Paris, Ripley)
GENERALES = [
    # pantalones: anchos si, ajustados/rectos/cargo no
    ("Jeans Baggy Hombre Azul", "abajo"),
    ("Jeans Wide Leg Negro", "abajo"),
    ("Pantalon Parachute Hombre", "abajo"),
    ("Jeans Carpenter Hombre", "abajo"),
    ("Jorts Baggy Denim", "abajo"),
    ("Jeans Straight Fit Hombre", None),
    ("Jeans Skinny Hombre", None),
    ("Jeans Slim Fit Azul", None),
    ("Jeans Relaxed Fit Hombre", None),
    ("Pantalon Cargo Baggy Hombre", None),
    ("Jeans 511 Slim Levi's", None),
    ("Pantalon Jogger Baggy", None),
    # parte superior: boxy/oversize si, largas no
    ("Polera Boxy Fit Negra", "arriba"),
    ("Polera Oversize Hombre", "arriba"),
    ("Polera Oversize Longline", None),
    # zapatillas
    ("Zapatillas New Balance 9060", "zapatillas"),
    ("Zapatillas Adidas Campus 00s", "zapatillas"),
    ("Zapatillas Nike Air Max Plus TN", "zapatillas"),
    ("Zapatillas Nike Air More Uptempo", "zapatillas"),
    ("Zapatillas Nike Shox TL", "zapatillas"),
    ("Botas Timberland 6 Inch Premium", "zapatillas"),
    ("Botas Dr. Martens 1460", "zapatillas"),
    ("Zapatillas Air Jordan 4 Retro", None),
    ("Zapatillas Jordan 1 Mid", None),
    ("Zapatillas Nike Jumpman", None),
]

# marcas de tu estilo (Kagi, Haze...): entran por tipo de prenda, pero igual con los "nunca"
PROPIAS = [
    ("Polera Basic Black", "arriba"),
    ("Jeans Lavado Gris", "abajo"),
    ("Pantalon Cargo Negro", None),
    ("Jeans Straight Azul", None),
    ("Gorro Beanie Negro", None),
    ("Bolso Tote Logo", None),
]


class Estilo(unittest.TestCase):
    def _casos(self, casos, propia):
        for titulo, esperado in casos:
            with self.subTest(titulo=titulo):
                self.assertEqual(c.clasificar(CFG, titulo, propia, G), esperado)

    def test_tiendas_generales(self):
        self._casos(GENERALES, False)

    def test_marcas_de_tu_estilo(self):
        self._casos(PROPIAS, True)

    def test_marcas_deportivas_fuera_solo_en_ropa(self):
        self.assertTrue(c.marca_excluida(CFG, {"marca": "Nike", "grupo": "arriba"}))
        self.assertTrue(c.marca_excluida(CFG, {"marca": "Under Armour", "grupo": "abajo"}))
        self.assertFalse(c.marca_excluida(CFG, {"marca": "Nike", "grupo": "zapatillas"}))
        self.assertFalse(c.marca_excluida(CFG, {"marca": "Bearcliff", "grupo": "arriba"}))
        self.assertTrue(c.marca_excluida(CFG, {"marca": "Shein", "grupo": "arriba"}))


class Config(unittest.TestCase):
    def test_config_actual_valido(self):
        self.assertEqual(c.validar_cfg(CFG), [])

    def test_detecta_errores(self):
        malo = dict(CFG, marcas_favoritas={"kagi": "15"}, estilo=dict(CFG["estilo"], abajo={"tipo": "jeans"}))
        errores = " ".join(c.validar_cfg(malo))
        self.assertIn("marcas_favoritas", errores)
        self.assertIn("estilo.abajo", errores)


if __name__ == "__main__":
    unittest.main(verbosity=1)
