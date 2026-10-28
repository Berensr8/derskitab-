"""Demo testleri. Çalıştırma: python -m unittest -v"""

import unittest

from derskitabi import demo


class DemoTesti(unittest.TestCase):
    def test_main_modul_adlarini_golgelemez(self):
        # main() içinde bir modülle aynı adlı değişken atanırsa modül o fonksiyonda kullanılamaz
        # (21 Ekim: "dusuk_oncelik" sayacı demo'yu 3. adımda UnboundLocalError ile durduruyordu)
        moduller = {ad for ad, deger in vars(demo).items() if type(deger).__name__ == "module"}
        self.assertFalse(moduller & set(demo.main.__code__.co_varnames))


if __name__ == "__main__":
    unittest.main()
