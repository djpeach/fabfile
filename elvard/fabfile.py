# -*- coding: utf-8 -*-
from contextlib import contextmanager
from fabric.api import task
from fabric.operations import local, run, require
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
    with prefix('export DJANGO_SETTINGS_MODULE="tomas_ehrlich.settings.{}"'.format(env.config['settings'])):
        with virtualenv(), cd('src'):
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
    with prefix('export DJANGO_SETTINGS_MODULE="tomas_ehrlich.settings.{}"'.format(env.config['settings'])):
        with virtualenv(), cd('src'):
            run('python manage.py syncdb --all --noinput')
            run('python manage.py migrate --fake --noinput')


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
    local('git push origin {} --tags'.format(env.config['master']))

    print yellow(stage_msg('Pushing to upstream…'))
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
