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

from unittest import TestCase

from formencode import Invalid
import mock

from .. import base


def ep(name, source=None, importer=None, **kw):
    mep = mock.Mock(name='mock_ep', **kw)
    mep.name = name
    if importer is not None:
        mep.load.return_value = importer
    else:
        mep.load.return_value.source = source
        mep.lv = mep.load.return_value.return_value
        mep.lv.source = source
    return mep


class TestProjectImporterDispatcher(TestCase):
    @mock.patch.object(base, 'iter_entry_points')
    def test_lookup(self, iep):
        eps = iep.return_value = [ep('ep1', 'first'), ep('ep2', 'second')]
        result = base.ProjectImporterDispatcher()._lookup('source', 'rest1', 'rest2')
        self.assertEqual(result, (eps[0].lv, ('rest1', 'rest2')))
        iep.assert_called_once_with('allura.project_importers', 'source')


class TestProjectImporter(TestCase):
    @mock.patch.object(base, 'iter_entry_points')
    def test_tool_importers(self, iep):
        eps = iep.return_value = [ep('ep1', 'foo'), ep('ep2', 'bar'), ep('ep3', 'foo')]
        pi = base.ProjectImporter()
        pi.source = 'foo'
        self.assertEqual(pi.tool_importers, {'ep1': eps[0].lv, 'ep3': eps[2].lv})
        iep.assert_called_once_with('allura.importers')



TA1 = mock.Mock(tool_label='foo', tool_description='foo_desc')
TA2 = mock.Mock(tool_label='qux', tool_description='qux_desc')
TA3 = mock.Mock(tool_label='baz', tool_description='baz_desc')

class TestToolImporter(TestCase):
    class TI1(base.ToolImporter):
        target_app = TA1

    class TI2(base.ToolImporter):
        target_app = TA2
        tool_label = 'bar'
        tool_description = 'bar_desc'

    class TI3(base.ToolImporter):
        target_app = [TA2, TA2]

    @mock.patch.object(base, 'iter_entry_points')
    def test_by_name(self, iep):
        eps = iep.return_value = [ep('my-name', 'my-source')]
        importer = base.ToolImporter.by_name('my-name')
        iep.assert_called_once_with('allura.importers', 'my-name')
        self.assertEqual(importer, eps[0].lv)

        iep.reset_mock()
        iep.return_value = []
        importer = base.ToolImporter.by_name('other-name')
        iep.assert_called_once_with('allura.importers', 'other-name')
        self.assertEqual(importer, None)

    @mock.patch.object(base, 'iter_entry_points')
    def test_by_app(self, iep):
        eps = iep.return_value = [
                ep('importer1', importer=self.TI1),
                ep('importer2', importer=self.TI2),
                ep('importer3', importer=self.TI3),
            ]
        importers = base.ToolImporter.by_app(TA2)
        self.assertEqual(set(importers.keys()), set([
                'importer2',
                'importer3',
            ]))
        self.assertIsInstance(importers['importer2'], self.TI2)
        self.assertIsInstance(importers['importer3'], self.TI3)

    def test_tool_label(self):
        self.assertEqual(self.TI1().tool_label, 'foo')
        self.assertEqual(self.TI2().tool_label, 'bar')
        self.assertEqual(self.TI3().tool_label, 'qux')

    def test_tool_description(self):
        self.assertEqual(self.TI1().tool_description, 'foo_desc')
        self.assertEqual(self.TI2().tool_description, 'bar_desc')
        self.assertEqual(self.TI3().tool_description, 'qux_desc')


class TestToolsValidator(TestCase):
    def setUp(self):
        self.tv = base.ToolsValidator('good-source')

    @mock.patch.object(base.ToolImporter, 'by_name')
    def test_empty(self, by_name):
        self.assertEqual(self.tv.to_python(''), [])
        self.assertEqual(by_name.call_count, 0)

    @mock.patch.object(base.ToolImporter, 'by_name')
    def test_no_ep(self, by_name):
        eps = by_name.return_value = None
        with self.assertRaises(Invalid) as cm:
            self.tv.to_python('my-value')
        self.assertEqual(cm.exception.msg, 'Invalid tool selected: my-value')
        by_name.assert_called_once_with('my-value')

    @mock.patch.object(base.ToolImporter, 'by_name')
    def test_bad_source(self, by_name):
        eps = by_name.return_value = ep('ep1', 'bad-source').lv
        with self.assertRaises(Invalid) as cm:
            self.tv.to_python('my-value')
        self.assertEqual(cm.exception.msg, 'Invalid tool selected: my-value')
        by_name.assert_called_once_with('my-value')

    @mock.patch.object(base.ToolImporter, 'by_name')
    def test_multiple(self, by_name):
        eps = by_name.side_effect = [ep('ep1', 'bad-source').lv, ep('ep2', 'good-source').lv, ep('ep3', 'bad-source').lv]
        with self.assertRaises(Invalid) as cm:
            self.tv.to_python(['value1', 'value2', 'value3'])
        self.assertEqual(cm.exception.msg, 'Invalid tools selected: value1, value3')
        self.assertEqual(by_name.call_args_list, [
                mock.call('value1'),
                mock.call('value2'),
                mock.call('value3'),
            ])

    @mock.patch.object(base.ToolImporter, 'by_name')
    def test_valid(self, by_name):
        eps = by_name.side_effect = [ep('ep1', 'good-source').lv, ep('ep2', 'good-source').lv, ep('ep3', 'bad-source').lv]
        self.assertEqual(self.tv.to_python(['value1', 'value2']), ['value1', 'value2'])
        self.assertEqual(by_name.call_args_list, [
                mock.call('value1'),
                mock.call('value2'),
            ])
