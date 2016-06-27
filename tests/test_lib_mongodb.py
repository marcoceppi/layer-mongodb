
import sys
sys.path.append('lib')

import json
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

    def test_as_text(self):
        self.assertEqual('yoooo', mongodb._as_text('yoooo'.encode('UTF-8')))

    def test_clean_json(self):
        mock_json = b'''
        {
            "set" : "test",
            "date" : ISODate("2016-06-26T17:41:09Z"),
            "myState" : 3,
            "members" : [
                {
                    "optime" : Timestamp(1466903785, 1),
                    "optimeDate" : ISODate("2016-06-26T01:16:25Z")
                }
            ],
            "ok" : 1
        }'''

        self.assertEqual('2016-06-26T17:41:09Z',
                         json.loads(mongodb.clean_json(mock_json))['date'])


class MongoDBMethodTest(unittest.TestCase):
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

class MongoDBTest(unittest.TestCase):
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

    @patch('builtins.open')
    def test_render_config(self, mopen):
        output = """baz = foobar\nfoo = bar"""
        m = mongodb.MongoDB('dummy')
        m._render_config({'foo': 'bar', 'baz': 'foobar'})
        mopen.assert_called_with(m.config_file, 'w')
        w = mopen.return_value.__enter__.return_value.write
        w.assert_called_with(output)

    @patch.object(mongodb.MongoDB, '_render_config')
    def test_configure(self, mcfg):
        m = mongodb.MongoDB('dummy')
        m.configure({'dbpath': 'foo', 'replicaset': 'test', 'noop': True})
        mcfg.assert_called_with({'dbpath': 'foo', 'replSet': 'test'})

    @patch('builtins.open')
    @patch('charms.layer.mongodb.lsb_release')
    def test_add_upstream(self, lsb, mopen):
        m = mongodb.MongoDB('dummy')
        m.upstream_repo = 'deb http://localhost {} dummy'

        lsb.side_effect = [{'DISTRIB_CODENAME': 'xenial'}]
        m.add_upstream()

        mopen.assert_called_with(m.upstream_list, 'w')
        w = mopen.return_value.__enter__.return_value.write
        w.assert_called_with('deb http://localhost xenial dummy')

    @patch('charms.layer.mongodb.subprocess')
    def test_run(self, ms):
        mjson = b'''
        {
            "ok": 1
        }'''

        com = ms.Popen.return_value
        com.communicate.return_value = [mjson, None]
        com.returncode = 0

        self.assertEqual({'ok': 1}, mongodb.MongoDB('dummy').run('doit()'))
        com.communicate.assert_called_with(input=b'doit()')

    @patch('charms.layer.mongodb.subprocess')
    def test_failed_run(self, ms):
        com = ms.Popen.return_value
        com.communicate.return_value = [None, b'Err']
        com.returncode = 1

        self.assertRaises(IOError, mongodb.MongoDB('dummy').run, 'fail()')

    @patch.object(mongodb.MongoDB, 'run')
    def test_init_replicaset(self, mrun):
        mrun.return_value = {'ok': 1}
        self.assertTrue(mongodb.MongoDB('dummy').init_replicaset())
        mrun.assert_called_with('rs.initiate()')

    @patch.object(mongodb.MongoDB, 'run')
    def test_already_init_replicaset(self, mrun):
        mrun.return_value = {'ok': 0, 'errmsg': 'already initialized'}
        self.assertTrue(mongodb.MongoDB('dummy').init_replicaset())

    @patch.object(mongodb.MongoDB, 'run')
    def test_failed_init_replicaset(self, mrun):
        mrun.return_value = {'ok': 0, 'errmsg': 'danger will robinson'}
        self.assertFalse(mongodb.MongoDB('dummy').init_replicaset())


