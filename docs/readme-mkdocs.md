## Static site generators

sphinx : too hard to use (for me)

jekyll : my favorite !!!

mkdocs
mkdocstrings: an mkdocs plugin to auto generate api

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

## setup environment

```
source mm_env/bin/activate

pip install mkdocs
pip install mkdocstrings
pip install mkdocstrings-python
pip install mkdocs-material
```

We will use mkdocstrings plugin to auto generate api web pages from google style doc strings in our code.

## modify mkdocs.yml

Add a `plugin` block with mkdocstrings

```
plugins:
  - mkdocs-jupyter
  - search
  - autorefs
  - mkdocstrings:
      watch:
        - ../src
      handlers:
        python:
          rendering:
            show_root_heading: false
            show_root_toc_entry: false
            show_category_heading: true
            group_by_category: false
            heading_level: 2
            #show_object_full_path: true
```

Add something like this to the `nav` section. One line per source file.

```
    - API:
        - Overview: api/overview.md
        - bAnalysis: api/bAnalysis.md
```