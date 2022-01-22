import asyncio
import logging
import re
from typing import List, Union

from em_jira.exceptions import InvalidArgumentsException
from em_jira.jira import Jira, JiraCFMapping as jconst
from em_utils.exceptions import UserErrorList
from em_utils.progress import progress
from jira import JIRAError, Issue

from requirements.exceptions import UserError
from requirements.helpers import parse_enum_entry
from requirements.summary_helpers import get_summary_from_description
from requirements.jira import jira_helper
from requirements.jira.jira_fields import get_value_from_field
from requirements.jira.jira_helper import parse_req_id, parse_status, parse_links, parse_asil, \
    parse_test_levels, parse_components_and_units, get_child_parent_dict_from_complete_tree, \
    get_or_create_folder, add_update_values_to_fields_dict, parse_customer_status, FIELDS
from requirements.jira.jira_requirement import JiraRequirement
from requirements.req_tree import ReqTree
from requirements.requirement import RequirementCategory, InternalStatus, RequirementAttributes, \
    RequirementStatus, Requirement, MAX_LENGTH_SUMMARY
from requirements.xhtml_config import DEFAULT_BOLD, DEFAULT_LIST, DEFAULT_LIST_TYPE, DEFAULT_SUB, \
    DEFAULT_SUP, \
    DEFAULT_ITALIC, DEFAULT_IMAGE, DEFAULT_STRIKE_TROUGH, DEFAULT_TABLE_HEAD, DEFAULT_TABLE_CELL, \
    DEFAULT_TABLE_ROW, \
    DEFAULT_BREAK

from em_jira.jira_custom_field_mapping import JiraCFMapping

_reporter = progress.get_reporter(__name__)
_logger = logging.getLogger(__name__)

BOLD = r'\*.*\*'
LIST = r'\* .*'
SUP = r'\^.*\^'
SUB = r'\~.*\~'
ITALIC = r' \_.*?\_ '
STRIKE_THROUGH = r' \-.*?\- '
IMAGE = '!\w+\.\w+!'
TABLE = r'\|\|.*\|'


def get_attachment_hashes_from_description(description: str):
    """ Finds md5-hashes with graphics ending in a string

    :param description: description string in a requirement
    """
    attachment_hashes = {}
    if description:
        graphics_in_description = re.findall(r'<xhtml:img>.*</xhtml:img>', description)
        for graphic in graphics_in_description:
            graphics_name = graphic.replace('<xhtml:img>', '')
            graphics_name = graphics_name.replace('</xhtml:img>', '')
            attachment_hashes[graphics_name] = graphics_name
    return attachment_hashes