class MongoDB20Test(unittest.TestCase):
    @patch('charms.layer.mongodb.apt_key')
    @patch.object(mongodb.MongoDB, 'add_upstream')
    def test_add_upstream(self, mup, mak):
        m = mongodb.MongoDB20('upstream', '2.0.99')
        m.add_upstream()
        mak.assert_called_with('7F0CEB10')
        mup.assert_called_once()

    @patch('charms.layer.mongodb.apt_update')
    @patch.object(mongodb.MongoDB, 'install')
    @patch.object(mongodb.MongoDB20, 'add_upstream')
    def test_install(self, mup, minstall, mau):
        m = mongodb.MongoDB20('upstream', '2.0.99')
        m.install()
        mup.assert_called_once()
        mau.assert_called_once()
        minstall.assert_called_once()

        mup.reset_mock()
        mau.reset_mock()
        minstall.reset_mock()

        m = mongodb.MongoDB20('archive')
        m.install()
        mup.assert_not_called()
        mau.assert_not_called()
        minstall.assert_called_once()

    @patch('charms.layer.mongodb.os')
    @patch.object(mongodb.MongoDB, 'uninstall')
    def test_uninstall(self, muninstall, mos):
        mos.path.exists.return_value = False
        m = mongodb.MongoDB20('upstream', '2.0.99')
        m.uninstall()
        mos.path.exists.assert_called_with(m.upstream_list)
        muninstall.assert_called_once()
        mos.unlink.assert_not_called()

        muninstall.reset_mock()
        mos.unlink.reset_mock()

        mos.path.exists.return_value = True
        m.uninstall()
        muninstall.assert_called_once()
        mos.unlink.assert_called_with(m.upstream_list)


class MongoDB30Test(unittest.TestCase):
    @patch('charms.layer.mongodb.apt_update')
    @patch.object(mongodb.MongoDB, 'install')
    @patch.object(mongodb.MongoDB30, 'add_upstream')
    def test_install(self, mup, minstall, mau):
        m = mongodb.MongoDB30('upstream', '3.0.99')
        m.install()
        mup.assert_called_once()
        mau.assert_called_once()
        minstall.assert_called_once()

    @patch('charms.layer.mongodb.os')
    @patch.object(mongodb.MongoDB, 'uninstall')
    def test_uninstall(self, muninstall, mos):
        mos.path.exists.return_value = False
        m = mongodb.MongoDB30('upstream', '3.0.99')
        m.uninstall()
        mos.path.exists.assert_called_with(m.upstream_list)
        muninstall.assert_called_once()
        mos.unlink.assert_not_called()

        muninstall.reset_mock()
        mos.unlink.reset_mock()

        mos.path.exists.return_value = True
        m.uninstall()
        muninstall.assert_called_once()
        mos.unlink.assert_called_with(m.upstream_list)


class MongoDB32Test(unittest.TestCase):
    @patch('charms.layer.mongodb.apt_key')
    @patch.object(mongodb.MongoDB, 'add_upstream')
    def test_add_upstream(self, mup, mak):
        m = mongodb.MongoDB32('upstream', '3.2.99')
        m.add_upstream()
        mak.assert_called_with('EA312927')
        mup.assert_called_once()


class MongoDBZSeriesTest(unittest.TestCase):
    @patch('charms.layer.mongodb.lsb_release')
    @patch.object(mongodb.MongoDB32, '__init__')
    def test_init(self, minit, lsb):
        lsb.return_value = {'DISTRIB_RELEASE': '16.04'}
        m = mongodb.MongoDBzSeries('archive')
        minit.assert_called_once()

        minit.reset_mock()
        lsb.return_value = {'DISTRIB_RELEASE': '14.10',
                            'DISTRIB_CODENAME': 'utopic'}

        self.assertRaises(Exception, mongodb.MongoDBzSeries, 'archive')
        minit.assert_not_called()


    @patch('charms.layer.mongodb.apt_key')
    @patch('charms.layer.mongodb.lsb_release')
    @patch.object(mongodb.MongoDB32, 'add_upstream')
    def test_add_upstream(self, mup, lsb, mak):
        lsb.return_value = {'DISTRIB_RELEASE': '16.04'}
        m = mongodb.MongoDBzSeries('archive')
        m.add_upstream()
        mak.assert_called_with('3427B191')
        mup.assert_called_once()
