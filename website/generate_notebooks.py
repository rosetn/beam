# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements. See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.

"""Script to generate Jupyter notebooks from a markdown page.

Dependencies:
  pip install -U nbformat

Usage:
  From root directory:
    python website/generate_notebooks.py --help

  Examples:
    python website/generate_notebooks.py \
      website/src/examples/transforms/element-wise/keys.md \
      --output-prefix examples/notebooks/transforms/element-wise/keys \
      --github-ipynb-url https://github.com/davidcavazos/beam/blob/notebooks/examples/notebooks/transforms/element-wise/keys-py.ipynb \
      --docs-url https://beam.apache.org/examples/transforms/element-wise/keys/ \
      --docs-logo-url https://beam.apache.org/images/logos/full-color/nameless/beam-logo-full-color-nameless-100.png \
      --variables-prefix site. \
      --imports \
        website/assets/license.md:0 \
        website/assets/setup-py.md:0:py \
        website/assets/setup-java.md:1:java \
        website/assets/setup-go.md:1:go \
        website/assets/cleanup.md:-1 \

  This will generate the following files:
    examples/notebooks/examples/transforms/element-wise/keys-java.ipynb
    examples/notebooks/examples/transforms/element-wise/keys-py.ipynb
    examples/notebooks/examples/transforms/element-wise/keys-go.ipynb
"""

import base64
import json
import nbformat
import os
import re
import requests

DEFAULT_KERNEL = 'python3'
LANGS = ['java', 'py', 'go']
VARIABLES_REGEX = r'\{\{\s*([^\s\{\}]+)\s*\}\}'  # Jekyll syntax: {{ site.variable }}
SPECIAL_SECTION_RE = re.compile('\{:\.[\w-]+\}')
GITHUB_SAMPLE_RE = re.compile(
    r'\{%\s*github_sample\s+/([\w-]+)/([\w-]+)/blob/([\w-]+)/([\w/.-]+)\s+tag\:(\w+)\s*%\}')
EOF = None


class Import:
  def __init__(self, str_value):
    # Format:
    #   path/to/filename.md:index
    #   path/to/filename.md:index:lang
    #   path/to/filename.md:index:lang&lang&...
    parts = str_value.split(':')
    self.path = parts[0]
    self.index = int(parts[1]) if len(parts) >= 2 else 0
    self.langs = parts[2].split('&') if len(parts) >= 3 else LANGS


# TODO: make `filename` into a file descriptor.
# TODO: `output_prefix` should default to something in the current directory.
# TODO: `filename` and `output_prefix` should be gotten from command line arguments at __main__.
# TODO: `output_prefix` should get a sensible default from `filename` at __main__.
def run(filename, langs=LANGS, output_prefix='notebook', **options):
  if output_prefix is None:
    output_prefix = os.path.splitext(os.path.basename(filename))[0]

  output_dir = os.path.dirname(output_prefix)
  if not os.path.exists(output_dir):
   os.makedirs(output_dir)

  for lang in langs:
    with open(filename) as f:
      notebook = new_notebook(f.read(), lang, **options)
    notebook_file = '{}-{}.ipynb'.format(output_prefix, lang)
    print('Writing: {}'.format(notebook_file))
    with open(notebook_file, 'w') as f:
      nbformat.write(notebook, f)


