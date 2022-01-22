""" Requirement class and enums """

import re
from collections import namedtuple
from enum import Enum
from typing import Union

from lxml import etree

from testutils.class_testing import TestLevel

from requirements.exceptions import UserError
from requirements.summary_helpers import get_summary_from_description
from requirements.xhtml_config import BREAK_TAGS


class ComponentType(Enum):
    """enum contains values for the different component types"""
    UNIT = "unit"
    COMPONENT = "component"


class InternalStatus(Enum):
    """enum contains values for the attribute InternalStatus"""

    CREATED = "created"
    MOVED = "moved"
    UPDATED = "updated"
    DELETED = "deleted"
    CHILDREN_UPDATED = "children_updated"


class RequirementCategory(Enum):
    """enum contains values for the attribute RequirementCategory"""

    FUNCTIONAL = "Functional Requirement"
    NON_FUNCTIONAL = "NonFunctional Requirement"
    HEADING = "Heading"
    INFORMATION = "Information"
    INTERFACE = "Interface"
    DESIGN_DECISION = "Design Decision"
    CUSTOM_TYPE = "Custom Type"


class RequirementStatus(Enum):
    """enum contains values for the attribute RequirementStatus"""

    IN_WORK = "In Work"
    IN_REVIEW = "In Review"
    NEW = "New"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    UNCLEAR_EXTERNAL = "Unclear External"
    UNCLEAR_INTERNAL = "Unclear Internal"


class RequirementStatusCustomer(Enum):
    """enum contains values for the attribute RequirementStatusCustomer"""

    IN_WORK = "In Work"
    IN_REVIEW = "In Review"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


class ASIL(Enum):
    """enum contains values for the attribute ASIL"""

    QM = "QM"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    QMA = "QM(A)"
    AA = "A(A)"
    QMB = "QM(B)"
    AB = "A(B)"
    BB = "B(B)"
    QMC = "QM(C)"
    AC = "A(C)"
    BC = "B(C)"
    CC = "C(C)"
    QMD = "QM(D)"
    AD = "A(D)"
    BD = "B(D)"
    CD = "C(D)"
    DD = "D(D)"


AttributeConfig = namedtuple("AttributeConfig", ["name", "type", "is_enum"])
MAX_LENGTH_SUMMARY = 50
MAX_LENGTH_SATISFIES = 250


def xhtml_to_raw(
        attribute_value: Union[str, etree._Element]) -> str:  # pylint: disable=protected-access
    """this function returns the raw string of a xhtml string

    :param attribute_value: attribute value to be checked and converted
    :return: converted string or None, if the given attribute value is not of type etree._Element
    """
    pattern = b'<[^>]*>'

    if isinstance(attribute_value, etree._Element):  # pylint: disable=protected-access
        attribute_value = etree.tostring(attribute_value, encoding='utf-8', method='xml')

    if attribute_value is not None:
        if not isinstance(attribute_value, bytes):
            for break_tag in BREAK_TAGS:
                attribute_value = attribute_value.replace(break_tag, '\n')
            attribute_value = str.encode(attribute_value)

        attribute_value = re.sub(pattern, b' ', attribute_value).decode('utf-8').strip()

    return attribute_value


