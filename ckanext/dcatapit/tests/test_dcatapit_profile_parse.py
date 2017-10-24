import os
import uuid
import json
from datetime import datetime

import nose
try:
    from unittest import mock
except ImportError:
    import mock

from rdflib import Graph, URIRef, BNode, Literal
from rdflib.namespace import RDF

from ckan.logic import schema
from ckan.tests.helpers import call_action
from ckan.plugins import toolkit
from ckan.lib.base import config
from ckan.model import meta, repo
from ckan.model.user import User
from ckan.model.group import Group
from ckan.model.package import Package


try:
    from ckan.tests import helpers
except ImportError:
    from ckan.new_tests import helpers

from ckanext.dcat.processors import RDFParser
from ckanext.dcatapit.dcat.profiles import (DCATAPIT)
from ckanext.dcatapit.plugin import DCATAPITGroupMapper
from ckanext.dcatapit.mapping import DCATAPIT_THEME_TO_MAPPING_SOURCE, DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS

eq_ = nose.tools.eq_
ok_ = nose.tools.ok_
assert_true = nose.tools.assert_true


class BaseParseTest(object):

    def _extras(self, dataset):
        extras = {}
        for extra in dataset.get('extras'):
            extras[extra['key']] = extra['value']
        return extras

    def _get_file_contents(self, file_name):
        path = os.path.join(os.path.dirname(__file__),
                            '..', '..', '..', 'examples',
                            file_name)
        with open(path, 'r') as f:
            return f.read()

