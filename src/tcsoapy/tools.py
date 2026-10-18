import logging
from typing import List
from dataclasses import dataclass
from pprint import pprint

from .request import TCRequest
from .response import Response


logger = logging.getLogger("tcsoapy.tools")


@dataclass
class Rule:
    """Revision Rule data object"""

    uid: str
    name: str
    description: str = None
    last_mod_date: str = None

    def __str__(self):
        return f"{self.uid} - {self.name}  - {self.description} [{self.last_mod_date}]"


class Tools:
    """
    Class with methods, which combite multiple request or are specific task solvers.
    """

    def __init__(self, tc_request: TCRequest):
        self.tc_request = tc_request

    def get_rules(self) -> List[Rule]:
        """Returns list of Rules"""
        rules = []
        rules_response_raw = self.tc_request.get_revision_rules()
        rules_response = Response(rules_response_raw)
        rule_dos = rules_response.get_data_objects_by_type("RevisionRule")
        logger.debug(f"Found {len(rule_dos)} RevisionRules")
        for rule_do in rule_dos:
            rule = Rule(
                uid=rule_do.get_uid(),
                name=rule_do.get_property("object_name").get_ui_value()
                if rule_do.get_property("object_name")
                else None,
                description=rule_do.get_property("object_desc").get_ui_value()
                if rule_do.get_property("object_desc")
                else None,
                last_mod_date=rule_do.get_property("last_mod_date").get_ui_value()
                if rule_do.get_property("last_mod_date")
                else None,
            )
            rules.append(rule)
        return rules

    def get_rule_uid_by_name(self, rule_name: str) -> str:
        """Returns UID of Revision Rule as String"""
        rules = self.get_rules()
        rules_dict = {rule.name: rule.uid for rule in rules}
        rule_uid = rules_dict.get(rule_name, None)
        return rule_uid

    def get_end_item_by_rule(self, rule_uid: str = None, rule_name: str = None) -> str:
        """
        Get End Item UID by rule uid OR rule name.
        Returns a tuple of End Item UID and End Item Name
        """
        if not rule_uid and not rule_name:
            raise ValueError("Either rule_uid or rule_name should be provided.")

        # Get Rule UID (by name) if it was not provided
        if not rule_uid:
            rule_uid = self.get_rule_uid_by_name(rule_name)

        if not rule_uid:
            raise ValueError(f"Rule '{rule_name}' not found.")

        # Get End Item UID:
        end_item_property_name = "rule_end_item"
        end_item_response_raw = self.tc_request.get_properties(
            [rule_uid],
            [
                end_item_property_name,
            ],
        )
        end_item_response = Response(end_item_response_raw)
        end_item_property = end_item_response.get_property(
            rule_uid, end_item_property_name
        )
        end_item_uid = end_item_property.get_value()

        # Get End Item  item_id
        item_id_property_name = "item_id"
        item_id_response_raw = self.tc_request.get_properties(
            [end_item_uid],
            [
                item_id_property_name,
            ],
        )
        item_id_response = Response(item_id_response_raw)
        item_id_property = item_id_response.get_property(
            end_item_uid, item_id_property_name
        )
        end_item = item_id_property.get_value()

        return end_item_uid, end_item

    def get_statuses_from_rule(
        self, rule_uid: str = None, rule_name: str = None
    ) -> List[str]:
        """
        Returns list of entry_text values as string for example:
            [
                'Has Status( Agreed, Configured Using Unit Number )',
                'Has Status( Approved, Configured Using Unit Number )',
                'Has Status( Rejected, Configured Using Unit Number )',
                'Has Status( Validation, Configured Using Unit Number )',
                'Has Status( Any Release Status, Configured Using Released Date )',
                'Has Item Type ( Purchased part, Standard Item)',
                'Precise',
                'Working(  )',
                'End Item( 000123 )',
            ]
        """
        if not rule_uid and not rule_name:
            raise ValueError("Either rule_uid or rule_name should be provided.")

        # Get Rule UID (by name) if it was not provided
        if not rule_uid:
            rule_uid = self.get_rule_uid_by_name(rule_name)

        if not rule_uid:
            raise ValueError(f"Rule '{rule_name}' not found.")

        entry_texts = []
        property_name = "entry_list"
        response_raw = self.tc_request.get_properties(
            [rule_uid],
            [
                property_name,
            ],
        )
        response = Response(response_raw)
        property = response.get_property(rule_uid, property_name)
        for value in property.values:
            entry_uid = value["value"]
            entry_props_resp_raw = self.tc_request.get_properties(
                [entry_uid], ["entry_text"]
            )
            entry_props_resp = Response(entry_props_resp_raw)
            property = entry_props_resp.get_property(entry_uid, "entry_text")
            entry_texts.append(property.get_ui_value())
        return entry_texts

    def get_revision_uid_by_item_id(
        self, item_id, revision_id="00", property_names=None, ui_value=False
    ) -> dict | None:
        """
        Returns UID and Object Type as dict  by item_id and rev_id.
        Option: to the dict can be also added proterties by propetry name,
                as value you can choose 'value' or 'uiValue' by setting up ui_value
                argument ('value' by default). But be careful, only basic properties
                are available in this response. Use 'get_properties' method to get
                more properties
        """
        response = self.tc_request.get_item_from_id(item_id, revision_id)
        try:
            item_rev_output = response["output"][0]["itemRevOutput"][0]["itemRevision"]
            data = {"uid": item_rev_output["uid"], "type": item_rev_output["type"]}
        except (KeyError, IndexError):
            # logger.exception(
            #     "Get item revision from output failed for item_id=%s, revision_id=%s",
            #     item_id,
            #     revision_id,
            # )
            return None

        if property_names:
            response = Response(response)
            do = response.get_data_object_by_uid(data["uid"])
            if do:
                for prpt_name in property_names:
                    try:
                        prp = do.get_property(prpt_name)
                        data[prpt_name] = (
                            prp.get_ui_value() if ui_value else prp.get_value()
                        )
                    except Exception as e:
                        logger.warning(
                            f"No {prpt_name} was found in data object with uid {data['uid']}: {e}"
                        )

        return data

    def get_item_uid_revision_uid(self, item_id, revision_id) -> tuple | None:
        """
        Returns a tuple of Item UID and  ItemRevision UID by Item ID and Revision ID
        (Item_UID, Revision_UID)
        or None if something failed
        """
        response = self.tc_request.get_item_from_id(item_id, revision_id)
        try:
            item_uid = response["output"][0]["item"]["uid"]
            item_rev_uid = response["output"][0]["itemRevOutput"][0]["itemRevision"][
                "uid"
            ]
            return (item_uid, item_rev_uid)
        except (KeyError, IndexError):
            return (None, None)
