# -*- coding: utf-8 -*-

#       Licensed to the Apache Software Foundation (ASF) under one
#       or more contributor license agreements.  See the NOTICE file
#       distributed with this work for additional information
#       regarding copyright ownership.  The ASF licenses this file
#       to you under the Apache License, Version 2.0 (the
#       "License"); you may not use this file except in compliance
#       with the License.  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing,
#       software distributed under the License is distributed on an
#       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#       KIND, either express or implied.  See the License for the
#       specific language governing permissions and limitations
#       under the License.

"""
Model tests for auth
"""

from nose.tools import (
    with_setup,
    assert_equal,
    assert_not_equal,
    assert_true,
    assert_not_in,
    assert_in,
)
from pylons import tmpl_context as c, app_globals as g
from webob import Request
from mock import patch, Mock
from datetime import datetime, timedelta

from ming.orm.ormsession import ThreadLocalORMSession
from ming.odm import session

from allura import model as M
from allura.lib import plugin
from allura.tests import decorators as td
from alluratest.controller import setup_basic_test, setup_global_objects, setup_functional_test


def setUp():
    setup_basic_test()
    ThreadLocalORMSession.close_all()
    setup_global_objects()


@with_setup(setUp)
def test_email_address():
    addr = M.EmailAddress(_id='test_admin@domain.net',
                          claimed_by_user_id=c.user._id)
    ThreadLocalORMSession.flush_all()
    assert addr.claimed_by_user() == c.user
    addr2 = M.EmailAddress.upsert('test@domain.net')
    addr3 = M.EmailAddress.upsert('test_admin@domain.net')
    assert addr3 is addr
    assert addr2 is not addr
    assert addr2
    addr4 = M.EmailAddress.upsert('test@DOMAIN.NET')
    assert addr4 is addr2
    with patch('allura.lib.app_globals.request', Request.blank('/')):
        addr.send_verification_link()
    assert addr is c.user.address_object('test_admin@domain.net')
    c.user.claim_address('test@DOMAIN.NET')
    assert 'test@domain.net' in c.user.email_addresses


@td.with_user_project('test-admin')
@with_setup(setUp)
def test_user():
    assert c.user.url() .endswith('/u/test-admin/')
    assert c.user.script_name .endswith('/u/test-admin/')
    assert_equal(set(p.shortname for p in c.user.my_projects()),
                 set(['test', 'test2', 'u/test-admin', 'adobe-1', '--init--']))
    # delete one of the projects and make sure it won't appear in my_projects()
    p = M.Project.query.get(shortname='test2')
    p.deleted = True
    ThreadLocalORMSession.flush_all()
    assert_equal(set(p.shortname for p in c.user.my_projects()),
                 set(['test', 'u/test-admin', 'adobe-1', '--init--']))
    u = M.User.register(dict(
        username='nosetest-user'))
    ThreadLocalORMSession.flush_all()
    assert_equal(u.private_project().shortname, 'u/nosetest-user')
    roles = g.credentials.user_roles(
        u._id, project_id=u.private_project().root_project._id)
    assert len(roles) == 3, roles
    u.set_password('foo')
    provider = plugin.LocalAuthenticationProvider(Request.blank('/'))
    assert provider._validate_password(u, 'foo')
    assert not provider._validate_password(u, 'foobar')
    u.set_password('foobar')
    assert provider._validate_password(u, 'foobar')
    assert not provider._validate_password(u, 'foo')


@with_setup(setUp)
def test_user_project_creates_on_demand():
    u = M.User.register(dict(username='foobar123'), make_project=False)
    ThreadLocalORMSession.flush_all()
    assert not M.Project.query.get(shortname='u/foobar123')
    assert u.private_project()
    assert M.Project.query.get(shortname='u/foobar123')


@with_setup(setUp)
def test_user_project_already_deleted_creates_on_demand():
    u = M.User.register(dict(username='foobar123'), make_project=True)
    p = M.Project.query.get(shortname='u/foobar123')
    p.deleted = True
    ThreadLocalORMSession.flush_all()
    assert not M.Project.query.get(shortname='u/foobar123', deleted=False)
    assert u.private_project()
    ThreadLocalORMSession.flush_all()
    assert M.Project.query.get(shortname='u/foobar123', deleted=False)