# pylint: disable=too-many-instance-attributes
class Requirement:
    """ Contains all common attributes of requirements independent of any tools. """

    def __init__(self, **kwargs):

        self._children = []
        self.parent = None
        self.req_id = None
        self.category = None
        self.status = None
        self.content = None
        self.summary = None
        self.asil = None
        self._links = set()
        self.satisfies = None
        self._components = set()
        self._units = set()
        self._test_levels = set()
        self.status_customer = None
        self._internal_status = set()
        self._updated_fields = set()
        self.customer_comments = None
        self.review_comments = None
        self.internal_comments = None
        self.release = None
        self._variants = set()
        self.attachment_hashes = {}
        self._optional_flags = set()

        self._set_attributes(**kwargs)

    def _set_attributes(self, **kwargs):
        """sets attributes of __init__

        :param kwargs: all inserted Attributes from __init__
        """

        invalid_arguments = []
        # iteration over all given attributes and their values
        for key, value in kwargs.items():
            try:
                # try to find attribute in Attribute config
                config = _ATTRIBUTE_CONFIG[key]
            except KeyError:
                # If the attribute could not be found in the Attribute collect it
                # append it to a list of invalid arguments
                invalid_arguments.append(key)
            else:
                if config.type == set:
                    # if the attributes type is list extend the
                    # instance attribute with the given value
                    getattr(self, key).clear()
                    getattr(self, key).update(value)
                else:
                    setattr(self, key, value)
        # throw a user error with all collected invalid arguments if any
        if invalid_arguments:
            raise UserError("Tried to initialize requirement object with "
                            "invalid arguments: {}".format(invalid_arguments))

    @property
    def children(self):
        return self._children

    @property
    def links(self):
        return self._links

    @property
    def components(self):
        return self._components

    @property
    def units(self):
        return self._units

    @property
    def test_levels(self):
        return self._test_levels

    @property
    def internal_status(self):
        return self._internal_status

    @property
    def updated_fields(self):
        return self._updated_fields

    @property
    def variants(self):
        return self._variants

    @property
    def optional_flags(self):
        return self._optional_flags

    @property
    def raw_content(self):
        return xhtml_to_raw(self.content)

    @property
    def raw_customer_comments(self):
        return xhtml_to_raw(self.customer_comments)

    @property
    def raw_review_comments(self):
        return xhtml_to_raw(self.review_comments)

    @property
    def raw_internal_comments(self):
        return xhtml_to_raw(self.internal_comments)

    @property
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, value):
        if value:
            self._summary = get_summary_from_description(value, MAX_LENGTH_SUMMARY)
        else:
            self._summary = value

    @property
    def satisfies(self):
        return self._satisfies

    @satisfies.setter
    def satisfies(self, value):
        if value:
            self._satisfies = get_summary_from_description(value, MAX_LENGTH_SATISFIES)
        else:
            self._satisfies = value

    def __eq__(self, other):
        if isinstance(other, Requirement):
            return self.req_id == other.req_id
        else:
            return False

    def __gt__(self, other):
        # Natural Sorting for Req IDs
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]

        # See https://docs.python.org/3.0/whatsnew/3.0.html#ordering-comparisons
        return alphanum_key(self.req_id) > alphanum_key(other.req_id)

    def __hash__(self):  # pragma: no cover
        return hash(self.req_id)

    def __str__(self):  # pragma: no cover
        _content = self.content if self.content else ""
        return "ID: {id} [{req_id}]({req_type}): {content}".format(
            id=id(self),
            req_id=self.req_id,
            req_type=self.category.value if self.category else "NoCategory",
            content=_content[:50] if _content and len(_content) > 50 else _content
        )


class RequirementAttributes(Enum):
    """enum contains values for the attribute RequirementAttributes"""

    REQ_ID = AttributeConfig("req_id", str, False)
    CATEGORY = AttributeConfig("category", RequirementCategory, True)
    STATUS = AttributeConfig("status", RequirementStatus, True)
    CONTENT = AttributeConfig("content", etree.Element, False)
    SUMMARY = AttributeConfig("summary", str, False)
    ASIL = AttributeConfig("asil", ASIL, True)
    LINKS = AttributeConfig("_links", set, False)
    SATISFIES = AttributeConfig("satisfies", str, False)
    COMPONENTS = AttributeConfig("_components", set, False)
    UNITS = AttributeConfig("_units", set, False)
    TEST_LEVELS = AttributeConfig("_test_levels", TestLevel, True)
    STATUS_CUSTOMER = AttributeConfig("status_customer", RequirementStatusCustomer, True)
    CUSTOMER_COMMENTS = AttributeConfig("customer_comments", etree.Element, False)
    REVIEW_COMMENTS = AttributeConfig("review_comments", etree.Element, False)
    INTERNAL_COMMENTS = AttributeConfig("internal_comments", etree.Element, False)
    RELEASE = AttributeConfig("release", str, False)
    VARIANTS = AttributeConfig("_variants", set, False)
    OPTIONAL_FLAGS = AttributeConfig("_optional_flags", set, False)
    ATTACHMENT_HASHES = AttributeConfig("attachment_hashes", dict, False)


# The attribute config holds information about the attribute names and their types
#   so they can be easily set in the constructor
_ATTRIBUTE_CONFIG = {
    x.value.name: x.value for x in RequirementAttributes
}


def reqs_are_equal(req1: Requirement, req2: Requirement):  # pragma: no cover
    for attr in RequirementAttributes:
        if getattr(req1, attr.value.name) != getattr(req2, attr.value.name):
            return False

    if req1.updated_fields != req2.updated_fields:
        return False

    if req1.internal_status != req2.internal_status:
        return False

    if req1.children != req2.children:
        return False

    if req1.parent != req2.parent:
        return False

    return True
