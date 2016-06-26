
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

    @patch('charms.layer.mongodb.installed')
    @patch('charms.layer.mongodb.version')
    def test_version_search(self, mv, mi):
        mi.return_value = True

        mv.return_value = '2.4.9'
        self.assertEqual(type(mongodb.mongodb()).__name__, 'MongoDB24')

        mv.return_value = '2.6.10'
        self.assertEqual(type(mongodb.mongodb()).__name__, 'MongoDB26')

        mv.return_value = '2.6.10-ubuntu1'
        self.assertEqual(type(mongodb.mongodb()).__name__, 'MongoDB26')

        mv.return_value = '3.2.1'
        self.assertEqual(type(mongodb.mongodb()).__name__, 'MongoDB32')

        mv.return_value = '3.4.1'
        self.assertEqual(type(mongodb.mongodb()).__name__, 'MongoDB32')

        with patch('charms.layer.mongodb.warnings') as mw:
            mv.return_value = '1.0'
            self.assertIsNone(mongodb.mongodb())


    @patch('charms.layer.mongodb.lsb_release')
    @patch('charms.layer.mongodb.platform')
    def test_mongodb_zseries(self, plat, lsb):
        lsb.side_effect = [{'DISTRIB_RELEASE': '16.04'}]
        plat.machine.return_value = 's390x'
        self.assertEqual(type(mongodb.mongodb('archive')).__name__,
                         'MongoDBzSeries')

class MongoDBClassTest(unittest.TestCase):
    def setUp(self):
        mongodb.MongoDB.package_map = {'dummy': ['foo={}', 'baz']}

    def test_mongodb(self):
        m = mongodb.MongoDB('dummy')
        self.assertEqual('dummy', m.source)
        self.assertEqual(None, m.version)

        self.assertRaises(Exception, mongodb.MongoDB, 'archive')

    def test_packages(self):
        m = mongodb.MongoDB('dummy', '9.9')
        self.assertEqual(['foo=9.9', 'baz'], m.packages())

    @patch('charms.layer.mongodb.apt_install')
    def test_install(self, mapt):
        m = mongodb.MongoDB('dummy', '99.9')
        m.install()
        mapt.assert_called_with(['foo=99.9', 'baz'])

    @patch('charms.layer.mongodb.apt_purge')
    @patch('charms.layer.mongodb._run_apt_command')
    def test_uninstall(self, mrac, mapt):
        m = mongodb.MongoDB('dummy', '99.9')
        m.uninstall()
        mapt.assert_called_with(['foo=99.9', 'baz'])
        mrac.assert_called_with(['apt-get', 'autoremove', '--purge', '--assume-yes'])
