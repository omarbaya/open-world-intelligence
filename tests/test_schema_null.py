"""Regression: jsonschema must support nullable COT and optional market values."""
import unittest
from jsonschema import validate
from core.desk_method import schema, SCHEMAS
class NullableSchemaTest(unittest.TestCase):
    def test_macro_nullable_cot(self):
        sample={key:({} if typ is dict else None if isinstance(typ,tuple) else []) for key,typ in SCHEMAS["macro"].items()}
        validate(sample,schema("macro"))
    def test_seven_roles_schema_creation(self):
        for role in SCHEMAS:
            self.assertEqual(schema(role)["type"],"object")
if __name__=="__main__":
    unittest.main()