@with_setup(setUp)
def test_user_project_does_not_create_on_demand_for_disabled_user():
    u = M.User.register(
        dict(username='foobar123', disabled=True), make_project=False)
    ThreadLocalORMSession.flush_all()
    assert not u.private_project()
    assert not M.Project.query.get(shortname='u/foobar123')


@with_setup(setUp)
def test_user_project_does_not_create_on_demand_for_anonymous_user():
    u = M.User.anonymous()
    ThreadLocalORMSession.flush_all()
    assert not u.private_project()
    assert not M.Project.query.get(shortname='u/anonymous')
    assert not M.Project.query.get(shortname='u/*anonymous')


@with_setup(setUp)
def test_project_role():
    role = M.ProjectRole(project_id=c.project._id, name='test_role')
    M.ProjectRole.by_user(c.user, upsert=True).roles.append(role._id)
    ThreadLocalORMSession.flush_all()
    roles = g.credentials.user_roles(
        c.user._id, project_id=c.project.root_project._id)
    roles_ids = [r['_id'] for r in roles]
    roles = M.ProjectRole.query.find({'_id': {'$in': roles_ids}})
    for pr in roles:
        assert pr.display()
        pr.special
        assert pr.user in (c.user, None, M.User.anonymous())


@with_setup(setUp)
def test_default_project_roles():
    roles = dict(
        (pr.name, pr)
        for pr in M.ProjectRole.query.find(dict(
            project_id=c.project._id)).all()
        if pr.name)
    assert 'Admin' in roles.keys(), roles.keys()
    assert 'Developer' in roles.keys(), roles.keys()
    assert 'Member' in roles.keys(), roles.keys()
    assert roles['Developer']._id in roles['Admin'].roles
    assert roles['Member']._id in roles['Developer'].roles

    # There're 1 user assigned to project, represented by
    # relational (vs named) ProjectRole's
    assert len(roles) == M.ProjectRole.query.find(dict(
        project_id=c.project._id)).count() - 1


@with_setup(setUp)
def test_email_address_claimed_by_user():
    addr = M.EmailAddress(_id='test_admin@domain.net',
                          claimed_by_user_id=c.user._id)
    c.user.disabled = True
    ThreadLocalORMSession.flush_all()
    assert addr.claimed_by_user() is None


@td.with_user_project('test-admin')
@with_setup(setUp)
def test_user_projects_by_role():
    assert_equal(set(p.shortname for p in c.user.my_projects()),
                 set(['test', 'test2', 'u/test-admin', 'adobe-1', '--init--']))
    assert_equal(set(p.shortname for p in c.user.my_projects_by_role_name('Admin')),
                 set(['test', 'test2', 'u/test-admin', 'adobe-1', '--init--']))
    # Remove admin access from c.user to test2 project
    project = M.Project.query.get(shortname='test2')
    admin_role = M.ProjectRole.by_name('Admin', project)
    developer_role = M.ProjectRole.by_name('Developer', project)
    user_role = M.ProjectRole.by_user(c.user, project=project, upsert=True)
    user_role.roles.remove(admin_role._id)
    user_role.roles.append(developer_role._id)
    ThreadLocalORMSession.flush_all()
    g.credentials.clear()
    assert_equal(set(p.shortname for p in c.user.my_projects()),
                 set(['test', 'test2', 'u/test-admin', 'adobe-1', '--init--']))
    assert_equal(set(p.shortname for p in c.user.my_projects_by_role_name('Admin')),
                 set(['test', 'u/test-admin', 'adobe-1', '--init--']))


@td.with_user_project('test-admin')
@with_setup(setUp)
def test_user_projects_unnamed():
    """
    Confirm that spurious ProjectRoles associating a user with
    a project to which they do not belong to any named group
    don't cause the user to count as a member of the project.
    """
    sub1 = M.Project.query.get(shortname='test/sub1')
    M.ProjectRole(
        user_id=c.user._id,
        project_id=sub1._id)
    ThreadLocalORMSession.flush_all()
    project_names = [p.shortname for p in c.user.my_projects()]
    assert_not_in('test/sub1', project_names)
    assert_in('test', project_names)