def new_notebook(
        content,
        lang='py',
        name=None,
        github_ipynb_url=None,
        kernel=DEFAULT_KERNEL,
        lang_type_format='{:.language-%s}',
        shell_type_unix='{:.shell-unix}',
        **options):

  lang_type = lang_type_format % lang
  cells = []
  if github_ipynb_url:
    if github_ipynb_url.startswith('https://'):
      github_ipynb_url = github_ipynb_url[len('https://'):]
    if github_ipynb_url.startswith('github.com/'):
      github_ipynb_url = github_ipynb_url[len('github.com/'):]
    source = (
      '<a href="https://colab.research.google.com/github/{}" target="_parent">'
        '<img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab"/>'
      '</a>'
      .format(github_ipynb_url)
    )
    cells.append(nbformat.v4.new_markdown_cell(source=source, metadata={'id': 'view-in-github'}))

  used_ids = {'view-in-github'}
  def cell_id(name):
    if name not in used_ids:
      used_ids.add(name)
      return name
    i = 2
    while True:
      numbered = '{}-{}'.format(name, i)
      if numbered not in used_ids:
        used_ids.add(name)
        return numbered
      i += 1

  header = ''
  for section in notebook_sections(content, lang, **options):
    first_line = section[0][0]
    if first_line.startswith('#'):
      header = first_line.strip('# ')
      if name is None:
        name = header

    for cell in section:
      if cell[0].startswith('<!--') and cell[-1].endswith('-->'):
        continue

      cell_type = None
      m = SPECIAL_SECTION_RE.search(cell[0])
      if m:
        cell_type = m.group(0)
        cell = cell[1:]

      is_code = False
      if cell[0].startswith('```') and cell[-1].endswith('```'):
        is_code = True
        lang = cell[0].lstrip('`')
        if lang:
          cell_type = lang_type_format % lang
        cell = cell[1:-1]

      metadata = {}
      source = '\n'.join(cell)
      if is_code:
        if cell_type is None or cell_type == lang_type:
          source, tag = code_block(source)
          if tag:
            metadata['id'] = cell_id('_' + tag)
          if source.startswith('#@title'):
            metadata['cellView'] = 'form'
          cells.append(nbformat.v4.new_code_cell(source=source, metadata=metadata))
        elif cell_type == shell_type_unix:
          source = shell_block(source)
          cells.append(nbformat.v4.new_code_cell(source=source, metadata=metadata))
      elif cell_type is None or cell_type == lang_type:
        if cell[0].startswith('#'):
          metadata['id'] = cell_id(re.sub(r'[^\w]+', '-', header.lower()))
        cells.append(nbformat.v4.new_markdown_cell(source=source, metadata=metadata))

  metadata = {
    'colab': {"toc_visible": True},
    'kernelspec': {'name': kernel, 'display_name': kernel},
  }
  if name:
    metadata['colab']['name'] = name
  return nbformat.v4.new_notebook(cells=cells, metadata=metadata)


def notebook_sections(
        content,
        lang='py',
        imports=None,
        docs_url=None,
        docs_logo_url=None,
        start_on_header=True,
        **options):
  if imports is None:
    imports = []

  docs_logo_img = ''
  if docs_logo_url:
    docs_logo_img = '<img src="{}" width="32" height="32" />'.format(docs_logo_url)
  view_the_docs_content = (
      '<table align="left">'
        '<td>'
          '<a target="_blank" href="{}">'
            '{}View the Docs'
          '</a>'
        '</td>'
      '</table>'
      .format(docs_url, docs_logo_img)
  )

  content_sections = [
    section
    for i, section in enumerate(sections(content, **options))
    if i != 0 or section[0][0].startswith('#')
  ]

  imports_dict = {}
  for _import in imports:
    if lang not in _import.langs:
      continue
    index = _import.index
    if index < 0:
      index = len(content_sections) + index + 1
    if index not in imports_dict:
      imports_dict[index] = []
    imports_dict[index].append(_import)

  for i, section in enumerate(content_sections):
    if i in imports_dict:
      for _import in imports_dict[i]:
        with open(_import.path) as f:
          import_content = f.read()
        for import_section in sections(import_content, **options):
          yield import_section
    if i == 0 and docs_url:
      for view_the_docs_section in sections(view_the_docs_content, **options):
        yield view_the_docs_section
    yield section

  i = len(content_sections)
  if i in imports_dict:
    for _import in imports_dict[i]:
      with open(_import.path) as f:
        import_content = f.read()
      for import_section in sections(import_content, **options):
        yield import_section
  if docs_url:
    for view_the_docs_section in sections(view_the_docs_content, **options):
      yield view_the_docs_section


def sections(content, **options):
  section = []
  cells_iter = cells(content, **options)
  cell = next(cells_iter)
  for next_cell in cells_iter:
    section.append(cell)
    if next_cell == EOF:
      yield section
      break
    if next_cell[0].startswith('#'):
      yield section
      section = []
    cell = next_cell


def cells(content, **options):
  cell = []
  paragraphs_iter = paragraphs(content, **options)
  paragraph = next(paragraphs_iter)
  for next_paragraph in paragraphs_iter:
    if cell:
      cell.append('')
    cell += paragraph
    if next_paragraph == EOF:
      yield cell
      break
    if next_paragraph[0].startswith('#'):
      yield cell
      cell = []
    elif next_paragraph[0].startswith('```') or paragraph[0].endswith('```'):
      yield cell
      cell = []
    elif SPECIAL_SECTION_RE.search(next_paragraph[0] + paragraph[0]):
      cell[0] = cell[0].strip()
      yield cell
      cell = []
    paragraph = next_paragraph
  yield EOF


