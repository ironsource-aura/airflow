# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""This module contains Google Dataplex hook."""

from __future__ import annotations

import time
from collections.abc import Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from airflow.exceptions import AirflowException
from airflow.providers.google.common.consts import CLIENT_INFO
from airflow.providers.google.common.hooks.base_google import (
    PROVIDE_PROJECT_ID,
    GoogleBaseAsyncHook,
    GoogleBaseHook,
)
from google.api_core.client_options import ClientOptions
from google.api_core.gapic_v1.method import DEFAULT, _MethodDefault
from google.cloud.dataplex_v1 import (
    DataplexServiceClient,
    DataScanServiceAsyncClient,
    DataScanServiceClient,
)
from google.cloud.dataplex_v1.services.catalog_service import CatalogServiceClient
from google.cloud.dataplex_v1.types import (
    AspectType,
    Asset,
    DataScan,
    DataScanJob,
    EntryGroup,
    EntryType,
    Lake,
    Task,
    Zone,
)
from google.protobuf.field_mask_pb2 import FieldMask

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

    from google.api_core.operation import Operation
    from google.api_core.retry import Retry
    from google.api_core.retry_async import AsyncRetry
    from google.cloud.dataplex_v1.services.catalog_service.pagers import (
        ListAspectTypesPager,
        ListEntryGroupsPager,
        ListEntryTypesPager,
    )

PATH_DATA_SCAN = "projects/{project_id}/locations/{region}/dataScans/{data_scan_id}"


class AirflowDataQualityScanException(AirflowException):
    """Raised when data quality scan rules fail."""


class AirflowDataQualityScanResultTimeoutException(AirflowException):
    """Raised when no result found after specified amount of seconds."""


