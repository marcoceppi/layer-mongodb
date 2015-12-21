from charmhelpers.core.hookenv import (
    config,
    status_set,
)

from charms.reactive import (
    hook,
    set_state,
    is_state,
    remove_state,
    main,
)

from charms import mongodb

cfg = config()


@hook('install')
def package_setup():
    #if config('source') == 'None':
    #    arm64_trusty_quirk()
    pass


@hook('config-changed')
def configure():
    if cfg.changed('version') and mongodb.installed():
        status_set('maintenance', 'uninstalling previous version')
        m = mongodb.mongodb(cfg.previous('version')).uninstall()
        remove_state('mongodb.installed')

    m = mongodb.mongodb(cfg.get('version'))
    if not mongodb.installed():
        status_set('maintenance', 'installing mongodb')
        m.install()
        set_state('mongodb.installed')

    update_status()


@hook('update-status')
def update_status():
    if mongodb.installed():
        status_set('active', 'mongodb {}'.format(mongodb.version()))
    else:
        status_set('active', 'unknown')


if __name__ == '__main__':
    main()
