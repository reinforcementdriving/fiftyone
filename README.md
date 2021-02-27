<div align="center">
<p align="center">

<!-- prettier-ignore -->
<img src="https://user-images.githubusercontent.com/25985824/106288517-2422e000-6216-11eb-871d-26ad2e7b1e59.png" height="55px"> &nbsp;
<img src="https://user-images.githubusercontent.com/25985824/106288518-24bb7680-6216-11eb-8f10-60052c519586.png" height="50px">

**The open-source tool for building high-quality datasets and computer vision
models.**

---

<!-- prettier-ignore -->
<a href="https://voxel51.com/fiftyone">Website</a> •
<a href="https://voxel51.com/docs/fiftyone">Docs</a> •
<a href="https://colab.research.google.com/github/voxel51/fiftyone-examples/blob/master/examples/quickstart.ipynb">Try it Now</a> •
<a href="https://voxel51.com/docs/fiftyone/tutorials/index.html">Tutorials</a> •
<a href="https://github.com/voxel51/fiftyone-examples">Examples</a> •
<a href="https://medium.com/voxel51">Blog</a> •
<a href="https://join.slack.com/t/fiftyone-users/shared_invite/zt-gtpmm76o-9AjvzNPBOzevBySKzt02gg">Community</a>

[![PyPI python](https://img.shields.io/pypi/pyversions/fiftyone)](https://pypi.org/project/fiftyone)
[![PyPI version](https://badge.fury.io/py/fiftyone.svg)](https://pypi.org/project/fiftyone)
[![Downloads](https://pepy.tech/badge/fiftyone)](https://pepy.tech/project/fiftyone)
[![Build](https://github.com/voxel51/fiftyone/workflows/Build/badge.svg?branch=develop&event=push)](https://github.com/voxel51/fiftyone/actions?query=workflow%3ABuild)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white)](https://join.slack.com/t/fiftyone-users/shared_invite/zt-gtpmm76o-9AjvzNPBOzevBySKzt02gg)
[![Medium](https://img.shields.io/badge/Medium-12100E?logo=medium&logoColor=white)](https://medium.com/voxel51)
[![Mailing list](http://bit.ly/2Md9rxM)](https://share.hsforms.com/1zpJ60ggaQtOoVeBqIZdaaA2ykyk)
[![Twitter](https://img.shields.io/twitter/follow/Voxel51?style=social)](https://twitter.com/voxel51)

<img alt="FiftyOne" src="https://user-images.githubusercontent.com/25985824/96070012-5c6fff80-0e6d-11eb-84d0-a88f8b026ee1.png">

</p>
</div>

---

[FiftyOne](http://www.voxel51.com/docs/fiftyone) is an open source ML tool
created by [Voxel51](https://voxel51.com) that helps you build high-quality
datasets and computer vision models.

With FiftyOne, you can search, sort, filter, visualize, analyze, and improve
your datasets without excess wrangling or writing custom scripts. It also
provides powerful functionality for analyzing your models, allowing you to
understand their strengths and weaknesses, visualize, diagnose, and correct
their failure modes, and more. FiftyOne is designed to be lightweight and
easily integrate into your existing CV/ML workflows.

You can get involved by joining our Slack community, reading our blog on
Medium, and following us on social media:

[![Slack](https://img.shields.io/badge/Slack-4A154B?logo=slack&logoColor=white)](https://join.slack.com/t/fiftyone-users/shared_invite/zt-gtpmm76o-9AjvzNPBOzevBySKzt02gg)
[![Medium](https://img.shields.io/badge/Medium-12100E?logo=medium&logoColor=white)](https://medium.com/voxel51)
[![Twitter](https://img.shields.io/badge/Twitter-1DA1F2?logo=twitter&logoColor=white)](https://twitter.com/voxel51)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?logo=linkedin&logoColor=white)](https://www.linkedin.com/company/voxel51)
[![Facebook](https://img.shields.io/badge/Facebook-1877F2?logo=facebook&logoColor=white)](https://www.facebook.com/voxel51)

## Installation

You can install the latest stable version of FiftyOne via `pip`:

```shell
pip install fiftyone
```

Consult the
[installation guide](https://voxel51.com/docs/fiftyone/getting_started/install.html)
for troubleshooting and other information about getting up-and-running with
FiftyOne.

## Quickstart

Dive right into FiftyOne by launching the quickstart:

```shell
fiftyone quickstart
```

This command will download a small dataset, launch the App, and print some
suggestions for exploring the dataset.

You can also check out
[this Colab notebook](https://colab.research.google.com/github/voxel51/fiftyone-examples/blob/master/examples/quickstart.ipynb)
to try some common workflows with the quickstart dataset, or run through
[this Colab notebok](https://colab.research.google.com/github/voxel51/fiftyone-examples/blob/master/examples/walkthrough.ipynb)
for a more detailed overview of FiftyOne.

## Documentation

Full documentation for FiftyOne is
[available online](https://voxel51.com/docs/fiftyone). In particular, see these
resources:

-   [Tutorials](https://voxel51.com/docs/fiftyone/tutorials/index.html)
-   [Recipes](https://voxel51.com/docs/fiftyone/recipes/index.html)
-   [User Guide](https://voxel51.com/docs/fiftyone/user_guide/index.html)
-   [CLI Documentation](https://voxel51.com/docs/fiftyone/cli/index.html)
-   [API Reference](https://voxel51.com/docs/fiftyone/api/fiftyone.html)

## Examples

Check out the [fiftyone-examples](https://github.com/voxel51/fiftyone-examples)
repository for open source and community-contributed examples of using
FiftyOne.

## Contributing to FiftyOne

FiftyOne is open source and community contributions are welcome!

Check out the
[contribution guide](https://github.com/voxel51/fiftyone/blob/develop/CONTRIBUTING.md)
to learn how to get involved.

## Installing from source

This section explains how to install the latest development version of FiftyOne
from source.

The instructions below are for macOS and Linux systems. Windows users may need
to make adjustments.

### Prerequisites

You will need:

-   [Python](https://www.python.org) (3.6 or newer)
-   [Node.js](https://nodejs.org) - on Linux, we recommend using
    [nvm](https://github.com/nvm-sh/nvm) to install an up-to-date version.
-   [Yarn](https://yarnpkg.com) - once Node.js is installed, you can install
    Yarn via `npm install -g yarn`
-   On Linux, you will need at least the `openssl` and `libcurl` packages. On
    Debian-based distributions, you will need to install `libcurl4` or
    `libcurl3` instead of `libcurl`, depending on the age of your distribution.
    For example:

```shell
# Ubuntu 18.04
sudo apt install libcurl4 openssl

# Fedora 32
sudo dnf install libcurl openssl
```

### Installation

We strongly recommend that you install FiftyOne in a
[virtual environment](https://voxel51.com/docs/fiftyone/getting_started/virtualenv.html)
to maintain a clean workspace. The install script is only supported in
POSIX-based systems (e.g. Mac and Linux).

1. Clone the repository:

```shell
git clone --recursive https://github.com/voxel51/fiftyone
cd fiftyone
```

2. Run the installation script:

```shell
bash install.bash
```

**NOTE:** The install script adds to your `nvm` settings in your `~/.bashrc` or
`~/.bash_profile`, which is needed for installing and building the App

**NOTE:** When you pull in new changes to the App, you will need to rebuild it,
which you can do either by rerunning the install script or just running
`yarn build-web` in the `./app` directory.

3. If you want to use the `fiftyone.brain` package, you will need to install it
   separately after installing FiftyOne:

```shell
pip install fiftyone-brain
```

### Customizing your ETA installation

Installing FiftyOne from source includes an
[ETA lite installation](https://github.com/voxel51/eta#lite-installation),
which should be sufficient for most users. If you want a full ETA installation,
or wish to otherwise customize your ETA installation,
[see here](https://github.com/voxel51/eta).

### Developer installation

If you would like to
[contribute to FiftyOne](https://github.com/voxel51/fiftyone/blob/develop/CONTRIBUTING.md),
you should perform a developer installation using the `-d` flag of the install
script:

```shell
bash install.bash -d
```

### Upgrading your source installation

To upgrade an existing source installation to the bleeding edge, simply pull
the latest `develop` branch and rerun the install script:

```shell
git checkout develop
git pull
bash install.bash [-d]
```

### Generating documentation

See the
[docs guide](https://github.com/voxel51/fiftyone/blob/develop/docs/docs_guide.md)
for information on building and contributing to the documentation.

## Uninstallation

You can uninstall FiftyOne as follows:

```shell
pip uninstall fiftyone fiftyone-brain fiftyone-db fiftyone-desktop
```

## Citation

If you use FiftyOne in your research, feel free to cite the project (but only
if you love it 😊):

```bibtex
@article{moore2020fiftyone,
  title={FiftyOne},
  author={Moore, B. E. and Corso, J. J.},
  journal={GitHub. Note: https://github.com/voxel51/fiftyone},
  year={2020}
}
```
