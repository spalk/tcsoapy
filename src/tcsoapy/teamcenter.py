import logging
from typing import List
import pprint

from .session import TCSession
from .request  import TCRequest
from .response import Response, DataObject, Property
from .tools import Tools

logger = logging.getLogger('tcsoapy')


class Teamcenter:
    def __init__(self, url: str, login: str, password: str):
        self.url = url
        self.login = login
        self.password = password
        self.session = None
        self.request: TCRequest = None
        
        self._create_session()
        self._create_request()

        self.tools = Tools(self.request)


    def get_properties(
            self, 
            uid: str | DataObject | List[str|DataObject],
            properties: str | List[str] | None = None
        ) -> List[Property] | None:
        """
        Returns properties for target object.
        Object can be set as: 
            - single UID (str)
            - list of UIDs (list)
            - DataObject
        Required properties can be set as:
            - single property name
            - list of property names
            - None (default list of properties will be returned)
        Returns DataObject with properties for the given target.
        """
        if isinstance(uid, str):
            uids = [uid]
        elif isinstance(uid, DataObject):
            uids = [uid.get_uid()]
        elif isinstance(uid, list):
            uids = []
            for i in uid:
                if isinstance(i, str):
                    uids.append(i)
                elif isinstance(i, DataObject):
                    uids.append(i.get_uid())
                else:
                    raise TypeError('UID list must be a string or a DataObject.')
        else:
            raise TypeError('uid must be a string, DataObject or a list of them.')

        if not properties: 
            properties = []
        elif isinstance(properties, str):
            properties = [properties]
        elif isinstance(properties, list):
            pass  
        else: 
            raise TypeError('properties must be a string or a list of them, or be empty (None).')

        if properties:
            response = self.request.get_properties(uids, properties)
        else:
            response = self.request.get_properties(uids)

        response = Response(response)
        # pprint.pprint(response.raw_response)
        data_objects = [response.get_data_object_by_uid(_uid) for _uid in uids]
        property_objects = []
        for do in data_objects:
            for prp in properties:
                property_obj = do.get_property(prp)
                property_objects.append(property_obj)

        return property_objects


    def get_item(self, uid: str) -> DataObject:
        """Returns DataObject with the given uid"""
        raw_response = self.request.get_properties([uid])
        response = Response(raw_response)
        if not response.data_objects and response.errors:
            print(response.errors)

        return response.get_data_object_by_uid(uid)


    def find(self, 
            item_id: str | None, 
            rev_id: str | None,
            name: str | None, 
            uid: str | None ) -> List[DataObject]:
        """Returns list of DataObjects matching the provided item id with/without revision, name or uid"""
        if item_id and rev_id: 
            ...
        if item_id:
            ...
        if name:
            ...
        if uid:
            return [self.get_item(uid)]
    
        raise ValueError("Invalid Item")


    def _create_session(self):
        self.session = TCSession(self.url, self.login, self.password)

    def _create_request(self):
        if not self.session:
            raise RuntimeError("Session has not been created. Ensure _create_session is called before _create_request.")
        self.request = TCRequest(self.session)
        



