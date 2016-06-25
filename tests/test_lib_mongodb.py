
import sys
sys.path.append('lib')

import unittest
from mock import patch

from charms.layer import mongodb


class ExtraTest(unittest.TestCase):
    @patch('charms.layer.mongodb.subprocess')
    def test_apt_key(self, sp):
        mongodb.apt_key('1111111')
        sp.check_call.assert_called_with(['apt-key', 'adv', '--keyserver',
            'hkps://keyserver.ubuntu.com', '--recv', '1111111'])

    @patch('charms.layer.mongodb.os')
    def test_installed(self, mos):
        isfile = mos.path.isfile
        isfile.return_value = True
        self.assertTrue(mongodb.installed())
        isfile.assert_called_with('/usr/bin/mongo')

    @patch('charms.layer.mongodb.subprocess')
    @patch('charms.layer.mongodb.installed')
    def test_version(self, mi, sp):
        sp.check_output.return_value = b'mongo: 5.5.9'
        mi.return_value = True
        self.assertEqual(mongodb.version(), '5.5.9')
        mi.return_value = False
        self.assertIsNone(mongodb.version())

class MongoDBTest(unittest.TestCase):
    @patch('charms.layer.mongodb.lsb_release')
    @patch('charms.layer.mongodb.platform')
    def test_mongodb_archive(self, plt, lsb):
        lsb.side_effect = [{'DISTRIB_CODENAME': 'xenial'}]
        self.assertEqual(type(mongodb.mongodb('archive')).__name__, 'MongoDB26')
        lsb.side_effect = [{'DISTRIB_CODENAME': 'trusty'}]
        self.assertEqual(type(mongodb.mongodb('archive')).__name__, 'MongoDB24')
        lsb.side_effect = [{'DISTRIB_CODENAME': 'nogo'}]
        self.assertRaises(Exception, mongodb.mongodb, 'archive')

    @patch('charms.layer.mongodb.platform')
    def test_mongodb_zseries(self, plat):
        plat.machine.return_value = 's390x'
        self.assertEqual(type(mongodb.mongodb('archive')).__name__,
                         'MongoDBzSeries')
