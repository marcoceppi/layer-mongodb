# Building

This requires the MongoDB interface, currently at [marcoceppi/interface-mongodb](https://github.com/marcoceppi/interface-mongodb).

If you haven't already, set up a $JUJU_REPOSITORY:

```
export JUJU_REPOSITORY=$HOME/charming
export LAYER_PATH=$JUJU_REPOSITORY/layers
export INTERFACE_PATH=$JUJU_REPOSITORY/interfaces

mkdir -p $LAYER_PATH $INTERFACE_PATH
```

Clone this repository to `$LAYER_PATH` and the interface to `$INTERFACE_PATH`

```
git clone https://github.com/marcoceppi/layer-mongodb $LAYER_PATH/mongodb
git clone https://github.com/marcoceppi/interface-mongodb $INTERFACE_PATH/mongodb
```

Once downloaded,

```
charm build $LAYER_PATH/mongodb
```

Once built successfully,

```
juju deploy $JUJU_REPOSITORY/builds/mongodb --series xenial
```

# Testing

Create a virtual environment and install the testing dependencies

```
cd $LAYER_PATH/mongodb
virtualenv -p python3 venv
. venv/bin/activate
pip install -r tests/requirements.txt
```

While the virtual environment is still activated, run nosetests

```
nosetests --with-coverage --cover-package=charms --cover-package=reactive --cover-erase
```

# Contributing

We welcome all contributions! To expedite the process, please fork this repository first.

Once forked and cloned locally, create a branch for the topic of this contribution. Typically these are named after the issue, for example if you're takling issue number 900 you would do the following:

```
git checkout -b issue-900
```

For new features, or changes without a corrosponding issue number, whatever name best suits these changes will do.

As you hack on features we request that commits be grouped logically. This can be achieved in your branch by rebasing commits to arrange them logically