class DataplexHook(GoogleBaseHook):
    """
    Hook for Google Dataplex.

    :param api_version: The version of the api that will be requested for example 'v3'.
    :param gcp_conn_id: The connection ID to use when fetching connection info.
    :param impersonation_chain: Optional service account to impersonate using short-term
        credentials, or chained list of accounts required to get the access_token
        of the last account in the list, which will be impersonated in the request.
        If set as a string, the account must grant the originating account
        the Service Account Token Creator IAM role.
        If set as a sequence, the identities from the list must grant
        Service Account Token Creator IAM role to the directly preceding identity, with first
        account from the list granting this role to the originating account (templated).
    """

    _conn: Resource | None = None

    def __init__(
        self,
        api_version: str = "v1",
        gcp_conn_id: str = "google_cloud_default",
        impersonation_chain: str | Sequence[str] | None = None,
        location: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            gcp_conn_id=gcp_conn_id,
            impersonation_chain=impersonation_chain,
            **kwargs,
        )
        self.api_version = api_version
        self.location = location

    def get_dataplex_client(self) -> DataplexServiceClient:
        """Return DataplexServiceClient."""
        client_options = ClientOptions(api_endpoint="dataplex.googleapis.com:443")

        return DataplexServiceClient(
            credentials=self.get_credentials(), client_info=CLIENT_INFO, client_options=client_options
        )

    def get_dataplex_data_scan_client(self) -> DataScanServiceClient:
        """Return DataScanServiceClient."""
        client_options = ClientOptions(api_endpoint="dataplex.googleapis.com:443")

        return DataScanServiceClient(
            credentials=self.get_credentials(), client_info=CLIENT_INFO, client_options=client_options
        )

    def get_dataplex_catalog_client(self) -> CatalogServiceClient:
        """Return CatalogServiceClient."""
        client_options = ClientOptions(api_endpoint="dataplex.googleapis.com:443")

        return CatalogServiceClient(
            credentials=self.get_credentials(), client_info=CLIENT_INFO, client_options=client_options
        )

    def wait_for_operation(self, timeout: float | None, operation: Operation):
        """Wait for long-lasting operation to complete."""
        try:
            return operation.result(timeout=timeout)
        except Exception:
            error = operation.exception(timeout=timeout)
            raise AirflowException(error)

    @GoogleBaseHook.fallback_to_default_project_id
    def create_aspect_type(
        self,
        location: str,
        aspect_type_id: str,
        aspect_type_configuration: AspectType | dict,
        project_id: str = PROVIDE_PROJECT_ID,
        validate_only: bool = False,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Create an EntryType resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param aspect_type_id: Required. AspectType identifier.
        :param aspect_type_configuration: Required. AspectType configuration body.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param validate_only: Optional. If set, performs request validation, but does not actually execute
            the create request.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.create_aspect_type(
            request={
                "parent": client.common_location_path(project_id, location),
                "aspect_type_id": aspect_type_id,
                "aspect_type": aspect_type_configuration,
                "validate_only": validate_only,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def get_aspect_type(
        self,
        location: str,
        aspect_type_id: str,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> AspectType:
        """
        Get an AspectType resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param aspect_type_id: Required. AspectType identifier.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.get_aspect_type(
            request={
                "name": client.aspect_type_path(project_id, location, aspect_type_id),
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def create_entry_type(
        self,
        location: str,
        entry_type_id: str,
        entry_type_configuration: EntryType | dict,
        project_id: str = PROVIDE_PROJECT_ID,
        validate_only: bool = False,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Create an EntryType resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param entry_type_id: Required. EntryType identifier.
        :param entry_type_configuration: Required. EntryType configuration body.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param validate_only: Optional. If set, performs request validation, but does not actually execute
            the create request.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.create_entry_type(
            request={
                "parent": client.common_location_path(project_id, location),
                "entry_type_id": entry_type_id,
                "entry_type": entry_type_configuration,
                "validate_only": validate_only,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def get_entry_type(
        self,
        location: str,
        entry_type_id: str,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> EntryType:
        """
        Get an EntryType resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param entry_type_id: Required. EntryGroup identifier.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.get_entry_type(
            request={
                "name": client.entry_type_path(project_id, location, entry_type_id),
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def delete_aspect_type(
        self,
        location: str,
        aspect_type_id: str,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Delete an AspectType resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param aspect_type_id: Required. AspectType identifier.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.delete_aspect_type(
            request={
                "name": client.aspect_type_path(project_id, location, aspect_type_id),
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def list_aspect_types(
        self,
        location: str,
        filter_by: str | None = None,
        order_by: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> ListAspectTypesPager:
        """
        List AspectTypes resources from specific location.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param filter_by: Optional. Filter to apply on the list results.
        :param order_by: Optional. Fields to order the results by.
        :param page_size: Optional. Maximum number of EntryGroups to return on one page.
        :param page_token: Optional. Token to retrieve the next page of results.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.list_aspect_types(
            request={
                "parent": client.common_location_path(project_id, location),
                "filter": filter_by,
                "order_by": order_by,
                "page_size": page_size,
                "page_token": page_token,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def update_aspect_type(
        self,
        location: str,
        aspect_type_id: str,
        aspect_type_configuration: dict | AspectType,
        project_id: str = PROVIDE_PROJECT_ID,
        update_mask: list[str] | FieldMask | None = None,
        validate_only: bool | None = False,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Update an AspectType resource.

        :param aspect_type_id: Required. ID of the AspectType to update.
        :param aspect_type_configuration: Required. The updated configuration body of the AspectType.
        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param update_mask: Optional. Names of fields whose values to overwrite on an entry group.
            If this parameter is absent or empty, all modifiable fields are overwritten. If such
            fields are non-required and omitted in the request body, their values are emptied.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param validate_only: Optional. The service validates the request without performing any mutations.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        _aspect_type = (
            deepcopy(aspect_type_configuration)
            if isinstance(aspect_type_configuration, dict)
            else AspectType.to_dict(aspect_type_configuration)
        )
        _aspect_type["name"] = client.aspect_type_path(project_id, location, aspect_type_id)
        return client.update_aspect_type(
            request={
                "aspect_type": _aspect_type,
                "update_mask": FieldMask(paths=update_mask) if type(update_mask) is list else update_mask,
                "validate_only": validate_only,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def delete_entry_type(
        self,
        location: str,
        entry_type_id: str,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Delete an EntryType resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param entry_type_id: Required. EntryType identifier.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.delete_entry_type(
            request={
                "name": client.entry_type_path(project_id, location, entry_type_id),
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def list_entry_types(
        self,
        location: str,
        filter_by: str | None = None,
        order_by: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> ListEntryTypesPager:
        """
        List EntryTypes resources from specific location.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param filter_by: Optional. Filter to apply on the list results.
        :param order_by: Optional. Fields to order the results by.
        :param page_size: Optional. Maximum number of EntryGroups to return on one page.
        :param page_token: Optional. Token to retrieve the next page of results.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.list_entry_types(
            request={
                "parent": client.common_location_path(project_id, location),
                "filter": filter_by,
                "order_by": order_by,
                "page_size": page_size,
                "page_token": page_token,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def update_entry_type(
        self,
        location: str,
        entry_type_id: str,
        entry_type_configuration: dict | EntryType,
        project_id: str = PROVIDE_PROJECT_ID,
        update_mask: list[str] | FieldMask | None = None,
        validate_only: bool | None = False,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Update an EntryType resource.

        :param entry_type_id: Required. ID of the EntryType to update.
        :param entry_type_configuration: Required. The updated configuration body of the EntryType.
        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param update_mask: Optional. Names of fields whose values to overwrite on an entry group.
            If this parameter is absent or empty, all modifiable fields are overwritten. If such
            fields are non-required and omitted in the request body, their values are emptied.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param validate_only: Optional. The service validates the request without performing any mutations.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        _entry_type = (
            deepcopy(entry_type_configuration)
            if isinstance(entry_type_configuration, dict)
            else EntryType.to_dict(entry_type_configuration)
        )
        _entry_type["name"] = client.entry_type_path(project_id, location, entry_type_id)
        return client.update_entry_type(
            request={
                "entry_type": _entry_type,
                "update_mask": FieldMask(paths=update_mask) if type(update_mask) is list else update_mask,
                "validate_only": validate_only,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def create_entry_group(
        self,
        location: str,
        entry_group_id: str,
        entry_group_configuration: EntryGroup | dict,
        project_id: str = PROVIDE_PROJECT_ID,
        validate_only: bool = False,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Create an Entry resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param entry_group_id: Required. EntryGroup identifier.
        :param entry_group_configuration: Required. EntryGroup configuration body.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param validate_only: Optional. If set, performs request validation, but does not actually execute
            the create request.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.create_entry_group(
            request={
                "parent": client.common_location_path(project_id, location),
                "entry_group_id": entry_group_id,
                "entry_group": entry_group_configuration,
                "validate_only": validate_only,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def get_entry_group(
        self,
        location: str,
        entry_group_id: str,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> EntryGroup:
        """
        Get an EntryGroup resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param entry_group_id: Required. EntryGroup identifier.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.get_entry_group(
            request={
                "name": client.entry_group_path(project_id, location, entry_group_id),
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def delete_entry_group(
        self,
        location: str,
        entry_group_id: str,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Delete an EntryGroup resource.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param entry_group_id: Required. EntryGroup identifier.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.delete_entry_group(
            request={
                "name": client.entry_group_path(project_id, location, entry_group_id),
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def list_entry_groups(
        self,
        location: str,
        filter_by: str | None = None,
        order_by: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        project_id: str = PROVIDE_PROJECT_ID,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> ListEntryGroupsPager:
        """
        List EntryGroups resources from specific location.

        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param filter_by: Optional. Filter to apply on the list results.
        :param order_by: Optional. Fields to order the results by.
        :param page_size: Optional. Maximum number of EntryGroups to return on one page.
        :param page_token: Optional. Token to retrieve the next page of results.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        return client.list_entry_groups(
            request={
                "parent": client.common_location_path(project_id, location),
                "filter": filter_by,
                "order_by": order_by,
                "page_size": page_size,
                "page_token": page_token,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def update_entry_group(
        self,
        location: str,
        entry_group_id: str,
        entry_group_configuration: dict | EntryGroup,
        project_id: str = PROVIDE_PROJECT_ID,
        update_mask: list[str] | FieldMask | None = None,
        validate_only: bool | None = False,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Operation:
        """
        Update an EntryGroup resource.

        :param entry_group_id: Required. ID of the EntryGroup to update.
        :param entry_group_configuration: Required. The updated configuration body of the EntryGroup.
        :param location: Required. The ID of the Google Cloud location that the task belongs to.
        :param update_mask: Optional. Names of fields whose values to overwrite on an entry group.
            If this parameter is absent or empty, all modifiable fields are overwritten. If such
            fields are non-required and omitted in the request body, their values are emptied.
        :param project_id: Optional. The ID of the Google Cloud project that the task belongs to.
        :param validate_only: Optional. The service validates the request without performing any mutations.
        :param retry: Optional. A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: Optional. The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Optional. Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_catalog_client()
        _entry_group = (
            deepcopy(entry_group_configuration)
            if isinstance(entry_group_configuration, dict)
            else EntryGroup.to_dict(entry_group_configuration)
        )
        _entry_group["name"] = client.entry_group_path(project_id, location, entry_group_id)
        return client.update_entry_group(
            request={
                "entry_group": _entry_group,
                "update_mask": FieldMask(paths=update_mask) if type(update_mask) is list else update_mask,
                "validate_only": validate_only,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    def create_task(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        body: dict[str, Any] | Task,
        dataplex_task_id: str,
        validate_only: bool | None = None,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Create a task resource within a lake.

        :param project_id: Required. The ID of the Google Cloud project that the task belongs to.
        :param region: Required. The ID of the Google Cloud region that the task belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake that the task belongs to.
        :param body: Required. The Request body contains an instance of Task.
        :param dataplex_task_id: Required. Task identifier.
        :param validate_only: Optional. Only validate the request, but do not perform mutations.
            The default is false.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        parent = f"projects/{project_id}/locations/{region}/lakes/{lake_id}"

        client = self.get_dataplex_client()
        result = client.create_task(
            request={
                "parent": parent,
                "task_id": dataplex_task_id,
                "task": body,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def delete_task(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        dataplex_task_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Delete the task resource.

        :param project_id: Required. The ID of the Google Cloud project that the task belongs to.
        :param region: Required. The ID of the Google Cloud region that the task belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake that the task belongs to.
        :param dataplex_task_id: Required. The ID of the Google Cloud task to be deleted.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        name = f"projects/{project_id}/locations/{region}/lakes/{lake_id}/tasks/{dataplex_task_id}"

        client = self.get_dataplex_client()
        result = client.delete_task(
            request={
                "name": name,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def list_tasks(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        page_size: int | None = None,
        page_token: str | None = None,
        filter: str | None = None,
        order_by: str | None = None,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        List tasks under the given lake.

        :param project_id: Required. The ID of the Google Cloud project that the task belongs to.
        :param region: Required. The ID of the Google Cloud region that the task belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake that the task belongs to.
        :param page_size: Optional. Maximum number of tasks to return. The service may return fewer than this
            value. If unspecified, at most 10 tasks will be returned. The maximum value is 1000;
            values above 1000 will be coerced to 1000.
        :param page_token: Optional. Page token received from a previous ListZones call. Provide this to
            retrieve the subsequent page. When paginating, all other parameters provided to ListZones must
            match the call that provided the page token.
        :param filter: Optional. Filter request.
        :param order_by: Optional. Order by fields for the result.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        parent = f"projects/{project_id}/locations/{region}/lakes/{lake_id}"

        client = self.get_dataplex_client()
        result = client.list_tasks(
            request={
                "parent": parent,
                "page_size": page_size,
                "page_token": page_token,
                "filter": filter,
                "order_by": order_by,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def get_task(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        dataplex_task_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Get task resource.

        :param project_id: Required. The ID of the Google Cloud project that the task belongs to.
        :param region: Required. The ID of the Google Cloud region that the task belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake that the task belongs to.
        :param dataplex_task_id: Required. The ID of the Google Cloud task to be retrieved.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        name = f"projects/{project_id}/locations/{region}/lakes/{lake_id}/tasks/{dataplex_task_id}"
        client = self.get_dataplex_client()
        result = client.get_task(
            request={
                "name": name,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def delete_lake(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
         Delete the lake resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake to be deleted.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        name = f"projects/{project_id}/locations/{region}/lakes/{lake_id}"

        client = self.get_dataplex_client()
        result = client.delete_lake(
            request={
                "name": name,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def create_lake(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        body: dict[str, Any] | Lake,
        validate_only: bool | None = None,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Create a lake resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param lake_id: Required. Lake identifier.
        :param body: Required. The Request body contains an instance of Lake.
        :param validate_only: Optional. Only validate the request, but do not perform mutations.
            The default is false.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        parent = f"projects/{project_id}/locations/{region}"
        client = self.get_dataplex_client()
        result = client.create_lake(
            request={
                "parent": parent,
                "lake_id": lake_id,
                "lake": body,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def get_lake(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Get lake resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake to be retrieved.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        name = f"projects/{project_id}/locations/{region}/lakes/{lake_id}/"
        client = self.get_dataplex_client()
        result = client.get_lake(
            request={
                "name": name,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def create_zone(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        zone_id: str,
        body: dict[str, Any] | Zone,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Create a zone resource within a lake.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake to be retrieved.
        :param body: Required. The Request body contains an instance of Zone.
        :param zone_id: Required. Zone identifier.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_client()

        name = f"projects/{project_id}/locations/{region}/lakes/{lake_id}"
        result = client.create_zone(
            request={
                "parent": name,
                "zone": body,
                "zone_id": zone_id,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def delete_zone(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        zone_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Delete a zone resource. All assets within a zone must be deleted before the zone can be deleted.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake to be retrieved.
        :param zone_id: Required. Zone identifier.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_client()

        name = f"projects/{project_id}/locations/{region}/lakes/{lake_id}/zones/{zone_id}"
        operation = client.delete_zone(
            request={"name": name},
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return operation

    @GoogleBaseHook.fallback_to_default_project_id
    def create_asset(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        zone_id: str,
        asset_id: str,
        body: dict[str, Any] | Asset,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Create an asset resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake to be retrieved.
        :param zone_id: Required. Zone identifier.
        :param asset_id: Required. Asset identifier.
        :param body: Required. The Request body contains an instance of Asset.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_client()

        name = f"projects/{project_id}/locations/{region}/lakes/{lake_id}/zones/{zone_id}"
        result = client.create_asset(
            request={
                "parent": name,
                "asset": body,
                "asset_id": asset_id,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def delete_asset(
        self,
        project_id: str,
        region: str,
        lake_id: str,
        asset_id: str,
        zone_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Delete an asset resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param lake_id: Required. The ID of the Google Cloud lake to be retrieved.
        :param zone_id: Required. Zone identifier.
        :param asset_id: Required. Asset identifier.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_client()

        name = f"projects/{project_id}/locations/{region}/lakes/{lake_id}/zones/{zone_id}/assets/{asset_id}"
        result = client.delete_asset(
            request={"name": name},
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def create_data_scan(
        self,
        project_id: str,
        region: str,
        body: dict[str, Any] | DataScan,
        data_scan_id: str | None = None,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Create a DataScan resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param data_scan_id: Required. Data Quality scan identifier.
        :param body: Required. The Request body contains an instance of DataScan.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_data_scan_client()

        parent = f"projects/{project_id}/locations/{region}"
        result = client.create_data_scan(
            request={
                "parent": parent,
                "data_scan": body,
                "data_scan_id": data_scan_id,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def run_data_scan(
        self,
        project_id: str,
        region: str,
        data_scan_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Run an on-demand execution of a DataScan.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param data_scan_id: Required. Data Quality scan identifier.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_data_scan_client()

        name = PATH_DATA_SCAN.format(project_id=project_id, region=region, data_scan_id=data_scan_id)
        result = client.run_data_scan(
            request={
                "name": name,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def get_data_scan_job(
        self,
        project_id: str,
        region: str,
        data_scan_id: str | None = None,
        job_id: str | None = None,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Get a DataScan Job resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param data_scan_id: Required. Data Quality scan identifier.
        :param job_id: Required. The resource name of the DataScanJob:
            projects/{project_id}/locations/{region}/dataScans/{data_scan_id}/jobs/{data_scan_job_id}
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_data_scan_client()

        name = f"projects/{project_id}/locations/{region}/dataScans/{data_scan_id}/jobs/{job_id}"
        result = client.get_data_scan_job(
            request={"name": name, "view": "FULL"},
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    def wait_for_data_scan_job(
        self,
        data_scan_id: str,
        job_id: str | None = None,
        project_id: str = PROVIDE_PROJECT_ID,
        region: str | None = None,
        wait_time: int = 10,
        result_timeout: float | None = None,
    ) -> Any:
        """
        Wait for Dataplex data scan job.

        :param job_id: Required. The job_id to wait for.
        :param data_scan_id: Required. Data Quality scan identifier.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param project_id: Optional. Google Cloud project ID.
        :param wait_time: Number of seconds between checks.
        :param result_timeout: Value in seconds for which operator will wait for the Data Quality scan result.
            Throws exception if there is no result found after specified amount of seconds.
        """
        start = time.monotonic()
        state = None
        while state not in (
            DataScanJob.State.CANCELLED,
            DataScanJob.State.FAILED,
            DataScanJob.State.SUCCEEDED,
        ):
            if result_timeout and start + result_timeout < time.monotonic():
                raise AirflowDataQualityScanResultTimeoutException(
                    f"Timeout: Data Quality scan {job_id} is not ready after {result_timeout}s"
                )
            time.sleep(wait_time)
            try:
                job = self.get_data_scan_job(
                    job_id=job_id,
                    data_scan_id=data_scan_id,
                    project_id=project_id,
                    region=region,
                )
                state = job.state
            except Exception as err:
                self.log.info("Retrying. Dataplex API returned error when waiting for job: %s", err)
        return job

    @GoogleBaseHook.fallback_to_default_project_id
    def get_data_scan(
        self,
        project_id: str,
        region: str,
        data_scan_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Get a DataScan resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param data_scan_id: Required. Data Quality scan identifier.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_data_scan_client()

        name = PATH_DATA_SCAN.format(project_id=project_id, region=region, data_scan_id=data_scan_id)
        result = client.get_data_scan(
            request={"name": name, "view": "FULL"},
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def update_data_scan(
        self,
        project_id: str,
        region: str,
        data_scan_id: str,
        body: dict[str, Any] | DataScan,
        update_mask: dict | FieldMask | None = None,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Update a DataScan resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param data_scan_id: Required. Data Quality scan identifier.
        :param body: Required. The Request body contains an instance of DataScan.
        :param update_mask: Required. Mask of fields to update.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_data_scan_client()

        full_scan_name = f"projects/{project_id}/locations/{region}/dataScans/{data_scan_id}"

        if body:
            if isinstance(body, DataScan):
                body.name = full_scan_name
            elif isinstance(body, dict):
                body["name"] = full_scan_name
            else:
                raise AirflowException("Unable to set scan_name.")

        if not update_mask:
            update_mask = FieldMask(
                paths=["data_quality_spec", "labels", "description", "display_name", "execution_spec"]
            )

        result = client.update_data_scan(
            request={
                "data_scan": body,
                "update_mask": update_mask,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def delete_data_scan(
        self,
        project_id: str,
        region: str,
        data_scan_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Delete a DataScan resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param data_scan_id: Required. Data Quality scan identifier.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_data_scan_client()

        name = PATH_DATA_SCAN.format(project_id=project_id, region=region, data_scan_id=data_scan_id)
        result = client.delete_data_scan(
            request={
                "name": name,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result

    @GoogleBaseHook.fallback_to_default_project_id
    def list_data_scan_jobs(
        self,
        project_id: str,
        region: str,
        data_scan_id: str,
        retry: Retry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        List DataScanJobs under the given DataScan.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param data_scan_id: Required. Data Quality scan identifier.
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = self.get_dataplex_data_scan_client()

        name = PATH_DATA_SCAN.format(project_id=project_id, region=region, data_scan_id=data_scan_id)
        result = client.list_data_scan_jobs(
            request={
                "parent": name,
            },
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )
        return result


class DataplexAsyncHook(GoogleBaseAsyncHook):
    """
    Asynchronous Hook for Google Cloud Dataplex APIs.

    All the methods in the hook where project_id is used must be called with
    keyword arguments rather than positional.
    """

    sync_hook_class = DataplexHook

    def __init__(
        self,
        gcp_conn_id: str = "google_cloud_default",
        impersonation_chain: str | Sequence[str] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(gcp_conn_id=gcp_conn_id, impersonation_chain=impersonation_chain, **kwargs)

    async def get_dataplex_data_scan_client(self) -> DataScanServiceAsyncClient:
        """Return DataScanServiceAsyncClient."""
        client_options = ClientOptions(api_endpoint="dataplex.googleapis.com:443")

        return DataScanServiceAsyncClient(
            credentials=(await self.get_sync_hook()).get_credentials(),
            client_info=CLIENT_INFO,
            client_options=client_options,
        )

    @GoogleBaseHook.fallback_to_default_project_id
    async def get_data_scan_job(
        self,
        project_id: str,
        region: str,
        data_scan_id: str | None = None,
        job_id: str | None = None,
        retry: AsyncRetry | _MethodDefault = DEFAULT,
        timeout: float | None = None,
        metadata: Sequence[tuple[str, str]] = (),
    ) -> Any:
        """
        Get a DataScan Job resource.

        :param project_id: Required. The ID of the Google Cloud project that the lake belongs to.
        :param region: Required. The ID of the Google Cloud region that the lake belongs to.
        :param data_scan_id: Required. DataScan identifier.
        :param job_id: Required. The resource name of the DataScanJob:
            projects/{project_id}/locations/{region}/dataScans/{data_scan_id}/jobs/{data_scan_job_id}
        :param retry: A retry object used  to retry requests. If `None` is specified, requests
            will not be retried.
        :param timeout: The amount of time, in seconds, to wait for the request to complete.
            Note that if `retry` is specified, the timeout applies to each individual attempt.
        :param metadata: Additional metadata that is provided to the method.
        """
        client = await self.get_dataplex_data_scan_client()

        name = f"projects/{project_id}/locations/{region}/dataScans/{data_scan_id}/jobs/{job_id}"
        result = await client.get_data_scan_job(
            request={"name": name, "view": "FULL"},
            retry=retry,
            timeout=timeout,
            metadata=metadata,
        )

        return result
