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

import mock
import tg
from nose.tools import assert_equal, assert_in, assert_not_in

from allura.lib.widgets.user_profile import SectionsUtil
from allura.tests import TestController


class TestPersonalDashboard(TestController):

    def test_dashboard(self):
        r = self.app.get('/dashboard')
        assert_equal('Test Admin / Dashboard', r.html.find('h1', 'project_title').text)
        sections = set([c for s in r.html.findAll(None, 'profile-section') for c in s['class'].split()])
        assert_in('tickets', sections)
        assert_in('projects', sections)
        assert_in('merge_requests', sections)
        assert_in('activity', sections)

    def test_dashboard_sections(self):
        def ep(n):
            m = mock.Mock()
            m.name = n
            m.load()().display.return_value = 'Section %s' % n
            return m
        eps = map(ep, ['a', 'b', 'c', 'd'])
        order = {'personal_dashboard_sections.order': 'b, d,c , f '}
        with mock.patch('allura.lib.helpers.iter_entry_points') as iep:
            with mock.patch.dict(tg.config, order):
                iep.return_value = eps
                sections = SectionsUtil.load_sections('personal_dashboard')
                assert_equal(sections, [
                    eps[1].load(),
                    eps[3].load(),
                    eps[2].load(),
                    eps[0].load()])
                r = self.app.get('/dashboard')
                assert_in('Section a', r.body)
                assert_in('Section b', r.body)
                assert_in('Section c', r.body)
                assert_in('Section d', r.body)
                assert_not_in('Section f', r.body)
