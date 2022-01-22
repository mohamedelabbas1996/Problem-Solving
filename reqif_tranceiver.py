import os
import random
import re
import string
from datetime import datetime
from enum import Enum

#from em_utils.exceptions import UserError
#from em_utils.io_utils.path_utils import parse_path
#from em_utils.progress import progress
from lxml import etree
#from testutils.class_testing import TestLevel

#from helpers import parse_enum_entry, create_md5hash_of_file
#from summary_helpers import get_summary_from_description
from req_tree import ReqTree
from reqif.reqif_requirement import ReqifRequirement
from requirement import RequirementCategory, RequirementStatus, ASIL, InternalStatus, \
    RequirementStatusCustomer
from xhtml_config import BOLD_TAGS, LIST_TAGS, LIST_TYPE_TAGS, SUB_TAGS, SUP_TAGS, \
    ITALIC_TAGS, \
    IMAGE_TAGS, STRIKE_TROUGH_TAGS, DEFAULT_BOLD, DEFAULT_LIST, DEFAULT_LIST_TYPE, DEFAULT_SUB, \
    DEFAULT_SUP, \
    DEFAULT_ITALIC, DEFAULT_IMAGE, DEFAULT_STRIKE_TROUGH, DEFAULT_TABLE_HEAD, DEFAULT_TABLE_ROW, \
    DEFAULT_TABLE_CELL, \
    BREAK_TAGS, DEFAULT_BREAK, ALL_XHTML_DEFAULT_TAGS

_reporter = progress.get_reporter(__name__)


def _create_spcobject_without_values(req: ReqifRequirement, object_type_id: str):
    date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    reqif_id = create_reqif_id()
    req.reqif_id = reqif_id
    spec_object = etree.fromstring('<SPEC-OBJECT LAST-CHANGE="{}" IDENTIFIER="{}" LONG-NAME="{}">'
                                   '<TYPE><SPEC-OBJECT-TYPE-REF>{}</SPEC-OBJECT-TYPE-REF></TYPE>'
                                   '<VALUES></VALUES>'
                                   '</SPEC-OBJECT>'.format(date, reqif_id, req.req_id, object_type_id))

    return spec_object


def _add_xhtml_value_to_spec_object(spec_object, attribute_value: str, type_ref: str):
    attribute_value = _resolve_xhtml_chars_in_str(attribute_value)
    attribute_value = attribute_value.replace('\n', '<xhtml:br/>')
    xhtml_value = etree.fromstring('<ATTRIBUTE-VALUE-XHTML>'
                                   '<DEFINITION>'
                                   '<ATTRIBUTE-DEFINITION-XHTML-REF>{}</ATTRIBUTE-DEFINITION-XHTML-REF>'
                                   '</DEFINITION>'
                                   '<THE-VALUE>'
                                   '<xhtml:div xmlns:xhtml="http://www.w3.org/1999/xhtml">{}</xhtml:div>'
                                   '</THE-VALUE>'
                                   '</ATTRIBUTE-VALUE-XHTML>'.format(type_ref, attribute_value))

    spec_object.find('./VALUES').append(xhtml_value)


def _resolve_xhtml_chars_in_str(value: str):
    """ changes < to &lt; and > to &gt; to mask xhtml specific chars in a string

    :returns: string with masked pointed brackets
    """
    value = value.replace('<', '&lt;')
    value = value.replace('>', '&gt;')
    return value


def create_reqif_id():
    """ creates random alphanumeric reqif-id by the format _{8}-{4}-{4}-{4}-{12}

    :returns: random reqif-id
    """
    first = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(8))
    second = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(4))
    third = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(4))
    fourth = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(4))
    fifth = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(12))
    return '_{}-{}-{}-{}-{}'.format(first, second, third, fourth, fifth)


def resolve_bold(text: str):
    """ resolves xhtml bold to stadart-xhtml

    :param text: string to check for xhtml bold

    :returns: string with resolved bold tags
    """
    for tag in BOLD_TAGS:
        if '</' in tag:
            text = text.replace(tag, DEFAULT_BOLD.replace('<', '</'))
        else:
            text = text.replace(tag, DEFAULT_BOLD)
    return re.sub(' +', ' ', text)


def resolve_list(text: str):
    """ resolves xhtml bold to stadart-xhtml

    :param text: string to check for xhtml bold

    :returns: string with resolved bold tags
    """
    for tag in LIST_TAGS:
        if '</' in tag:
            text = text.replace(tag, DEFAULT_LIST.replace('<', '</'))
        else:
            text = text.replace(tag, DEFAULT_LIST)
    for tag in LIST_TYPE_TAGS:
        if '</' in tag:
            text = text.replace(tag, DEFAULT_LIST_TYPE.replace('<', '</'))
        else:
            text = text.replace(tag, DEFAULT_LIST_TYPE)
    return re.sub(' +', ' ', text)


def resolve_sup(text: str):
    """ resolves xhtml bold to stadart-xhtml

    :param text: string to check for xhtml bold

    :returns: string with resolved bold tags
    """
    for tag in SUP_TAGS:
        if '</' in tag:
            text = text.replace(tag, DEFAULT_SUP.replace('<', '</'))
        else:
            text = text.replace(tag, DEFAULT_SUP)
    return re.sub(' +', ' ', text)


def resolve_sub(text: str):
    """ resolves xhtml bold to stadart-xhtml

    :param text: string to check for xhtml bold

    :returns: string with resolved bold tags
    """
    for tag in SUB_TAGS:
        if '</' in tag:
            text = text.replace(tag, DEFAULT_SUB.replace('<', '</'))
        else:
            text = text.replace(tag, DEFAULT_SUB)
    return re.sub(' +', ' ', text)


def resolve_italic(text: str):
    """ resolves xhtml italic to stadart-xhtml

    :param text: string to check for xhtml italic

    :returns: string with resolved italic tags
    """
    for tag in ITALIC_TAGS:
        if '</' in tag:
            text = text.replace(tag, DEFAULT_ITALIC.replace('<', '</'))
        else:
            text = text.replace(tag, DEFAULT_ITALIC)
    return re.sub(' +', ' ', text)


