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

import luigi
import luigi.contrib.redshift
import mock

from helpers import unittest


# Fake AWS and S3 credentials taken from `../redshift_test.py`.
AWS_ACCESS_KEY = 'key'
AWS_SECRET_KEY = 'secret'

BUCKET = 'bucket'
KEY = 'key'


class DummyS3CopyToTable(luigi.contrib.redshift.S3CopyToTable):

    # Class attributes taken from `DummyPostgresImporter` in
    # `../postgres_test.py`.
    host = 'dummy_host'
    database = 'dummy_database'
    user = 'dummy_user'
    password = 'dummy_password'
    table = 'dummy_table'
    columns = (
        ('some_text', 'text'),
        ('some_int', 'int'),
    )

    aws_access_key_id = AWS_ACCESS_KEY
    aws_secret_access_key = AWS_SECRET_KEY
    s3_load_path = 's3://%s/%s' % (BUCKET, KEY)
    copy_options = ''


class TestS3CopyToTable(unittest.TestCase):
    def test_pyfix(self) :
        pass
