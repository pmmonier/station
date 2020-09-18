# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import argparse
import time
import uuid
import json
import os
from concurrent.futures import Future
from awscrt import io
from awscrt.io import LogLevel
from awscrt.mqtt import Connection, Client, QoS
from awsiot.greengrass_discovery import DiscoveryClient, DiscoverResponse
from awsiot import mqtt_connection_builder


class iotDevice:
    basePath = os.path.abspath(os.getcwd())
    allowed_actions = ['both', 'publish', 'subscribe']
    certificate_path = "{}/crt/nj/adda013961.cert.pem".format(basePath)
    private_key_path = '{}/crt/nj/adda013961.private.key'.format(basePath)
    root_ca_path = '{}/crt/nj/root-CA.crt'.format(basePath)
    response_file_path = '{}/response.txt'.format(basePath)
    # thing_name = 'pub'
    thing_name = 'station_1'
    region = 'us-east-1'
    mode = 'subscribe'
    topic_validateTicket = 'topic_validateTicket'
    topic_response_validateTicket = 'topic_response_validateTicket'

    def __init__(self):
        self.conn = None
        self.start()

    def on_connection_interupted(self, connection, error, **kwargs):
        print('connection interrupted with error {}'.format(error))

    def on_connection_resumed(self, connection, return_code, session_present, **kwargs):
        print('connection resumed with return code {}, session present {}'.format(return_code, session_present))

    # Try IoT endpoints until we find one that works
    def try_iot_endpoints(self, discover_response, client_bootstrap):
        for gg_group in discover_response.gg_groups:
            for gg_core in gg_group.cores:
                for connectivity_info in gg_core.connectivity:
                    try:
                        print('Trying core {} at host {} port {}'.format(gg_core.thing_arn,
                                                                         connectivity_info.host_address,
                                                                         connectivity_info.port))
                        mqtt_connection = mqtt_connection_builder.mtls_from_path(
                            endpoint=connectivity_info.host_address,
                            port=connectivity_info.port,
                            cert_filepath=self.certificate_path,
                            pri_key_filepath=self.private_key_path,
                            client_bootstrap=client_bootstrap,
                            ca_bytes=gg_group.certificate_authorities[0].encode('utf-8'),
                            on_connection_interrupted=self.on_connection_interupted,
                            on_connection_resumed=self.on_connection_resumed,
                            client_id=self.thing_name,
                            clean_session=False,
                            keep_alive_secs=6)

                        connect_future = mqtt_connection.connect()
                        connect_future.result()
                        print('Connected!')
                        return mqtt_connection

                    except Exception as e:
                        print('Connection failed with exception {}'.format(e))
                        continue

        exit('All connection attempts failed')

    def publishMessage(self, p):
        messageJson = json.dumps(p)
        open(self.response_file_path, 'w').close()
        pub_future, _ = self.conn.publish(self.topic_validateTicket, messageJson, QoS.AT_MOST_ONCE)
        pub_future.result()
        print('Published topic {}: {}\n'.format(self.topic_validateTicket, messageJson))
        while True:
            time.sleep(0.05)
            f = open(self.response_file_path, "r")
            response = f.read()
            print('before while', response)
            if response != '':
                break

        open(self.response_file_path, 'w').close()
        print('file data', response)
        return json.loads(response)

    def start(self):
        event_loop_group = io.EventLoopGroup(1)
        host_resolver = io.DefaultHostResolver(event_loop_group)
        client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

        tls_options = io.TlsContextOptions.create_client_with_mtls_from_path(self.certificate_path,
                                                                             self.private_key_path)
        if self.root_ca_path:
            tls_options.override_default_trust_store_from_path(None, self.root_ca_path)
        tls_context = io.ClientTlsContext(tls_options)

        socket_options = io.SocketOptions()
        socket_options.connect_timeout_ms = 3000

        print('Performing greengrass discovery...')
        discovery_client = DiscoveryClient(client_bootstrap, socket_options, tls_context, self.region)
        resp_future = discovery_client.discover(self.thing_name)
        discover_response = resp_future.result()
        mqtt_connection = self.try_iot_endpoints(discover_response, client_bootstrap)
        self.conn = mqtt_connection
        if self.mode == 'both' or self.mode == 'subscribe':
            def on_publish(topic, payload, **kwargs):
                print('Publish received on topic {}'.format(topic))
                f = open(self.response_file_path, "w")
                f.write(payload)
                f.close()
                print(payload)

            subscribe_future, _ = mqtt_connection.subscribe(self.topic_response_validateTicket, QoS.AT_MOST_ONCE,
                                                            on_publish)
            subscribe_result = subscribe_future.result()
            print(subscribe_result)
