import logging
from collections.abc import Iterable

logger = logging.getLogger("tcsoapy.response")


class Property:
    def __init__(self, name, values, modifiable, uiValue, uiValues):
        self.name = name
        self.values = values
        self.uiValue = uiValue
        self.uiValues = uiValues
        self.modifiable = modifiable
        self.parent = None

    def __str__(self):
        return f"Parent: {self.parent.get_uid()}, {self.name}: {self.get_value()}"

    def get_value(self):
        return self.values[0]["value"] if self.values else None

    def get_values(self) -> list:
        return [v["value"] for v in self.values]

    def get_ui_value(self):
        return self.uiValue

    def is_modifiable(self):
        return self.modifiable

    def get_parent(self):
        return self.parent

    def set_parent(self, dataobject: "DataObject"):
        self.parent = dataobject


class DataObject:
    def __init__(self, uid, object_type, properties):
        self.uid = uid
        self.type = object_type
        self.properties = []
        for prop in properties:
            prop_obj = Property(**prop.__dict__["__values__"])
            prop_obj.set_parent(self)
            self.properties.append(prop_obj)

    def get_property(self, name: str) -> Property | None:
        if not self.properties:
            return None
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None

    def get_uid(self):
        return self.uid

    def get_type(self):
        return self.type


class Response:
    def __init__(self, response_data):
        self.raw_response = response_data
        self.data_objects_raw = self._get_data_objects_raw(response_data)
        errors = (
            response_data.partialErrors if "partialErrors" in response_data else None
        )
        if errors:
            print(errors)
        self.data_objects = [
            DataObject(obj["uid"], obj["type"], obj["properties"])
            for obj in self.data_objects_raw
        ]
        # if not self.data_objects:
        #     logger.warning("No Data Objects were found in response")
        self.plain_objects = self._get_plain_objs(response_data)

    def get_data_object_by_uid(self, uid):
        for obj in self.data_objects:
            if obj.get_uid() == uid:
                return obj
        return None

    def get_data_objects_by_type(self, object_type):
        return [obj for obj in self.data_objects if obj.get_type() == object_type]

    def get_all_uids(self):
        return [obj.get_uid() for obj in self.data_objects]

    def do_count(self):
        return len(self.data_objects)

    def get_property(self, do_uid: str, property_name: str) -> Property | None:
        data_object = self.get_data_object_by_uid(do_uid)
        if not data_object:
            logger.warning(f"No Data Object was found in respose by uid {do_uid}")
            return None
        property = data_object.get_property(property_name)
        if not property:
            logger.warning(f"Property {property_name} not found in Data Object")
            return None
        return property

    def get_plain_objs(self) -> list[str]:
        """Returns list of uids"""
        return self.plain_objects

    def _get_plain_objs(self, response_data) -> list:
        if "ServiceData" not in response_data:
            return []
        if (
            not response_data["ServiceData"]
            or "plainObjs" not in response_data["ServiceData"]
        ):
            return []
        if not response_data["ServiceData"]["plainObjs"]:
            return []
        try:
            uids = [i["uid"] for i in response_data["ServiceData"]["plainObjs"]]
        except Exception as e:
            logger.error(
                "Extraction plain objects uids from ServiceData failed",
                e,
                exc_info=True,
            )
            uids = []
        return uids

    def get_output(self):
        if hasattr(self.raw_response, "output"):
            return self.raw_response.output
        return []

    def _get_data_objects_raw(self, response_data):
        if "dataObjects" in response_data:
            return response_data.dataObjects
        elif (
            "ServiceData" in response_data
            and isinstance(response_data["ServiceData"], Iterable)
            and "dataObjects" in response_data["ServiceData"]
        ):
            return response_data.ServiceData.dataObjects
        else:
            return []
