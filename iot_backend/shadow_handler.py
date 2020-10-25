"""
This module handles all the communication with the AWS IoT Device Shadow Service.

It uses the AWS SDK boto3. Boto3 must be configured before use, its configuration files reside in '~/aws' directory.
See online documentation for instructions about configuration and usage.
"""

import boto3
import json


def get_device_shadow(aws_thing_name: str) -> dict:
    """Gets the shadow for the specified thing.

    :param aws_thing_name: The name of the AWS IoT thing.
    :return: The device shadow.
    """

    client = boto3.client('iot-data')

    response = client.get_thing_shadow(thingName=aws_thing_name)

    shadow = json.loads(response['payload'].read())

    return shadow


def update_device_shadow(aws_thing_name: str, request_state_document) -> dict:
    """Updates the shadow for the specified thing.

    Updates affect only the fields specified in the request state document.
    Any field with a value of null is removed from the device's shadow.

    A request state document has the following format:

    {
        "state": {
            "desired": {
                "attribute1": integer2,
                "attribute2": "string2",
                ...
                "attributeN": boolean2
            },
            "reported": {
                "attribute1": integer1,
                "attribute2": "string1",
                ...
                "attributeN": boolean1
            }
        },
        "clientToken": "token",
        "version": version
    }

    state — Updates affect only the fields specified.
            Typically, you'll use either the desired or the reported property, but not both in the same request.
                desired — The state properties and values requested to be updated in the device.
                reported — The state properties and values reported by the device.
    clientToken — If used, you can match the request and corresponding response by the client token.
    version — If used, the Device Shadow service processes the update only if the specified version matches the latest version it has.

    :param aws_thing_name: The name of the AWS IoT thing.
    :param request_state_document: The state information, in JSON format.
    :return: The output from the UpdateThingShadow operation.
    """

    client = boto3.client('iot-data')

    response = client.update_thing_shadow(
        thingName=aws_thing_name,
        payload=request_state_document,
    )

    return response


# main function for testing purposes
if __name__ == '__main__':

    # test get shadow
    shadow_data = get_device_shadow('FleetDevice2e713bfd-e6a3-4451-8e42-1a627d1c452f')
    print(json.dumps(shadow_data, indent=4))

    # test set shadow
    json_test = """
                {
                    "state": {
                        "desired": {
                            "test_property": "test123456789",
                            "statetest_property": null
                        }
                    }
                }
                """

    res = update_device_shadow('FleetDevice2e713bfd-e6a3-4451-8e42-1a627d1c452f', json_test)
    print(res)
