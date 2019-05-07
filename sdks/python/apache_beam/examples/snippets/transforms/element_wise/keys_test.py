#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import absolute_import

import logging
import unittest
from unittest import mock

import apache_beam as beam
import unittest
from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that
from apache_beam.testing.util import equal_to

from apache_beam.examples.snippets.transforms.element_wise import keys


@mock.patch('apache_beam.Pipeline', TestPipeline)
@mock.patch('apache_beam.examples.snippets.transforms.element_wise.keys.print', lambda x: x)
class KeysTest(unittest.TestCase):
  def test_keys(self):
    # [START keys_outputs]
    outputs = [
      'Wind power',
      'Hydropower',
      'Solar energy',
      'Geothermal',
      'Bioenergy',
    ]
    # [END keys_outputs]

    def test(pcollection):
      assert_that(pcollection, equal_to(outputs))
    keys.keys(test)


if __name__ == '__main__':
  unittest.main()
