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

import json

from mock import patch, MagicMock
from nose.tools import assert_equal, assert_in, assert_not_in
from ming.odm import ThreadLocalORMSession
from pylons import tmpl_context as c
from tg import config

from allura import model as M
from allura.tests import TestController
from allura.lib import helpers as h
from allura.lib.decorators import task


class TestSiteAdmin(TestController):

    def test_access(self):
        r = self.app.get('/nf/admin/', extra_environ=dict(
            username='test-user'), status=403)

        r = self.app.get('/nf/admin/', extra_environ=dict(
            username='*anonymous'), status=302)
        r = r.follow()
        assert 'Login' in r

    def test_home(self):
        r = self.app.get('/nf/admin/', extra_environ=dict(
            username='root'))
        assert 'Site Admin Home' in r

    def test_stats(self):
        r = self.app.get('/nf/admin/stats/', extra_environ=dict(
            username='root'))
        assert 'Forge Site Admin' in r.html.find(
            'h2', {'class': 'dark title'}).contents[0]
        stats_table = r.html.find('table')
        cells = stats_table.findAll('td')
        assert cells[0].contents[0] == 'Adobe', cells[0].contents[0]

    def test_tickets_access(self):
        self.app.get('/nf/admin/api_tickets', extra_environ=dict(
            username='test-user'), status=403)

    def test_new_projects_access(self):
        self.app.get('/nf/admin/new_projects', extra_environ=dict(
            username='test_user'), status=403)
        r = self.app.get('/nf/admin/new_projects', extra_environ=dict(
            username='*anonymous'), status=302).follow()
        assert 'Login' in r

    def test_new_projects(self):
        r = self.app.get('/nf/admin/new_projects', extra_environ=dict(
            username='root'))
        headers = r.html.find('table').findAll('th')
        assert headers[1].contents[0] == 'Created'
        assert headers[2].contents[0] == 'Shortname'
        assert headers[3].contents[0] == 'Name'
        assert headers[4].contents[0] == 'Short description'
        assert headers[5].contents[0] == 'Summary'
        assert headers[6].contents[0] == 'Homepage'
        assert headers[7].contents[0] == 'Admins'

    def test_new_projects_deleted_projects(self):
        '''Deleted projects should not be visible here'''
        r = self.app.get('/nf/admin/new_projects', extra_environ=dict(
            username='root'))
        count = len(r.html.find('table').findAll('tr'))
        p = M.Project.query.get(shortname='test')
        p.deleted = True
        ThreadLocalORMSession.flush_all()
        r = self.app.get('/nf/admin/new_projects', extra_environ=dict(
            username='root'))
        assert_equal(len(r.html.find('table').findAll('tr')), count - 1)

    def test_new_projects_daterange_filtering(self):
        r = self.app.get('/nf/admin/new_projects', extra_environ=dict(
            username='root'))
        count = len(r.html.find('table').findAll('tr'))
        assert_equal(count, 7)

        filtr = r.forms[0]
        filtr['start-dt'] = '2000/01/01 10:10:10'
        filtr['end-dt'] = '2000/01/01 09:09:09'
        r = filtr.submit()
        count = len(r.html.find('table').findAll('tr'))
        assert_equal(count, 1)  # only row with headers - no results

    def test_reclone_repo_access(self):
        r = self.app.get('/nf/admin/reclone_repo', extra_environ=dict(
            username='*anonymous'), status=302).follow()
        assert 'Login' in r

    def test_reclone_repo(self):
        r = self.app.get('/nf/admin/reclone_repo')
        assert 'Reclone repository' in r

    def test_reclone_repo_default_value(self):
        r = self.app.get('/nf/admin/reclone_repo')
        assert 'value="p"' in r

    def test_task_list(self):
        r = self.app.get('/nf/admin/task_manager',
                         extra_environ=dict(username='*anonymous'), status=302)
        import math
        M.MonQTask.post(math.ceil, (12.5,))
        r = self.app.get('/nf/admin/task_manager?page_num=1')
        assert 'math.ceil' in r, r

    def test_task_view(self):
        import math
        task = M.MonQTask.post(math.ceil, (12.5,))
        url = '/nf/admin/task_manager/view/%s' % task._id
        r = self.app.get(
            url, extra_environ=dict(username='*anonymous'), status=302)
        r = self.app.get(url)
        assert 'math.ceil' in r, r

    def test_task_new(self):
        r = self.app.get('/nf/admin/task_manager/new')
        assert 'New Task' in r, r

    def test_task_create(self):
        project = M.Project.query.get(shortname='test')
        app = project.app_instance('admin')
        user = M.User.by_username('root')

        task_args = dict(
            args=['foo'],
            kwargs=dict(bar='baz'))

        r = self.app.post('/nf/admin/task_manager/create', params=dict(
            task='allura.tests.functional.test_site_admin.test_task',
            task_args=json.dumps(task_args),
            user='root',
            path='/p/test/admin',
        ), status=302)
        task = M.MonQTask.query.find({}).sort('_id', -1).next()
        assert str(task._id) in r.location
        assert task.context['project_id'] == project._id
        assert task.context['app_config_id'] == app.config._id
        assert task.context['user_id'] == user._id
        assert task.args == task_args['args']
        assert task.kwargs == task_args['kwargs']

    def test_task_doc(self):
        r = self.app.get('/nf/admin/task_manager/task_doc', params=dict(
            task_name='allura.tests.functional.test_site_admin.test_task'))
        assert json.loads(r.body)['doc'] == 'test_task doc string'

    @patch('allura.model.auth.request')
    def test_users(self, request):
        request.url = 'http://host.domain/path/'
        c.user = M.User.by_username('test-user-1')
        M.AuditLog.log_user('test activity user 1')
        M.AuditLog.log_user('test activity user 2', user=M.User.by_username('test-user-2'))
        r = self.app.get('/nf/admin/users')
        assert_not_in('test activity', r)
        r = self.app.get('/nf/admin/users?username=admin1')
        assert_not_in('test activity', r)
        r = self.app.get('/nf/admin/users?username=test-user-1')
        assert_in('test activity user 1', r)
        assert_not_in('test activity user 2', r)
        r = self.app.get('/nf/admin/users?username=test-user-2')
        assert_not_in('test activity user 1', r)
        assert_in('test activity user 2', r)


