import os
import unittest

loader = unittest.TestLoader()
start_dir = os.path.dirname(__file__)
suite = loader.discover(start_dir)

runner = unittest.TextTestRunner()
runner.run(suite)
