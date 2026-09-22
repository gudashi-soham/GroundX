from pathlib import Path
from django.test import TestCase


class AnalyticsCodebaseTest(TestCase):
    def test_analytics_module_does_not_reference_pandas_or_matplotlib(self):
        service_file = Path(__file__).resolve().parent / 'services.py'
        content = service_file.read_text(encoding='utf-8')

        self.assertNotIn('import pandas', content)
        self.assertNotIn('import matplotlib', content)
        self.assertNotIn('pandas', content.lower())
        self.assertNotIn('matplotlib', content.lower())