class TestProjectsSearch(TestController):

    TEST_HIT = MagicMock(hits=1, docs=[{
        'name_s': 'Test Project',
        'is_nbhd_project_b': False,
        'is_root_b': True,
        'title': ['Project Test Project'],
        'deleted_b': False,
        'shortname_s': 'test',
        'private_b': False,
        'url_s': 'http://localhost:8080/p/test/',
        'neighborhood_id_s': '53ccf6e6100d2b0741746c66',
        'removal_changed_date_dt': '2014-07-21T11:18:00.087Z',
        'registration_dt': '2014-07-21T11:18:00Z',
        'type_s': 'Project',
        '_version_': 1474236502200287232,
        'neighborhood_name_s': 'Projects',
        'id': 'allura/model/project/Project#53ccf6e8100d2b0741746e9f',
    }])

    @patch('allura.controllers.site_admin.search')
    def test_default_fields(self, search):
        search.search_projects.return_value = self.TEST_HIT
        r = self.app.get('/nf/admin/search_projects?q=fake&f=shortname')
        options = [o['value'] for o in r.html.findAll('option')]
        assert_equal(options, ['shortname', 'name', '__custom__'])
        ths = [th.text for th in r.html.findAll('th')]
        assert_equal(ths, ['Short name', 'Full name', 'Registered', 'Deleted?', 'Details'])

    @patch('allura.controllers.site_admin.search')
    def test_additional_fields(self, search):
        search.search_projects.return_value = self.TEST_HIT
        with h.push_config(config, **{'search.project.additional_fields': 'private, url'}):
            r = self.app.get('/nf/admin/search_projects?q=fake&f=shortname')
        options = [o['value'] for o in r.html.findAll('option')]
        assert_equal(options, ['shortname', 'name', 'private', 'url', '__custom__'])
        ths = [th.text for th in r.html.findAll('th')]
        assert_equal(ths, ['Short name', 'Full name', 'Registered', 'Deleted?',
                           'private', 'url', 'Details'])


@task
def test_task(*args, **kw):
    """test_task doc string"""
    pass