class JiraTranceiver:  # pylint: disable=too-many-instance-attributes
    """ This Tranceiver handles the import and export from requirements from/to Jira"""

    def __init__(self, jira_instance: Jira, project: str, req_path: str, components: list,
                 labels: list = None, link_map: dict = None, use_implements: bool = False,
                 move_deleted: bool = True, updated_attributes: list = None,
                 deleted_folder: str = None, unit_template: str = None, config_filter: dict = None,
                 read_reqs_from_folder: bool = False):
        self.req_path = req_path
        self.components = components
        self.labels = labels
        self.link_map = {} if not link_map else link_map
        self._use_implements = use_implements
        self._move_deleted = move_deleted
        self._updated_attributes = updated_attributes
        self._unit_template = unit_template

        self.folder_id = None
        self.req_tree = None

        self.jira_instance = jira_instance
        self.project = project

        self.existing_jira_components = [component.name for component
                                         in self.jira_instance.project_components(project)]
        self.r4j_child_parent_dict = get_child_parent_dict_from_complete_tree(jira_instance,
                                                                              project)
        if not deleted_folder:
            deleted_folder = "Deleted Requirements"

        self.deleted_folder_id = get_or_create_folder(self.jira_instance,
                                                      self.project,
                                                      deleted_folder)["id"]

        self.reqs_processed = 0
        self.config_filter = config_filter
        self.read_reqs_from_folder = read_reqs_from_folder

    def read(self):
        """ Retrieves a ReqTree from a jira project

        :returns: A ReqTree, holding a list of requirements and the R4J Tree structure of the
                  given req_path
        """

        # Determine the folder ID from the req_path, this is later needed for linking reqs
        # at the root level
        self._determine_folder_id(self.req_path)

        # Get all jira requirement issues for the given components and levels
        _reporter.status("Fetch requirement issues from Jira")
        if self.config_filter:
            all_req_issues = self.jira_instance.get_issues_by_config_filter(self.project,
                                                                            self.config_filter['type'],
                                                                            self.config_filter['value'],
                                                                            json_result=True)
        # the elif exists soley for compatibility reasons.
        # with the json-configuration for transfering reqs it should never be reached
        elif all([_cmp in self.existing_jira_components for _cmp in self.components]):
            all_req_issues = jira_helper.get_req_issues_from_project(self.jira_instance,
                                                                     self.project,
                                                                     components=self.components,
                                                                     labels=self.labels)
        else:
            all_req_issues = []

        if self.read_reqs_from_folder:
            self._add_reqs_from_folder(all_req_issues)

        # Create a list of internal JiraRequirement objects from the jira issues
        _reporter.start('Convert Jira Issues to Requirement Objects', len(all_req_issues))
        all_reqs = []
        for _idx, _req_issue in enumerate(all_req_issues):
            all_reqs.append(self.raw_to_req(_req_issue, self.link_map))
            _reporter.progress(_idx + 1)
        _reporter.finish()

        # Get tree structure from jira with the given req path
        r4j_tree = self.jira_instance.get_folder_by_id(self.project, self.folder_id).get("issues")

        # Build child-parent tree
        req_path_tree = self._build_req_path_tree({req.jira_id: req for req in all_reqs}, r4j_tree)

        # Create an instance of ReqTree that holds all requirements and the requirement tree
        self.req_tree = ReqTree(req_path_tree, all_reqs)

        return self.req_tree

    def write(self):
        """ Writes/Updates Jira requirements in a R4J Jira project by the given ReqTree. """

        self._determine_folder_id(self.req_path)
        self._create_new_reqs(self.req_tree.get_all_requirements_list())
        self._update_reqs(self.req_tree.get_all_requirements_list())
        self._update_attachments(self.req_tree.get_all_requirements_list())

        self._transition_reqs(self.req_tree.get_all_requirements_list())
        self._link_reqs(self.req_tree.get_all_requirements_list())

        _reporter.start("Moving reqs in R4J Tree", None)
        self._recursive_move(self.req_tree.get_tree())
        if self._move_deleted:
            self._recursive_move([_req for _req in self.req_tree.get_all_requirements_list() if
                                  InternalStatus.DELETED in _req.internal_status and self.r4j_child_parent_dict.get(
                                      _req.jira_id) != self.deleted_folder_id])
        _reporter.finish()
        self.reqs_processed = 0

        # Clear internal status after update is finished
        for jira_req in self.req_tree.get_all_requirements_list():
            jira_req.internal_status.clear()

        # Refresh child parent dict so that next time this tranceiver is used
        # for import or export, it got the right parent/child relations
        self.r4j_child_parent_dict = get_child_parent_dict_from_complete_tree(self.jira_instance,
                                                                              self.project)

    def _determine_folder_id(self, req_path):
        """ Determines the id of the folder by looking up the req_path.
        If it does not exist, it will be created.

        :param req_path: Path to get or create folder from/in
        """
        if not self.folder_id:
            # If no folder id is set by a former read, get or
            # create the folder and set the folder id
            folder = get_or_create_folder(self.jira_instance, self.project, req_path)
            self.folder_id = folder["id"]

    def _link_reqs(self, all_reqs: List[JiraRequirement]):
        """ Asynchronously updated the links from the give list of requirements

        :param all_reqs: List of requirements to update links for
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Only if the RequirementAttribute LINKS has changed we need to update the links
        tasks = [
            self._link_req(_req) for _req in all_reqs if
            RequirementAttributes.LINKS in _req.updated_fields
            or RequirementAttributes.SATISFIES in _req.updated_fields
            or (InternalStatus.CREATED in _req.internal_status and (
                    _req.links or _req.satisfies))]

        if tasks:
            _reporter.start("Link requirements", len(tasks))
            loop.run_until_complete(asyncio.wait(tasks))
            self.reqs_processed = 0
            _reporter.finish()

    async def _link_req(self, jira_req: JiraRequirement):
        """ Updates the links for a given JiraRequirement

        :param jira_req: JiraRequirement to update the links for
        """
        jira_req_issue = self.jira_instance.issue(jira_req.jira_id, fields=[jconst.ISSUELINKS])

        # Get a list of existing links from the jira issue
        _existing_issue_links = self._get_existing_issue_link_mapping_from_req(jira_req_issue)

        link_id_list = []
        if jira_req.satisfies:
            link_id_list.extend([req_id.strip() for req_id in str(jira_req.satisfies).split(",")])
        if jira_req.links:
            link_id_list.extend([link for link in jira_req.links if link])

        for _link_id in link_id_list:
            _jira_link_id = self._get_issue_key_from_link_map(_link_id)

            if not _jira_link_id:
                continue

            # If the link that should be created already exists in the issue links
            # remove it from the existing issue links mapping and continue without linking
            if _jira_link_id in _existing_issue_links:
                _existing_issue_links.pop(_jira_link_id, None)
                continue

            try:
                link_res = self.jira_instance.create_issue_link(
                    "satisfies" if not self._use_implements else 'implements',
                    jira_req.jira_id, _jira_link_id)
                if link_res.status_code != 201:  # pragma: no cover
                    _logger.warning(
                        "The requirement %s with jira id %s could not be linked with %s",
                        jira_req.req_id, jira_req.jira_id, _jira_link_id)
            except JIRAError:  # pragma: no cover
                _logger.warning("The requirement %s with jira id %s could not be linked with %s "
                                "due to a jira error",
                                jira_req.req_id, jira_req.jira_id, _jira_link_id)

        # Only links to requirements are still in the dict which should not be linked anymore
        # so unlink those
        if _existing_issue_links:
            _reporter.status("Deleting obsolete links")
            for _, link_id in _existing_issue_links.items():
                self.jira_instance.delete_issue_link(link_id)
        self.reqs_processed += 1
        _reporter.progress(self.reqs_processed)

    def _get_issue_key_from_link_map(self, _link_id: str) -> str:
        """ Gets the jira issue key for a given req_id from the link map.

        :param _link_id: Usually a requirement id. If a jira issue key is
                            given here, just return this
        :returns: Issue key of the issue that is represented by the link
        """
        if self.link_map.get(_link_id):
            # If _link is an external req_id linking to a jira issue id, use the issue id
            _link_id = self.link_map[_link_id]
        elif _link_id in self.link_map.values():
            # If _link is already an jira issue id, do nothing
            pass
        else:
            # Linked issue could not be found
            return ''
        return _link_id

    @staticmethod
    def _get_existing_issue_link_mapping_from_req(jira_req_issue: Issue) -> dict:
        """ Gets a dictionary containing all existing links to requirements with the link ids.

        :param jira_req_issue: Requirement Issue to get links from
        :returns: Dictionary linked_issue_key <-> link
        """
        req_type_values = {req_type.value for req_type in RequirementCategory}
        _existing_issue_links = jira_req_issue.raw["fields"]["issuelinks"]
        _existing_issue_links = {
            _link['outwardIssue']['key']: _link['id'] for _link in _existing_issue_links if
            _link.get('outwardIssue') and _link['outwardIssue']['fields']['issuetype'][
                'name'] in req_type_values and
            _link["type"]["name"] == "Requirement"
        }
        return _existing_issue_links

    def _transition_reqs(self, all_reqs: List[JiraRequirement]):
        """ Asynchronously transitions the Requirements from the given list.

        :param all_reqs: List of Requirements where to look up for transitions to make
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        error_list = UserErrorList()
        # Only create a task for Requirements that have the RequirementAttribute STATUS in the
        # set of updated attributes and have a status set
        tasks = [self._transition_req(_req) for _req in all_reqs if
                 (RequirementAttributes.STATUS in _req.updated_fields
                  or InternalStatus.CREATED in _req.internal_status)
                 and _req.status is not None]

        if tasks:
            _reporter.start("Transition requirements", len(tasks))
            result = loop.run_until_complete(asyncio.wait(tasks))
            self.reqs_processed = 0
            for res in result:
                for task in res:
                    if task._exception:
                        error_list.add_message(task._exception.args[0])
            if error_list.get_messages():
                raise error_list
            _reporter.finish()

    async def _transition_req(self, jira_req: JiraRequirement):
        """ Transitions a single requirement to another status in jira

        :param jira_req: JiraRequirement that should be transitioned to another status
        """
        try:
            jira_req_issue = self.jira_instance.issue(jira_req.jira_id)

            # the status is ACCEPTED or REJECTED, the transition needs to be to status Done
            if jira_req.status == RequirementStatus.ACCEPTED:
                self.jira_instance.transition_issue_status(jira_req_issue, "Done",
                                                           transition_name="Accept Issue")
            elif jira_req.status == RequirementStatus.REJECTED:
                self.jira_instance.transition_issue_status(jira_req_issue, "Done",
                                                           transition_name="Reject Issue")
            # the status is another one, so just use the value from the RequirementStatus Enum
            else:
                self.jira_instance.transition_issue_status(jira_req_issue, jira_req.status.value)
            self.reqs_processed += 1
            _reporter.progress(self.reqs_processed)
        except JIRAError as ex:
            raise UserError(
                'JIRAError during asyncronus transitioning of {}: {}'.format(jira_req.req_id,
                                                                             ex.text))

    def _create_new_reqs(self, all_reqs: List[Union[JiraRequirement, Requirement]]):
        """ Aynchronously creates new jira issues from the given list of requirements-

        :param all_reqs: List of Requirements where to look for new ones in
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        error_list = UserErrorList()
        # Only create tasks for requirements that are marked as CREATED
        tasks = [self._create_new_req(_req) for _req in all_reqs if
                 InternalStatus.CREATED in _req.internal_status]

        if tasks:
            _reporter.start("Creating new reqs", len(tasks))
            result = loop.run_until_complete(asyncio.wait(tasks))
            self.reqs_processed = 0
            for res in result:
                for task in res:
                    if task._exception:
                        error_list.add_message(task._exception.args[0])
            if error_list.get_messages():
                raise error_list
            _reporter.finish()

    async def _create_new_req(self, req: Union[JiraRequirement, Requirement]):
        """ Creates a new jira issue from a given Requirement

        :param req: Requirement that should be created in jira
        """

        # Convert the Requirement object to a dict as needed by the Jira API
        try:
            raw_update_req = self._req_to_raw(req)
            jira_fields_dict = raw_update_req["fields"]
            jira_update_dict = raw_update_req["update"]
            jira_fields_dict[jconst.PROJECT] = self.project

            # Append tranceiver specific components to the list of components for the issue
            if self.components:
                existing_components = jira_fields_dict.get(jconst.COMPONENTS, [])
                existing_components.extend([
                    {"name": component}
                    for component in self.components
                ])
                jira_fields_dict[jconst.COMPONENTS] = existing_components

            # Create components in jira that don't exist yet
            for _cmp in jira_fields_dict.get(jconst.COMPONENTS, []):
                if _cmp["name"] not in self.existing_jira_components:
                    self.jira_instance.create_component(_cmp["name"], self.project)
                    self.existing_jira_components.append(_cmp["name"])

            # Set tranceiver specific labels for the issue
            if self.labels:
                jira_fields_dict[jconst.LABELS] = self.labels

            # Add update fields (format with set) to fields dict
            # because the create expects another format then update
            add_update_values_to_fields_dict(jira_update_dict, jira_fields_dict)
            new_jira_req = self.jira_instance.create_issue(fields=jira_fields_dict, prefetch=False)
            req.jira_id = new_jira_req.key
            # fill link map with all requirements, since each req can be linked to each req
            self.link_map[req.req_id] = req.jira_id
            self.reqs_processed += 1
            _reporter.progress(self.reqs_processed)
        except JIRAError as ex:
            raise UserError(
                'JIRAError during asyncronus creation of {}: {}'.format(req.req_id, ex.text))

    def _recursive_move(self, reqs: List[JiraRequirement]):
        """ Traverses the given list of requirements and is recursively called for the children
        of all requirements.

        :param reqs: List of requirements where to look for moved ones in
        """
        for jira_req in reqs:
            # The reqs position has changed, move the req in jira
            if InternalStatus.MOVED in jira_req.internal_status:
                self._move_req(jira_req)
            # If the reqs internal status is CREATED the req must be created in the tree
            # If the reqs internal status is DELETED it must be moved to the "Deleted Requirements"
            # folder
            elif {InternalStatus.CREATED, InternalStatus.DELETED} & jira_req.internal_status:
                self._move_req(jira_req)

            # Handle child reqs:
            if jira_req.children:
                self._recursive_move(jira_req.children)
            self.reqs_processed += 1
            _reporter.progress(self.reqs_processed)

    def _move_req(self, jira_req: JiraRequirement):
        """ Moves a single requirement in the R4J tree

        :param jira_req: Requirement that should be moved
        """

        # Remove jira_req from parent if it has one, as this function is only called if it
        # indeed moved to a new location
        old_parent_jira_id = self.r4j_child_parent_dict.get(jira_req.jira_id)
        if old_parent_jira_id:
            try:
                # old parent is an integer, it is the id of a folder, so remove it from the folder
                if isinstance(old_parent_jira_id, int):
                    self.jira_instance.remove_existing_issue_from_folder(self.project,
                                                                         old_parent_jira_id,
                                                                         jira_req.jira_id)
                # old parent is an issue, so remove it from the issue
                else:
                    self.jira_instance.remove_child_rel_from_parent(self.project,
                                                                    old_parent_jira_id,
                                                                    jira_req.jira_id)
            except InvalidArgumentsException as exc:  # pragma: no cover
                _logger.warning(
                    "Could not remove Issue %s from parent %s due to the following exception: %s",
                    jira_req.jira_id, old_parent_jira_id, str(exc))

        # If the req.parent is a Requriement, it must be an issue, so add it as child to this issue
        if isinstance(jira_req.parent, Requirement):
            self.jira_instance.add_child_issue_to_parent_issue(self.project,
                                                               jira_req.parent.jira_id,
                                                               jira_req.jira_id)
        # If the req has no parent and is not marked as DELETED it must have been moved
        # to the root folder, so add it as child to the root folder
        elif InternalStatus.DELETED not in jira_req.internal_status:
            self.jira_instance.add_existing_issue_to_folder(self.project, self.folder_id,
                                                            jira_req.jira_id)
        else:
            self.jira_instance.add_existing_issue_to_folder(self.project, self.deleted_folder_id,
                                                            jira_req.jira_id)

    def _update_reqs(self, all_reqs: List[JiraRequirement]):
        """ Asynchronously updates jira requirement issues by the given list of JiraRequirements

        :param all_reqs: List of Requirements, where to look for updated ones
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        error_list = UserErrorList()
        # Only create tasks for requirements that have the Internal Status UPDATED
        tasks = [self._update_req(_req) for _req in all_reqs if
                 InternalStatus.UPDATED in _req.internal_status and _req.updated_fields - {
                     RequirementAttributes.LINKS, RequirementAttributes.STATUS}]

        if tasks:
            _reporter.start("Updating existing reqs", len(tasks))
            result = loop.run_until_complete(asyncio.wait(tasks))
            self.reqs_processed = 0
            for res in result:
                for task in res:
                    if task._exception:
                        error_list.add_message(task._exception.args[0])
            if error_list.get_messages():
                raise error_list
            _reporter.finish()

    def _check_component_values(self, attributes: list, jira_req: JiraRequirement):  # pylint: disable=too-many-branches
        """ checks the requirement attributes which get written in the
                jira field components. Goal is to only change the values that are
                supposed to update (do not update variants if only units are
                supposed to get updated) and not leak handwritten components
            :param attributes: which attributes are supposed to get updated
            :param jira_req: knows the components which were read in at the
                                attribute jira_components
        """
        # parameter to remember if the components field in jira has to get updated
        # each attribute (units, optional_flags, variants, components)
        # can cause to update the components field in jira
        update_components = False

        # if the attributes are supposed to get updated:
        # delete all components which start with the corresponding prefix
        # ('Unit_', 'OPT_', 'VAR_', 'CMP') from the components which were
        # read in and then add the new ones
        if "_units" in attributes or "units" in attributes:
            update_components = True
            for jira_cmp in list(jira_req.jira_components):
                if jira_cmp.startswith("Unit_"):
                    jira_req.jira_components.remove(jira_cmp)
            for _unit in jira_req.units:
                jira_req.jira_components.add("Unit_{}".format(_unit))

        if "_optional_flags" in attributes or "optional_flags" in attributes:
            update_components = True
            for jira_cmp in list(jira_req.jira_components):
                if jira_cmp.startswith("OPT_"):
                    jira_req.jira_components.remove(jira_cmp)
            for _opt in jira_req.optional_flags:
                jira_req.jira_components.add("OPT_{}".format(_opt))

        if "_variants" in attributes or "variants" in attributes:
            update_components = True
            for jira_cmp in list(jira_req.jira_components):
                if jira_cmp.startswith("VAR_"):
                    jira_req.jira_components.remove(jira_cmp)
            for _var in jira_req.variants:
                jira_req.jira_components.add("VAR_{}".format(_var))

        if "_components" in attributes or "components" in attributes:
            # set bool false, components is already in attributes
            update_components = False
            for jira_cmp in list(jira_req.jira_components):
                if jira_cmp.startswith("CMP_"):
                    jira_req.jira_components.remove(jira_cmp)
            for cmp in jira_req.components:
                jira_req.jira_components.add("CMP_{}".format(cmp))

        if update_components:
            attributes.append("components")

    def _check_attributes_to_update(self, jira_fields_dict: dict,
                                    jira_req: JiraRequirement) -> dict:
        """ only the attributes that where changed should be updated
            these attributes are in the list self._updated_attributes

            :param jira_fields_dict: all fields of one requirement
                                    {jira_attribute: value}

            :return: fields of one requirement that should be updated
                                    {jira_attribute: value}
        """
        checked_jira_fields_dict = dict()
        attributes = list()

        # because this function is called after _req_to_raw
        # the attribute names have to comply with the jira naming
        # especially the custom fields
        # the attributes that are supposed to update get
        # matched here:
        for attr in self._updated_attributes:
            # string if from fix_value, dict if from updated_attributes
            if isinstance(attr, RequirementAttributes):
                attr = attr.value.name
            if jconst.PLAIN_FIELD_NAME_MAPPING.get(attr):
                attributes.append(jconst.PLAIN_FIELD_NAME_MAPPING.get(attr))
            else:
                attributes.append(attr)

        # some attributes cause the update of other attributes,
        # they have to be added to attributes
        if "content" in attributes:
            if "summary" not in attributes:
                attributes.append("summary")
            attributes.append("description")

        self._check_component_values(attributes, jira_req)

        if "release" in attributes:
            attributes.append("fixVersions")

        if "category" in attributes:
            attributes.append("issuetype")

        # just take the attributes that are supposed to be updated
        # from the jira_fields_dict
        for key, value in jira_fields_dict.items():
            if key in attributes:
                # components have to be formated
                if key == "components":
                    checked_jira_fields_dict[key] = []
                    checked_jira_fields_dict[key].extend(
                        [{"name": cmp} for cmp in jira_req.jira_components])
                else:
                    checked_jira_fields_dict[key] = value

        return checked_jira_fields_dict

    async def _update_req(self, jira_req: JiraRequirement):
        """ Updates a single jira requirement issue by a JiraRequirement

        :param jira_req: JiraRequirement whose representing jira issue should be updated
        """
        try:
            # Get update dict as needed for the jira rest api
            raw_update_req = self._req_to_raw(jira_req)

            if self._updated_attributes:
                jira_fields_dict = self._check_attributes_to_update(raw_update_req["fields"],
                                                                    jira_req)
            else:
                jira_fields_dict = raw_update_req["fields"]
            jira_update_dict = raw_update_req["update"]

            # Append tranceiver specific components to the list of components for the issue
            if self.components:
                existing_components = jira_fields_dict.get(jconst.COMPONENTS, [])
                existing_components.extend([
                    {"name": component}
                    for component in self.components
                ])
                jira_fields_dict[jconst.COMPONENTS] = existing_components

            # Create components in jira that don't exist yet
            for _cmp in jira_fields_dict[jconst.COMPONENTS]:
                if _cmp["name"] not in self.existing_jira_components:
                    self.jira_instance.create_component(_cmp["name"], self.project)
                    self.existing_jira_components.append(_cmp["name"])

            # Set tranceiver specific labels for the issue
            if self.labels:
                jira_fields_dict[jconst.LABELS] = self.labels

            # Get the existing jira issue (only field summary as to performance reasons,
            # we can't get issues without any fields)
            jira_req_issue = self.jira_instance.issue(jira_req.jira_id, fields=[jconst.SUMMARY])
            jira_req_issue.update(fields=jira_fields_dict, update=jira_update_dict)
            self.reqs_processed += 1
            _reporter.progress(self.reqs_processed)
        except JIRAError as ex:
            raise UserError(
                'JIRAError during asyncronus creation of {}: {}'.format(jira_req.req_id, ex.text))

    def _req_to_raw(self, jira_req: JiraRequirement) -> dict:  # pylint: disable=too-many-branches
        """ Converts a JiraRequirement to a dict as needed by the jira rest api

        :param jira_req: JiraRequirement that should be converted to a raw dict
        :returns: Dictionary with the requirements attributes as needed by the jira api
        """
        fields = {}
        update = {}
        self._convert_xhtml_to_jira_markup(jira_req)
        # No need for checking if the req has those attributes, as those are mandatory in Jira
        fields[jconst.ISSUETYPE] = {"name": jira_req.category.value}

        if jira_req.summary is not None and jira_req.summary != "":
            fields[jconst.SUMMARY] = get_summary_from_description(jira_req.summary, MAX_LENGTH_SUMMARY)
        elif jira_req.content is not None and jira_req.content != "":
            fields[jconst.SUMMARY] = get_summary_from_description(jira_req.content, MAX_LENGTH_SUMMARY)
        else:
            fields[jconst.SUMMARY] = "No Summary"

        if jira_req.content is not None:
            fields[jconst.DESCRIPTION] = str(jira_req.content)
        if jira_req.status_customer is not None:
            fields[jconst.STATUS_CUSTOMER] = {"value": str(jira_req.status_customer.value)}

        fields[jconst.REVIEW_COMMENTS] = str(
            jira_req.raw_review_comments) if jira_req.review_comments is not None else None
        fields[jconst.CUSTOMER_COMMENTS] = str(
            jira_req.raw_customer_comments) if jira_req.customer_comments is not None else None
        fields[jconst.INTERNAL_COMMENTS] = str(
            jira_req.raw_internal_comments) if jira_req.internal_comments is not None else None
        fields[jconst.SATISFIES] = str(
            jira_req.satisfies) if jira_req.satisfies is not None else None

        if jira_req.req_id is not None:
            fields[jconst.REQUIREMENT_ID] = str(jira_req.req_id)
        if jira_req.asil is not None:
            fields[jconst.ASIL] = {"value": jira_req.asil.value}
        if jira_req.test_levels:
            update[jconst.TEST_LEVELS] = [{"set": [
                {"value": _test_level.value}
                for _test_level in jira_req.test_levels
            ]}]
        if jira_req.units:
            if self._unit_template:
                fields[jconst.COMPONENTS] = [{"name": "Unit_{}".format(self._unit_template).format(unit)} for unit in
                                             jira_req.units]
            else:
                fields[jconst.COMPONENTS] = [{"name": "Unit_{}".format(unit)} for unit in
                                             jira_req.units]
        if jira_req.components:
            if not fields.get(jconst.COMPONENTS):
                fields[jconst.COMPONENTS] = []
            fields[jconst.COMPONENTS].extend(
                [{"name": "CMP_{}".format(cmp)} for cmp in jira_req.components])

        if jira_req.optional_flags:
            if not fields.get(jconst.COMPONENTS):
                fields[jconst.COMPONENTS] = []
            fields[jconst.COMPONENTS].extend(
                [{"name": "OPT_{}".format(flag)} for flag in jira_req.optional_flags])

        if jira_req.variants:
            if not fields.get(jconst.COMPONENTS):
                fields[jconst.COMPONENTS] = []
            fields[jconst.COMPONENTS].extend(
                [{"name": "VAR_{}".format(variant)} for variant in jira_req.variants])

        if jira_req.release:
            fields[jconst.FIX_VERSIONS] = [{"name": release.strip()} for release in jira_req.release.split(',')]

        return {"fields": fields, "update": update}

    def _convert_xhtml_to_jira_markup(self, jira_req: JiraRequirement):
        if jira_req.summary:
            jira_req.summary = self._prepare_content(jira_req.summary, jira_req)
        if jira_req.content:
            jira_req.content = self._prepare_content(jira_req.content, jira_req)
        if jira_req.customer_comments:
            jira_req.customer_comments = self._prepare_content(jira_req.customer_comments, jira_req)
        if jira_req.internal_comments:
            jira_req.internal_comments = self._prepare_content(jira_req.internal_comments, jira_req)
        if jira_req.review_comments:
            jira_req.review_comments = self._prepare_content(jira_req.review_comments, jira_req)

    def _prepare_content(self, content, jira_req):
        if DEFAULT_BOLD in content:
            content = self.resolve_bold(content)
        if DEFAULT_LIST in content:
            content = self.resolve_list(content)
        if DEFAULT_SUB in content:
            content = self.resolve_sub(content)
        if DEFAULT_SUP in content:
            content = self.resolve_sup(content)
        if DEFAULT_ITALIC in content:
            content = self.resolve_italic(content)
        if DEFAULT_STRIKE_TROUGH in content:
            content = self.resolve_strikethrough(content)
        if DEFAULT_IMAGE in content:
            content = self.resolve_image(content, jira_req)
        if DEFAULT_TABLE_HEAD in content:
            content = self.resolve_table(content)
        if DEFAULT_BREAK in content:
            content = content.replace(DEFAULT_BREAK, '\n')
        # Remove all remaining xhtml tags
        remaining_xhtml = re.findall(r'(</?(reqif-)?xhtml.*?/?>)', content)
        for remaining_tag in remaining_xhtml:
            content = content.replace(remaining_tag[0], '')

        return content.strip()

    @staticmethod
    def resolve_bold(text: str):
        """ resolves xhtml bold to Jira-Format

        :param text: string to check for xhtml bold

        :returns: string with resolved bold tags
        """
        text = text.replace(DEFAULT_BOLD.replace('<', '</'), '*')
        text = text.replace(DEFAULT_BOLD, '*')
        return text

    @staticmethod
    def resolve_list(text: str):
        """ resolves xhtml bold to Jira-Format

        :param text: string to check for xhtml bold

        :returns: string with resolved bold tags
        """
        text = text.replace(DEFAULT_LIST.replace('<', '</'), '\n')
        text = text.replace(DEFAULT_LIST, '* ')
        text = text.replace(DEFAULT_LIST_TYPE, '')
        return text

    @staticmethod
    def resolve_sup(text: str):
        """ resolves xhtml bold to Jira-Format

        :param text: string to check for xhtml bold

        :returns: string with resolved bold tags
        """
        text = text.replace(DEFAULT_SUP.replace('<', '</'), '^ ')
        text = text.replace(DEFAULT_SUP, ' ^')
        return text

    @staticmethod
    def resolve_sub(text: str):
        """ resolves xhtml bold to Jira-Format

        :param text: string to check for xhtml bold

        :returns: string with resolved bold tags
        """
        text = text.replace(DEFAULT_SUB.replace('<', '</'), '~ ')
        text = text.replace(DEFAULT_SUB, ' ~')
        return text

    @staticmethod
    def resolve_italic(text: str):
        """ resolves xhtml italic to Jira-Format

        :param text: string to check for xhtml italic

        :returns: string with resolved italic tags
        """
        text = text.replace(DEFAULT_ITALIC.replace('<', '</'), '_')
        text = text.replace(DEFAULT_ITALIC, '_')
        return text

    @staticmethod
    def resolve_strikethrough(text: str):
        """ resolves xhtml strikethrough to Jira-Format

        :param text: string to check for xhtml strikethrough

        :returns: string with resolved strikethrough tags
        """
        text = text.replace(DEFAULT_STRIKE_TROUGH, '-')
        text = text.replace(DEFAULT_STRIKE_TROUGH.replace('<', '</'), '-')
        return text

    @staticmethod
    def resolve_image(text: str, req: Requirement):
        """ resolves xhtml image tags

        :param text: string to check for xhtml image
        :param req: requirement object

        :returns: string with resolved image tags
        """
        if DEFAULT_IMAGE in text:
            images = re.findall(r'(?<=<xhtml:img>).*?(?=</xhtml:img>)', text)
            for image in images:
                for att_hash in req.attachment_hashes:
                    if att_hash == image:
                        text = text.replace('<xhtml:img>' + att_hash + '</xhtml:img>',
                                            '!' + att_hash + '!')

        return text

    @staticmethod
    def resolve_table(text: str):
        """ resolves xhtml table to Jira-Format

        :param text: string to check for xhtml table

        :returns: string with resolved table tags
        """
        table_content = ''
        text = text.replace(DEFAULT_TABLE_HEAD, '')
        text = text.replace(DEFAULT_TABLE_HEAD.replace('<', '</'), '')
        table_rows = re.findall('<xhtml:tr>.*?</xhtml:tr>', text, re.MULTILINE | re.DOTALL)
        for row in table_rows:
            if not table_rows.index(row):
                row = row.replace(DEFAULT_TABLE_ROW, '')
                row = row.replace(DEFAULT_TABLE_ROW.replace('<', '</'), '||')
                row = row.replace(DEFAULT_TABLE_CELL, '||')
                row = row.replace(DEFAULT_TABLE_CELL.replace('<', '</'), '')
                row = re.sub(r"\s+", " ", row)
            else:
                row = row.replace(DEFAULT_TABLE_ROW, '')
                row = row.replace(DEFAULT_TABLE_ROW.replace('<', '</'), '|')
                row = row.replace(DEFAULT_TABLE_CELL, '|')
                row = row.replace(DEFAULT_TABLE_CELL.replace('<', '</'), '')
                row = re.sub(r"\s+", " ", row)
            table_content = table_content + row.strip() + '\n'
        return table_content

    def raw_to_req(self, req_issue: dict, link_map: dict) -> JiraRequirement:
        """ Creates an instance of JiraRequirement by parsing the
                fields from a given jira issue dict

        :param req_issue: jira issue dict
        :param link_map: Mapping of all linkable issues (req_id <=> jira_id)
        :returns: a new JiraRequirement with all attributes as given in the jira issue dict
        """
        jira_req = JiraRequirement(req_issue["key"])
        fields = req_issue["fields"]

        jira_req.category = parse_enum_entry(fields.get(jconst.ISSUETYPE)["name"],
                                             RequirementCategory)
        jira_req.content = self._get_jira_str_as_xhtml(get_value_from_field(jconst.DESCRIPTION,
                                                                            fields.get(
                                                                                jconst.DESCRIPTION)))
        jira_req.summary = self._get_jira_str_as_xhtml(
            get_value_from_field(jconst.SUMMARY, fields.get(jconst.SUMMARY)))
        jira_req.attachment_hashes = get_attachment_hashes_from_description(jira_req.content)
        jira_req.review_comments = self._get_jira_str_as_xhtml(
            get_value_from_field(jconst.REVIEW_COMMENTS,
                                 fields.get(jconst.REVIEW_COMMENTS)))
        jira_req.customer_comments = self._get_jira_str_as_xhtml(get_value_from_field(
            jconst.CUSTOMER_COMMENTS,
            fields.get(jconst.CUSTOMER_COMMENTS)))
        jira_req.internal_comments = self._get_jira_str_as_xhtml(get_value_from_field(
            jconst.INTERNAL_COMMENTS,
            fields.get(jconst.INTERNAL_COMMENTS)))
        jira_req.satisfies = get_value_from_field(jconst.SATISFIES,
                                                  fields.get(jconst.SATISFIES))

        parse_req_id(fields, jira_req, req_issue)
        parse_status(fields, jira_req)
        parse_customer_status(fields, jira_req)
        parse_links(fields, jira_req, link_map)
        parse_asil(fields, jira_req)
        parse_test_levels(fields, jira_req)
        parse_components_and_units(fields, jira_req)
        fix_versions = ','.join(get_value_from_field(jconst.FIX_VERSIONS,
                                                     fields.get(jconst.FIX_VERSIONS, [])))
        jira_req.release = fix_versions if fix_versions else None

        return jira_req

    def _get_jira_str_as_xhtml(self,
                               jira_str: str):  # pylint: disable=too-many-locals,too-many-branches
        """ replaces all Jira formating directives with xhtml tags

        :param jira_str: string from Jira Textbox
        :returns: string with xhtml notation
        """
        if isinstance(jira_str, str):
            if '\n' in jira_str:
                jira_str = jira_str.replace('\n', DEFAULT_BREAK)

            jira_str = self._resolve_jira_markup(jira_str, '*', DEFAULT_BOLD)
            jira_str = self._resolve_jira_markup(jira_str, '~', DEFAULT_SUB)
            jira_str = self._resolve_jira_markup(jira_str, '^', DEFAULT_SUP)
            jira_str = self._resolve_jira_markup(jira_str, '_', DEFAULT_ITALIC)
            jira_str = self._resolve_jira_markup(jira_str, '-', DEFAULT_STRIKE_TROUGH)

            for list_string in re.findall(LIST, jira_str):
                xhtml_list = list_string.replace('* ', DEFAULT_LIST, 1)
                xhtml_list = xhtml_list + DEFAULT_LIST.replace('<', '</')
                jira_str = jira_str.replace(list_string,
                                            DEFAULT_LIST_TYPE + xhtml_list + DEFAULT_LIST_TYPE.replace(
                                                '<', '</'))

            for image_string in re.findall(IMAGE, jira_str):
                xhtml_image = image_string.replace('!', DEFAULT_IMAGE, 1)
                xhtml_image = xhtml_image.replace('!', DEFAULT_IMAGE.replace('<', '</'), 1)
                jira_str = jira_str.replace(image_string, xhtml_image)

            for table_content in re.findall(TABLE, jira_str):
                table_rows = jira_str.strip().split(DEFAULT_BREAK)
                xhtml_table = DEFAULT_TABLE_HEAD
                for row in table_rows:
                    xhtml_table = xhtml_table + DEFAULT_TABLE_ROW
                    if table_rows.index(row) == 0:
                        header_cells = row.split('||')[1:-1]
                        for header in header_cells:
                            xhtml_table = xhtml_table + DEFAULT_TABLE_CELL + header + DEFAULT_BREAK + \
                                          DEFAULT_TABLE_CELL.replace('<', '</')
                        xhtml_table = xhtml_table + DEFAULT_TABLE_ROW.replace('<', '</')
                    else:
                        body_cells = row.split('|')[1:-1]
                        for header in body_cells:
                            xhtml_table = xhtml_table + DEFAULT_TABLE_CELL + header + DEFAULT_BREAK + \
                                          DEFAULT_TABLE_CELL.replace('<', '</')
                        xhtml_table = xhtml_table + DEFAULT_TABLE_ROW.replace('<', '</')
                        jira_str = jira_str.replace(row, "")
                xhtml_table = xhtml_table + DEFAULT_TABLE_HEAD.replace('<', '</')
                jira_str = jira_str.replace(table_content, xhtml_table)

        return jira_str

    def _build_req_path_tree(self, all_reqs_dict: dict, r4j_tree: list) -> list:
        """ Creates the tree structure for a ReqTree by recursing over the r4j tree structure and
        building the tree with references to the JiraRequirement objects from the list of all dicts.
        That means in the ReqTree object a JiraRequirement from the tree will always be the same
        object as the one with the same req_id in the list of all JiraRequirements.

        :param all_reqs_dict: Mapping from jira_id <-> JiraRequirement from the list of all reqs
        :param r4j_tree: Tree structure as retrieved from R4J
        :returns: Internal requirement tree structure, refering to the objects from
                  this list of all reqs
        """
        jira_req_tree = []

        for _r4j_req in r4j_tree:
            _jira_req = all_reqs_dict[_r4j_req["key"]]
            # Create child/parent structure for every JiraRequirement at the root level
            child_reqs = _r4j_req.get("childReqs", {}).get("childReq", [])
            for _r4j_child_req in child_reqs:
                self._build_subtree(all_reqs_dict, _r4j_child_req, parent=_jira_req)

            # The JiraRequirements in r4j_tree are at root level here, so just add them to a list
            jira_req_tree.append(_jira_req)

        return jira_req_tree

    def _build_subtree(self, all_reqs_dict: dict, r4j_req: dict,
                       parent: JiraRequirement):
        """ Builds child/parent structure for all JiraRequirements that are not at the root level

        :param all_reqs_dict: Mapping from jira_id <-> JiraRequirement from the list of all reqs
        :param r4j_req: current r4j req whose parents and childs should be set
        :param parent: parent of the given r4j_req
        """
        _jira_req = all_reqs_dict[r4j_req["key"]]
        _jira_req.parent = parent
        parent.children.append(_jira_req)

        child_reqs = r4j_req.get("childReqs", {}).get("childReq", [])
        for _r4j_child_req in child_reqs:
            self._build_subtree(all_reqs_dict, _r4j_child_req, parent=_jira_req)

    def _update_attachments(self, all_reqs: List[JiraRequirement]):
        """ Updates Attachments for Jira-Issues (Attachments are never deleted)

        :param all_reqs: List of Requirements, where to look for updated ones
        """
        for req in all_reqs:
            if RequirementAttributes.ATTACHMENT_HASHES in req.updated_fields:
                for image_hash, image in req.attachment_hashes.items():
                    if image_hash != image:
                        # check if attachment already exists
                        if image_hash not in [attachment.filename for attachment in
                                              self.jira_instance.issue(req.jira_id).fields.attachment]:
                            self.jira_instance.add_attachment(req.jira_id, image, image_hash)
            elif InternalStatus.CREATED in req.internal_status:
                for image_hash, image in req.attachment_hashes.items():
                    self.jira_instance.add_attachment(req.jira_id, image, image_hash)

    @staticmethod
    def _resolve_jira_markup(jira_str: str, jira_markup_char: str, default_node: str):
        """ Breplaces jira markup in a string with xhtml nodes

        :param jira_str: string received from Jira
        :param jira_markup_char: jira markup character as string
        :param default_node: default xhtml_node as string to replace jira markup
        :returns: string with xhtml markup
        """

        start_pattern = r'^\{jira_char}.*?\{jira_char}[\s.!?:]'.format(jira_char=jira_markup_char)
        start_to_end_pattern = r'^\{jira_char}.*\{jira_char}$'.format(jira_char=jira_markup_char)
        inbetween_pattern = r'(?=(\s\{jira_char}.*?\{jira_char}[\s.!?:]))'.format(
            jira_char=jira_markup_char)

        # find formated string from start to middle
        for formated_string in re.findall(start_pattern, jira_str):
            xhtml_formated_string = formated_string.replace(jira_markup_char, default_node, 1)
            xhtml_formated_string = xhtml_formated_string.replace(jira_markup_char,
                                                                  default_node.replace('<', '</'),
                                                                  1)
            jira_str = jira_str.replace(formated_string, xhtml_formated_string)
        # find formated string from middle to end; uses inverted original string for better usage of regex
        for formated_string in re.findall(start_pattern, jira_str[::-1]):
            formated_string = formated_string[::-1]
            xhtml_formated_string = formated_string.replace(jira_markup_char, default_node, 1)
            xhtml_formated_string = xhtml_formated_string.replace(jira_markup_char,
                                                                  default_node.replace('<', '</'),
                                                                  1)
            jira_str = jira_str.replace(formated_string, xhtml_formated_string)
        # find formated string from start to end
        for formated_string in re.findall(start_to_end_pattern, jira_str):
            xhtml_formated_string = formated_string.replace(jira_markup_char, default_node, 1)
            xhtml_formated_string = xhtml_formated_string[0:xhtml_formated_string.rfind(
                jira_markup_char)] + default_node.replace(
                '<', '</')
            jira_str = jira_str.replace(formated_string, xhtml_formated_string)
        # find formated string inbetween the string
        for formated_string in re.findall(inbetween_pattern, jira_str):
            xhtml_formated_string = formated_string.replace(jira_markup_char, default_node, 1)
            xhtml_formated_string = xhtml_formated_string.replace(jira_markup_char,
                                                                  default_node.replace('<', '</'),
                                                                  1)
            jira_str = jira_str.replace(formated_string, xhtml_formated_string)

        return jira_str

    def _add_reqs_from_folder(self, issues_from_filter: list):
        """ Addes missing Jira issues from a r4j folder to a given list of issues

        :param issues_from_filter: Jira Issues received from a filter function
        """

        query_string = 'issue in requirementsPath("{}/{}")'.format(self.jira_instance.project(self.project).name,
                                                                   self.req_path)
        issues_from_folder = self.jira_instance.get_all_issues_from_query(query_string,
                                                                          json_result=True,
                                                                          fields=[JiraCFMapping.REQUIREMENT_ID])
        ids_from_filter = [issiu['key'] for issiu in issues_from_filter]
        ids_from_folder = [issiu['key'] for issiu in issues_from_folder]
        missing_ids = [x for x in ids_from_folder if x not in ids_from_filter]
        issues_from_filter.extend(self.jira_instance.get_jira_issues_by_id_list(missing_ids, json_result=True))
