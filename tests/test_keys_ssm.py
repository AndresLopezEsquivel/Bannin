"""Loading the keys from Parameter Store, against a fake SSM: botocore's
Stubber answers each call with the response the test gives it, and the
test fails if the call's parameters differ. No request leaves the machine."""

import secrets

import boto3
import pytest
from botocore.stub import Stubber

from bannin.keys import KeyConfigError, load_keys

ENV = {"BANNIN_KEYS_SOURCE": "ssm"}
# The call load_keys must make.
CALL = {"Path": "/bannin/api-keys", "WithDecryption": True}
KEY_1 = "bn_" + secrets.token_urlsafe(32)
KEY_2 = "bn_" + secrets.token_urlsafe(32)


def param(key_id, value, kind="SecureString"):
    return {"Name": f"/bannin/api-keys/{key_id}", "Type": kind, "Value": value}


@pytest.fixture
def ssm():
    """A real boto3 client with made-up credentials, wired to a Stubber."""
    client = boto3.client(
        "ssm",
        region_name="us-east-1",
        aws_access_key_id="fake",
        aws_secret_access_key="fake",
    )
    with Stubber(client) as stubber:
        yield client, stubber
        stubber.assert_no_pending_responses()


def test_one_page(ssm):
    client, stubber = ssm
    params = [param("key_01", KEY_1), param("key_02", KEY_2)]
    stubber.add_response("get_parameters_by_path", {"Parameters": params}, CALL)
    assert load_keys(ENV, client) == {"key_01": KEY_1, "key_02": KEY_2}


def test_two_pages(ssm):
    client, stubber = ssm
    first = {"Parameters": [param("key_01", KEY_1)], "NextToken": "t"}
    stubber.add_response("get_parameters_by_path", first, CALL)
    second = {"Parameters": [param("key_02", KEY_2)]}
    stubber.add_response("get_parameters_by_path", second, {**CALL, "NextToken": "t"})
    assert load_keys(ENV, client) == {"key_01": KEY_1, "key_02": KEY_2}


@pytest.mark.parametrize(
    "params",
    [
        [],  # no keys
        [param("Key-1", KEY_1)],  # a bad ID
        [param("key_01", KEY_1, kind="String")],  # not encrypted
        [param("key_01", KEY_1), param("key_02", KEY_1)],  # the same key twice
        [param("key_01", KEY_1), param("key_02", KEY_2), param("key_03", "bn_x")],
    ],
)
def test_bad_parameters_stop_loading_without_naming_a_key(ssm, params):
    client, stubber = ssm
    stubber.add_response("get_parameters_by_path", {"Parameters": params}, CALL)
    with pytest.raises(KeyConfigError) as caught:
        load_keys(ENV, client)
    assert KEY_1 not in str(caught.value)


def test_access_denied_stops_loading(ssm):
    client, stubber = ssm
    stubber.add_client_error("get_parameters_by_path", "AccessDeniedException")
    with pytest.raises(client.exceptions.ClientError):
        load_keys(ENV, client)
