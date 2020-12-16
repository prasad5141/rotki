import json
import logging
import re
from http import HTTPStatus
from typing import Any, Dict, Optional, Tuple

import gevent
import requests
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from typing_extensions import Literal

from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors import RemoteError
from rotkehlchen.typing import ChecksumEthAddress, Timestamp

log = logging.getLogger(__name__)


GRAPH_QUERY_LIMIT = 1000
RE_MULTIPLE_WHITESPACE = re.compile(r'\s+')
RETRY_STATUS_CODES = {
    HTTPStatus.INTERNAL_SERVER_ERROR,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
}
RETRY_BACKOFF_FACTOR = 0.2


def format_query_indentation(querystr: str) -> str:
    """Format a triple quote and indented GraphQL query by:
    - Removing returns
    - Replacing multiple inner whitespaces with one
    - Removing leading and trailing whitespaces
    """
    return RE_MULTIPLE_WHITESPACE.sub(' ', querystr).strip()


def get_common_params(
        from_ts: Timestamp,
        to_ts: Timestamp,
        address: ChecksumEthAddress,
        address_type: Literal['Bytes!', 'String!'] = 'Bytes!',
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    param_types = {
        '$start_ts': 'Int!',
        '$end_ts': 'Int!',
        '$address': address_type,
    }
    param_values = {
        'start_ts': from_ts,
        'end_ts': to_ts,
        'address': address.lower(),
    }
    return param_types, param_values


class Graph():

    def __init__(self, url: str) -> None:
        """
        - May raise requests.RequestException if there is a problem connecting to the subgraph"""
        transport = RequestsHTTPTransport(url=url)
        try:
            self.client = Client(transport=transport)
        except (requests.exceptions.RequestException) as e:
            raise RemoteError(f'Failed to connect to the graph at {url} due to {str(e)}') from e

    def query(
            self,
            querystr: str,
            param_types: Optional[Dict[str, Any]] = None,
            param_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Queries The Graph for a particular query

        May raise:
        - RemoteError: If there is a problem querying the subgraph

        Retry logic is triggered by a specific status code in the exception
        message.
        """
        prefix = ''
        if param_types is not None:
            prefix = 'query '
            prefix += json.dumps(param_types).replace('"', '').replace('{', '(').replace('}', ')')
            prefix += '{'

        querystr = prefix + querystr
        log.debug(f'Querying The Graph for {querystr}')

        retries_left = QUERY_RETRY_TIMES
        while retries_left > 0:
            try:
                result = self.client.execute(gql(querystr), variable_values=param_values)
            except (requests.exceptions.RequestException, Exception) as e:
                # NB: error status code expected to be in exception message
                exc_msg = str(e)
                is_retry_status_code = False
                for status_code in RETRY_STATUS_CODES:
                    if str(status_code.value) in exc_msg:
                        is_retry_status_code = True
                        break

                if not is_retry_status_code:
                    raise RemoteError(
                        f'Failed to query the graph for {querystr} due to {str(e)}',
                    ) from e

                # Retry logic
                retries_left -= 1
                base_msg = f'The Graph query to {querystr} failed due to {exc_msg}'
                if retries_left:
                    sleep_seconds = RETRY_BACKOFF_FACTOR * pow(2, QUERY_RETRY_TIMES - retries_left)
                    retry_msg = (
                        f'Retrying query after {sleep_seconds} seconds. '
                        f'Retries left: {retries_left}.'
                    )
                    log.error(f'{base_msg}. {retry_msg}')
                    gevent.sleep(sleep_seconds)
                else:
                    raise RemoteError(f'{base_msg}. No retries left.') from e
            else:
                break

        log.debug('Got result from The Graph query')
        return result
