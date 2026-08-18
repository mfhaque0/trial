import unittest
from app.services.calculations import ACTIVITY_LEVELS, CalculationError, bmr_for, calculate_assessment, normalise_height, normalise_weight

class CalculationTests(unittest.TestCase):
    def setUp(self): self.data={"age":32,"sex":"female","height_unit":"cm","height":165,"weight":65,"weight_unit":"kg","activity":"moderate","goal":"maintain"}
    def test_height_conversion_all_supported_units(self):
        self.assertEqual(normalise_height({"height_unit":"cm","height":165}),1.65);self.assertEqual(normalise_height({"height_unit":"m","height":1.65}),1.65)
        self.assertAlmostEqual(normalise_height({"height_unit":"in","height":65}),1.651);self.assertAlmostEqual(normalise_height({"height_unit":"ft_in","feet":5,"inches":5}),1.651)
    def test_weight_conversion(self):
        self.assertEqual(normalise_weight({"weight":65,"weight_unit":"kg"}),65);self.assertAlmostEqual(normalise_weight({"weight":143.3,"weight_unit":"lb"}),65,places=1)
    def test_bmi_categories_and_invalid_input(self):
        self.assertEqual(calculate_assessment(self.data)["bmi"]["category"],"Standard range");self.data["weight"]=45;self.assertEqual(calculate_assessment(self.data)["bmi"]["category"],"Below the standard range")
        self.data["weight"]=75;self.assertEqual(calculate_assessment(self.data)["bmi"]["category"],"Above the standard range");self.data["weight"]=0
        with self.assertRaises(CalculationError): calculate_assessment(self.data)
    def test_mifflin_st_jeor_for_each_sex(self): self.assertEqual(bmr_for("female",30,60,1.65),1320);self.assertEqual(bmr_for("male",30,60,1.65),1486)
    def test_all_activity_multipliers_apply_to_tdee(self):
        for activity,(multiplier,_) in ACTIVITY_LEVELS.items(): self.data["activity"]=activity;result=calculate_assessment(self.data);self.assertEqual(result["tdee"],round(result["bmr"]*multiplier))
    def test_goal_adjustments(self):
        maintain=calculate_assessment(self.data)["target"];self.data["goal"]="loss";self.assertEqual(calculate_assessment(self.data)["target"],maintain-300);self.data["goal"]="gain";self.assertEqual(calculate_assessment(self.data)["target"],maintain+250)
    def test_default_and_custom_macros(self):
        self.assertEqual(calculate_assessment(self.data)["macros"]["protein"]["percent"],25);self.data.update(custom_macros=True,macros={"protein":30,"carbs":40,"fat":30});self.assertEqual(calculate_assessment(self.data)["macros"]["protein"]["percent"],30)
        self.data["macros"]={"protein":0,"carbs":70,"fat":30};self.assertEqual(calculate_assessment(self.data)["macros"]["protein"]["grams"],0);self.data["macros"]={"protein":25,"carbs":45,"fat":20}
        with self.assertRaises(CalculationError): calculate_assessment(self.data)
    def test_water_and_low_target_warning(self):
        self.assertEqual(calculate_assessment(self.data)["water_litres"],2.1);self.data.update(height=180,weight=35,goal="loss",activity="sedentary");result=calculate_assessment(self.data);self.assertLess(result["target"],1200);self.assertEqual(result["warnings"][0]["code"],"low_calorie_target")