def resolve_strikethrough(text: str):
    """ resolves xhtml strikethrough to stadart-xhtml

    :param text: string to check for xhtml strikethrough

    :returns: string with resolved strikethrough tags
    """
    for tag in STRIKE_TROUGH_TAGS:
        if '</' in tag:
            text = text.replace(tag, DEFAULT_STRIKE_TROUGH.replace('<', '</'))
        else:
            text = text.replace(tag, DEFAULT_STRIKE_TROUGH)
    return re.sub(' +', ' ', text)


def resolve_break(text: str):
    """ resolves xhtml break to stadart-xhtml

    :param text: string to check for xhtml strikethrough

    :returns: string with resolved strikethrough tags
    """
    for tag in BREAK_TAGS:
        text = text.replace(tag, DEFAULT_BREAK)
    return re.sub(' +', ' ', text)


def resolve_image(text: str, reqif_path: str):
    """ resolves xhtml image tags to stadart-xhtml

    :param text: string to check for xhtml image
    :param reqif_path: path to reqif file

    :returns: string with resolved image tags
    """
    images = dict()
    ole_regex = re.compile(
        r'<(reqif-)?xhtml:object\s*type=\"application/rtf\"\s*data=\".+?.ole\">\s*(<(reqif-)?xhtml:object\s+type=\"image/png\"\s+data=\".+?.png\")>.+?(</(reqif-)?xhtml:object>){2}',
        re.MULTILINE | re.DOTALL)
    text = ole_regex.sub(r'\g<2>/>', text)

    for tag in IMAGE_TAGS:
        text = text.replace('.ole', '.png').replace('application/rtf', 'image/png')
        image_objects = re.findall(tag + '.*?/>', text, re.MULTILINE | re.DOTALL)
        for image in image_objects:
            image_name = parse_path(re.search(r'(?<=data=\").*?(?=\")', image).group())
            if os.path.isfile(image_name):
                full_image_path = image_name
            else:
                full_image_path = parse_path(os.path.join(os.path.dirname(reqif_path), image_name))
            image_hash = create_md5hash_of_file(full_image_path)
            image_name = image_hash + '.' + image_name.split('.')[-1]
            images[image_name] = full_image_path
            text = text.replace(image,
                                ' ' + DEFAULT_IMAGE + image_name + DEFAULT_IMAGE.replace('<', '</'))
    return re.sub(' +', ' ', text), images


def value_in_enum(value: str, enum: Enum, mapping: dict = None):
    """ mapps a value und checks if the result exists in an enum,
        returns the corresponding enum value

    :param value: value to check for in Enum
    :param enum: enum for specific property
    :param mapping: (opt.) Mapping for source values to values defined in Enums

    :returns: Enum value matching value
    """
    if not mapping:
        mapping = {}

    if value in mapping.keys():
        value = mapping[value]

    if value:
        return parse_enum_entry(value, enum)
    else:
        return value


def _get_reqif_dom(reqif_file: str) -> etree.ElementTree:
    """ gets the complete reqif file as ElementTree

    :param reqif_file: filepath to reqif file

    :returns: Element tree and corresponding namespace
    """
    parser = etree.XMLParser(remove_blank_text=True)
    try:
        reqif_dom = etree.parse(reqif_file, parser)
    except OSError:
        raise FileNotFoundError(
            'The specified reqif-File {} could not be found.'.format(reqif_file))
    root = reqif_dom.getroot()
    namespace = {k if k is not None else 'def': v for k, v in root.nsmap.items()}

    return reqif_dom, namespace


