from datetime import datetime

import libtaxii
from libtaxii.common import generate_message_id
from libtaxii.clients import HttpClient
import libtaxii.messages_10 as tm10
import libtaxii.messages_11 as tm11

from libtaxii.constants import *

from .abstract import AbstractClient
from .utils import extract_content, ts_to_date, ContentBlock
from .exceptions import *

import logging
log = logging.getLogger(__name__)


class Client11(AbstractClient):

    taxii_version = libtaxii.VID_TAXII_XML_11


    def _discovery_request(self, uri):
        request = tm11.DiscoveryRequest(message_id=self._generate_id())
        response = self._execute_request(request, uri=uri)
        return response


    def get_collections(self, uri=None):

        request = tm11.CollectionInformationRequest(message_id=self._generate_id())
        response = self._execute_request(request, uri=uri, service_type=SVC_COLLECTION_MANAGEMENT)

        return response


    def push(self, content, content_binding, subtype=None, collections=[], uri=None):

        content_block = tm11.ContentBlock(tm11.ContentBinding(content_binding), content)

        if subtype:
            content_block.content_binding.subtype_ids.append(subtype)

        inbox_message = tm11.InboxMessage(message_id=self._generate_id(), content_blocks=[content_block])

        if collections:
            inbox_message.destination_collection_names.extend(collections)

        response = self._execute_request(inbox_message, uri=uri, service_type=SVC_INBOX)


    def poll(self, collection, begin_date=None, end_date=None, subscription=None, uri=None):

        data = dict(
            message_id = self._generate_id(),
            collection_name = collection,
            exclusive_begin_timestamp_label = begin_date,
            inclusive_end_timestamp_label = end_date
        )

        if subscription:
            data['subscription_id'] = subscription_id
        else:
            data['poll_parameters'] = tm11.PollRequest.PollParameters()

        request = tm11.PollRequest(**data)

        response = self._execute_request(request, uri=uri, service_type=SVC_POLL)


        for block in extract_content(response, source=self.host, source_collection=collection):
            yield block

        while response.more:
            part = response.result_part_number + 1
            for block in self.fulfillment(collection, response.result_id, part_number=part, uri=uri, service=service):
                yield block


    def fulfillment(self, collection, result_id, part_number=1, uri=None, service=None):

        request = tm11.PollFulfillmentRequest(
            message_id = self._generate_id(),
            collection_name = collection,
            result_id = result_id,
            result_part_number = part_number
        )

        response = self._execute_request(request, uri=uri, service_type=SVC_POLL)

        for block in extract_content(response, source=self.host, source_collection=collection):
            yield block

