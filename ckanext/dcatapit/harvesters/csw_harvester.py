import re
import json
import logging
import ckanext.dcatapit.harvesters.utils as utils

from ckan.plugins.core import SingletonPlugin
from ckanext.spatial.harvesters.csw import CSWHarvester

from ckanext.spatial.model import ISODocument
from ckanext.spatial.model import ISOElement
from ckanext.spatial.model import ISOKeyword
from ckanext.spatial.model import ISOResponsibleParty

from ckanext.dcatapit.model import License

log = logging.getLogger(__name__)

class ISOTextGroup(ISOElement):
    elements = [
        ISOElement(
            name="text",
            search_paths=[
                "gmd:LocalisedCharacterString/text()"
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="locale",
            search_paths=[
                "gmd:LocalisedCharacterString/@locale"
            ],
            multiplicity="1",
        )
    ]


ISODocument.elements.append(
    ISOResponsibleParty(
        name="cited-responsible-party",
        search_paths=[
            "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty",
            "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty"
        ],
        multiplicity="1..*",
    )
)

ISODocument.elements.append(
    ISOElement(
        name="conformity-specification-title",
        search_paths=[
            "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:specification/gmd:CI_Citation/gmd:title/gco:CharacterString/text()"
        ],
        multiplicity="1",
     ))

ISODocument.elements.append(
    ISOTextGroup(
        name="conformity-title-text",
        search_paths=[
            "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:specification/gmd:CI_Citation/gmd:title/gmd:PT_FreeText/gmd:textGroup",
            ],
        multiplicity="1..*",
     ))

ISOKeyword.elements.append(
    ISOElement(
        name="thesaurus-title",
        search_paths=[
            "gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
        ],
        multiplicity="1",
    ))

ISOKeyword.elements.append(
    ISOElement(
        name="thesaurus-identifier",
        search_paths=[
            "gmd:thesaurusName/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
        ],
        multiplicity="1",
    ))

ISOResponsibleParty.elements.append(
    ISOTextGroup(
        name="organisation-name-localized",
        search_paths=[
            "gmd:organisationName/gmd:PT_FreeText/gmd:textGroup"
        ],
        multiplicity="1..*",
    )
)

class DCATAPITCSWHarvester(CSWHarvester, SingletonPlugin):

    _dcatapit_config = {
        'dataset_themes': [{'theme': 'OP_DATPRO', 'subthemes': []}],
        'dataset_places': None,
        'dataset_languages': 'ITA',
        'frequency': 'UNKNOWN',
        'agents': {
            'publisher': {
                'code': 'temp_ipa',
                'role': 'publisher',
                'code_regex': {
                    'regex': '\(([^)]+)\:([^)]+)\)',
                    'groups': [2]  # optional, dependes by the regular expression
                },
                'name_regex': {
                    'regex': '([^(]*)(\(IPA[^)]*\))(.+)',
                    'groups': [1, 3]  # optional, dependes by the regular expression
                }
            },
            'owner': {
                'code': 'temp_ipa',
                'role': 'owner',
                'code_regex': {
                    'regex': '\(([^)]+)\:([^)]+)\)',
                    'groups': [2]  # optional, dependes by the regular expression
                },
                'name_regex': {
                    'regex': '([^(]*)(\(IPA[^)]*\))(.+)',
                    'groups': [1, 3]  # optional, dependes by the regular expression
                }
            },
            'author': {
                'code': 'temp_ipa',
                'role': 'author',
                'code_regex': {
                    'regex': '\(([^)]+)\:([^)]+)\)',
                    'groups': [2]  # optional, dependes by the regular expression
                },
                'name_regex': {
                    'regex': '([^(]*)(\(IPA[^)]*\))(.+)',
                    'groups': [1, 3]  # optional, dependes by the regular expression
                }
            }
        },
        'controlled_vocabularies': {
            'dcatapit_skos_theme_id': 'theme.data-theme-skos',
            'dcatapit_skos_places_id': 'theme.places-skos'
        }
    }

    _ckan_locales_mapping = {
        'ita': 'it',
        'ger': 'de',
        'eng': 'en_GB'
    }

    def info(self):
        return {
            'name': 'DCAT_AP-IT CSW Harvester',
            'title': 'DCAT_AP-IT CSW Harvester',
            'description': 'DCAT_AP-IT Harvester for harvesting dcatapit fields from CWS',
            'form_config_interface': 'Text'
        }

    def get_package_dict(self, iso_values, harvest_object):
        package_dict = super(DCATAPITCSWHarvester, self).get_package_dict(iso_values, harvest_object)

        mapping_frequencies_to_mdr_vocabulary = self.source_config.get('mapping_frequencies_to_mdr_vocabulary', \
            utils._mapping_frequencies_to_mdr_vocabulary)
        mapping_languages_to_mdr_vocabulary = self.source_config.get('mapping_languages_to_mdr_vocabulary', \
            utils._mapping_languages_to_mdr_vocabulary)

        self._default_values = default_values = self.source_config.get('default_values') or {}

        dcatapit_config = self.source_config.get('dcatapit_config', self._dcatapit_config)

        #if dcatapit_config and not all(name in dcatapit_config for name in self._dcatapit_config):
        #    dcatapit_config = self._dcatapit_config
        #    log.warning('Some keys are missing in dcatapit_config configuration property, \
        #        keyes to use are: dataset_theme, dataset_language, agent_code, frequency, \
        #        agent_code_regex, org_name_regex and dcatapit_skos_theme_id. Using defaults')
        #elif not dcatapit_config:
        #    dcatapit_config = self._dcatapit_config

        controlled_vocabularies = dcatapit_config.get('controlled_vocabularies', \
            self._dcatapit_config.get('controlled_vocabularies'))
        agents = dcatapit_config.get('agents', self._dcatapit_config.get('agents'))

        # ------------------------------#
        #    MANDATORY FOR DCAT-AP_IT   #
        # ------------------------------#

        #  -- identifier -- #
        identifier = iso_values["guid"]
        package_dict['extras'].append({'key': 'identifier', 'value': identifier})

        default_agent_code = identifier.split(':')[0] if ':' in identifier else None

        #  -- theme -- #
        dataset_themes = []
        if iso_values["keywords"]:
            default_vocab_id = self._dcatapit_config.get('controlled_vocabularies').get('dcatapit_skos_theme_id')
            dataset_themes = utils.get_controlled_vocabulary_values('eu_themes', \
                controlled_vocabularies.get('dcatapit_skos_theme_id', default_vocab_id), iso_values["keywords"])

        if dataset_themes:
            dataset_themes = list(set(dataset_themes))
            dataset_themes = [{'theme': str(l), 'subthemes': []} for l in dataset_themes]

        else:
            dataset_themes = default_values.get('dataset_theme')

        if isinstance(dataset_themes, (str, unicode,)):
            dataset_themes = [{'theme': dt} for dt in dataset_themes.strip('{}').split(',')]

        log.info("Medatata harvested dataset themes: %r", dataset_themes)
        package_dict['extras'].append({'key': 'theme', 'value': json.dumps(dataset_themes)})

        #  -- publisher -- #
        citedResponsiblePartys = iso_values["cited-responsible-party"]
        agent_name, agent_code = utils.get_responsible_party(citedResponsiblePartys, agents.get('publisher', \
            self._dcatapit_config.get('agents').get('publisher')))
        package_dict['extras'].append({'key': 'publisher_name', 'value': agent_name})
        package_dict['extras'].append({'key': 'publisher_identifier', 'value': agent_code or default_agent_code})

        #  -- modified -- #
        revision_date = iso_values["date-updated"] or iso_values["date-released"]
        package_dict['extras'].append({'key': 'modified', 'value': revision_date})

        #  -- frequency -- #
        updateFrequency = iso_values["frequency-of-update"]
        package_dict['extras'].append({'key': 'frequency', 'value': \
            mapping_frequencies_to_mdr_vocabulary.get(updateFrequency, \
            dcatapit_config.get('frequency', self._dcatapit_config.get('frequency')))})

        #  -- rights_holder -- #
        citedResponsiblePartys = iso_values["cited-responsible-party"]
        agent_name, agent_code = utils.get_responsible_party(citedResponsiblePartys, \
            agents.get('owner', self._dcatapit_config.get('agents').get('owner')))
        package_dict['extras'].append({'key': 'holder_name', 'value': agent_name})
        package_dict['extras'].append({'key': 'holder_identifier', 'value': agent_code or default_agent_code})

        # -----------------------------------------------#
        #    OTHER FIELDS NOT MANDATORY FOR DCAT_AP-IT   #
        # -----------------------------------------------#

        #  -- alternate_identifier nothing to do  -- #

        #  -- issued -- #
        publication_date = iso_values["date-released"]
        package_dict['extras'].append({'key': 'issued', 'value': publication_date})

        #  -- geographical_name  -- #
        dataset_places = []
        if iso_values["keywords"]:
            default_vocab_id = self._dcatapit_config.get('controlled_vocabularies').get('dcatapit_skos_theme_id')
            dataset_places = utils.get_controlled_vocabulary_values('places', \
                controlled_vocabularies.get('dcatapit_skos_places_id', default_vocab_id), iso_values["keywords"])

        if dataset_places and len(dataset_places) > 1:
            dataset_places = list(set(dataset_places))
            dataset_places = '{' + ','.join(str(l) for l in dataset_places) + '}'
        else:
            dataset_places = dataset_places[0] if dataset_places and len(dataset_places) > 0 else dcatapit_config.get('dataset_places', \
                self._dcatapit_config.get('dataset_places'))

        if dataset_places:
            log.info("Medatata harvested dataset places: %r", dataset_places)
            package_dict['extras'].append({'key': 'geographical_name', 'value': dataset_places})

        #  -- geographical_geonames_url nothing to do  -- #

        #  -- language -- #
        dataset_languages = iso_values["dataset-language"]
        language = None
        if dataset_languages and len(dataset_languages) > 0:
            languages = []
            for language in dataset_languages:
                lang = mapping_languages_to_mdr_vocabulary.get(language, None)
                if lang:
                    languages.append(lang)

            if len(languages) > 1:
                language = '{' + ','.join(str(l) for l in languages) + '}'
            else:
                language = languages[0] if len(languages) > 0 else dcatapit_config.get('dataset_languages', \
                    self._dcatapit_config.get('dataset_languages'))

            log.info("Medatata harvested dataset languages: %r", language)
        else:
            language = dcatapit_config.get('dataset_language')

        package_dict['extras'].append({'key': 'language', 'value': language})

        # temporal_coverage
        # ##################
        temporal_coverage = []
        temporal_start = None
        temporal_end = None

        for key in ['temporal-extent-begin', 'temporal-extent-end']:
            if len(iso_values[key]) > 0:
                temporal_extent_value = iso_values[key][0]
                if key == 'temporal-extent-begin':
                    temporal_start = temporal_extent_value
                if key == 'temporal-extent-end':
                    temporal_end = temporal_extent_value
        if temporal_start:
            temporal_coverage.append({'temporal_start': temporal_start,
                                      'temporal_end': temporal_end})
        if temporal_coverage:
            package_dict['extras'].append({'key': 'temporal_coverage', 'value': json.dumps(temporal_coverage)})

        # conforms_to
        # ##################
        conforms_to_identifier = iso_values["conformity-specification-title"]
        conforms_to_locale = self._ckan_locales_mapping.get(iso_values["metadata-language"], 'it').lower()

        conforms_to = {'identifier': conforms_to_identifier,
                       'title': {conforms_to_locale: conforms_to_identifier}}

        for entry in iso_values["conformity-title-text"]:
            if entry['text'] and entry['locale'].lower()[1:]:
                conforms_to_locale = self._ckan_locales_mapping[entry['locale'].lower()[1:]]
                if self._ckan_locales_mapping[entry['locale'].lower()[1:]]:
                    conforms_to['title'][conforms_to_locale] = entry['text']
        
        if conforms_to:
            package_dict['extras'].append({'key': 'conforms_to', 'value': json.dumps([conforms_to])})

        # creator
        # ###############
        citedResponsiblePartys = iso_values["cited-responsible-party"]
        self.localized_creator = []

        for party in citedResponsiblePartys:
            if party["role"] == "author":
                creator_name = party["organisation-name"]

                agent_code, organization_name = self.get_agent('author', creator_name, default_values)
                creator_lang = self._ckan_locales_mapping.get(iso_values["metadata-language"], 'it').lower()
                
                creator = {'creator_name': {creator_lang: organization_name or creator_name},
                           'creator_identifier': agent_code or default_agent_code}

                for entry in party["organisation-name-localized"]:
                    if entry['text'] and entry['locale'].lower()[1:]:
                        agent_code, organization_name = self.get_agent('author', entry['text'], default_values)
                        creator_lang = self._ckan_locales_mapping[entry['locale'].lower()[1:]]
                        if creator_lang:
                            creator['creator_name'][creator_lang] = organization_name or entry['text']
                package_dict['extras'].append({'key': 'creator', 'value': json.dumps([creator])})


        #  -- license handling -- #
        license_id = package_dict.get('license_id')
        license_url = None
        license = None
        access_constraints = None
        for ex in package_dict['extras']:
            if ex['key'] == 'license_url':
                license_url = ex['value']
            elif ex['key'] == 'license':
                license = ex['value']
            elif ex['key'] == 'access_constraints':
                access_constraints = ex['value']

        if not (access_constraints or license_id or license or license_url):
            l = License.get(License.DEFAULT_LICENSE)

        else:
            l, default = License.find_by_token(access_constraints, license, license_id, license_url)
        
        for res in package_dict['resources']:
            res['license_type'] = l.uri

        # End of processing, return the modified package
        return package_dict


    def get_agent(self, agent_type, agent_string, default_values):

        ## Agent Code
        agent_regex_config = self._dcatapit_config['agents'][agent_type]['code_regex']

        aregex = agent_regex_config.get('regex') or default_values.get('agent_code_regex').get('regex')
        agent_code = re.search(aregex, agent_string)
        if agent_code:
            regex_groups = agent_regex_config.get('groups')
            
            if regex_groups and isinstance(regex_groups, list) and len(regex_groups) > 0:
                code = ''
                for group in regex_groups:
                    code += agent_code.group(group)

                agent_code = code

            agent_code = agent_code.lower().strip()

        ## Agent Name
        org_name_regex_config = self._dcatapit_config['agents'][agent_type]['name_regex']

        oregex = org_name_regex_config.get('regex') or self._default_values.get('org_name_regex').get('regex')
        organization_name = re.search(oregex, agent_string)
        if organization_name:
            regex_groups = org_name_regex_config.get('groups')

            if regex_groups and isinstance(regex_groups, list) and len(regex_groups) > 0:
                code = ''
                for group in regex_groups:
                    code += organization_name.group(group)

                organization_name = code

            organization_name = organization_name.lstrip()

        return [agent_code, organization_name]

