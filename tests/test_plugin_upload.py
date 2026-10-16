"""The optional uploader must reject entity expansion in XML-RPC responses."""
# SPDX-License-Identifier: BSD-3-Clause
import importlib.util
from pathlib import Path
import unittest

from defusedxml.common import EntitiesForbidden

spec = importlib.util.spec_from_file_location(
    'plugin_upload', Path(__file__).resolve().parents[1] / 'plugin_upload.py')
uploader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uploader)


class UploadParserTests(unittest.TestCase):
    def test_xml_entity_expansion_is_rejected(self):
        response = '''<?xml version="1.0"?>
<!DOCTYPE methodResponse [<!ENTITY injected "expanded">]>
<methodResponse><params><param><value><string>&injected;</string></value>
</param></params></methodResponse>'''
        with self.assertRaises(EntitiesForbidden):
            uploader.xmlrpc.client.loads(response)

    def test_regular_response_is_supported(self):
        response = uploader.xmlrpc.client.dumps(('plugin-id',),
                                                methodresponse=True)
        values, method = uploader.xmlrpc.client.loads(response)
        self.assertEqual(values, ('plugin-id',))
        self.assertIsNone(method)


if __name__ == '__main__':
    unittest.main()
