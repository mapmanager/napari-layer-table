## Static site generators

- We will use mkdocs to build a static site with custom written documentation.
- We will use the mkdocstrings plugin to auto generate api web pages from google style doc strings in our code.

## Setup a local environment

To use mkdocs in a local environment, you need the following ...

```
pip install mkdocs
pip install mkdocstrings
pip install mkdocstrings-python
pip install mkdocs-material
```

## Interacting with mkdocs on the command line

1) To serve and browse the static site locally

```
mkdocs serve
```

Keep an eye on the command line output, it gives warnings when there are typos in your docstrings.

2) To push changes to github

```
mkdocs gh-deploy
```

Note: This pushes to `main branch gh-pages`. I think the contents of the remote main branch gh-pages are built from what you have locally. If you are locally on main branch it will use that. If you are locally on branch `'myBranch` it will use that.

## Modify mkdocs.yml

Add a `plugins` block with mkdocstrings

```
plugins:
  #- mkdocs-jupyter
  - search
  - autorefs
  - mkdocstrings:
      watch:
        - src
      handlers:
        python:
          selection:
            inherited_members: false
          rendering:
            show_root_heading: false
            show_root_toc_entry: false
            show_category_heading: true
            group_by_category: false
            heading_level: 1
            merge_init_into_class: true
            show_signature_annotations: true
            #show_object_full_path: true
```

Add something like this to the `nav` section. One line per source file.

```
nav:
- Home: index.md
- Scripting: scripting.md
- API:
    - Overview: api/overview.md
    - _my_widget: api/_my_widget.md
    - _table_widget: api/_table_widget.md
    - _data_model: api/_data_model.md
```

## Modify file in `docs/` folder

Given the structure of the mkdocs.yml `vav` section, the `docs/` folder looks like this

```
docs
├── api
│   ├── _data_model.md
│   ├── _my_widget.md
│   ├── _table_widget.md
│   └── overview.md
├── img
│   └── simple-script-screenshot.png
├── index.md
└── scripting.md
```

For the api, the contents of docs/api/_data_model.md looks as follows. This just expands theformatted docstring into the browser.

```
::: napari_layer_table._data_model.pandasModel
```

## Make a new branch

```
git checkout -b activate-mkdocs
git push origin activate-mkdocs

#remote: Create a pull request for 'activate-mkdocs' on GitHub by visiting:
#remote:      https://github.com/mapmanager/napari-layer-table/pull/new/activate-mkdocs
```

## start using pyenv again

```
# install pyenv
git clone https://github.com/pyenv/pyenv ~/.pyenv

# setup pyenv (you should also put these three lines in .bashrc or similar)
export PATH="${HOME}/.pyenv/bin:${PATH}"
export PYENV_ROOT="${HOME}/.pyenv"
eval "$(pyenv init -)"

# install Python 3.7
pyenv install 3.7.12

# make it available globally
pyenv global system 3.7.12
```

