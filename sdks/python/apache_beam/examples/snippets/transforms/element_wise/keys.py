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
from __future__ import print_function


def keys(test=None):
  """Extracts the key from each element in a collection of key-value pairs.

  To run this snippet from the root directory:
    python sdks/python/apache_beam/examples/snippets/transforms/element_wise/keys.py keys
  """

  # [START keys]
  import apache_beam as beam

  with beam.Pipeline() as pipeline:
    energy_sources = (
      pipeline
      # Global energy capacity in 2017 (in GW)
      | 'Create inputs' >> beam.Create([
          ('Wind power', 540),
          ('Hydropower', 1154),
          ('Solar energy', 390),
          ('Geothermal', 12.9),
          ('Bioenergy', 109),
        ])
      | 'Keys' >> beam.Keys()
      | 'Print' >> beam.Map(print)
    )
    # [END keys]
    if test:
      test(energy_sources)


if __name__ == '__main__':
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument('example', help='Name of the example function to run')
  args = parser.parse_args()

  eval(args.example + '()')