def paragraphs(content, variables=None, variables_regex=VARIABLES_REGEX,
               variables_prefix=''):
  if variables is None:
    variables = {}

  variables_re = re.compile(variables_regex)
  in_code_block = False
  paragraph = []
  for line in content.splitlines():
    line = line.rstrip()
    m = variables_re.search(line)
    if m:
      variable_name = m.group(1)
      if variable_name.startswith(variables_prefix):
        variable_name = variable_name[len(variables_prefix):]
      variable_value = str(variables[variable_name])
      line = line.replace(m.group(0), variable_value)
    if in_code_block:
      if line.endswith('```'):
        in_code_block = False
        line = line.rstrip('`')
        if line:
          paragraph.append(line)
        paragraph.append('```')
        yield paragraph
        paragraph = []
      else:
        paragraph.append(line)
    elif line.lstrip().startswith('```'):
      in_code_block = True
      paragraph.append(line.strip())
    elif line:
      paragraph.append(line)
    elif paragraph:
      yield paragraph
      paragraph = []
  if paragraph:
    yield paragraph
  yield EOF


def code_block(source):
  first_tag = ''
  for m in GITHUB_SAMPLE_RE.finditer(source):
    owner, repo, branch, path, tag = m.groups()
    if not first_tag:
      first_tag = tag
    url = 'https://api.github.com/repos/{}/{}/contents/{}'.format(owner, repo, path)
    req = requests.get(url, params={'ref': branch})
    if req.status_code == requests.codes.ok:
      req = req.json()
      content = base64.b64decode(req['content']).decode('utf-8')
      snippet = extract_snippet(content, tag)
      source = source.replace(m.group(0), snippet)
  return source.rstrip(), first_tag


def shell_block(source):
  return '\n'.join([
      '!{}'.format(line) if line and not line.startswith('#') else line
      for line in source.splitlines()
  ])


def extract_snippet(content, tag):
  tag_start_re = re.compile(r'\[\s*START\s+{}\s*\]'.format(tag))
  tag_end_re = re.compile(r'\[\s*END\s+{}\s*\]'.format(tag))
  
  started = False
  min_indent = float('Inf')
  snippet = []
  for line in content.splitlines():
    if not started and tag_start_re.search(line):
      started = True
    elif started:
      if tag_end_re.search(line):
        break
      snippet.append(line)
      if line.strip():
        indent = len(line) - len(line.lstrip())
        min_indent = min(indent, min_indent)
  if min_indent != float('Inf'):
    snippet = [line[min_indent:] for line in snippet]
  return '\n'.join(snippet)


if __name__ == '__main__':
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument('markdown_file', help='Path to a markdown file.')
  parser.add_argument(
      '--langs',
      nargs='+',
      default=LANGS,
      help='Languages to generate notebooks for: {}.'.format(', '.join(LANGS)),
  )
  parser.add_argument(
      '--output-prefix',
      default=None,
      help='File path prefix for the generated ipynb files.',
  )

  # Options.
  parser.add_argument(
    '--name',
    help='Name to display as title on Colab.',
  )
  parser.add_argument(
    '--imports',
    type=Import,
    nargs='+',
    default=[],
    help='Imports in the format: "path/to/markdown.md:index:lang&lang&...". '
         'Languages are optional.',
  )
  parser.add_argument(
      '--no-start-on-header',
      action='store_false',
      help='Set to start the notebook on the first header found.',
  )
  parser.add_argument(
    '--github-ipynb-url',
    help='URL of the GitHub ipynb file.',
  )
  parser.add_argument(
    '--docs-url',
    help='URL of the equivalent documentation page.',
  )
  parser.add_argument(
    '--docs-logo-url',
    help='URL of the logo for the "View the Docs" button.',
  )

  parser.add_argument(
    '--variables-yaml',
    help='YAML filename where variables are stored.',
  )
  parser.add_argument(
    '--variables-regex',
    default=VARIABLES_REGEX,
    help='Regular expression for the variable format. '
         'Must contain 1 group for the variable name.',
  )
  parser.add_argument(
    '--variables-prefix',
    default='',
    help='Prefix for variables, example: "site." for Jekyll variables.',
  )

  parser.add_argument(
    '--kernel',
    default=DEFAULT_KERNEL,
    help='Notebook kernel to use, defaults to "python3".',
  )
  args = parser.parse_args()

  run(
    args.markdown_file,
    langs=args.langs,
    output_prefix=args.output_prefix,

    # Options.
    imports=args.imports,
    start_on_header=not args.no_start_on_header,
    github_ipynb_url=args.github_ipynb_url,
    docs_url=args.docs_url,
    docs_logo_url=args.docs_logo_url,

    variables={
      'branch_repo': 'davidcavazos/beam/blob/notebooks',
    },
    variables_prefix=args.variables_prefix,

    kernel=args.kernel,
  )
