# -*- coding: utf-8 -*-
import os.path
from contextlib import contextmanager
from datetime import date
from fabric.decorators import task, roles
from fabric.operations import local, run, require, get
from fabric.context_managers import cd, prefix
from fabric.colors import green, yellow
from fabric.state import env


def activate():
    return 'source {}/{}'.format(env.config['directory'], env.activate)


def stage_msg(msg):
    return '{}: {}'.format(env.stage, msg)


@contextmanager
def virtualenv(directory=None):
    directory = env.config['directory']

    with cd(directory):
        with prefix(activate()):
            yield


@contextmanager
def manage():
    with prefix('export DJANGO_SETTINGS_MODULE="{}.settings.{}"'.format(env.project, env.config['settings'])):
        with virtualenv(), cd(env.project):
            yield


@task
def staging():
    """Configure staging environment."""
    env.stage = 'staging'
    env.config = env.stages[env.stage]


@task
def stable(tagname=None):
    """Configure staging environment."""
    env.stage = 'stable'
    env.config = env.stages[env.stage]
    env.tagname = tagname


def _enable_disable_apache_site(enable=True):
    if enable:
        run('a2ensite {}'.format(env.config['apache_site']))
    else:
        run('a2dissite {}'.format(env.config['apache_site']))
    run('service apache2 reload')


@roles('root')
@task
def enable_apache():
    _enable_disable_apache_site(True)


@roles('root')
@task
def disable_apache():
    _enable_disable_apache_site(False)


@task
def setup_staticfiles():
    """Create public directories for static and media files."""
    print yellow(stage_msg('Creating static files directories…'))
    with cd(env.config['directory']):
        run('mkdir -p public/{media,static}')


@task
def update_staticfiles():
    """Update static files via collectstatic command."""
    print yellow(stage_msg('Updating static files…'))
    with manage():
        run('python manage.py collectstatic --noinput')


@task
def setup_virtualenv():
    """Create new bare virtual environment."""
    run('virtualenv {}/env'.format(env.config['directory']))


@task
def update_virtualenv():
    """Install new packages to virtual environment."""
    print yellow(stage_msg('Installing packages…'))
    with virtualenv():
        run('pip install -r requirenments.txt')


@task
def update_database():
    """Update static database using South."""
    with manage():
        run('python manage.py syncdb --all --noinput')
        run('python manage.py migrate --fake --noinput')


@task
def pull_database():
    datafile = '{}.json'.format(date.today())
    remote_path = os.path.join(env.config['directory'], 'backup')
    remote_file = os.path.join(remote_path, datafile)
    local_file = datafile
    with manage():
        run('mkdir {}'.format(remote_path))
        run('python manage.py dumpdata > {}'.format(remote_file))
        get(remote_file, local_file)
        run('rm {}'.format(remote_file))
    

@task
def setup_repository():
    """Clone specific branch from repository."""
    require('stage', provided_by=('stable', 'staging'))

    print yellow(stage_msg('Cloning repository…'))
    run('git clone -b {} {} {}'.format(
        env.config['master'], 
        env.repository, 
        env.config['directory']))
    setup_staticfiles()


@task
def deploy():
    """Full deployment of python code via git."""
    require('stage', provided_by=('stable', 'staging'))

    print yellow(stage_msg('Updating local branches…'))
    local('git checkout {}'.format(env.config['master']))
    local('git merge {}'.format(env.config['slave']))
    if env.stage == 'stable' and env.tagname:
        local('git tag -s {}'.format(env.tagname))

    print yellow(stage_msg('Pushing to upstream…'))
    local('git push origin {} --tags'.format(env.config['master']))
    with cd(env.config['directory']):
        run('git fetch')
        run('git fetch --tags')
        run('git merge origin/{}'.format(env.config['master']))
    print green(stage_msg('Complete'))


@task
def restart_wsgi():
    """Restart WSGI server."""
    print yellow(stage_msg('Restarting WSGI process…'))
    run('touch {}/apache/{}'.format(env.config['directory'], env.wsgi))


@task
def setup():
    """Full setup, clone new directory, setup virtualenv and create public
    directories."""
    setup_repository()
    setup_virtualenv()
    setup_staticfiles()


@task
def update():
    """Full update, push/pull new code, update packages in virtualenv, collect
    static files and restart server."""
    deploy()
    update_virtualenv()
    update_staticfiles()
    restart_wsgi()
