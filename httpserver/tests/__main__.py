import os
import unittest

loader = unittest.TestLoader()
start_dir = os.path.dirname(__file__)
suite = loader.discover(start_dir)


class NewResult(unittest.TextTestResult):
    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        return doc_first_line or ""


class NewRunner(unittest.TextTestRunner):
    resultclass = NewResult


runner = NewRunner(verbosity=2)
runner.run(suite)
