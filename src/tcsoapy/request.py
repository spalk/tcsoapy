import pprint

from zeep import Client

from .session import TCSession


class TCRequest:
    def __init__(self, session: TCSession) -> None:
        self.host = session.serveradress
        self.transport = session.get_transport()

    def __get_client(self, service_name: str):
        wsdl = "%s/%s?wsdl" % (self.host, service_name)
        return Client(wsdl, transport=self.transport)

    def get_properties(self, uids: list, property_names: list | None = None):
        client = self.__get_client("Core-2006-03-DataManagement")
        objects = [{"uid": uid} for uid in uids]
        response = client.service.getProperties(
            objects=objects, attributes=property_names
        )
        return response

    def set_property(self, uid: str, property_name: str, value: str):
        client = self.__get_client("Core-2010-09-DataManagement")
        response = client.service.setProperties(
            info={
                "object": {"uid": uid},
                "vecNameVal": {"name": property_name, "values": value},
                "timestamp": "",
            },
            # options="ENABLE_PSE_BULLETIN_BOARD",
        )
        return response

    def get_children(self, uid, property_names=[]):
        client = self.__get_client("Core-2013-05-DataManagement")
        response = client.service.getChildren(
            inputs=[
                {"clientId": "", "obj": {"uid": uid}, "propertyNames": property_names}
            ]
        )
        return response

    def expand_grm_relations_for_secondary(self, revision_uid, relation_name):
        client = self.__get_client("Core-2007-09-DataManagement")
        response = client.service.expandGRMRelationsForSecondary(
            secondaryObjects={"uid": revision_uid},
            pref={
                "expItemRev": False,
                "returnRelations": True,
                "info": {"relationTypeName": relation_name},
            },
        )
        return response

    def get_revision_rules(self):
        client = self.__get_client("Cad-2007-01-StructureManagement")
        response = client.service.getRevisionRules()
        return response

    def get_classification_objects(self, uid: str, properties: list):
        client = self.__get_client("Classification-2007-01-Classification")
        response = client.service.getClassificationObjects(
            clsObjTags={"uid": uid, "properties": properties},
        )
        return response

    def expand_grm_relations_for_primary(self, revision_uid, relation_name):
        """
        Returns relation objects by parent revision uid and relation type name
        """
        client = self.__get_client("Core-2007-09-DataManagement")
        response = client.service.expandGRMRelationsForPrimary(
            primaryObjects={"uid": revision_uid},
            pref={
                "expItemRev": False,
                "returnRelations": True,
                "info": {"relationTypeName": relation_name},
            },
        )
        return response

    def get_session_info(self):
        client = self.__get_client("Core-2007-01-Session")
        response = client.service.getTCSessionInfo()
        return response

    def get_item_revision(self, item_id, revision_id, query_uid):
        """Runs the saved query with UID `query_uid` (e.g. "Item Revision...") by Item ID and Revision."""
        client = self.__get_client("Query-2008-06-SavedQuery")
        response = client.service.executeSavedQueries(
            input=[
                {
                    "query": {"uid": query_uid},
                    "entries": ["Item ID", "Revision"],
                    "values": [item_id, revision_id],
                    "clientId": "tcsoapy",
                    "maxNumToReturn": 100,
                    "requestId": "",
                    "resultsType": "0",
                }
            ]
        )
        if response.arrayOfQueryResults.results:
            if response.arrayOfQueryResults.results[0].objects:
                return response.arrayOfQueryResults.results[0].objects[0]
        return None

    def get_bom(
        self, item_uid, revision_uid, revision_rule_uid="", unit="", one_level=False, exclude_filter="None"
    ):
        """
        Returns response from `expandPSAllLevels` action.
        Attention: bomwindow should be closed after use with method `close_bom_window`

        Args:
            exclude_filter: Filter to exclude the type of BOMLines.
                Valid values: "None", "ExcludeOverridden", "ExcludeICHistory",
                              "ExcludeGDEs", "ExcludeNonImanItemLines"
        """
        client = self.__get_client("Cad-2007-01-StructureManagement")
        create_bom_window_response = client.service.createBOMWindows(
            info=[
                {
                    "item": {"uid": item_uid},
                    "itemRev": {"uid": revision_uid},
                    "bomView": {
                        "uid": "",
                        "properties": {
                            "name": "bl_quantity",
                        },
                    },
                    "revRuleConfigInfo": {
                        "revRule": {"uid": revision_rule_uid},
                        "clientId": "tcsoapy",
                        "props": {
                            "unitNo": unit,
                            "date": "",
                            "today": "",
                            "endItem": {
                                "uid": "",
                            },
                            "endItemRevision": {
                                "uid": "",
                            },
                        },
                    },
                    "clientId": "tcsoapy",
                    "objectForConfigure": {"uid": ""},
                    "activeAssemblyArrangement": {"uid": ""},
                }
            ]
        )
        if not create_bom_window_response.output[0].bomWindow:
            print("No bom window")
            return None

        # bom_window_uid = create_bom_window_response.output[0].bomWindow.uid
        top_line_uid = create_bom_window_response.output[0].bomLine.uid

        # excludeFilter options:
        #   "ExcludeGDEs"
        #   "ExcludeICHistory"
        #   "ExcludeNonImanItemLines"
        #   "ExcludeOverridden"
        #   "None"

        if one_level:
            response = client.service.expandPSOneLevel(
                input={
                    "excludeFilter": exclude_filter,
                    "parentBomLines": [{"uid": top_line_uid}],
                },
                pref={"expItemRev": ""},
            )
        else:
            response = client.service.expandPSAllLevels(
                input={
                    "excludeFilter": exclude_filter,
                    "parentBomLines": [{"uid": top_line_uid}],
                },
                pref={"expItemRev": ""},
            )

        return response

    def get_bom_optimized(
        self, item_uid, revision_uid, revision_rule_uid="", unit="", exclude_filter="None", batch_size=50
    ):
        """
        Returns response from batched `expandPSOneLevel` calls, optimized by:
        1. Checking bl_has_children property to skip unnecessary expansions
        2. Batching multiple parent UIDs into single SOAP requests (like RAC does)

        This method processes BOM level-by-level (breadth-first) and batches
        expansions at each level for much better performance.

        Attention: bomwindow should be closed after use with method `close_bom_window`

        Args:
            exclude_filter: Filter to exclude the type of BOMLines.
                Valid values: "None", "ExcludeOverridden", "ExcludeICHistory",
                              "ExcludeGDEs", "ExcludeNonImanItemLines"
            batch_size: Number of UIDs to expand in a single request (default: 50)

        Returns:
            Combined response with all expanded BOM lines, similar to expandPSAllLevels
        """
        from .response import Response
        import time

        client = self.__get_client("Cad-2007-01-StructureManagement")

        # Create BOM window
        create_bom_window_response = client.service.createBOMWindows(
            info=[
                {
                    "item": {"uid": item_uid},
                    "itemRev": {"uid": revision_uid},
                    "bomView": {
                        "uid": "",
                        "properties": {
                            "name": "bl_quantity",
                        },
                    },
                    "revRuleConfigInfo": {
                        "revRule": {"uid": revision_rule_uid},
                        "clientId": "tcsoapy",
                        "props": {
                            "unitNo": unit,
                            "date": "",
                            "today": "",
                            "endItem": {"uid": ""},
                            "endItemRevision": {"uid": ""},
                        },
                    },
                    "clientId": "tcsoapy",
                    "objectForConfigure": {"uid": ""},
                    "activeAssemblyArrangement": {"uid": ""},
                }
            ]
        )

        if not create_bom_window_response.output[0].bomWindow:
            print("No bom window")
            return None

        top_line_uid = create_bom_window_response.output[0].bomLine.uid

        # Keep first response and aggregate into it
        first_response = None
        all_data_objects = {}  # Dict to collect unique dataObjects by UID
        processed_uids = set()
        request_count = 0  # Track number of SOAP requests
        expansion_times = []  # Track timing for analysis
        total_bomlines_expanded = 0  # Track total BOM lines processed

        def check_has_children(response_obj: Response, bom_line_uid: str) -> bool:
            """Check if BOM line has children using bl_has_children property"""
            data_obj = response_obj.get_data_object_by_uid(bom_line_uid)
            if data_obj:
                prop = data_obj.get_property("bl_has_children")
                if prop:
                    value = prop.get_value()
                    return value == "1" or value == 1 or value is True
            return False

        def expand_batch(parent_uids: list, depth: int) -> Response:
            """Expand multiple parent UIDs in a single SOAP request"""
            nonlocal first_response, request_count

            if not parent_uids:
                return None

            request_count += 1
            start_time = time.time()

            try:
                response = client.service.expandPSOneLevel(
                    input={
                        "excludeFilter": exclude_filter,
                        "parentBomLines": [{"uid": uid} for uid in parent_uids],
                    },
                    pref={"expItemRev": ""},
                )
                elapsed = time.time() - start_time
                expansion_times.append(elapsed)

                # Log batched expansion
                print(f"   Request {request_count} (depth {depth}): Expanded {len(parent_uids)} parents [{elapsed:.2f}s]")

                # Store first response as base, extend its output for subsequent responses
                if first_response is None:
                    first_response = response
                else:
                    if hasattr(response, 'output') and response.output:
                        first_response.output.extend(response.output)

                # Collect dataObjects from ServiceData
                if hasattr(response, 'serviceData'):
                    if hasattr(response.serviceData, 'modelObjects') and response.serviceData.modelObjects:
                        for obj in response.serviceData.modelObjects:
                            all_data_objects[obj.uid] = obj
                    elif hasattr(response.serviceData, 'plain') and response.serviceData.plain:
                        for obj in response.serviceData.plain:
                            if hasattr(obj, 'uid'):
                                all_data_objects[obj.uid] = obj

                return Response(response)

            except Exception as e:
                if "Document is empty" in str(e) or "Invalid XML content" in str(e):
                    print(f"   ⚠ Request {request_count} (depth {depth}): Empty response for batch")
                    return None
                raise

        # Breadth-first expansion with batching
        print(f"   Starting batched expansion from top line: {top_line_uid}")
        current_level = [top_line_uid]  # UIDs to expand at current level
        depth = 0
        first_level_count = 0

        while current_level:
            # Filter out already processed UIDs
            current_level = [uid for uid in current_level if uid not in processed_uids]
            if not current_level:
                break

            print(f"   → Level {depth}: {len(current_level)} items to expand")
            if depth == 1:
                first_level_count = len(current_level)

            # Mark as processed
            processed_uids.update(current_level)
            total_bomlines_expanded += len(current_level)

            # Process in batches
            next_level = []  # UIDs to expand at next level
            unconfigured_count = 0

            for i in range(0, len(current_level), batch_size):
                batch = current_level[i:i+batch_size]
                response_obj = expand_batch(batch, depth)

                if not response_obj:
                    continue

                # Collect children that need expansion
                for item in response_obj.get_output():
                    children = item.children if hasattr(item, 'children') else []
                    for child in children:
                        child_uid = child.bomLine.uid if hasattr(child, 'bomLine') else None
                        if not child_uid:
                            continue

                        # Check if child has valid item revision (not unconfigured)
                        child_rev_uid = child.itemRevOfBOMLine.uid if hasattr(child, 'itemRevOfBOMLine') else None
                        if not child_rev_uid or child_rev_uid == "AAAAAAAAAAAAAA":
                            unconfigured_count += 1
                            continue

                        # Only expand if child has children and not already processed
                        if check_has_children(response_obj, child_uid) and child_uid not in processed_uids:
                            next_level.append(child_uid)

            if unconfigured_count > 0:
                print(f"   ⚠ Skipped {unconfigured_count} unconfigured children at level {depth}")

            # Show progress for depth 1+
            if depth > 0 and first_level_count > 0:
                completed_first_level = len([uid for uid in current_level if uid in processed_uids])
                # This is approximate since we're doing breadth-first now

            # Move to next level
            current_level = next_level
            depth += 1

        print(f"   ✓ All levels processed (deepest level: {depth - 1})")
        print(f"   Total SOAP requests: {request_count}")
        print(f"   Total BOM lines expanded: {total_bomlines_expanded}")
        print(f"   Total outputs collected: {len(first_response.output) if first_response and hasattr(first_response, 'output') else 0}")
        print(f"   Total data objects: {len(all_data_objects)}")

        # Timing analysis
        if expansion_times:
            avg_time = sum(expansion_times) / len(expansion_times)
            total_time = sum(expansion_times)
            print(f"   Total expansion time: {total_time:.2f}s")
            print(f"   Average request time: {avg_time:.3f}s")

        # Update the first response with all collected data objects
        if first_response and hasattr(first_response, 'serviceData'):
            first_response.serviceData.modelObjects = list(all_data_objects.values())

        return first_response

    def close_bom_window(self, bomwindow_uid):
        client = self.__get_client("Cad-2007-01-StructureManagement")
        try:
            response = client.service.closeBOMWindows(bomWindows=[{"uid": bomwindow_uid}])
            return response
        except Exception as e:
            # Server sometimes returns empty response on successful close
            # which causes XML parsing error - this is actually success
            if "Document is empty" in str(e) or "Invalid XML content" in str(e):
                return None
            raise

    def create_dataset(
        self,
        container_uid: str,
        name: str,
        relation_type: str,
        tool_used: str,
        _type: str,
    ):
        """
        <input clientId="1" datasetId="" datasetRev="" description="" name="My dataset" relationType="IMAN_manifestation" toolUsed="MSExcel" type="MSExcelTemplate">
            <container uid="<container_uid>"/>
        </input>
        """
        client = self.__get_client("Core-2008-06-DataManagement")
        response = client.service.createDatasets2(
            input={
                "clientId": "tcsoapy",
                "name": name,
                "relationType": relation_type,
                "toolUsed": tool_used,
                "type": _type,
                "container": {"uid": container_uid},
                "description": "",
                "datasetId": "",
                "datasetRev": "",
            }
        )
        return response

    def get_validation_result_raw(self, uid: str):
        """
        Gets the raw response containing the validation result object related to a master form.
        This is a workaround to get the 'validation_is_up_to_date' property, which is not
        directly available on the master form.
        """
        client = self.__get_client("Core-2006-03-DataManagement")
        response = client.service.getProperties(
            objects=[{"uid": uid}],
            attributes=["validation_result_objs", "fnd0_final_val_result"],
        )
        return response

    def refresh_pom_cache(self):
        client = self.__get_client("Core-2007-06-Session")
        response = client.service.refreshPOMCachePerRequest(refresh=True)
        return response

    def set_policy(self, policy_name):
        client = self.__get_client("Core-2007-01-Session")
        response = client.service.setObjectPropertyPolicy(policy_name)
        return response

    def get_where_used(self, uid, rule_uid="", levels=1):
        client = self.__get_client("Core-2007-01-DataManagement")
        response = client.service.whereUsed(
            numLevels=levels,
            whereUsedPrecise=False,
            objects={"uid": uid},
            rule={"uid": rule_uid},
        )
        return response

    def get_where_referenced(self, uid, levels=1):
        client = self.__get_client("Core-2007-01-DataManagement")
        response = client.service.whereReferenced(
            numLevels=levels,
            objects={"uid": uid},
        )
        return response

    def get_item_from_id(self, item_id, revision_id):
        client = self.__get_client("Core-2007-01-DataManagement")
        response = client.service.getItemFromId(
            nRev=1,
            infos={"itemId": item_id, "revIds": revision_id},
            pref=["structure_revisions", "bvr_occurrences"],
        )
        return response
