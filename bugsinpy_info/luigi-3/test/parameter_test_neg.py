# -*- coding: utf-8 -*-
#
# Copyright 2012-2015 Spotify AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import datetime

from helpers import with_config, LuigiTestCase, parsing, in_parse, RunOnceTask
from datetime import timedelta
import enum
import mock

import luigi
import luigi.date_interval
import luigi.interface
import luigi.notifications
from luigi.mock import MockTarget
from luigi.parameter import ParameterException
from luigi import six
from worker_test import email_patch

luigi.notifications.DEBUG = True



class TestSerializeTupleParameter(LuigiTestCase):
    def test_Serialize(self):
        the_tuple = (1, 2, 3)

        self.assertEqual(luigi.TupleParameter().parse(luigi.TupleParameter().serialize(the_tuple)), the_tuple)