
import sys
import unittest
from mock import patch, MagicMock, call

sys.path.append('.')
sys.path.append('lib')

from reactive import mongodb  # noqa: E402


class MockConfig(MagicMock):
    _d = {'prev': {}, 'cur': {}}

    def previous(self, k):
        return self._d['prev'].get(k)

    def get(self, k, default=None):
        return self._d['cur'].get(k, default)


class ReactiveTestCase(unittest.TestCase):
    patches = ['set_state', 'config', 'remove_state', 'status_set']
    callables = {'config': MockConfig}

    def setUp(self):
        for p in self.patches:
            c = self.callables.get(p, MagicMock)
            a = 'reactive.mongodb.{}'.format(p)
            setattr(self, '{}_mock'.format(p),
                    patch(a, new_callable=c).start())
        super(ReactiveTestCase, self).setUp()

    def tearDown(self):
        for p in self.patches:
            getattr(self, '{}_mock'.format(p)).stop()
        super(ReactiveTestCase, self).tearDown()


class ReactiveTest(ReactiveTestCase):
    @patch('reactive.mongodb.mongodb')
    def test_install(self, mgo):
        mgo.installed.return_value = False
        self.config_mock._d['cur'] = {'version': 'archive'}

        mongodb.install()

        mgo.mongodb.assert_called_with('archive')
        mgo.mongodb.return_value.install.assert_called()
        self.set_state_mock.assert_called_with('mongodb.installed')

    @patch('reactive.mongodb.mongodb')
    def test_install_upstream(self, mgo):
        mgo.installed.return_value = True
        self.config_mock._d['prev'] = {'version': '99.99.99'}
        self.config_mock._d['cur'] = {'version': 'archive'}

        mongodb.install()

        mgo.mongodb.assert_has_calls([
            call('99.99.99'),
            call().uninstall(),
            call('archive'),
            call().install(),
        ])

        self.remove_state_mock.assert_has_calls([
            call('mongodb.installed'),
            call('mongodb.ready'),
        ])
        self.set_state_mock.assert_called_with('mongodb.installed')

    @patch('reactive.mongodb.mongodb')
    @patch('reactive.mongodb.service_restart')
    def test_configure(self, msr, mgo):
        self.config_mock._d['cur'] = {'version': 'archive'}

        mongodb.configure()

        mgo.mongodb.assert_called_with('archive')
        mgo.mongodb.return_value.configure.assert_called()

        msr.assert_called_with('mongodb')

        self.set_state_mock.assert_called_with('mongodb.ready')

    def test_check_config(self):
        mongodb.check_config()
        self.remove_state_mock.assert_called_with('mongodb.ready')

    @patch('reactive.mongodb.mongodb')
    def test_update_status(self, mgo):
        mgo.installed.return_value = False

        mongodb.update_status()

        self.status_set_mock.assert_called_with('blocked',
                                                'unable to install mongodb')

    @patch('reactive.mongodb.mongodb')
    def test_update_status_installed(self, mgo):
        mgo.installed.return_value = True
        mgo.version.return_value = '99.99'

        mongodb.update_status()

        self.status_set_mock.assert_called_with('active', 'mongodb 99.99')