class ReqIfTransceiver:  # pylint: disable=too-many-instance-attributes
    """ class for ReqIf-Requirements import and export """

    def __init__(self, reqif_file_path: str, attribute_config: dict, value_mapping: dict,
                 custom_raw_to_req_callback=None,
                 value_mapping_inverse=None, template: str = None, document_type: str = None,
                 default_values: dict = {}):
        self._reqTree = None
        if template:
            if not os.path.isfile(template):
                raise UserError('The given Template-File {} could not be found. '
                                'Please check your input'.format(template))
        else:
            if document_type:
                if document_type == 'SRS':
                    template = parse_path(os.path.dirname(__file__) + '\\templates\\SRS_Template.reqif')
                else:
                    raise UserError('For the desired Documenttype {}, no Tempalte is defined!')
        if template:
            _reqif_dom, _namespace = _get_reqif_dom(template)
        else:
            _reqif_dom, _namespace = _get_reqif_dom(reqif_file_path)
        self._reqif_file_path = reqif_file_path
        self._reqif_dom = _reqif_dom
        self._namespace = _namespace
        self._attribute_config = attribute_config
        self._value_mapping = value_mapping
        self._value_mapping_inverse = value_mapping_inverse if value_mapping_inverse else \
            {v: k for k, v in value_mapping.items()}
        self._custom_raw_to_req_callback = custom_raw_to_req_callback
        self._template = template
        self._default_values = default_values

    def read(self):
        """ reads all Requirements from a reqif-file"""
        _reporter.status("Reading requirements from reqif file")

        # Get all Spectypes from ReqIf
        spectypes_dict = self._get_spectypes()
        # Get all Specobjects (Requirements) from ReqIf
        specobjects_dict = self._get_specobjects()
        # Get all Specrelations from ReqIf
        specrelations_dict = self._get_spec_relations()

        resolved_specobjects_dict = self._resolve_reqif_references(specobjects_dict,
                                                                   spectypes_dict,
                                                                   specrelations_dict)
        req_dict = {}
        req_list = []

        _reporter.start("Converting raw spec objects to internal Requirement Objects",
                        len(resolved_specobjects_dict.keys()))
        for idx, specobject in enumerate(resolved_specobjects_dict.values()):
            new_req = self.raw_to_req(specobject)
            req_dict[specobject['reqif_id']] = new_req
            req_list.append(new_req)
            _reporter.progress(idx + 1)
        _reporter.finish()

        req_tree = []
        reqif_reqs = self._reqif_dom.findall('//def:SPECIFICATIONS/def:SPECIFICATION',
                                             self._namespace)
        for req in reqif_reqs:
            reqif_requirement = []
            self._get_spec_hierarchy(req, reqif_requirement,
                                     req_dict)
            req_tree.append(reqif_requirement)
        self._reqTree = ReqTree(req_tree[0], req_list)
        self._resolve_reqif_tables()

        return self._reqTree

    def write(self):
        """ updates a given reqif-file"""
        spectypes_dict = self._get_spectypes()
        if self._template:
            self._create_reqif_from_template(spectypes_dict)
        else:
            for req in self._reqTree.get_tree():
                self._update_reqif_req(req, spectypes_dict)
        self._reqif_dom.write(self._reqif_file_path, pretty_print=True)
        return self._reqif_dom

    # pylint: disable=too-many-branches
    def raw_to_req(self, specobject: dict) -> ReqifRequirement:
        """ converts a dictonary with the values of a reqif file to a Requirement Object

        :param specobject: dict containing all information to a Requirement

        :returns: ReqIf-Requirement-Object
        """
        self._get_req_with_mapping(specobject)
        new_req = ReqifRequirement(specobject['reqif_id'])
        if specobject.get('req_id'):
            new_req.req_id = re.sub(r'<.*?>', '', specobject['req_id']).strip()
        if specobject.get('content') is not None:
            content = specobject['content']
            new_req.content = self._prepare_content(content, new_req)
            new_req.summary = get_summary_from_description(new_req.raw_content)
        elif self._default_values.get('content'):
            new_req.content = self._default_values.get('content')
        if not new_req.summary:
            if specobject.get('TableType'):
                new_req.content = specobject['TableType']
                new_req.summary = get_summary_from_description(specobject['TableType'])
            elif self._default_values.get('summary'):
                new_req.summary = self._default_values.get('summary')
        if specobject.get('category'):
            new_req.category = value_in_enum(specobject['category'],
                                             RequirementCategory,
                                             self._value_mapping)
        elif self._default_values.get('category'):
            new_req.category = self._default_values.get('category')
        else:
            new_req.category = RequirementCategory.CUSTOM_TYPE
        if specobject.get('asil'):
            new_req.asil = value_in_enum(specobject['asil'], ASIL, self._value_mapping)
        elif self._default_values.get('asil'):
            new_req.asil = self._default_values.get('asil')
        if specobject.get('status_customer'):
            new_req.status_customer = value_in_enum(specobject['status_customer'],
                                                    RequirementStatusCustomer,
                                                    self._value_mapping)
        elif self._default_values.get('status_customer'):
            new_req.status_customer = self._default_values.get('status_customer')
        if specobject.get('test_levels'):
            new_req.test_levels.add(value_in_enum(specobject['test_levels'],
                                                  TestLevel,
                                                  self._value_mapping))
        elif self._default_values.get('test_levels'):
            new_req.test_levels.add(self._default_values.get('test_levels'))
        if specobject.get('customer_comments'):
            new_req.customer_comments = self._prepare_content(specobject['customer_comments'], new_req)
        elif self._default_values.get('customer_comments'):
            new_req.customer_comments = self._default_values.get('customer_comments')
        if specobject.get('internal_comments'):
            new_req.internal_comments = self._prepare_content(specobject['internal_comments'], new_req)
        elif self._default_values.get('internal_comments'):
            new_req.internal_comments = self._default_values.get('internal_comments')
        if specobject.get('review_comments'):
            new_req.review_comments = self._prepare_content(specobject['review_comments'],
                                                            new_req)
        elif self._default_values.get('review_comments'):
            new_req.review_comments = self._default_values.get('review_comments')
        if specobject.get('status'):
            new_req.status = value_in_enum(specobject['status'],
                                           RequirementStatus,
                                           self._value_mapping)
        elif self._default_values.get('status'):
            new_req.status = self._default_values.get('status')
        if specobject.get('components'):
            new_req.components.add(specobject['components'])
        if self._custom_raw_to_req_callback:
            self._custom_raw_to_req_callback(new_req, specobject)
        return new_req

    def _prepare_content(self, content, new_req):
        if any([tag in content for tag in BOLD_TAGS]):
            content = resolve_bold(content)
        if any([tag in content for tag in LIST_TAGS]):
            content = resolve_list(content)
        if any([tag in content for tag in SUB_TAGS]):
            content = resolve_sub(content)
        if any([tag in content for tag in SUP_TAGS]):
            content = resolve_sup(content)
        if any([tag in content for tag in ITALIC_TAGS]):
            content = resolve_italic(content)
        if any([tag in content for tag in STRIKE_TROUGH_TAGS]):
            content = resolve_strikethrough(content)
        if any([tag in content for tag in BREAK_TAGS]):
            content = resolve_break(content)
        if any([tag in content for tag in IMAGE_TAGS]):
            content, images = resolve_image(content, self._reqif_file_path)
            new_req.attachment_hashes.update(images)

        # Remove all remaining xhtml tags
        remaining_xhtml = re.findall(r'(</?(reqif-)?xhtml.*?/?>)', content)
        for remaining_tag in remaining_xhtml:
            if remaining_tag[0] not in ALL_XHTML_DEFAULT_TAGS:
                content = content.replace(remaining_tag[0], '')
        return content

    def req_to_raw(self):
        """ has to be implemented if reqif-documents should be generated"""
        raise NotImplementedError

    def _get_spec_relations(self) -> dict:
        """ Extracts the spec-relations from the ReqIf-Document for linking

        :returns: dictonary containing all relations (reqif_id <-> reqif_id)
        """
        spec_relations = self._reqif_dom.findall('//def:SPEC-RELATIONS/def:SPEC-RELATION',
                                                 self._namespace)
        spec_relations_dict = {}

        for spec_relation in spec_relations:
            source_node = spec_relation.find('./def:SOURCE/def:SPEC-OBJECT-REF', self._namespace)
            source = source_node.text if source_node else ''
            target_node = spec_relation.find('./def:TARGET/def:SPEC-OBJECT-REF', self._namespace)
            target = target_node.text if target_node else ''
            if not spec_relations_dict.get(source):
                spec_relations_dict[source] = []
            spec_relations_dict[source].append(target)

        return spec_relations_dict

    def _get_spectypes(self) -> dict:
        """ Extracts the spec-types (representing data-types) from the ReqIf-Document

        :returns: dictonary containing all spec-types
        """
        spec_types = self._reqif_dom.findall('//def:SPEC-TYPES/*/def:SPEC-ATTRIBUTES/*',
                                             self._namespace)
        spec_types_dict = {}
        _reporter.start("Parsing spec-types from Reqif document", len(spec_types))
        for idx, spec_type in enumerate(spec_types):
            type_id = spec_type.attrib['IDENTIFIER']
            name = spec_type.attrib['LONG-NAME']
            datatype_def = spec_type.find('./def:TYPE/*', self._namespace).text
            spec_types_dict[type_id] = [name, spec_type.tag, datatype_def]
            _reporter.progress(idx + 1)
        _reporter.finish()

        return spec_types_dict

    def _get_specobjects(self) -> dict:
        """ Extracts the Specobjects (Requirements) from the ReqIf-Document

        :returns: dictonary containing all Requirements, referencable by ReqIf-Id
        """
        specobjects_dict = {}
        specobjects = self._reqif_dom.findall('//def:SPEC-OBJECTS/def:SPEC-OBJECT', self._namespace)
        _reporter.start("Parsing spec-objects from Reqif document", len(specobjects))
        for idx, specobject in enumerate(specobjects):
            values = specobject.findall('./def:VALUES/*', self._namespace)
            specobjects_dict[specobject.attrib['IDENTIFIER']] = values
            _reporter.progress(idx + 1)
        _reporter.finish()

        return specobjects_dict

    def _resolve_reqif_references(self, specobject_dict: dict, spectypes_dict: dict,
                                  specrelations_dict: dict) -> dict:
        """ Resolves ReqIf References and Mapps the The Propertynames according to config

        :param specobject_dict: Dictonary containing the ReqIf-Requirements
        :param spectypes_dict: Dictonary containing the ReqIf-spectypes
        :param specrelations_dict: Dictonary containing the SpecRelations

        :returns: dictonary containing all Requirements with resolved References
                  and mapped Properties
        """
        result_dict = {}
        # Iterate all Requirements
        _reporter.start("Resolving references for spec-objects", len(specobject_dict.keys()))
        for idx, specobject_key in enumerate(specobject_dict.keys()):
            new_specobject = {}
            spec_object = specobject_dict[specobject_key]
            # Iterate all attributes of a Requirement,
            # call function for specific attribute-type
            for attrib in spec_object:
                attrib_definition = \
                    spectypes_dict[attrib.find('./def:DEFINITION/*', self._namespace).text][0]
                attrib_type = re.sub('{.*}', '', attrib.tag)
                if attrib_type == 'ATTRIBUTE-VALUE-INTEGER':
                    new_specobject[attrib_definition] = self._get_integer(attrib)
                elif attrib_type == 'ATTRIBUTE-VALUE-BOOLEAN':
                    new_specobject[attrib_definition] = self._get_boolen(attrib)
                elif attrib_type == 'ATTRIBUTE-VALUE-XHTML':
                    new_specobject[attrib_definition] = self._get_xhtml(attrib)
                elif attrib_type == 'ATTRIBUTE-VALUE-ENUMERATION':
                    new_specobject[attrib_definition] = self._get_enumeration(attrib,
                                                                              self._reqif_dom)
                elif attrib_type == 'ATTRIBUTE-VALUE-STRING':
                    new_specobject[attrib_definition] = self._get_string(attrib)
                elif attrib_type == 'ATTRIBUTE-VALUE-DATE':
                    new_specobject[attrib_definition] = self._get_date(attrib)
                elif attrib_type == 'ATTRIBUTE-VALUE-REAL':
                    new_specobject[attrib_definition] = self._get_real(attrib)
                else:  # pragma: no branch
                    raise ValueError(
                        'Could not parse Requirement with specobject key '
                        '{}. Unknown Attributetype {}'.format(specobject_key, attrib_type))
            new_specobject['reqif_id'] = specobject_key
            # get relations
            new_specobject['_links'] = specrelations_dict.get(specobject_key)
            result_dict[specobject_key] = new_specobject
            _reporter.progress(idx + 1)
        _reporter.finish()

        return result_dict

    def _get_req_with_mapping(self, specobject: dict) -> dict:
        """ mappes attributes of ReqIf Requirements to
        given attributes of th config

        :param specobject: Requirements-Object
        """
        # use default config and update by given config
        _config = {
            "req_id": "ID",
            "req_type": "Category",
            "description": "Text"
        }

        _config.update(self._attribute_config)

        # map attribute names by config
        for source_attr_name, dest_attr_name in _config.items():
            # map all attributes if a list is given
            if isinstance(dest_attr_name, list):
                for attr_name in dest_attr_name:
                    if specobject.get(attr_name) is not None:
                        specobject[source_attr_name] = specobject.get(attr_name)
            else:
                attr_name = dest_attr_name
                if specobject.get(attr_name) is not None:
                    specobject[source_attr_name] = specobject.get(attr_name)

    def _get_spec_hierarchy(self, req: 'Element', result_list: list,
                            req_dict: dict) -> list:
        """ Gives the unstructered Requirements the Tree-Structure,
        based on the Spec-Hierarchy Nodes in Req-If

        :param req: xml-Tree of a reqif-requirement
        :param result_list: Requirements_tree, designed as parameter for recursiv-call
        :param req_dict: dictonary with raw requiremnt-dictonarys parsed from reqif
        :returns: List of Requirement-Objects with Hirarchy-Information
        """
        spec_objects = req.findall(
            "./def:CHILDREN/def:SPEC-HIERARCHY/def:OBJECT/def:SPEC-OBJECT-REF",
            self._namespace)
        for spec_object in spec_objects:
            # create a requirement object from the requirement dict, append it to the given list
            req = req_dict[spec_object.text]
            if spec_object.getparent().getparent().get(
                    'IS-TABLE-INTERNAL') == 'true':  # pragma: no branch
                if spec_object.getparent().getparent().getparent().getparent().get(
                        'IS-TABLE-INTERNAL') != 'true':
                    req.reqif_tablehead = True
            result_list.append(req)

            # and get spec hierachy for the requirement object from the SPEC-HIERARCHY xml element
            self._get_spec_hierarchy(spec_object.getparent().getparent(), req.children,
                                     req_dict)

    def _get_attribute_value(self, node: etree.ElementTree) -> str:
        """ gets the value of a Reqif-Requirement-Property

        :param node: etree.ElementTree-Object containing a property of a spec-object

        :returns: value of the property
        """
        # Integer, Boolean, String, Date and Real get handled the same way
        if re.sub('{.*}', '', node.tag) in ('ATTRIBUTE-VALUE-INTEGER',
                                            'ATTRIBUTE-VALUE-BOOLEAN',
                                            'ATTRIBUTE-VALUE-STRING',
                                            'ATTRIBUTE-VALUE-DATE',
                                            'ATTRIBUTE-VALUE-REAL'):
            return node.attrib['THE-VALUE']
        elif re.sub('{.*}', '', node.tag) == 'ATTRIBUTE-VALUE-ENUMERATION':
            enums = node.findall('./def:VALUES/*', self._namespace)
            enum_values = []
            for enum_ref in enums:
                enum_values.append(
                    self._reqif_dom.find("//*[@IDENTIFIER='{}']".format(
                        enum_ref.text), self._namespace).attrib['LONG-NAME'])
            return ', '.join(enum_values)
        elif re.sub('{.*}', '', node.tag) == 'ATTRIBUTE-VALUE-XHTML':  # pragma: no cover
            return self._get_xhtml(node)
        else:  # pragma: no cover
            print('Unbekannter Value-Type: %s', (str(node)))
            return str(node)

    def _set_attribute_value(self, value: str, node: etree.ElementTree):
        """ sets the value of a Reqif-Requirement-Property

        :param value: value to be set
        :param node: etree.ElementTree-Object containing a property of a spec-object
        """
        # Integer, Boolean, String, Date and Real get handled the same way
        if re.sub('{.*}', '', node.tag) in ('ATTRIBUTE-VALUE-INTEGER',
                                            'ATTRIBUTE-VALUE-BOOLEAN',
                                            'ATTRIBUTE-VALUE-STRING',
                                            'ATTRIBUTE-VALUE-DATE',
                                            'ATTRIBUTE-VALUE-REAL'):
            node.attrib['THE-VALUE'] = value
        elif re.sub('{.*}', '', node.tag) == 'ATTRIBUTE-VALUE-ENUMERATION':
            try:
                enum_definitions = self._reqif_dom.find(
                    '//def:DATATYPE-DEFINITION-ENUMERATION/'
                    'def:SPECIFIED-VALUES/def:ENUM-VALUE[@LONG-NAME="{}"]'.format(
                        value), self._namespace)
                enum_list = enum_definitions.getparent().findall('./def:ENUM-VALUE',
                                                                 self._namespace)
                idx = [enum.attrib['LONG-NAME'] for enum in enum_list].index(value)
                node.find('./def:VALUES/def:ENUM-VALUE-REF', self._namespace).text = \
                    [enum.attrib['IDENTIFIER'] for enum in enum_list][idx]
            # falscher Wert für ein Enum
            except AttributeError:
                raise ValueError(
                    'Der Enum Wert {} ist im Reqif-Dokument nicht definiert'.format(
                        value))
        elif re.sub('{.*}', '', node.tag) == 'ATTRIBUTE-VALUE-XHTML':  # pragma: no cover
            print('Änderungen an XHTML-Knoten noch nicht implementiert')

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-nested-blocks
    # pylint: disable=too-many-branches
    def _update_reqif_req(self, req: 'Requirement', spectypes_dict: dict):
        """ updates ReqIf Requirements

        :param req: Requirement-Object with values to update Reqif; Source-Requirement
        :param spectypes_dict: Dict with all Spec-Types in the ReqIf-File
        """
        spec_object = self._get_spec_object(req.req_id)

        if InternalStatus.UPDATED in req._internal_status:
            if hasattr(req, 'status') and req.status:
                status_ref = self._get_spectyps_ref(spectypes_dict, 'status')
                status_node = self._get_status_node(spectypes_dict, spec_object)
                if req.status == RequirementStatus.IN_WORK:
                    value = self._value_mapping_inverse.get(RequirementStatus.IN_WORK)
                elif req.status == RequirementStatus.IN_REVIEW:
                    value = self._value_mapping_inverse.get(RequirementStatus.IN_REVIEW)
                elif req.status == RequirementStatus.NEW:
                    value = self._value_mapping_inverse.get(RequirementStatus.NEW)
                elif req.status == RequirementStatus.ACCEPTED:
                    value = self._value_mapping_inverse.get(RequirementStatus.ACCEPTED)
                elif req.status == RequirementStatus.REJECTED:
                    value = self._value_mapping_inverse.get(RequirementStatus.REJECTED)
                elif req.status == RequirementStatus.UNCLEAR_EXTERNAL:
                    value = self._value_mapping_inverse.get(RequirementStatus.UNCLEAR_EXTERNAL)
                elif req.status == RequirementStatus.UNCLEAR_INTERNAL:
                    value = self._value_mapping_inverse.get(RequirementStatus.UNCLEAR_INTERNAL)
                else:
                    raise ValueError(
                        'Requirement {} got an unknown Requirement-Status: {}'.format(
                            req.req_id, req.status))

                enum_ref_nodes = \
                    self._reqif_dom.findall(
                        "//def:DATATYPE-DEFINITION-ENUMERATION[@IDENTIFIER='{}']/"
                        "def:SPECIFIED-VALUES/*".format(spectypes_dict[status_ref][2]),
                        self._namespace)
                for enum_ref in enum_ref_nodes:
                    if enum_ref.attrib['LONG-NAME'] == value:
                        value = enum_ref.attrib['IDENTIFIER']
                        status_node.find('def:VALUES/def:ENUM-VALUE-REF',
                                         self._namespace).text = value
                        values_node = spec_object.findall("def:VALUES", self._namespace)[0]
                        values_node.append(status_node)
                        break

            if hasattr(req, 'internal_comments') and req.internal_comments:
                internal_comment_node = self._get_internal_comments_node(spectypes_dict,
                                                                         spec_object, req)
                values_node = spec_object.findall("def:VALUES", self._namespace)[0]
                values_node.append(internal_comment_node)

            if hasattr(req, 'customer_comments') and req.customer_comments:
                customer_comment_node = self._get_customer_comments_node(spectypes_dict,
                                                                         spec_object, req)
                values_node = spec_object.findall("def:VALUES", self._namespace)[0]
                values_node.append(customer_comment_node)

            if hasattr(req, 'review_comments') and req.review_comments:
                review_comments_node = self._get_review_comments_node(spectypes_dict,
                                                                      spec_object, req)
                values_node = spec_object.findall("def:VALUES", self._namespace)[0]
                values_node.append(review_comments_node)

        # recursive call for Child-Elements
        for child in req.children:
            self._update_reqif_req(child, spectypes_dict)

    def _get_spectyps_ref(self, spectypes_dict, req_attribute_name):
        spectyps_ref = None
        for key, values in spectypes_dict.items():
            if values[0] == self._attribute_config[req_attribute_name]:
                spectyps_ref = key
                break
        return spectyps_ref

    def _get_status_node(self, spectypes_dict, spec_object):
        for spectype_id, spectypes_value in spectypes_dict.items():
            if self._attribute_config['status'] == spectypes_value[0]:
                attribute_reqif_id = spectype_id

        spec_object_values = spec_object.findall('def:VALUES/*', self._namespace)
        status_node = None
        for value in spec_object_values:
            node_as_string = etree.tostring(value, encoding="unicode")
            if attribute_reqif_id in node_as_string:
                status_node = value
                break

        if not status_node:
            status_node = etree.fromstring(
                '<def:ATTRIBUTE-VALUE-ENUMERATION xmlns:def="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd">'
                '<def:DEFINITION>'
                '<def:ATTRIBUTE-DEFINITION-ENUMERATION-REF >{}</def:ATTRIBUTE-DEFINITION-ENUMERATION-REF>'
                '</def:DEFINITION>'
                '<def:VALUES>'
                '<def:ENUM-VALUE-REF>'
                '</def:ENUM-VALUE-REF>'
                '</def:VALUES>'
                '</def:ATTRIBUTE-VALUE-ENUMERATION>'.format(attribute_reqif_id))

        return status_node

    def _get_internal_comments_node(self, spectypes_dict, spec_object, req):
        for spectype_id, spectypes_value in spectypes_dict.items():
            if self._attribute_config['internal_comments'] == spectypes_value[0]:
                attribute_reqif_id = spectype_id

        internal_comments_node = None
        def_nodes = spec_object.findall(
            'def:VALUES/def:ATTRIBUTE-VALUE-XHTML/def:DEFINITION/def:ATTRIBUTE-DEFINITION-XHTML-REF',
            self._namespace)
        for node in def_nodes:
            if node.text is attribute_reqif_id:
                internal_comments_node = node
                break
        if not internal_comments_node:
            internal_comments_node = etree.fromstring(
                '<def:ATTRIBUTE-VALUE-XHTML xmlns:def="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd">'
                '<def:DEFINITION>'
                '<def:ATTRIBUTE-DEFINITION-XHTML-REF >{}</def:ATTRIBUTE-DEFINITION-XHTML-REF>'
                '</def:DEFINITION><def:THE-VALUE>'
                '<reqif-xhtml:div xmlns:reqif-xhtml="http://www.w3.org/1999/xhtml">'
                '{}</reqif-xhtml:div>'
                '</def:THE-VALUE>'
                '</def:ATTRIBUTE-VALUE-XHTML>'.format(attribute_reqif_id,
                                                      self._convert_xhtml_to_reqif(
                                                          req.internal_comments)))

        return internal_comments_node

    def _get_customer_comments_node(self, spectypes_dict, spec_object, req):
        for spectype_id, spectypes_value in spectypes_dict.items():
            if self._attribute_config['customer_comments'] == spectypes_value[0]:
                attribute_reqif_id = spectype_id

        customer_comments_node = None
        def_nodes = spec_object.findall(
            'def:VALUES/def:ATTRIBUTE-VALUE-XHTML/def:DEFINITION/def:ATTRIBUTE-DEFINITION-XHTML-REF',
            self._namespace)
        for node in def_nodes:
            if node.text is attribute_reqif_id:
                customer_comments_node = node
                break
        if not customer_comments_node:
            customer_comments_node = etree.fromstring(
                '<def:ATTRIBUTE-VALUE-XHTML xmlns:def="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd">'
                '<def:DEFINITION>'
                '<def:ATTRIBUTE-DEFINITION-XHTML-REF >{}</def:ATTRIBUTE-DEFINITION-XHTML-REF>'
                '</def:DEFINITION><def:THE-VALUE>'
                '<reqif-xhtml:div xmlns:reqif-xhtml="http://www.w3.org/1999/xhtml">'
                '{}</reqif-xhtml:div>'
                '</def:THE-VALUE>'
                '</def:ATTRIBUTE-VALUE-XHTML>'.format(attribute_reqif_id,
                                                      self._convert_xhtml_to_reqif(
                                                          req.customer_comments)))

        return customer_comments_node

    def _get_review_comments_node(self, spectypes_dict, spec_object, req):
        for spectype_id, spectypes_value in spectypes_dict.items():
            if self._attribute_config['review_comments'] == spectypes_value[0]:
                attribute_reqif_id = spectype_id

        review_comments_node = None
        def_nodes = spec_object.findall(
            'def:VALUES/def:ATTRIBUTE-VALUE-XHTML/def:DEFINITION/def:ATTRIBUTE-DEFINITION-XHTML-REF',
            self._namespace)
        for node in def_nodes:
            if node.text is attribute_reqif_id:
                review_comments_node = node
                break
        if not review_comments_node:
            review_comments_node = etree.fromstring(
                '<def:ATTRIBUTE-VALUE-XHTML xmlns:def="http://www.omg.org/spec/ReqIF/20110401/reqif.xsd">'
                '<def:DEFINITION>'
                '<def:ATTRIBUTE-DEFINITION-XHTML-REF >{}</def:ATTRIBUTE-DEFINITION-XHTML-REF>'
                '</def:DEFINITION><def:THE-VALUE>'
                '<reqif-xhtml:div xmlns:reqif-xhtml="http://www.w3.org/1999/xhtml">'
                '{}</reqif-xhtml:div>'
                '</def:THE-VALUE>'
                '</def:ATTRIBUTE-VALUE-XHTML>'.format(attribute_reqif_id,
                                                      self._convert_xhtml_to_reqif(
                                                          req.review_comments)))

        return review_comments_node

    def _convert_xhtml_to_reqif(self, xhtml_string: str):
        if DEFAULT_STRIKE_TROUGH in xhtml_string:
            xhtml_string = xhtml_string.replace(DEFAULT_STRIKE_TROUGH,
                                                '<reqif-xhtml:span style="text-decoration: line-through;">')
            xhtml_string = xhtml_string.replace(DEFAULT_STRIKE_TROUGH.replace('<', '</'),
                                                '</reqif-xhtml:span>')

        if DEFAULT_IMAGE in xhtml_string:
            images = re.findall('<xhtml:img>.*</xhtml:img>', xhtml_string)
            for image in images:
                updated_image = image.replace('<xhtml:img>',
                                              '<xhtml:object xmlns:xhtml="http://www.w3.org/1999/xhtml" data="')
                updated_image = updated_image.replace('</xhtml:img>', '"/>')
                updated_image = updated_image.replace('\\', '/')
                xhtml_string = xhtml_string.replace(image, updated_image)

        return xhtml_string

    @staticmethod
    def _get_boolen(node: etree.ElementTree) -> str:
        """ Extracts the Value of a boolean attribute of a SPEC-OBJECT

        :param node: etree.ElementTree-Object containing boolean attribute of a SPEC-OBJECT
        :returns: string: boolean value as a string
        """
        return node.attrib['THE-VALUE']

    @staticmethod
    def _get_date(node: etree.ElementTree) -> str:
        """ Extracts the Value of a date attribute of a SPEC-OBJECT

        :param node: etree.ElementTree-Object containing date attribute of a SPEC-OBJECT
        :returns: string: date value as a string
        """
        return node.attrib['THE-VALUE']

    @staticmethod
    def _get_integer(node: etree.ElementTree) -> str:
        """ Extracts the Value of a integer attribute of a SPEC-OBJECT

        :param node: etree.ElementTree-Object containing integer attribute of a SPEC-OBJECT
        :returns: string: integer value as a string
        """
        return node.attrib['THE-VALUE']

    @staticmethod
    def _get_real(node: etree.ElementTree) -> str:
        """ Extracts the Value of a real attribute of a SPEC-OBJECT

        :param node: etree.ElementTree-Object containing real attribute of a SPEC-OBJECT
        :returns: string: real value as a string
        """
        return node.attrib['THE-VALUE']

    @staticmethod
    def _get_string(node: etree.ElementTree) -> str:
        """ Extracts the Value of a string attribute of a SPEC-OBJECT

        :param node: etree.ElementTree-Object containing string attribute of a SPEC-OBJECT
        :returns: string: string value as a string
        """
        return node.attrib['THE-VALUE']

    def _get_enumeration(self, node: etree.ElementTree, reqif_dom: etree.ElementTree) -> str:
        """ Extracts the Value of a enum attribute of a SPEC-OBJECT
        if more than one enum values are given, they are joined by ','

        :param node: etree.ElementTree-Object containing enum attribute of a SPEC-OBJECT
        :returns: string: enum value as a string
        """
        enums = node.findall('./def:VALUES/*', self._namespace)
        enum_values = []
        for enum_ref in enums:
            enum_values.append(
                reqif_dom.find("//*[@IDENTIFIER='{}']".format(enum_ref.text)).attrib['LONG-NAME'])
        return ', '.join(enum_values)

    def _get_xhtml(self, node: etree.ElementTree) -> etree.ElementTree:
        """ Extracts the Value of a xhtml attribute of a SPEC-OBJECT

        :param node: etree.ElementTree-Object containing xhtml attribute of a SPEC-OBJECT
        :returns: ElementTree: xhtml node
        """
        node_value = node.find('./def:THE-VALUE/*', self._namespace)
        if isinstance(node_value, etree._Element):
            node_as_text = etree.tostring(node_value, encoding='utf-8', method='xml').decode(
                "utf-8")
            text_value = re.sub(r'<reqif-xhtml:div[^>]+>', '', node_as_text)
            text_value = re.sub(r'<xhtml:div[^>]+>', '', text_value)
            text_value = re.sub(r'</reqif-xhtml:div>', '', text_value)
            text_value = re.sub(r'</xhtml:div>', '', text_value)
            return text_value
        else:
            return node_value

    def _resolve_reqif_tables(self):
        for req in self._reqTree._req_list:
            if req.reqif_tablehead:
                self._get_table_content_from_children(req)

    def _get_table_content_from_children(self, req: ReqifRequirement):
        if not req.content:
            req.content = ''
        table_content = req.content + '\n' + DEFAULT_TABLE_HEAD
        for table_row in req.children:
            table_content = table_content + DEFAULT_TABLE_ROW
            for table_cell in table_row.children:
                if not table_cell.content:
                    table_cell.content = ''
                table_content = table_content + DEFAULT_TABLE_CELL + table_cell.content + \
                    DEFAULT_TABLE_CELL.replace('<', '</')
            table_content = table_content + DEFAULT_TABLE_ROW.replace('<', '</')
        table_content = table_content + DEFAULT_TABLE_HEAD.replace('<', '</')
        table_content = table_content.replace(DEFAULT_BREAK, '')

        req.content = table_content

    def _create_reqif_from_template(self, spectypes_dict: dict):
        """ creates a new reqif document from a given template

        :param spectypes_dict: dictonary with specobjects retrieved from reqif
        """
        # creates a new dict of spectypes with type-name as key instead of reqif-id
        spec_types_by_name_dict = {v[0]: v[1:3] + [k] for k, v in spectypes_dict.items()}
        object_type_id = \
            self._reqif_dom.find('//def:SPEC-TYPES/def:SPEC-OBJECT-TYPE', self._namespace).attrib['IDENTIFIER']
        for req in self._reqTree.get_all_requirements_list():
            self._create_new_specobject(req, spec_types_by_name_dict, object_type_id)
        self._create_spec_hirarchy()

    def _create_new_specobject(self, req: ReqifRequirement, spec_types_by_name_dict: dict, object_type_id: str):
        """ creates a new reqif specobject (issue) from a req-object

        :param req: python requierement
        :param spec_types_by_name_dict: dictonary of spectypes with key= name and vale = [type, definitionref, reqif-id]
        :param object_type_id: id of the objecttype (fixed for most reqifs)
        """
        spec_object = _create_spcobject_without_values(req, object_type_id)
        for req_attribute, reqif_attribute in self._attribute_config.items():
            if req_attribute == 'content':
                if req.category == RequirementCategory.HEADING:
                    reqif_attribute = ['ReqIF.ChapterName']
                else:
                    reqif_attribute = ['ReqIF.Text']
            if isinstance(reqif_attribute, str):
                reqif_attribute = [reqif_attribute]
            for attribute in reqif_attribute:
                if spec_types_by_name_dict.get(attribute):
                    if req.__getattribute__(req_attribute):
                        attribute_value = req.__getattribute__(req_attribute)
                        spectype = spec_types_by_name_dict.get(attribute)
                        if 'ATTRIBUTE-DEFINITION-XHTML' in spectype[0]:
                            _add_xhtml_value_to_spec_object(spec_object, attribute_value, spectype[2])
                        elif 'ATTRIBUTE-DEFINITION-ENUMERATION' in spectype[0]:
                            self._add_enum_value_to_spec_object(spec_object, attribute_value, spectype[2])
        self._reqif_dom.find('//def:SPEC-OBJECTS', self._namespace).append(spec_object)

    def _add_enum_value_to_spec_object(self, spec_object, attribute_value: str, type_ref: str):
        """ adds value to spec object element

        :param spec_object: lxml Element containing a reqif spec-object
        :param attribute_value: value of the enum to add
        :param type_ref: reqif ref of the enum type
        """
        enum_ref = self._get_enum_ref_by_value(attribute_value)
        enum_value = etree.fromstring('<ATTRIBUTE-VALUE-ENUMERATION>'
                                      '<DEFINITION>'
                                      '<ATTRIBUTE-DEFINITION-ENUMERATION-REF>{}</ATTRIBUTE-DEFINITION-ENUMERATION-REF>'
                                      '</DEFINITION>'
                                      '<VALUES>'
                                      '<ENUM-VALUE-REF>{}</ENUM-VALUE-REF>'
                                      '</VALUES>'
                                      '</ATTRIBUTE-VALUE-ENUMERATION>'.format(type_ref, enum_ref))
        spec_object.find('./VALUES').append(enum_value)

    def _get_enum_ref_by_value(self, attribute_values):
        """ gets the enum ref of an attribute value

        :param attribute_values: string or list of enum values

        :returns enum_ref: reqif ref of an enum value
        """
        if isinstance(attribute_values, (Enum, str)):
            attribute_values = [attribute_values]
        for attribute_value in attribute_values:
            if self._value_mapping_inverse.get(attribute_value):
                attribute_value = self._value_mapping_inverse[attribute_value]

            enum_ref = self._reqif_dom.find('//def:ENUM-VALUE[@LONG-NAME="{}"]'.format(attribute_value),
                                            self._namespace).attrib['IDENTIFIER']
        return enum_ref

    def _create_spec_hirarchy(self):
        """ creates the spec hirarchy of the reqif representing the parent-child relations of the Requirements
        """
        start_node = self._reqif_dom.find('//def:SPECIFICATIONS/def:SPECIFICATION/def:CHILDREN', self._namespace)
        for req in self._reqTree.get_tree():
            self._create_hirarchy_node(req, start_node)

    def _create_hirarchy_node(self, req: ReqifRequirement, start_node):
        """ creats hirarchy nodes with recursive calls

        :param req: Requirement to create hirarchy for
        :param start_node: etree element to start with
        """
        date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
        reqif_id = create_reqif_id()
        hirarchy = etree.fromstring('<SPEC-HIERARCHY IS-TABLE-INTERNAL="false" LAST-CHANGE="{}" IDENTIFIER="{}">'
                                    '<OBJECT>'
                                    '<SPEC-OBJECT-REF>{}</SPEC-OBJECT-REF>'
                                    '</OBJECT>'
                                    '<CHILDREN></CHILDREN>'
                                    '</SPEC-HIERARCHY>'.format(date, reqif_id, req.reqif_id))
        start_node.append(hirarchy)
        new_start_node = hirarchy.find('./CHILDREN', self._namespace)
        for child in req.children:
            self._create_hirarchy_node(child, new_start_node)

    def _get_spec_object(self, req_id):
        """ finds the specobject for a specific id

        :param req_id: Requirement id to look for

        :returns spec_object: lxml elemnt of the specobject
        """
        spec_object = self._reqif_dom.find(
            "//def:SPEC-OBJECTS/def:SPEC-OBJECT[@LONG-NAME='{}']".format(req_id), self._namespace)
        if not spec_object:
            xpath_results = self._reqif_dom.xpath(
                '//def:SPEC-OBJECTS/def:SPEC-OBJECT/def:VALUES/*/*/*/*[text()="{}"]'.format(req_id),
                namespaces=self._namespace)
            if xpath_results:
                spec_object = xpath_results[0].getparent().getparent().getparent().getparent().getparent()
            else:
                raise UserError('The Specobject with the ReqID "{}" could not be found!'.format(req_id))

        return spec_object