class TestDCATAPITProfileParsing(BaseParseTest):

    def test_graph_to_dataset(self):

        contents = self._get_file_contents('dataset.rdf')

        p = RDFParser(profiles=['it_dcat_ap'])

        p.parse(contents)

        datasets = [d for d in p.datasets()]

        eq_(len(datasets), 1)

        dataset = datasets[0]

        # Basic fields
        eq_(dataset['title'], u'Dataset di test DCAT_AP-IT')
        eq_(dataset['notes'], u'dcatapit dataset di test')

        #  Simple values
        eq_(dataset['issued'], u'2016-11-29')
        eq_(dataset['modified'], u'2016-11-29')
        eq_(dataset['identifier'], u'ISBN')
        #eq_(dataset['temporal_start'], '2016-11-01')
        #eq_(dataset['temporal_end'], '2016-11-30')
        eq_(dataset['frequency'], 'UPDATE_CONT')

        geographical_name = dataset['geographical_name'][1:-1].split(',') if ',' in dataset['geographical_name'] else [dataset['geographical_name']]
        geographical_name.sort()
        geographical_name = '{' + ','.join([str(x) for x in geographical_name]) + '}'
        eq_(geographical_name, '{ITA_BZO}')

        eq_(dataset['publisher_name'], 'bolzano')
        eq_(dataset['publisher_identifier'], '234234234')
        eq_(dataset['creator_name'], 'test')
        eq_(dataset['creator_identifier'], '412946129')
        eq_(dataset['holder_name'], 'bolzano')
        eq_(dataset['holder_identifier'], '234234234')

        alternate_identifier = dataset['alternate_identifier'].split(',') if ',' in dataset['alternate_identifier'] else [dataset['alternate_identifier']]
        alternate_identifier.sort()
        alternate_identifier = ','.join([str(x) for x in alternate_identifier])
        eq_(alternate_identifier, 'ISBN,TEST')

        theme = dataset['theme'][1:-1].split(',') if ',' in dataset['theme'] else [dataset['theme']]
        theme.sort()
        theme = '{' + ','.join([str(x) for x in theme]) + '}'
        eq_(theme, '{ECON,ENVI}')

        eq_(dataset['geographical_geonames_url'], 'http://www.geonames.org/3181913')

        language = dataset['language'][1:-1].split(',') if ',' in dataset['language'] else [dataset['language']]
        language.sort()
        language = '{' + ','.join([str(x) for x in language]) + '}'
        eq_(language, '{DEU,ENG,ITA}')
        
        eq_(dataset['is_version_of'], 'http://dcat.geo-solutions.it/dataset/energia-da-fonti-rinnovabili2')

        conforms_to = dataset['conforms_to'].split(',') if ',' in dataset['conforms_to'] else [dataset['conforms_to']]
        conforms_to.sort()
        conforms_to = '{' + ','.join([str(x) for x in conforms_to]) + '}'
        eq_(conforms_to, '{CONF1,CONF2,CONF3}')

        # Multilang values
        ok_(dataset['DCATAPIT_MULTILANG_BASE'])

        multilang_notes = dataset['DCATAPIT_MULTILANG_BASE'].get('notes', None)
        ok_(multilang_notes)
        eq_(multilang_notes['de'], u'dcatapit test-dataset')
        eq_(multilang_notes['it'], u'dcatapit dataset di test')
        eq_(multilang_notes['en_GB'], u'dcatapit dataset test')

        multilang_holder_name = dataset['DCATAPIT_MULTILANG_BASE'].get('holder_name', None)
        ok_(multilang_holder_name)
        eq_(multilang_holder_name['de'], u'bolzano')
        eq_(multilang_holder_name['it'], u'bolzano')
        eq_(multilang_holder_name['en_GB'], u'bolzano')

        multilang_title = dataset['DCATAPIT_MULTILANG_BASE'].get('title', None)
        ok_(multilang_title)
        eq_(multilang_title['de'], u'Dcatapit Test-Dataset')
        eq_(multilang_title['it'], u'Dataset di test DCAT_AP-IT')
        eq_(multilang_title['en_GB'], u'DCAT_AP-IT test dataset')

    def test_mapping(self):

        contents = self._get_file_contents('dataset.rdf')

        p = RDFParser(profiles=['it_dcat_ap'])

        p.parse(contents)
        datasets = [d for d in p.datasets()]
        eq_(len(datasets), 1)
        package_dict = datasets[0]


        user = User.get('dummy')
        if not user:
           user = call_action('user_create',
                               name='dummy',
                               password='dummy',
                               email='dummy@dummy.com')
        org = Group.by_name('dummy')
        if org is None:
            org  = call_action('organization_create',
                                context={'user': user.name},
                                name='dummy')
        existing_g = Group.by_name('existing-group')
        if existing_g is None:
            existing_g  = call_action('group_create',
                                      context={'user': user.name},
                                      name='existing-group')

        context = {'user': 'dummy', 'defer_commit': True}
        package_schema = schema.default_create_package_schema()
        context['schema'] = package_schema
        _p = {'frequency': 'manual',
              'publisher_name': 'dummy',
              'extras': [{'key':'theme', 'value':['non-mappable', 'thememap1']}],
              'groups': [],
              'title': 'dummy',
              'holder_name': 'dummy',
              'holder_identifier': 'dummy',
              'name': 'dummy',
              'notes': 'dummy',
              'owner_org': 'dummy',
              'modified': datetime.now(),
              'publisher_identifier': 'dummy',
              'guid': unicode(uuid.uuid4),
              'identifier': 'dummy'}
        
        package_dict.update(_p)
        config[DCATAPIT_THEME_TO_MAPPING_SOURCE] = ''
        package_data = call_action('package_create', context=context, **package_dict)

        p = Package.get(package_data['id'])

        # no groups should be assigned at this point (no map applied)
        assert {'theme': ['non-mappable', 'thememap1']} == p.extras, (_p['extras'], 'vs', p.extras,)
        assert [] == p.get_groups()

        package_data = call_action('package_show', context=context, id=package_data['id'])

        # use test mapping, which replaces thememap1 to thememap2 and thememap3
        test_map_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'examples', 'test_map.ini')
        config[DCATAPIT_THEME_TO_MAPPING_SOURCE] = test_map_file

        package_dict['theme'] = ['non-mappable', 'thememap1']

        expected_groups_existing = ['existing-group']
        expected_groups_new = expected_groups_existing + ['somegroup1', 'somegroup2']

        package_dict.pop('extras', None)
        p = Package.get(package_data['id'])
        context['package'] = p 
        package_data = call_action('package_update', context=context, **package_dict)
        
        meta.Session.flush()
        meta.Session.revision = repo.new_revision()

        # check - only existing group should be assigned
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups() if not g.is_organization]
        assert expected_groups_existing == groups, (expected_groups_existing, 'vs', groups,)

        config[DCATAPIT_THEME_TO_MAPPING_ADD_NEW_GROUPS] = 'true'


        package_dict['theme'] = ['non-mappable', 'thememap1']
        package_data = call_action('package_update', context=context, **package_dict)


        meta.Session.flush()
        meta.Session.revision = repo.new_revision()

        # recheck - this time, new groups should appear
        p = Package.get(package_data['id'])
        groups = [g.name for g in p.get_groups() if not g.is_organization]

        assert set(expected_groups_new) == set(groups), (expected_groups_new, 'vs', groups,)

        meta.Session.rollback()
