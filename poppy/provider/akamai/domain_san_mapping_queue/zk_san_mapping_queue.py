# Copyright (c) 2014 Rackspace, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from kazoo.recipe import queue
from oslo_config import cfg

from poppy.common import decorators
from poppy.provider.akamai.domain_san_mapping_queue import base
from poppy.provider.akamai import utils


AKAMAI_OPTIONS = [
    # queue backend configs
    cfg.StrOpt(
        'queue_backend_type',
        help='SAN Cert Queueing backend'),
    cfg.ListOpt(
        'queue_backend_host',
        default=['localhost'],
        help='default queue backend server hosts'),
    cfg.IntOpt(
        'queue_backend_port',
        default=2181,
        help='default'
        ' default queue backend server port (e.g: 2181)'),
    cfg.StrOpt(
        'san_mapping_queue_path',
        default='/san_mapping_queue',
        help='Zookeeper path '
        'for san_mapping_queue'
    ),
]

AKAMAI_GROUP = 'drivers:provider:akamai:queue'


class ZookeeperSanMappingQueue(base.SanMappingQueue):

    def __init__(self, conf):
        super(ZookeeperSanMappingQueue, self).__init__(conf)

        self._conf.register_opts(AKAMAI_OPTIONS,
                                 group=AKAMAI_GROUP)
        self.akamai_conf = self._conf[AKAMAI_GROUP]

    @decorators.lazy_property(write=False)
    def san_mapping_queue_backend(self):
        return queue.LockingQueue(
            self.zk_client,
            self.akamai_conf.san_mapping_queue_path)

    @decorators.lazy_property(write=False)
    def zk_client(self):
        return utils.connect_to_zookeeper_queue_backend(self.akamai_conf)

    def enqueue_san_mapping(self, san_domain_map):
        self.san_mapping_queue_backend.put(san_domain_map)

    def traverse_queue(self, consume=False):
        res = []
        while len(self.san_mapping_queue_backend) > 0:
            item = self.san_mapping_queue_backend.get()
            self.san_mapping_queue_backend.consume()
            res.append(item)
        if consume is False:
            self.san_mapping_queue_backend.put_all(res)
        return res

    def put_queue_data(self, queue_data):
        # put queue data will replace all existing
        # queue data with the incoming new queue_data
        # dequeue all the existing data
        while len(self.san_mapping_queue_backend) > 0:
            self.san_mapping_queue_backend.get()
            self.san_mapping_queue_backend.consume()
        # put in all the new data
        self.san_mapping_queue_backend.put_all(queue_data)
        return queue_data

    def dequeue_san_mapping(self, consume=True):
        res = self.san_mapping_queue_backend.get()
        if consume:
            self.san_mapping_queue_backend.consume()
        return res