@patch.object(g, 'user_message_max_messages', 3)
def test_check_sent_user_message_times():
    user1 = M.User.register(dict(username='test-user'), make_project=False)
    time1 = datetime.utcnow() - timedelta(minutes=30)
    time2 = datetime.utcnow() - timedelta(minutes=45)
    time3 = datetime.utcnow() - timedelta(minutes=70)
    user1.sent_user_message_times = [time1, time2, time3]
    assert user1.can_send_user_message()
    assert_equal(len(user1.sent_user_message_times), 2)
    user1.sent_user_message_times.append(
        datetime.utcnow() - timedelta(minutes=15))
    assert not user1.can_send_user_message()


@td.with_user_project('test-admin')
@with_setup(setUp)
def test_user_track_active():
    # without this session flushing inside track_active raises Exception
    setup_functional_test()
    c.user = M.User.by_username('test-admin')

    assert_equal(c.user.last_access['session_date'], None)
    assert_equal(c.user.last_access['session_ip'], None)
    assert_equal(c.user.last_access['session_ua'], None)

    req = Mock(headers={'User-Agent': 'browser'}, remote_addr='addr')
    c.user.track_active(req)
    c.user = M.User.by_username(c.user.username)
    assert_not_equal(c.user.last_access['session_date'], None)
    assert_equal(c.user.last_access['session_ip'], 'addr')
    assert_equal(c.user.last_access['session_ua'], 'browser')

    # ensure that session activity tracked with a whole-day granularity
    prev_date = c.user.last_access['session_date']
    c.user.track_active(req)
    c.user = M.User.by_username(c.user.username)
    assert_equal(c.user.last_access['session_date'], prev_date)
    yesterday = datetime.utcnow() - timedelta(1)
    c.user.last_access['session_date'] = yesterday
    session(c.user).flush(c.user)
    c.user.track_active(req)
    c.user = M.User.by_username(c.user.username)
    assert_true(c.user.last_access['session_date'] > yesterday)

    # ...or if IP or User Agent has changed
    req.remote_addr = 'new addr'
    c.user.track_active(req)
    c.user = M.User.by_username(c.user.username)
    assert_equal(c.user.last_access['session_ip'], 'new addr')
    assert_equal(c.user.last_access['session_ua'], 'browser')
    req.headers['User-Agent'] = 'new browser'
    c.user.track_active(req)
    c.user = M.User.by_username(c.user.username)
    assert_equal(c.user.last_access['session_ip'], 'new addr')
    assert_equal(c.user.last_access['session_ua'], 'new browser')


@with_setup(setUp)
def test_user_index():
    c.user.email_addresses = ['email1', 'email2']
    c.user.set_pref('email_address', 'email2')
    idx = c.user.index()
    assert_equal(idx['id'], c.user.index_id())
    assert_equal(idx['title'], 'User test-admin')
    assert_equal(idx['type_s'], 'User')
    assert_equal(idx['username_s'], 'test-admin')
    assert_equal(idx['email_addresses_t'], 'email1 email2')
    assert_equal(idx['email_address_s'], 'email2')
    assert_in('last_password_updated_dt', idx)
    assert_equal(idx['disabled_b'], False)
    assert_in('results_per_page_i', idx)
    assert_in('email_format_s', idx)
    assert_in('disable_user_messages_b', idx)
    assert_equal(idx['display_name_s'], 'Test Admin')
    assert_equal(idx['sex_s'], 'Unknown')
    assert_in('birthdate_dt', idx)
    assert_in('localization_s', idx)
    assert_in('timezone_s', idx)
    assert_in('socialnetworks_t', idx)
    assert_in('telnumbers_t', idx)
    assert_in('skypeaccount_s', idx)
    assert_in('webpages_t', idx)
    assert_in('skills_t', idx)
    assert_in('last_access_login_date_dt', idx)
    assert_in('last_access_login_ip_s', idx)
    assert_in('last_access_login_ua_t', idx)
    assert_in('last_access_session_date_dt', idx)
    assert_in('last_access_session_ip_s', idx)
    assert_in('last_access_session_ua_t', idx)
    # provided bby auth provider
    assert_in('user_registration_date_dt', idx)
