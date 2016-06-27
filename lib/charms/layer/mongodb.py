
import os
import warnings
import subprocess
import platform
import json

from charmhelpers.fetch import (
    apt_install,
    apt_purge,
    apt_update,
    _run_apt_command,
)

from charmhelpers.core.host import (
    lsb_release,
)


def _as_text(bytestring):
    """Naive conversion of subprocess output to Python string"""
    return bytestring.decode("utf-8", "replace")


# FIXME: Do this as a JSONDecoder, if possible
def clean_json(s):
    return _as_text(s).replace('ISODate(',
                               '').replace(', 1',
                                           '').replace('Timestamp(',
                                                       '').replace(')', '')


def apt_key(key_id):
    subprocess.check_call(['apt-key', 'adv', '--keyserver',
                           'hkps://keyserver.ubuntu.com', '--recv', key_id])


class MongoDB(object):
    upstream_list = '/etc/apt/sources.list.d/mongodb.list'
    config_file = '/etc/mongodb.conf'
    # Juju configuration options used for MongoDB
    config_options = ['dbpath', 'logpath', 'logappend', 'bind_ip', 'port',
                      'journal', 'cpu', 'auth', 'verbose', 'objcheck', 'quota',
                      'oplog', 'nocursors', 'nohints', 'noscripting',
                      'notablescans', 'noprealloc', 'nssize', 'mms-token',
                      'mms-name', 'mms-interval', 'oplogSize', 'opIdMem',
                      'replicaset']
    config_map = {
        # JUJU CFG: MONGO CFG
        'replicaset': 'replSet',
    }

    def __init__(self, source, version=None):
        if source not in self.package_map.keys():
            raise Exception('{0} is not a valid source'.format(source))
        self.source = source
        self.version = version

    def install(self):
        apt_install(self.packages())

    def uninstall(self):
        apt_purge(self.packages())
        _run_apt_command(['apt-get', 'autoremove', '--purge', '--assume-yes'])

    def configure(self, config):
        cfg = {self.config_map.get(k, k): v
               for k, v in iter(config.items()) if k in self.config_options}
        self._render_config(cfg)

    def packages(self):
        return [p.format(self.version) for p in self.package_map[self.source]]

    def add_upstream(self):
        with open(self.upstream_list, 'w') as f:
            distrib = lsb_release()['DISTRIB_CODENAME']
            f.write(self.upstream_repo.format(distrib))

    def _render_config(self, cfg):
        with open(self.config_file, 'w') as f:
            f.write('\n'.join(
                    sorted(['%s = %s' % (k, v) for (k, v) in cfg.items()])))

    def run(self, cmd):
        """Run a mongo command returns result of command as obj"""

        p = subprocess.Popen(["mongo", "--quiet"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(input=cmd.encode('UTF-8'))
        if p.returncode:
            raise IOError("mongo command failed {!r}:\n"
                          "{}".format(cmd, _as_text(err)))
        return json.loads(clean_json(out))

    def init_replicaset(self):
        r = self.run('rs.initiate()')
        if r['ok']:
            return True

        if r['errmsg'] == 'already initialized':
            return True

        return False


class MongoDB20(MongoDB):
    package_map = {
        'upstream': [
            'mongodb-10gen={}',
        ],
        'archive': [
            'mongodb-server',
        ],
    }

    upstream_repo = 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen'

    def install(self):
        if self.source == 'upstream':
            self.add_upstream()
            apt_update()

        super(MongoDB20, self).install()

    def add_upstream(self):
        apt_key('7F0CEB10')
        super(MongoDB20, self).add_upstream()

    def uninstall(self):
        super(MongoDB20, self).uninstall()
        if os.path.exists(self.upstream_list):
            os.unlink(self.upstream_list)


class MongoDB22(MongoDB20):
    pass


class MongoDB24(MongoDB20):
    pass


class MongoDB26(MongoDB20):
    package_map = {
        'upstream': [
            'mongodb-org-server={}',
            'mongodb-org-shell={}',
            'mongodb-org-tools={}',
        ],
        'archive': [
            'mongodb-server',
        ],
    }


class MongoDB30(MongoDB):
    package_map = {
        'upstream': [
            'mongodb-org-server={}',
            'mongodb-org-shell={}',
            'mongodb-org-tools={}',
        ],
    }

    upstream_repo = 'deb http://repo.mongodb.org/apt/ubuntu {0}/mongodb-org/3.0 multiverse'

    def install(self):
        self.add_upstream()
        apt_update()
        super(MongoDB30, self).install()

    def uninstall(self):
        super(MongoDB30, self).uninstall()
        if os.path.exists(self.upstream_list):
            os.unlink(self.upstream_list)


class MongoDB31(MongoDB30):
    package_map = {
        'upstream': [
            'mongodb-org-unstable-server={}',
            'mongodb-org-unstable-shell={}',
            'mongodb-org-unstable-tools={}',
        ],
    }

    upstream_repo = 'deb http://repo.mongodb.org/apt/ubuntu {0}/mongodb-org/3.1 multiverse'


class MongoDB32(MongoDB30):
    upstream_repo = 'deb http://repo.mongodb.org/apt/ubuntu {0}/mongodb-org/3.2 multiverse'

    def add_upstream(self):
        apt_key('EA312927')
        super(MongoDB32, self).add_upstream()


class MongoDBzSeries(MongoDB32):
    package_map = {
        'archive': [
            'mongodb-server',
        ],
    }

    upstream_repo = 'deb http://ppa.launchpad.net/ubuntu-s390x-community/mongodb/ubuntu {0} main'

    def __init__(self, source, version=None):
        lsb = lsb_release()
        year = lsb['DISTRIB_RELEASE'].split('.')[0]
        if int(year) < 16:
            distrib = lsb['DISTRIB_CODENAME']
            raise Exception('{0} is not deployable on zSeries'.format(distrib))

        super(MongoDBzSeries, self).__init__(source, version)

    def add_upstream(self):
        apt_key('3427B191')
        super(MongoDBzSeries, self).add_upstream()


def installed():
    return os.path.isfile('/usr/bin/mongo')


def version():
    if not installed():
        return None
    return subprocess.check_output(
               ['/usr/bin/mongo', '--version'],
               stderr=subprocess.STDOUT).decode('UTF-8').split(': ')[1]


_distro_map = {
    'precise': MongoDB20,
    'trusty': MongoDB24,
    'xenial': MongoDB26,
}


_arch_map = {
    's390x': MongoDBzSeries,
}


def mongodb(ver=None):
    if not ver and installed():
        ver = version()
    if platform.machine() in _arch_map:
        return _arch_map[platform.machine()]('archive')
    if not ver or ver == 'archive':
        distro = lsb_release()['DISTRIB_CODENAME']
        if distro not in _distro_map.keys():
            _msg = 'Unknown distribution: {0}. Please deploy only on: {1}'
            raise Exception(_msg.format(distro, _distro_map.keys()))

        return _distro_map[distro]('archive')

    def subclasses(cls):
        return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                       for g in subclasses(s)]

    def search(version):
        # Does a count down search of version until next lowest match. So
        # long as it doesn't drop below a major version things should be good.
        major, minor = [c for c in version.replace('.', '')[:2]]
        minor_range = reversed(range(0, int(minor) + 1))
        needles = ['MongoDB{0}{1}'.format(major, v) for v in minor_range]

        for needle in needles:
            for m in subclasses(MongoDB):
                if m.__name__ == needle:
                    return m('upstream', version)

        warnings.warn('No viable major version found')
        return None

    return search(ver)
