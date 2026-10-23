import sqlite3
import unittest
from compiler import run_optional_rea_release
from contracts.rea_pipeline import PipelineResult

class EntryPointTests(unittest.TestCase):
    def test_default_entrypoint_cannot_dispatch(self):
        calls=[]
        with sqlite3.connect(":memory:") as db:
            result=run_optional_rea_release(
                db,b"candidate",None,None,issuer="nobody",issuer_key=b"",
                destination_id="none",observer_id="none",observer_key=b"",
                dispatch=lambda *_: calls.append(True),
                observe=lambda *_: calls.append("observed"))
        self.assertIsInstance(result,PipelineResult)
        self.assertEqual(result.state,"DRY_RUN")
        self.assertEqual(calls,[])

if __name__ == "__main__":
    unittest.main()
