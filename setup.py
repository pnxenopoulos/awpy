from setuptools import setup, find_packages, Extension
import os
import platform
import sys


if sys.platform != 'win32' and platform.python_implementation() == 'CPython':
    try:
        import wheel.bdist_wheel
    except ImportError:
        cmdclass = {}
    else:
        class bdist_wheel(wheel.bdist_wheel.bdist_wheel):
            def finalize_options(self) -> None:
                self.py_limited_api = f'cp3{sys.version_info[1]}'
                super().finalize_options()

        cmdclass = {'bdist_wheel': bdist_wheel}
else:
    cmdclass = {}


def get_version():
    root_dir = os.path.dirname(os.path.abspath(__file__))

    version_file_name = os.path.join(root_dir, "VERSION")

    if os.path.exists(version_file_name):
        with open(version_file_name, "r") as version_file:
            version = version_file.read()
    else:
        raise Exception("VERSION file not found")

    return version

setup(
    name="csgo",
    version=get_version(),
    packages=find_packages(),
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=[
        "pandas>=0.25.3",
        "numpy>=1.18.1",
        "scipy>=1.4.1",
        "matplotlib>=3.1.2",
        "networkx>=2.6.3",
        "textdistance>=4.2.0",
        "imageio>=2.9.0",
        "tqdm>=4.55.2",
    ],
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        "": [
            "data/map/*.png",
            "data/map/*.json",
            "data/nav/*.txt",
            "data/nav/*.csv"
        ]
    },
    # metadata to display on PyPI
    author="Peter Xenopoulos",
    author_email="xenopoulos@nyu.edu",
    description="Counter-Strike: Global Offensive data parsing, analysis and visualization functions",
    keywords="esports sports-analytics csgo counter-strike",
    url="https://github.com/pnxenopoulos/csgo",
    project_urls={
        "Issues": "https://github.com/pnxenopoulos/csgo/issues",
        "Documentation": "https://github.com/pnxenopoulos/csgo/tree/main/docs",
        "Github": "https://github.com/pnxenopoulos/csgo/",
    },
    classifiers=["License :: OSI Approved :: MIT License"],
    build_golang={'root': 'github.com/evilgeniuses/csgo', 'strip': False},
    ext_modules=[
        Extension(
            'csgo.parser.wrapper',
            sources=['csgo/parser/wrapper.go'],
            include_dirs=[f'{os.path.dirname(os.path.realpath(__file__))}/csgo/parser'],
            py_limited_api=True, define_macros=[('Py_LIMITED_API', None)]
        )
    ],
    cmdclass=cmdclass,
    setup_requires=['setuptools-golang'],
)
