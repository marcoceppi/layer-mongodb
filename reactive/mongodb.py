from charmhelpers.core.hookenv import (
    config,
    status_set,
    open_port,
    close_port,
)

from charmhelpers.core.host import service_restart

from charms.reactive import (
    hook,
    when,
    when_not,
    set_state,
    remove_state,
    main,
)

from charms.layer import mongodb


@when('config.changed.version')
def install():
    cfg = config()
    if mongodb.installed():
        status_set('maintenance',
                   'uninstalling mongodb {}'.format(mongodb.version()))
        m = mongodb.mongodb(cfg.previous('version')).uninstall()
        remove_state('mongodb.installed')
        remove_state('mongodb.ready')

    m = mongodb.mongodb(cfg.get('version'))
    status_set('maintenance', 'installing mongodb')
    m.install()
    set_state('mongodb.installed')


@when('mongodb.installed')
@when_not('mongodb.ready')
def configure():
    c = config()
    m = mongodb.mongodb(c.get('version'))
    m.configure(c)
    service_restart('mongodb')

    if c.changed('port') and c.previous('port'):
        close_port(c.previous('port'))
    open_port(c['port'])

    set_state('mongodb.ready')


@when('config.changed')
@when_not('config.changed.version')
def check_config():
    remove_state('mongodb.ready')


@hook('update-status')
def update_status():
    if mongodb.installed():
        status_set('active', 'mongodb {}'.format(mongodb.version()))
    else:
        status_set('blocked', 'unable to install mongodb')


if __name__ == '__main__':
    main()  # pragma: no cover
